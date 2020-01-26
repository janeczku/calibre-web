#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 shavitmichael, OzzieIsaacs
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

import sys
import uuid
from datetime import datetime
from time import gmtime, strftime

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from flask import (
    Blueprint,
    request,
    make_response,
    jsonify,
    json,
    url_for,
    redirect,
)
from flask_login import login_required, current_user
from werkzeug.datastructures import Headers
from sqlalchemy import func
from sqlalchemy.sql.expression import or_
import requests

from . import config, logger, kobo_auth, db, helper, ub
from .services import SyncToken as SyncToken
from .web import download_required

KOBO_FORMATS = {"KEPUB": ["KEPUB"], "EPUB": ["EPUB", "EPUB3"]}
KOBO_STOREAPI_URL = "https://storeapi.kobo.com"

kobo = Blueprint("kobo", __name__, url_prefix="/kobo/<auth_token>")
kobo_auth.disable_failed_auth_redirect_for_blueprint(kobo)
kobo_auth.register_url_value_preprocessor(kobo)

log = logger.create()


def get_store_url_for_current_request():
    # Programmatically modify the current url to point to the official Kobo store
    base, sep, request_path_with_auth_token = request.full_path.rpartition("/kobo/")
    auth_token, sep, request_path = request_path_with_auth_token.rstrip("?").partition(
        "/"
    )
    return KOBO_STOREAPI_URL + "/" + request_path


CONNECTION_SPECIFIC_HEADERS = [
    "connection",
    "content-encoding",
    "content-length",
    "transfer-encoding",
]


def redirect_or_proxy_request():
    if request.method == "GET":
        return redirect(get_store_url_for_current_request(), 307)
    if request.method == "DELETE":
        return make_response(jsonify({}))
    else:
        # The Kobo device turns other request types into GET requests on redirects, so we instead proxy to the Kobo store ourselves.
        outgoing_headers = Headers(request.headers)
        outgoing_headers.remove("Host")
        store_response = requests.request(
            method=request.method,
            url=get_store_url_for_current_request(),
            headers=outgoing_headers,
            data=request.get_data(),
            allow_redirects=False,
        )

        response_headers = store_response.headers
        for header_key in CONNECTION_SPECIFIC_HEADERS:
            response_headers.pop(header_key, default=None)

        return make_response(
            store_response.content, store_response.status_code, response_headers.items()
        )


@kobo.route("/v1/library/sync")
@login_required
@download_required
def HandleSyncRequest():
    sync_token = SyncToken.SyncToken.from_headers(request.headers)
    log.info("Kobo library sync request received.")

    # TODO: Limit the number of books return per sync call, and rely on the sync-continuatation header
    # instead so that the device triggers another sync.

    new_books_last_modified = sync_token.books_last_modified
    new_books_last_created = sync_token.books_last_created
    entitlements = []

    # We reload the book database so that the user get's a fresh view of the library
    # in case of external changes (e.g: adding a book through Calibre).
    db.reconnect_db(config)

    archived_books = (
        ub.session.query(ub.ArchivedBook)
        .filter(ub.ArchivedBook.user_id == int(current_user.id))
        .all()
    )

    # We join-in books that have had their Archived bit recently modified in order to either:
    #   * Restore them to the user's device.
    #   * Delete them from the user's device.
    # (Ideally we would use a join for this logic, however cross-database joins don't look trivial in SqlAlchemy.)
    recently_restored_or_archived_books = []
    archived_book_ids = {}
    new_archived_last_modified = datetime.min
    for archived_book in archived_books:
        if archived_book.last_modified > sync_token.archive_last_modified:
            recently_restored_or_archived_books.append(archived_book.book_id)
        if archived_book.is_archived:
            archived_book_ids[archived_book.book_id] = True
        new_archived_last_modified = max(
            new_archived_last_modified, archived_book.last_modified)

    # sqlite gives unexpected results when performing the last_modified comparison without the datetime cast.
    # It looks like it's treating the db.Books.last_modified field as a string and may fail
    # the comparison because of the +00:00 suffix.
    changed_entries = (
        db.session.query(db.Books)
        .join(db.Data)
        .filter(or_(func.datetime(db.Books.last_modified) > sync_token.books_last_modified,
                    db.Books.id.in_(recently_restored_or_archived_books)))
        .filter(db.Data.format.in_(KOBO_FORMATS))
        .all()
    )
    for book in changed_entries:
        entitlement = {
            "BookEntitlement": create_book_entitlement(book, archived=(book.id in archived_book_ids)),
            "BookMetadata": get_metadata(book),
            "ReadingState": reading_state(book),
        }
        if book.timestamp > sync_token.books_last_created:
            entitlements.append({"NewEntitlement": entitlement})
        else:
            entitlements.append({"ChangedEntitlement": entitlement})

        new_books_last_modified = max(
            book.last_modified, sync_token.books_last_modified
        )
        new_books_last_created = max(book.timestamp, sync_token.books_last_created)

    sync_token.books_last_created = new_books_last_created
    sync_token.books_last_modified = new_books_last_modified
    sync_token.archive_last_modified = new_archived_last_modified

    return generate_sync_response(request, sync_token, entitlements)


def generate_sync_response(request, sync_token, entitlements):
    # We first merge in sync results from the official Kobo store.
    outgoing_headers = Headers(request.headers)
    outgoing_headers.remove("Host")
    sync_token.set_kobo_store_header(outgoing_headers)
    store_response = requests.request(
        method=request.method,
        url=get_store_url_for_current_request(),
        headers=outgoing_headers,
        data=request.get_data(),
    )

    store_entitlements = store_response.json()
    entitlements += store_entitlements
    sync_token.merge_from_store_response(store_response)

    response = make_response(jsonify(entitlements))

    sync_token.to_headers(response.headers)
    try:
        # These headers could probably use some more investigation.
        response.headers["x-kobo-sync"] = store_response.headers["x-kobo-sync"]
        response.headers["x-kobo-sync-mode"] = store_response.headers[
            "x-kobo-sync-mode"
        ]
        response.headers["x-kobo-recent-reads"] = store_response.headers[
            "x-kobo-recent-reads"
        ]
    except KeyError:
        pass

    return response


@kobo.route("/v1/library/<book_uuid>/metadata")
@login_required
@download_required
def HandleMetadataRequest(book_uuid):
    log.info("Kobo library metadata request received for book %s" % book_uuid)
    book = db.session.query(db.Books).filter(db.Books.uuid == book_uuid).first()
    if not book or not book.data:
        log.info(u"Book %s not found in database", book_uuid)
        return redirect_or_proxy_request()

    metadata = get_metadata(book)
    return jsonify([metadata])


def get_download_url_for_book(book, book_format):
    return url_for(
        "web.download_link",
        book_id=book.id,
        book_format=book_format.lower(),
        _external=True,
    )


def create_book_entitlement(book, archived):
    book_uuid = book.uuid
    return {
        "Accessibility": "Full",
        "ActivePeriod": {"From": current_time(),},
        "Created": book.timestamp,
        "CrossRevisionId": book_uuid,
        "Id": book_uuid,
        "IsRemoved": archived,
        "IsHiddenFromArchive": False,
        "IsLocked": False,
        "LastModified": book.last_modified,
        "OriginCategory": "Imported",
        "RevisionId": book_uuid,
        "Status": "Active",
    }


def current_time():
    return strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())


def get_description(book):
    if not book.comments:
        return None
    return book.comments[0].text


# TODO handle multiple authors
def get_author(book):
    if not book.authors:
        return None
    return book.authors[0].name


def get_publisher(book):
    if not book.publishers:
        return None
    return book.publishers[0].name


def get_series(book):
    if not book.series:
        return None
    return book.series[0].name


def get_metadata(book):
    download_urls = []

    for book_data in book.data:
        if book_data.format not in KOBO_FORMATS:
            continue
        for kobo_format in KOBO_FORMATS[book_data.format]:
            download_urls.append(
                {
                    "Format": kobo_format,
                    "Size": book_data.uncompressed_size,
                    "Url": get_download_url_for_book(book, book_data.format),
                    # The Kobo forma accepts platforms: (Generic, Android)
                    "Platform": "Generic",
                    # "DrmType": "None", # Not required
                }
            )

    book_uuid = book.uuid
    metadata = {
        "Categories": ["00000000-0000-0000-0000-000000000001",],
        "Contributors": get_author(book),
        "CoverImageId": book_uuid,
        "CrossRevisionId": book_uuid,
        "CurrentDisplayPrice": {"CurrencyCode": "USD", "TotalAmount": 0},
        "CurrentLoveDisplayPrice": {"TotalAmount": 0},
        "Description": get_description(book),
        "DownloadUrls": download_urls,
        "EntitlementId": book_uuid,
        "ExternalIds": [],
        "Genre": "00000000-0000-0000-0000-000000000001",
        "IsEligibleForKoboLove": False,
        "IsInternetArchive": False,
        "IsPreOrder": False,
        "IsSocialEnabled": True,
        "Language": "en",
        "PhoneticPronunciations": {},
        "PublicationDate": book.pubdate,
        "Publisher": {"Imprint": "", "Name": get_publisher(book),},
        "RevisionId": book_uuid,
        "Title": book.title,
        "WorkId": book_uuid,
    }

    if get_series(book):
        if sys.version_info < (3, 0):
            name = get_series(book).encode("utf-8")
        else:
            name = get_series(book)
        metadata["Series"] = {
            "Name": get_series(book),
            "Number": book.series_index,
            "NumberFloat": float(book.series_index),
            # Get a deterministic id based on the series name.
            "Id": uuid.uuid3(uuid.NAMESPACE_DNS, name),
        }

    return metadata


def reading_state(book):
    # TODO: Implement
    reading_state = {
        # "StatusInfo": {
        #     "LastModified": get_single_cc_value(book, "lastreadtimestamp"),
        #     "Status": get_single_cc_value(book, "reading_status"),
        # }
        # TODO: CurrentBookmark, Location
    }
    return reading_state


@kobo.route("/<book_uuid>/image.jpg")
@login_required
def HandleCoverImageRequest(book_uuid):
    log.debug("Cover request received for book %s" % book_uuid)
    book_cover = helper.get_book_cover_with_uuid(
        book_uuid, use_generic_cover_on_failure=False
    )
    if not book_cover:
        return redirect(get_store_url_for_current_request(), 307)
    return book_cover


@kobo.route("")
def TopLevelEndpoint():
    return make_response(jsonify({}))


@kobo.route("/v1/library/<book_uuid>", methods=["DELETE"])
@login_required
def HandleBookDeletionRequest(book_uuid):
    log.info("Kobo book deletion request received for book %s" % book_uuid)
    book = db.session.query(db.Books).filter(db.Books.uuid == book_uuid).first()
    if not book:
        log.info(u"Book %s not found in database", book_uuid)
        return redirect_or_proxy_request()

    book_id = book.id
    archived_book = (
        ub.session.query(ub.ArchivedBook)
        .filter(ub.ArchivedBook.book_id == book_id)
        .first()
    )
    if not archived_book:
        archived_book = ub.ArchivedBook(user_id=current_user.id, book_id=book_id)
    archived_book.is_archived = True
    archived_book.last_modified = datetime.utcnow()

    ub.session.merge(archived_book)
    ub.session.commit()

    return ("", 204)


# TODO: Implement the following routes
@kobo.route("/v1/library/<book_uuid>/state", methods=["PUT"])
@kobo.route("/v1/library/tags", methods=["POST"])
@kobo.route("/v1/library/tags/<shelf_name>", methods=["POST"])
@kobo.route("/v1/library/tags/<tag_id>", methods=["DELETE"])
def HandleUnimplementedRequest(book_uuid=None, shelf_name=None, tag_id=None):
    return redirect_or_proxy_request()


@kobo.app_errorhandler(404)
def handle_404(err):
    # This handler acts as a catch-all for endpoints that we don't have an interest in
    # implementing (e.g: v1/analytics/gettests, v1/user/recommendations, etc)
    return redirect_or_proxy_request()


@kobo.route("/v1/initialization")
@login_required
def HandleInitRequest():
    outgoing_headers = Headers(request.headers)
    outgoing_headers.remove("Host")
    store_response = requests.request(
        method=request.method,
        url=get_store_url_for_current_request(),
        headers=outgoing_headers,
        data=request.get_data(),
    )

    store_response_json = store_response.json()
    if "Resources" in store_response_json:
        kobo_resources = store_response_json["Resources"]

        calibre_web_url = url_for("web.index", _external=True).strip("/")
        kobo_resources["image_host"] = calibre_web_url
        kobo_resources["image_url_quality_template"] = unquote(url_for("kobo.HandleCoverImageRequest", _external=True,
            auth_token = kobo_auth.get_auth_token(),
            book_uuid="{ImageId}"))
        kobo_resources["image_url_template"] = unquote(url_for("kobo.HandleCoverImageRequest", _external=True,
            auth_token = kobo_auth.get_auth_token(),
            book_uuid="{ImageId}"))

    return make_response(store_response_json, store_response.status_code)
