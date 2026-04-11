# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2024 contributors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
REST API for reading progress sync.

Exposes per-user, per-book reading progress stored by the Kobo sync integration
so that phone-based or other external EPUB readers can share a reading position
with a Kobo device.

Position format
---------------
The ``location`` field carries a KoboSpan position string produced by the Kobo
firmware, stored verbatim during Kobo sync.  A typical value looks like::

    "file:///mnt/onboard/path/to/book.kepub.epub!OEBPS/chapter01.html#koboSpan-id"

The ``location.type`` field will be ``"KoboSpan"`` for positions recorded by a
Kobo device.  External readers that understand KoboSpan can use this directly;
readers that only understand percentage-based progress can use
``progress_percent`` instead.

Endpoints
---------
``GET /api/reading-progress/<book_id>``
    Returns the current reading progress for the authenticated user.

``PUT /api/reading-progress/<book_id>``
    Accepts a JSON body to update reading progress.  All fields are optional;
    omit any field you do not wish to change.  After a successful PUT the Kobo
    device will receive the updated position on its next sync (via
    ``/v1/library/sync`` or ``/v1/library/<uuid>/state``).
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, abort
from .cw_login import current_user
from . import logger, ub, calibre_db, csrf
from .kobo import get_or_create_reading_state, get_read_status_for_kobo, get_ub_read_status
from .usermanagement import user_login_required

log = logger.create()

reading_progress = Blueprint("reading_progress", __name__, url_prefix="/api")


@reading_progress.route("/reading-progress/<int:book_id>", methods=["GET"])
@user_login_required
def get_reading_progress(book_id):
    """Return the stored reading progress for the current user and the given book.

    Response JSON fields:
        book_id                          — integer calibre book ID
        status                           — "ReadyToRead", "Reading", or "Finished"
        last_modified                    — ISO-8601 UTC timestamp of the last state change
        progress_percent                 — float 0-100, overall book progress (may be absent)
        content_source_progress_percent  — float 0-100, in-chapter progress (may be absent)
        location                         — KoboSpan position object (may be absent):
            value  — the raw KoboSpan position string
            type   — position type, typically "KoboSpan"
            source — source href of the spine item containing this span
        statistics                       — reading time object (may be absent):
            spent_reading_minutes        — cumulative minutes spent reading
            remaining_time_minutes       — estimated minutes remaining
    """
    book = calibre_db.get_book(book_id)
    if not book:
        abort(404, description="Book not found")

    kobo_reading_state = get_or_create_reading_state(book_id)
    current_bookmark = kobo_reading_state.current_bookmark
    book_read = kobo_reading_state.book_read_link
    statistics = kobo_reading_state.statistics

    response = {
        "book_id": book_id,
        "status": get_read_status_for_kobo(book_read),
        "last_modified": kobo_reading_state.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")
        if kobo_reading_state.last_modified else None,
    }

    if current_bookmark.progress_percent is not None:
        response["progress_percent"] = current_bookmark.progress_percent
    if current_bookmark.content_source_progress_percent is not None:
        response["content_source_progress_percent"] = current_bookmark.content_source_progress_percent
    if current_bookmark.location_value:
        response["location"] = {
            "value": current_bookmark.location_value,
            "type": current_bookmark.location_type,
            "source": current_bookmark.location_source,
        }
    if statistics:
        stats = {}
        if statistics.spent_reading_minutes is not None:
            stats["spent_reading_minutes"] = statistics.spent_reading_minutes
        if statistics.remaining_time_minutes is not None:
            stats["remaining_time_minutes"] = statistics.remaining_time_minutes
        if stats:
            response["statistics"] = stats

    return jsonify(response)


@csrf.exempt
@reading_progress.route("/reading-progress/<int:book_id>", methods=["PUT"])
@user_login_required
def update_reading_progress(book_id):
    """Update reading progress for the current user and the given book.

    All JSON body fields are optional; only the fields present in the request
    are updated — omitted fields are left unchanged.

    Request JSON fields:
        status                           — "ReadyToRead", "Reading", or "Finished"
        progress_percent                 — float 0-100
        content_source_progress_percent  — float 0-100 (in-chapter progress)
        location                         — KoboSpan position object:
            value  — KoboSpan position string, e.g.
                     "file:///mnt/onboard/...!OEBPS/ch01.html#koboSpan-id"
            type   — position type; use "KoboSpan" for Kobo-compatible positions
            source — source href of the spine item containing this span

    After a successful response the Kobo device will pick up the updated
    position on its next sync.
    """
    book = calibre_db.get_book(book_id)
    if not book:
        abort(404, description="Book not found")

    data = request.get_json(force=True, silent=True)
    if data is None:
        abort(400, description="Request body must be valid JSON")

    kobo_reading_state = get_or_create_reading_state(book_id)
    current_bookmark = kobo_reading_state.current_bookmark
    book_read = kobo_reading_state.book_read_link

    try:
        if "status" in data:
            status_str = data["status"]
            if status_str not in ("ReadyToRead", "Reading", "Finished"):
                abort(400, description="Invalid status value; must be ReadyToRead, Reading, or Finished")
            new_status = get_ub_read_status(status_str)
            if new_status == ub.ReadBook.STATUS_IN_PROGRESS and new_status != book_read.read_status:
                book_read.times_started_reading += 1
                book_read.last_time_started_reading = datetime.now(timezone.utc)
            book_read.read_status = new_status

        if "progress_percent" in data:
            current_bookmark.progress_percent = float(data["progress_percent"])

        if "content_source_progress_percent" in data:
            current_bookmark.content_source_progress_percent = float(data["content_source_progress_percent"])

        location = data.get("location")
        if location is not None:
            current_bookmark.location_value = location.get("value")
            current_bookmark.location_type = location.get("type")
            current_bookmark.location_source = location.get("source")
    except (KeyError, TypeError, ValueError):
        ub.session.rollback()
        abort(400, description="Malformed request data")

    # Advance priority_timestamp so the Kobo device picks up this update on
    # next sync instead of overwriting it with an older position from the device.
    kobo_reading_state.priority_timestamp = datetime.now(timezone.utc)

    ub.session.merge(kobo_reading_state)
    ub.session_commit()

    log.debug("Reading progress updated for book %d by user %s via external API", book_id, current_user.name)
    return jsonify({
        "result": "success",
        "last_modified": kobo_reading_state.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")
        if kobo_reading_state.last_modified else None,
    })
