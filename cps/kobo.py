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

import base64
import datetime
import os
import uuid
from time import gmtime, strftime
import json
from urllib.parse import unquote

from flask import (
    Blueprint,
    request,
    make_response,
    jsonify,
    current_app,
    url_for,
    redirect,
    abort
)
from flask_login import current_user
from werkzeug.datastructures import Headers
from sqlalchemy import func
from sqlalchemy.sql.expression import and_, or_
from sqlalchemy.exc import StatementError
from sqlalchemy.sql import select
import requests


from . import config, logger, kobo_auth, db, calibre_db, helper, shelf as shelf_lib, ub, csrf, kobo_sync_status
from .constants import sqlalchemy_version2
from .helper import get_download_link
from .services import SyncToken as SyncToken
from .web import download_required
from .kobo_auth import requires_kobo_auth, get_auth_token

KOBO_FORMATS = {"KEPUB": ["KEPUB"], "EPUB": ["EPUB3", "EPUB"]}
KOBO_STOREAPI_URL = "https://storeapi.kobo.com"
KOBO_IMAGEHOST_URL = "https://kbimages1-a.akamaihd.net"

SYNC_ITEM_LIMIT = 100

kobo = Blueprint("kobo", __name__, url_prefix="/kobo/<auth_token>")
kobo_auth.disable_failed_auth_redirect_for_blueprint(kobo)
kobo_auth.register_url_value_preprocessor(kobo)

log = logger.create()


def get_store_url_for_current_request():
    # Programmatically modify the current url to point to the official Kobo store
    __, __, request_path_with_auth_token = request.full_path.rpartition("/kobo/")
    __, __, request_path = request_path_with_auth_token.rstrip("?").partition(
        "/"
    )
    return KOBO_STOREAPI_URL + "/" + request_path


CONNECTION_SPECIFIC_HEADERS = [
    "connection",
    "content-encoding",
    "content-length",
    "transfer-encoding",
]


def get_kobo_activated():
    return config.config_kobo_sync


def make_request_to_kobo_store(sync_token=None):
    outgoing_headers = Headers(request.headers)
    outgoing_headers.remove("Host")
    if sync_token:
        sync_token.set_kobo_store_header(outgoing_headers)

    store_response = requests.request(
        method=request.method,
        url=get_store_url_for_current_request(),
        headers=outgoing_headers,
        data=request.get_data(),
        allow_redirects=False,
        timeout=(2, 10)
    )
    log.debug("Content: " + str(store_response.content))
    log.debug("StatusCode: " + str(store_response.status_code))
    return store_response


def redirect_or_proxy_request():
    if config.config_kobo_proxy:
        if request.method == "GET":
            return redirect(get_store_url_for_current_request(), 307)
        else:
            # The Kobo device turns other request types into GET requests on redirects,
            # so we instead proxy to the Kobo store ourselves.
            store_response = make_request_to_kobo_store()

            response_headers = store_response.headers
            for header_key in CONNECTION_SPECIFIC_HEADERS:
                response_headers.pop(header_key, default=None)

            return make_response(
                store_response.content, store_response.status_code, response_headers.items()
            )
    else:
        return make_response(jsonify({}))


def convert_to_kobo_timestamp_string(timestamp):
    try:
        return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    except AttributeError as exc:
        log.debug("Timestamp not valid: {}".format(exc))
        return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")


@kobo.route("/v1/library/sync")
@requires_kobo_auth
@download_required
def HandleSyncRequest():
    sync_token = SyncToken.SyncToken.from_headers(request.headers)
    log.info("Kobo library sync request received.")
    log.debug("SyncToken: {}".format(sync_token))
    if not current_app.wsgi_app.is_proxied:
        log.debug('Kobo: Received unproxied request, changed request port to external server port')

    # if no books synced don't respect sync_token
    if not ub.session.query(ub.KoboSyncedBooks).filter(ub.KoboSyncedBooks.user_id == current_user.id).count():
        sync_token.books_last_modified = datetime.datetime.min
        sync_token.books_last_created = datetime.datetime.min
        sync_token.reading_state_last_modified = datetime.datetime.min

    new_books_last_modified = sync_token.books_last_modified # needed for sync selected shelfs only
    new_books_last_created = sync_token.books_last_created # needed to distinguish between new and changed entitlement
    new_reading_state_last_modified = sync_token.reading_state_last_modified

    new_archived_last_modified = datetime.datetime.min
    sync_results = []

    # We reload the book database so that the user get's a fresh view of the library
    # in case of external changes (e.g: adding a book through Calibre).
    calibre_db.reconnect_db(config, ub.app_DB_path)

    only_kobo_shelves = current_user.kobo_only_shelves_sync

    if only_kobo_shelves:
        if sqlalchemy_version2:
            changed_entries = select(db.Books,
                                     ub.ArchivedBook.last_modified,
                                     ub.BookShelf.date_added,
                                     ub.ArchivedBook.is_archived)
        else:
            changed_entries = calibre_db.session.query(db.Books,
                                                       ub.ArchivedBook.last_modified,
                                                       ub.BookShelf.date_added,
                                                       ub.ArchivedBook.is_archived)
        changed_entries = (changed_entries
                           .join(db.Data).outerjoin(ub.ArchivedBook, and_(db.Books.id == ub.ArchivedBook.book_id,
                                                                          ub.ArchivedBook.user_id == current_user.id))
                           .filter(db.Books.id.notin_(calibre_db.session.query(ub.KoboSyncedBooks.book_id)
                                           .filter(ub.KoboSyncedBooks.user_id == current_user.id)))
                .filter(ub.BookShelf.date_added > sync_token.books_last_modified)
                .filter(db.Data.format.in_(KOBO_FORMATS))
                .filter(calibre_db.common_filters(allow_show_archived=True))
                .order_by(db.Books.id)
                .order_by(ub.ArchivedBook.last_modified)
                .join(ub.BookShelf, db.Books.id == ub.BookShelf.book_id)
                .join(ub.Shelf)
                .filter(ub.Shelf.user_id == current_user.id)
                .filter(ub.Shelf.kobo_sync)
                .distinct()
        )
    else:
        if sqlalchemy_version2:
            changed_entries = select(db.Books, ub.ArchivedBook.last_modified, ub.ArchivedBook.is_archived)
        else:
            changed_entries = calibre_db.session.query(db.Books,
                                                       ub.ArchivedBook.last_modified,
                                                       ub.ArchivedBook.is_archived)
        changed_entries = (changed_entries
                   .join(db.Data).outerjoin(ub.ArchivedBook, and_(db.Books.id == ub.ArchivedBook.book_id,
                                                                  ub.ArchivedBook.user_id == current_user.id))
                   .filter(db.Books.id.notin_(calibre_db.session.query(ub.KoboSyncedBooks.book_id)
                                              .filter(ub.KoboSyncedBooks.user_id == current_user.id)))
                   .filter(calibre_db.common_filters(allow_show_archived=True))
                   .filter(db.Data.format.in_(KOBO_FORMATS))
                   .order_by(db.Books.last_modified)
                   .order_by(db.Books.id)
        )


    reading_states_in_new_entitlements = []
    if sqlalchemy_version2:
        books = calibre_db.session.execute(changed_entries.limit(SYNC_ITEM_LIMIT))
    else:
        books = changed_entries.limit(SYNC_ITEM_LIMIT)
    log.debug("Books to Sync: {}".format(len(books.all())))
    for book in books:
        formats = [data.format for data in book.Books.data]
        if not 'KEPUB' in formats and config.config_kepubifypath and 'EPUB' in formats:
            helper.convert_book_format(book.Books.id, config.config_calibre_dir, 'EPUB', 'KEPUB', current_user.name)

        kobo_reading_state = get_or_create_reading_state(book.Books.id)
        entitlement = {
            "BookEntitlement": create_book_entitlement(book.Books, archived=(book.is_archived == True)),
            "BookMetadata": get_metadata(book.Books),
        }

        if kobo_reading_state.last_modified > sync_token.reading_state_last_modified:
            entitlement["ReadingState"] = get_kobo_reading_state_response(book.Books, kobo_reading_state)
            new_reading_state_last_modified = max(new_reading_state_last_modified, kobo_reading_state.last_modified)
            reading_states_in_new_entitlements.append(book.Books.id)

        ts_created = book.Books.timestamp

        try:
            ts_created = max(ts_created, book.date_added)
        except AttributeError:
            pass

        if ts_created > sync_token.books_last_created:
            sync_results.append({"NewEntitlement": entitlement})
        else:
            sync_results.append({"ChangedEntitlement": entitlement})

        new_books_last_modified = max(
            book.Books.last_modified, new_books_last_modified
        )
        try:
            new_books_last_modified = max(
                new_books_last_modified, book.date_added
            )
        except AttributeError:
            pass

        new_books_last_created = max(ts_created, new_books_last_created)
        kobo_sync_status.add_synced_books(book.Books.id)

    if sqlalchemy_version2:
        max_change = calibre_db.session.execute(changed_entries
                                                .filter(ub.ArchivedBook.is_archived)
                                                .filter(ub.ArchivedBook.user_id == current_user.id)
                                                .order_by(func.datetime(ub.ArchivedBook.last_modified).desc()))\
            .columns(db.Books).first()
    else:
        max_change = changed_entries.from_self().filter(ub.ArchivedBook.is_archived)\
            .filter(ub.ArchivedBook.user_id==current_user.id) \
            .order_by(func.datetime(ub.ArchivedBook.last_modified).desc()).first()

    max_change = max_change.last_modified if max_change else new_archived_last_modified

    new_archived_last_modified = max(new_archived_last_modified, max_change)

    # no. of books returned
    if sqlalchemy_version2:
        entries = calibre_db.session.execute(changed_entries).all()
        book_count = len(entries)
    else:
        book_count = changed_entries.count()
    # last entry:
    cont_sync = bool(book_count)
    log.debug("Remaining books to Sync: {}".format(book_count))
    # generate reading state data
    changed_reading_states = ub.session.query(ub.KoboReadingState)

    if only_kobo_shelves:
        changed_reading_states = changed_reading_states.join(ub.BookShelf,
                                                             ub.KoboReadingState.book_id == ub.BookShelf.book_id)\
            .join(ub.Shelf)\
            .filter(current_user.id == ub.Shelf.user_id)\
            .filter(ub.Shelf.kobo_sync,
                    or_(
                        ub.KoboReadingState.last_modified > sync_token.reading_state_last_modified,
                        func.datetime(ub.BookShelf.date_added) > sync_token.books_last_modified
                    )).distinct()
    else:
        changed_reading_states = changed_reading_states.filter(
            ub.KoboReadingState.last_modified > sync_token.reading_state_last_modified)

    changed_reading_states = changed_reading_states.filter(
        and_(ub.KoboReadingState.user_id == current_user.id,
             ub.KoboReadingState.book_id.notin_(reading_states_in_new_entitlements)))\
        .order_by(ub.KoboReadingState.last_modified)
    cont_sync |= bool(changed_reading_states.count() > SYNC_ITEM_LIMIT)
    for kobo_reading_state in changed_reading_states.limit(SYNC_ITEM_LIMIT).all():
        book = calibre_db.session.query(db.Books).filter(db.Books.id == kobo_reading_state.book_id).one_or_none()
        if book:
            sync_results.append({
                "ChangedReadingState": {
                    "ReadingState": get_kobo_reading_state_response(book, kobo_reading_state)
                }
            })
            new_reading_state_last_modified = max(new_reading_state_last_modified, kobo_reading_state.last_modified)

    sync_shelves(sync_token, sync_results, only_kobo_shelves)

    # update last created timestamp to distinguish between new and changed entitlements
    if not cont_sync:
        sync_token.books_last_created = new_books_last_created
    sync_token.books_last_modified = new_books_last_modified
    sync_token.archive_last_modified = new_archived_last_modified
    sync_token.reading_state_last_modified = new_reading_state_last_modified

    return generate_sync_response(sync_token, sync_results, cont_sync)


def generate_sync_response(sync_token, sync_results, set_cont=False):
    extra_headers = {}
    if config.config_kobo_proxy and not set_cont:
        # Merge in sync results from the official Kobo store.
        try:
            store_response = make_request_to_kobo_store(sync_token)

            store_sync_results = store_response.json()
            sync_results += store_sync_results
            sync_token.merge_from_store_response(store_response)
            extra_headers["x-kobo-sync"] = store_response.headers.get("x-kobo-sync")
            extra_headers["x-kobo-sync-mode"] = store_response.headers.get("x-kobo-sync-mode")
            extra_headers["x-kobo-recent-reads"] = store_response.headers.get("x-kobo-recent-reads")

        except Exception as ex:
            log.error("Failed to receive or parse response from Kobo's sync endpoint: {}".format(ex))
    if set_cont:
        extra_headers["x-kobo-sync"] = "continue"
    sync_token.to_headers(extra_headers)

    # log.debug("Kobo Sync Content: {}".format(sync_results))
    # jsonify decodes the unicode string different to what kobo expects
    response = make_response(json.dumps(sync_results), extra_headers)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


@kobo.route("/v1/library/<book_uuid>/metadata")
@requires_kobo_auth
@download_required
def HandleMetadataRequest(book_uuid):
    if not current_app.wsgi_app.is_proxied:
        log.debug('Kobo: Received unproxied request, changed request port to external server port')
    log.info("Kobo library metadata request received for book %s" % book_uuid)
    book = calibre_db.get_book_by_uuid(book_uuid)
    if not book or not book.data:
        log.info(u"Book %s not found in database", book_uuid)
        return redirect_or_proxy_request()

    metadata = get_metadata(book)
    response = make_response(json.dumps([metadata], ensure_ascii=False))
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


def get_download_url_for_book(book, book_format):
    if not current_app.wsgi_app.is_proxied:
        if ':' in request.host and not request.host.endswith(']'):
            host = "".join(request.host.split(':')[:-1])
        else:
            host = request.host

        return "{url_scheme}://{url_base}:{url_port}/kobo/{auth_token}/download/{book_id}/{book_format}".format(
            url_scheme=request.scheme,
            url_base=host,
            url_port=config.config_external_port,
            auth_token=get_auth_token(),
            book_id=book.id,
            book_format=book_format.lower()
        )
    return url_for(
        "kobo.download_book",
        auth_token=kobo_auth.get_auth_token(),
        book_id=book.id,
        book_format=book_format.lower(),
        _external=True,
    )


def create_book_entitlement(book, archived):
    book_uuid = str(book.uuid)
    return {
        "Accessibility": "Full",
        "ActivePeriod": {"From": convert_to_kobo_timestamp_string(datetime.datetime.now())},
        "Created": convert_to_kobo_timestamp_string(book.timestamp),
        "CrossRevisionId": book_uuid,
        "Id": book_uuid,
        "IsRemoved": archived,
        "IsHiddenFromArchive": False,
        "IsLocked": False,
        "LastModified": convert_to_kobo_timestamp_string(book.last_modified),
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


def get_author(book):
    if not book.authors:
        return {"Contributors": None}
    author_list = []
    autor_roles = []
    for author in book.authors:
        autor_roles.append({"Name":author.name})    #.encode('unicode-escape').decode('latin-1')
        author_list.append(author.name)
    return {"ContributorRoles": autor_roles, "Contributors":author_list}


def get_publisher(book):
    if not book.publishers:
        return None
    return book.publishers[0].name


def get_series(book):
    if not book.series:
        return None
    return book.series[0].name

def get_seriesindex(book):
    return book.series_index or 1


def get_metadata(book):
    download_urls = []
    kepub = [data for data in book.data if data.format == 'KEPUB']

    for book_data in kepub if len(kepub) > 0 else book.data:
        if book_data.format not in KOBO_FORMATS:
            continue
        for kobo_format in KOBO_FORMATS[book_data.format]:
            # log.debug('Id: %s, Format: %s' % (book.id, kobo_format))
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
        "Categories": ["00000000-0000-0000-0000-000000000001", ],
        # "Contributors": get_author(book),
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
        "PublicationDate": convert_to_kobo_timestamp_string(book.pubdate),
        "Publisher": {"Imprint": "", "Name": get_publisher(book),},
        "RevisionId": book_uuid,
        "Title": book.title,
        "WorkId": book_uuid,
    }
    metadata.update(get_author(book))

    if get_series(book):
        name = get_series(book)
        metadata["Series"] = {
            "Name": get_series(book),
            "Number": get_seriesindex(book),        # ToDo Check int() ?
            "NumberFloat": float(get_seriesindex(book)),
            # Get a deterministic id based on the series name.
            "Id": str(uuid.uuid3(uuid.NAMESPACE_DNS, name)),
        }

    return metadata

@csrf.exempt
@kobo.route("/v1/library/tags", methods=["POST", "DELETE"])
@requires_kobo_auth
# Creates a Shelf with the given items, and returns the shelf's uuid.
def HandleTagCreate():
    # catch delete requests, otherwise the are handeld in the book delete handler
    if request.method == "DELETE":
        abort(405)
    name, items = None, None
    try:
        shelf_request = request.json
        name = shelf_request["Name"]
        items = shelf_request["Items"]
        if not name:
            raise TypeError
    except (KeyError, TypeError):
        log.debug("Received malformed v1/library/tags request.")
        abort(400, description="Malformed tags POST request. Data has empty 'Name', missing 'Name' or 'Items' field")

    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.name == name, ub.Shelf.user_id ==
                                              current_user.id).one_or_none()
    if shelf and not shelf_lib.check_shelf_edit_permissions(shelf):
        abort(401, description="User is unauthaurized to create shelf.")

    if not shelf:
        shelf = ub.Shelf(user_id=current_user.id, name=name, uuid=str(uuid.uuid4()))
        ub.session.add(shelf)

    items_unknown_to_calibre = add_items_to_shelf(items, shelf)
    if items_unknown_to_calibre:
        log.debug("Received request to add unknown books to a collection. Silently ignoring items.")
    ub.session_commit()
    return make_response(jsonify(str(shelf.uuid)), 201)


@csrf.exempt
@kobo.route("/v1/library/tags/<tag_id>", methods=["DELETE", "PUT"])
@requires_kobo_auth
def HandleTagUpdate(tag_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.uuid == tag_id,
                                              ub.Shelf.user_id == current_user.id).one_or_none()
    if not shelf:
        log.debug("Received Kobo tag update request on a collection unknown to CalibreWeb")
        if config.config_kobo_proxy:
            return redirect_or_proxy_request()
        else:
            abort(404, description="Collection isn't known to CalibreWeb")

    if not shelf_lib.check_shelf_edit_permissions(shelf):
        abort(401, description="User is unauthaurized to edit shelf.")

    if request.method == "DELETE":
        shelf_lib.delete_shelf_helper(shelf)
    else:
        name = None
        try:
            shelf_request = request.json
            name = shelf_request["Name"]
        except (KeyError, TypeError):
            log.debug("Received malformed v1/library/tags rename request.")
            abort(400, description="Malformed tags POST request. Data is missing 'Name' field")

        shelf.name = name
        ub.session.merge(shelf)
        ub.session_commit()
    return make_response(' ', 200)


# Adds items to the given shelf.
def add_items_to_shelf(items, shelf):
    book_ids_already_in_shelf = set([book_shelf.book_id for book_shelf in shelf.books])
    items_unknown_to_calibre = []
    for item in items:
        try:
            if item["Type"] != "ProductRevisionTagItem":
                items_unknown_to_calibre.append(item)
                continue

            book = calibre_db.get_book_by_uuid(item["RevisionId"])
            if not book:
                items_unknown_to_calibre.append(item)
                continue

            book_id = book.id
            if book_id not in book_ids_already_in_shelf:
                shelf.books.append(ub.BookShelf(book_id=book_id))
        except KeyError:
            items_unknown_to_calibre.append(item)
    return items_unknown_to_calibre


@csrf.exempt
@kobo.route("/v1/library/tags/<tag_id>/items", methods=["POST"])
@requires_kobo_auth
def HandleTagAddItem(tag_id):
    items = None
    try:
        tag_request = request.json
        items = tag_request["Items"]
    except (KeyError, TypeError):
        log.debug("Received malformed v1/library/tags/<tag_id>/items/delete request.")
        abort(400, description="Malformed tags POST request. Data is missing 'Items' field")

    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.uuid == tag_id,
                                              ub.Shelf.user_id == current_user.id).one_or_none()
    if not shelf:
        log.debug("Received Kobo request on a collection unknown to CalibreWeb")
        abort(404, description="Collection isn't known to CalibreWeb")

    if not shelf_lib.check_shelf_edit_permissions(shelf):
        abort(401, description="User is unauthaurized to edit shelf.")

    items_unknown_to_calibre = add_items_to_shelf(items, shelf)
    if items_unknown_to_calibre:
        log.debug("Received request to add an unknown book to a collection. Silently ignoring item.")

    ub.session.merge(shelf)
    ub.session_commit()
    return make_response('', 201)


@csrf.exempt
@kobo.route("/v1/library/tags/<tag_id>/items/delete", methods=["POST"])
@requires_kobo_auth
def HandleTagRemoveItem(tag_id):
    items = None
    try:
        tag_request = request.json
        items = tag_request["Items"]
    except (KeyError, TypeError):
        log.debug("Received malformed v1/library/tags/<tag_id>/items/delete request.")
        abort(400, description="Malformed tags POST request. Data is missing 'Items' field")

    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.uuid == tag_id,
                                              ub.Shelf.user_id == current_user.id).one_or_none()
    if not shelf:
        log.debug(
            "Received a request to remove an item from a Collection unknown to CalibreWeb.")
        abort(404, description="Collection isn't known to CalibreWeb")

    if not shelf_lib.check_shelf_edit_permissions(shelf):
        abort(401, description="User is unauthaurized to edit shelf.")

    items_unknown_to_calibre = []
    for item in items:
        try:
            if item["Type"] != "ProductRevisionTagItem":
                items_unknown_to_calibre.append(item)
                continue

            book = calibre_db.get_book_by_uuid(item["RevisionId"])
            if not book:
                items_unknown_to_calibre.append(item)
                continue

            shelf.books.filter(ub.BookShelf.book_id == book.id).delete()
        except KeyError:
            items_unknown_to_calibre.append(item)
    ub.session_commit()

    if items_unknown_to_calibre:
        log.debug("Received request to remove an unknown book to a collecition. Silently ignoring item.")

    return make_response('', 200)


# Add new, changed, or deleted shelves to the sync_results.
# Note: Public shelves that aren't owned by the user aren't supported.
def sync_shelves(sync_token, sync_results, only_kobo_shelves=False):
    new_tags_last_modified = sync_token.tags_last_modified
    # transmit all archived shelfs independent of last sync (why should this matter?)
    for shelf in ub.session.query(ub.ShelfArchive).filter(ub.ShelfArchive.user_id == current_user.id):
        new_tags_last_modified = max(shelf.last_modified, new_tags_last_modified)
        sync_results.append({
            "DeletedTag": {
                "Tag": {
                    "Id": shelf.uuid,
                    "LastModified": convert_to_kobo_timestamp_string(shelf.last_modified)
                }
            }
        })
        ub.session.delete(shelf)
        ub.session_commit()

    extra_filters = []
    if only_kobo_shelves:
        for shelf in ub.session.query(ub.Shelf).filter(
            func.datetime(ub.Shelf.last_modified) > sync_token.tags_last_modified,
            ub.Shelf.user_id == current_user.id,
            not ub.Shelf.kobo_sync
        ):
            sync_results.append({
                "DeletedTag": {
                    "Tag": {
                        "Id": shelf.uuid,
                        "LastModified": convert_to_kobo_timestamp_string(shelf.last_modified)
                    }
                }
            })
        extra_filters.append(ub.Shelf.kobo_sync)

    if sqlalchemy_version2:
        shelflist = ub.session.execute(select(ub.Shelf).outerjoin(ub.BookShelf).filter(
            or_(func.datetime(ub.Shelf.last_modified) > sync_token.tags_last_modified,
                func.datetime(ub.BookShelf.date_added) > sync_token.tags_last_modified),
            ub.Shelf.user_id == current_user.id,
            *extra_filters
        ).distinct().order_by(func.datetime(ub.Shelf.last_modified).asc())).columns(ub.Shelf)
    else:
        shelflist = ub.session.query(ub.Shelf).outerjoin(ub.BookShelf).filter(
            or_(func.datetime(ub.Shelf.last_modified) > sync_token.tags_last_modified,
                func.datetime(ub.BookShelf.date_added) > sync_token.tags_last_modified),
            ub.Shelf.user_id == current_user.id,
            *extra_filters
        ).distinct().order_by(func.datetime(ub.Shelf.last_modified).asc())


    for shelf in shelflist:
        if not shelf_lib.check_shelf_view_permissions(shelf):
            continue

        new_tags_last_modified = max(shelf.last_modified, new_tags_last_modified)

        tag = create_kobo_tag(shelf)
        if not tag:
            continue

        if shelf.created > sync_token.tags_last_modified:
            sync_results.append({
                "NewTag": tag
            })
        else:
            sync_results.append({
                "ChangedTag": tag
            })
    sync_token.tags_last_modified = new_tags_last_modified
    ub.session_commit()


# Creates a Kobo "Tag" object from a ub.Shelf object
def create_kobo_tag(shelf):
    tag = {
        "Created": convert_to_kobo_timestamp_string(shelf.created),
        "Id": shelf.uuid,
        "Items": [],
        "LastModified": convert_to_kobo_timestamp_string(shelf.last_modified),
        "Name": shelf.name,
        "Type": "UserTag"
    }
    for book_shelf in shelf.books:
        book = calibre_db.get_book(book_shelf.book_id)
        if not book:
            log.info(u"Book (id: %s) in BookShelf (id: %s) not found in book database",  book_shelf.book_id, shelf.id)
            continue
        tag["Items"].append(
            {
                "RevisionId": book.uuid,
                "Type": "ProductRevisionTagItem"
            }
        )
    return {"Tag": tag}

@csrf.exempt
@kobo.route("/v1/library/<book_uuid>/state", methods=["GET", "PUT"])
@requires_kobo_auth
def HandleStateRequest(book_uuid):
    book = calibre_db.get_book_by_uuid(book_uuid)
    if not book or not book.data:
        log.info(u"Book %s not found in database", book_uuid)
        return redirect_or_proxy_request()

    kobo_reading_state = get_or_create_reading_state(book.id)

    if request.method == "GET":
        return jsonify([get_kobo_reading_state_response(book, kobo_reading_state)])
    else:
        update_results_response = {"EntitlementId": book_uuid}

        try:
            request_data = request.json
            request_reading_state = request_data["ReadingStates"][0]

            request_bookmark = request_reading_state["CurrentBookmark"]
            if request_bookmark:
                current_bookmark = kobo_reading_state.current_bookmark
                current_bookmark.progress_percent = request_bookmark["ProgressPercent"]
                current_bookmark.content_source_progress_percent = request_bookmark["ContentSourceProgressPercent"]
                location = request_bookmark["Location"]
                if location:
                    current_bookmark.location_value = location["Value"]
                    current_bookmark.location_type = location["Type"]
                    current_bookmark.location_source = location["Source"]
                update_results_response["CurrentBookmarkResult"] = {"Result": "Success"}

            request_statistics = request_reading_state["Statistics"]
            if request_statistics:
                statistics = kobo_reading_state.statistics
                statistics.spent_reading_minutes = int(request_statistics["SpentReadingMinutes"])
                statistics.remaining_time_minutes = int(request_statistics["RemainingTimeMinutes"])
                update_results_response["StatisticsResult"] = {"Result": "Success"}

            request_status_info = request_reading_state["StatusInfo"]
            if request_status_info:
                book_read = kobo_reading_state.book_read_link
                new_book_read_status = get_ub_read_status(request_status_info["Status"])
                if new_book_read_status == ub.ReadBook.STATUS_IN_PROGRESS \
                    and new_book_read_status != book_read.read_status:
                    book_read.times_started_reading += 1
                    book_read.last_time_started_reading = datetime.datetime.utcnow()
                book_read.read_status = new_book_read_status
                update_results_response["StatusInfoResult"] = {"Result": "Success"}
        except (KeyError, TypeError, ValueError, StatementError):
            log.debug("Received malformed v1/library/<book_uuid>/state request.")
            ub.session.rollback()
            abort(400, description="Malformed request data is missing 'ReadingStates' key")

        ub.session.merge(kobo_reading_state)
        ub.session_commit()
        return jsonify({
            "RequestResult": "Success",
            "UpdateResults": [update_results_response],
        })


def get_read_status_for_kobo(ub_book_read):
    enum_to_string_map = {
        None: "ReadyToRead",
        ub.ReadBook.STATUS_UNREAD: "ReadyToRead",
        ub.ReadBook.STATUS_FINISHED: "Finished",
        ub.ReadBook.STATUS_IN_PROGRESS: "Reading",
    }
    return enum_to_string_map[ub_book_read.read_status]


def get_ub_read_status(kobo_read_status):
    string_to_enum_map = {
        None: None,
        "ReadyToRead": ub.ReadBook.STATUS_UNREAD,
        "Finished": ub.ReadBook.STATUS_FINISHED,
        "Reading": ub.ReadBook.STATUS_IN_PROGRESS,
    }
    return string_to_enum_map[kobo_read_status]


def get_or_create_reading_state(book_id):
    book_read = ub.session.query(ub.ReadBook).filter(ub.ReadBook.book_id == book_id,
                                                          ub.ReadBook.user_id == int(current_user.id)).one_or_none()
    if not book_read:
        book_read = ub.ReadBook(user_id=current_user.id, book_id=book_id)
    if not book_read.kobo_reading_state:
        kobo_reading_state = ub.KoboReadingState(user_id=book_read.user_id, book_id=book_id)
        kobo_reading_state.current_bookmark = ub.KoboBookmark()
        kobo_reading_state.statistics = ub.KoboStatistics()
        book_read.kobo_reading_state = kobo_reading_state
    ub.session.add(book_read)
    ub.session_commit()
    return book_read.kobo_reading_state


def get_kobo_reading_state_response(book, kobo_reading_state):
    return {
        "EntitlementId": book.uuid,
        "Created": convert_to_kobo_timestamp_string(book.timestamp),
        "LastModified": convert_to_kobo_timestamp_string(kobo_reading_state.last_modified),
        # AFAICT PriorityTimestamp is always equal to LastModified.
        "PriorityTimestamp": convert_to_kobo_timestamp_string(kobo_reading_state.priority_timestamp),
        "StatusInfo": get_status_info_response(kobo_reading_state.book_read_link),
        "Statistics": get_statistics_response(kobo_reading_state.statistics),
        "CurrentBookmark": get_current_bookmark_response(kobo_reading_state.current_bookmark),
    }


def get_status_info_response(book_read):
    resp = {
        "LastModified": convert_to_kobo_timestamp_string(book_read.last_modified),
        "Status": get_read_status_for_kobo(book_read),
        "TimesStartedReading": book_read.times_started_reading,
    }
    if book_read.last_time_started_reading:
        resp["LastTimeStartedReading"] = convert_to_kobo_timestamp_string(book_read.last_time_started_reading)
    return resp


def get_statistics_response(statistics):
    resp = {
        "LastModified": convert_to_kobo_timestamp_string(statistics.last_modified),
    }
    if statistics.spent_reading_minutes:
        resp["SpentReadingMinutes"] = statistics.spent_reading_minutes
    if statistics.remaining_time_minutes:
        resp["RemainingTimeMinutes"] = statistics.remaining_time_minutes
    return resp


def get_current_bookmark_response(current_bookmark):
    resp = {
        "LastModified": convert_to_kobo_timestamp_string(current_bookmark.last_modified),
    }
    if current_bookmark.progress_percent:
        resp["ProgressPercent"] = current_bookmark.progress_percent
    if current_bookmark.content_source_progress_percent:
        resp["ContentSourceProgressPercent"] = current_bookmark.content_source_progress_percent
    if current_bookmark.location_value:
        resp["Location"] = {
            "Value": current_bookmark.location_value,
            "Type": current_bookmark.location_type,
            "Source": current_bookmark.location_source,
        }
    return resp

@kobo.route("/<book_uuid>/<width>/<height>/<isGreyscale>/image.jpg", defaults={'Quality': ""})
@kobo.route("/<book_uuid>/<width>/<height>/<Quality>/<isGreyscale>/image.jpg")
@requires_kobo_auth
def HandleCoverImageRequest(book_uuid, width, height,Quality, isGreyscale):
    book_cover = helper.get_book_cover_with_uuid(
        book_uuid, use_generic_cover_on_failure=False
    )
    if not book_cover:
        if config.config_kobo_proxy:
            log.debug("Cover for unknown book: %s proxied to kobo" % book_uuid)
            return redirect(KOBO_IMAGEHOST_URL +
                            "/{book_uuid}/{width}/{height}/false/image.jpg".format(book_uuid=book_uuid,
                                                                                   width=width,
                                                                                   height=height), 307)
        else:
            log.debug("Cover for unknown book: %s requested" % book_uuid)
            # additional proxy request make no sense, -> direct return
            return make_response(jsonify({}))
    log.debug("Cover request received for book %s" % book_uuid)
    return book_cover


@kobo.route("")
def TopLevelEndpoint():
    return make_response(jsonify({}))


@csrf.exempt
@kobo.route("/v1/library/<book_uuid>", methods=["DELETE"])
@requires_kobo_auth
def HandleBookDeletionRequest(book_uuid):
    log.info("Kobo book deletion request received for book %s" % book_uuid)
    book = calibre_db.get_book_by_uuid(book_uuid)
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
    archived_book.last_modified = datetime.datetime.utcnow()

    ub.session.merge(archived_book)
    ub.session_commit()
    if archived_book.is_archived:
        kobo_sync_status.remove_synced_book(book_id)
    return "", 204


# TODO: Implement the following routes
@csrf.exempt
@kobo.route("/v1/library/<dummy>", methods=["DELETE", "GET"])
def HandleUnimplementedRequest(dummy=None):
    log.debug("Unimplemented Library Request received: %s", request.base_url)
    return redirect_or_proxy_request()


# TODO: Implement the following routes
@csrf.exempt
@kobo.route("/v1/user/loyalty/<dummy>", methods=["GET", "POST"])
@kobo.route("/v1/user/profile", methods=["GET", "POST"])
@kobo.route("/v1/user/wishlist", methods=["GET", "POST"])
@kobo.route("/v1/user/recommendations", methods=["GET", "POST"])
@kobo.route("/v1/analytics/<dummy>", methods=["GET", "POST"])
def HandleUserRequest(dummy=None):
    log.debug("Unimplemented User Request received: %s", request.base_url)
    return redirect_or_proxy_request()


@csrf.exempt
@kobo.route("/v1/user/loyalty/benefits", methods=["GET"])
def handle_benefits():
    if config.config_kobo_proxy:
        return redirect_or_proxy_request()
    else:
        return make_response(jsonify({"Benefits": {}}))


@csrf.exempt
@kobo.route("/v1/analytics/gettests", methods=["GET", "POST"])
def handle_getests():
    if config.config_kobo_proxy:
        return redirect_or_proxy_request()
    else:
        testkey = request.headers.get("X-Kobo-userkey","")
        return make_response(jsonify({"Result": "Success", "TestKey":testkey, "Tests": {}}))


@csrf.exempt
@kobo.route("/v1/products/<dummy>/prices", methods=["GET", "POST"])
@kobo.route("/v1/products/<dummy>/recommendations", methods=["GET", "POST"])
@kobo.route("/v1/products/<dummy>/nextread", methods=["GET", "POST"])
@kobo.route("/v1/products/<dummy>/reviews", methods=["GET", "POST"])
@kobo.route("/v1/products/featured/<dummy>", methods=["GET", "POST"])
@kobo.route("/v1/products/featured/", methods=["GET", "POST"])
@kobo.route("/v1/products/books/external/<dummy>", methods=["GET", "POST"])
@kobo.route("/v1/products/books/series/<dummy>", methods=["GET", "POST"])
@kobo.route("/v1/products/books/<dummy>", methods=["GET", "POST"])
@kobo.route("/v1/products/books/<dummy>/", methods=["GET", "POST"])
@kobo.route("/v1/products/dailydeal", methods=["GET", "POST"])
@kobo.route("/v1/products/deals", methods=["GET", "POST"])
@kobo.route("/v1/products", methods=["GET", "POST"])
@kobo.route("/v1/affiliate", methods=["GET", "POST"])
@kobo.route("/v1/deals", methods=["GET", "POST"])
def HandleProductsRequest(dummy=None):
    log.debug("Unimplemented Products Request received: %s", request.base_url)
    return redirect_or_proxy_request()


def make_calibre_web_auth_response():
    # As described in kobo_auth.py, CalibreWeb doesn't make use practical use of this auth/device API call for
    # authentation (nor for authorization). We return a dummy response just to keep the device happy.
    content = request.get_json()
    AccessToken = base64.b64encode(os.urandom(24)).decode('utf-8')
    RefreshToken = base64.b64encode(os.urandom(24)).decode('utf-8')
    return  make_response(
        jsonify(
            {
                "AccessToken": AccessToken,
                "RefreshToken": RefreshToken,
                "TokenType": "Bearer",
                "TrackingId": str(uuid.uuid4()),
                "UserKey": content['UserKey'],
            }
        )
    )


@csrf.exempt
@kobo.route("/v1/auth/device", methods=["POST"])
@requires_kobo_auth
def HandleAuthRequest():
    log.debug('Kobo Auth request')
    if config.config_kobo_proxy:
        try:
            return redirect_or_proxy_request()
        except Exception:
            log.error("Failed to receive or parse response from Kobo's auth endpoint. Falling back to un-proxied mode.")
    return make_calibre_web_auth_response()


@kobo.route("/v1/initialization")
@requires_kobo_auth
def HandleInitRequest():
    log.info('Init')

    kobo_resources = None
    if config.config_kobo_proxy:
        try:
            store_response = make_request_to_kobo_store()
            store_response_json = store_response.json()
            if "Resources" in store_response_json:
                kobo_resources = store_response_json["Resources"]
        except Exception:
            log.error("Failed to receive or parse response from Kobo's init endpoint. Falling back to un-proxied mode.")
    if not kobo_resources:
        kobo_resources = NATIVE_KOBO_RESOURCES()

    if not current_app.wsgi_app.is_proxied:
        log.debug('Kobo: Received unproxied request, changed request port to external server port')
        if ':' in request.host and not request.host.endswith(']'):
            host = "".join(request.host.split(':')[:-1])
        else:
            host = request.host
        calibre_web_url = "{url_scheme}://{url_base}:{url_port}".format(
            url_scheme=request.scheme,
            url_base=host,
            url_port=config.config_external_port
        )
        log.debug('Kobo: Received unproxied request, changed request url to %s', calibre_web_url)
        kobo_resources["image_host"] = calibre_web_url
        kobo_resources["image_url_quality_template"] = unquote(calibre_web_url +
                                                               url_for("kobo.HandleCoverImageRequest",
                                                                       auth_token=kobo_auth.get_auth_token(),
                                                                       book_uuid="{ImageId}",
                                                                       width="{width}",
                                                                       height="{height}",
                                                                       Quality='{Quality}',
                                                                       isGreyscale='isGreyscale'))
        kobo_resources["image_url_template"] = unquote(calibre_web_url +
                                                       url_for("kobo.HandleCoverImageRequest",
                                                               auth_token=kobo_auth.get_auth_token(),
                                                               book_uuid="{ImageId}",
                                                               width="{width}",
                                                               height="{height}",
                                                               isGreyscale='false'))
    else:
        kobo_resources["image_host"] = url_for("web.index", _external=True).strip("/")
        kobo_resources["image_url_quality_template"] = unquote(url_for("kobo.HandleCoverImageRequest",
                                                                       auth_token=kobo_auth.get_auth_token(),
                                                                       book_uuid="{ImageId}",
                                                                       width="{width}",
                                                                       height="{height}",
                                                                       Quality='{Quality}',
                                                                       isGreyscale='isGreyscale',
                                                                       _external=True))
        kobo_resources["image_url_template"] = unquote(url_for("kobo.HandleCoverImageRequest",
                                                               auth_token=kobo_auth.get_auth_token(),
                                                               book_uuid="{ImageId}",
                                                               width="{width}",
                                                               height="{height}",
                                                               isGreyscale='false',
                                                               _external=True))

    response = make_response(jsonify({"Resources": kobo_resources}))
    response.headers["x-kobo-apitoken"] = "e30="

    return response


@kobo.route("/download/<book_id>/<book_format>")
@requires_kobo_auth
@download_required
def download_book(book_id, book_format):
    return get_download_link(book_id, book_format, "kobo")


def NATIVE_KOBO_RESOURCES():
    return {
        "account_page": "https://secure.kobobooks.com/profile",
        "account_page_rakuten": "https://my.rakuten.co.jp/",
        "add_entitlement": "https://storeapi.kobo.com/v1/library/{RevisionIds}",
        "affiliaterequest": "https://storeapi.kobo.com/v1/affiliate",
        "audiobook_subscription_orange_deal_inclusion_url": "https://authorize.kobo.com/inclusion",
        "authorproduct_recommendations": "https://storeapi.kobo.com/v1/products/books/authors/recommendations",
        "autocomplete": "https://storeapi.kobo.com/v1/products/autocomplete",
        "blackstone_header": {"key": "x-amz-request-payer", "value": "requester"},
        "book": "https://storeapi.kobo.com/v1/products/books/{ProductId}",
        "book_detail_page": "https://store.kobobooks.com/{culture}/ebook/{slug}",
        "book_detail_page_rakuten": "https://books.rakuten.co.jp/rk/{crossrevisionid}",
        "book_landing_page": "https://store.kobobooks.com/ebooks",
        "book_subscription": "https://storeapi.kobo.com/v1/products/books/subscriptions",
        "categories": "https://storeapi.kobo.com/v1/categories",
        "categories_page": "https://store.kobobooks.com/ebooks/categories",
        "category": "https://storeapi.kobo.com/v1/categories/{CategoryId}",
        "category_featured_lists": "https://storeapi.kobo.com/v1/categories/{CategoryId}/featured",
        "category_products": "https://storeapi.kobo.com/v1/categories/{CategoryId}/products",
        "checkout_borrowed_book": "https://storeapi.kobo.com/v1/library/borrow",
        "configuration_data": "https://storeapi.kobo.com/v1/configuration",
        "content_access_book": "https://storeapi.kobo.com/v1/products/books/{ProductId}/access",
        "customer_care_live_chat": "https://v2.zopim.com/widget/livechat.html?key=Y6gwUmnu4OATxN3Tli4Av9bYN319BTdO",
        "daily_deal": "https://storeapi.kobo.com/v1/products/dailydeal",
        "deals": "https://storeapi.kobo.com/v1/deals",
        "delete_entitlement": "https://storeapi.kobo.com/v1/library/{Ids}",
        "delete_tag": "https://storeapi.kobo.com/v1/library/tags/{TagId}",
        "delete_tag_items": "https://storeapi.kobo.com/v1/library/tags/{TagId}/items/delete",
        "device_auth": "https://storeapi.kobo.com/v1/auth/device",
        "device_refresh": "https://storeapi.kobo.com/v1/auth/refresh",
        "dictionary_host": "https://kbdownload1-a.akamaihd.net",
        "discovery_host": "https://discovery.kobobooks.com",
        "eula_page": "https://www.kobo.com/termsofuse?style=onestore",
        "exchange_auth": "https://storeapi.kobo.com/v1/auth/exchange",
        "external_book": "https://storeapi.kobo.com/v1/products/books/external/{Ids}",
        "facebook_sso_page": "https://authorize.kobo.com/signin/provider/Facebook/login?returnUrl=http://store.kobobooks.com/",
        "featured_list": "https://storeapi.kobo.com/v1/products/featured/{FeaturedListId}",
        "featured_lists": "https://storeapi.kobo.com/v1/products/featured",
        "free_books_page": {
            "EN": "https://www.kobo.com/{region}/{language}/p/free-ebooks",
            "FR": "https://www.kobo.com/{region}/{language}/p/livres-gratuits",
            "IT": "https://www.kobo.com/{region}/{language}/p/libri-gratuiti",
            "NL": "https://www.kobo.com/{region}/{language}/List/bekijk-het-overzicht-van-gratis-ebooks/QpkkVWnUw8sxmgjSlCbJRg",
            "PT": "https://www.kobo.com/{region}/{language}/p/livros-gratis",
        },
        "fte_feedback": "https://storeapi.kobo.com/v1/products/ftefeedback",
        "get_tests_request": "https://storeapi.kobo.com/v1/analytics/gettests",
        "giftcard_epd_redeem_url": "https://www.kobo.com/{storefront}/{language}/redeem-ereader",
        "giftcard_redeem_url": "https://www.kobo.com/{storefront}/{language}/redeem",
        "help_page": "https://www.kobo.com/help",
        "kobo_audiobooks_enabled": "False",
        "kobo_audiobooks_orange_deal_enabled": "False",
        "kobo_audiobooks_subscriptions_enabled": "False",
        "kobo_nativeborrow_enabled": "True",
        "kobo_onestorelibrary_enabled": "False",
        "kobo_redeem_enabled": "True",
        "kobo_shelfie_enabled": "False",
        "kobo_subscriptions_enabled": "False",
        "kobo_superpoints_enabled": "False",
        "kobo_wishlist_enabled": "True",
        "library_book": "https://storeapi.kobo.com/v1/user/library/books/{LibraryItemId}",
        "library_items": "https://storeapi.kobo.com/v1/user/library",
        "library_metadata": "https://storeapi.kobo.com/v1/library/{Ids}/metadata",
        "library_prices": "https://storeapi.kobo.com/v1/user/library/previews/prices",
        "library_stack": "https://storeapi.kobo.com/v1/user/library/stacks/{LibraryItemId}",
        "library_sync": "https://storeapi.kobo.com/v1/library/sync",
        "love_dashboard_page": "https://store.kobobooks.com/{culture}/kobosuperpoints",
        "love_points_redemption_page": "https://store.kobobooks.com/{culture}/KoboSuperPointsRedemption?productId={ProductId}",
        "magazine_landing_page": "https://store.kobobooks.com/emagazines",
        "notifications_registration_issue": "https://storeapi.kobo.com/v1/notifications/registration",
        "oauth_host": "https://oauth.kobo.com",
        "overdrive_account": "https://auth.overdrive.com/account",
        "overdrive_library": "https://{libraryKey}.auth.overdrive.com/library",
        "overdrive_library_finder_host": "https://libraryfinder.api.overdrive.com",
        "overdrive_thunder_host": "https://thunder.api.overdrive.com",
        "password_retrieval_page": "https://www.kobobooks.com/passwordretrieval.html",
        "post_analytics_event": "https://storeapi.kobo.com/v1/analytics/event",
        "privacy_page": "https://www.kobo.com/privacypolicy?style=onestore",
        "product_nextread": "https://storeapi.kobo.com/v1/products/{ProductIds}/nextread",
        "product_prices": "https://storeapi.kobo.com/v1/products/{ProductIds}/prices",
        "product_recommendations": "https://storeapi.kobo.com/v1/products/{ProductId}/recommendations",
        "product_reviews": "https://storeapi.kobo.com/v1/products/{ProductIds}/reviews",
        "products": "https://storeapi.kobo.com/v1/products",
        "provider_external_sign_in_page": "https://authorize.kobo.com/ExternalSignIn/{providerName}?returnUrl=http://store.kobobooks.com/",
        "purchase_buy": "https://www.kobo.com/checkout/createpurchase/",
        "purchase_buy_templated": "https://www.kobo.com/{culture}/checkout/createpurchase/{ProductId}",
        "quickbuy_checkout": "https://storeapi.kobo.com/v1/store/quickbuy/{PurchaseId}/checkout",
        "quickbuy_create": "https://storeapi.kobo.com/v1/store/quickbuy/purchase",
        "rating": "https://storeapi.kobo.com/v1/products/{ProductId}/rating/{Rating}",
        "reading_state": "https://storeapi.kobo.com/v1/library/{Ids}/state",
        "redeem_interstitial_page": "https://store.kobobooks.com",
        "registration_page": "https://authorize.kobo.com/signup?returnUrl=http://store.kobobooks.com/",
        "related_items": "https://storeapi.kobo.com/v1/products/{Id}/related",
        "remaining_book_series": "https://storeapi.kobo.com/v1/products/books/series/{SeriesId}",
        "rename_tag": "https://storeapi.kobo.com/v1/library/tags/{TagId}",
        "review": "https://storeapi.kobo.com/v1/products/reviews/{ReviewId}",
        "review_sentiment": "https://storeapi.kobo.com/v1/products/reviews/{ReviewId}/sentiment/{Sentiment}",
        "shelfie_recommendations": "https://storeapi.kobo.com/v1/user/recommendations/shelfie",
        "sign_in_page": "https://authorize.kobo.com/signin?returnUrl=http://store.kobobooks.com/",
        "social_authorization_host": "https://social.kobobooks.com:8443",
        "social_host": "https://social.kobobooks.com",
        "stacks_host_productId": "https://store.kobobooks.com/collections/byproductid/",
        "store_home": "www.kobo.com/{region}/{language}",
        "store_host": "store.kobobooks.com",
        "store_newreleases": "https://store.kobobooks.com/{culture}/List/new-releases/961XUjtsU0qxkFItWOutGA",
        "store_search": "https://store.kobobooks.com/{culture}/Search?Query={query}",
        "store_top50": "https://store.kobobooks.com/{culture}/ebooks/Top",
        "tag_items": "https://storeapi.kobo.com/v1/library/tags/{TagId}/Items",
        "tags": "https://storeapi.kobo.com/v1/library/tags",
        "taste_profile": "https://storeapi.kobo.com/v1/products/tasteprofile",
        "update_accessibility_to_preview": "https://storeapi.kobo.com/v1/library/{EntitlementIds}/preview",
        "use_one_store": "False",
        "user_loyalty_benefits": "https://storeapi.kobo.com/v1/user/loyalty/benefits",
        "user_platform": "https://storeapi.kobo.com/v1/user/platform",
        "user_profile": "https://storeapi.kobo.com/v1/user/profile",
        "user_ratings": "https://storeapi.kobo.com/v1/user/ratings",
        "user_recommendations": "https://storeapi.kobo.com/v1/user/recommendations",
        "user_reviews": "https://storeapi.kobo.com/v1/user/reviews",
        "user_wishlist": "https://storeapi.kobo.com/v1/user/wishlist",
        "userguide_host": "https://kbdownload1-a.akamaihd.net",
        "wishlist_page": "https://store.kobobooks.com/{region}/{language}/account/wishlist",
    }
