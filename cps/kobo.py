#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs
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

import os
import sys
import uuid
from base64 import b64decode, b64encode
from datetime import datetime
from time import gmtime, strftime

from jsonschema import validate, exceptions
from flask import (
    Blueprint,
    request,
    make_response,
    jsonify,
    json,
    current_app,
    url_for,
    redirect,
)
from flask_login import login_required
from werkzeug.datastructures import Headers
from sqlalchemy import func
import requests

from . import config, logger, kobo_auth, db, helper
from .web import download_required

KOBO_FORMATS = {"KEPUB": ["KEPUB"], "EPUB": ["EPUB", "EPUB3"]}
KOBO_STOREAPI_URL = "https://storeapi.kobo.com"

kobo = Blueprint("kobo", __name__, url_prefix="/kobo/<auth_token>")
kobo_auth.disable_failed_auth_redirect_for_blueprint(kobo)
kobo_auth.register_url_value_preprocessor(kobo)

log = logger.create()


def b64encode_json(json_data):
    if sys.version_info < (3, 0):
        return b64encode(json.dumps(json_data))
    else:
        return b64encode(json.dumps(json_data).encode())


# Python3 has a timestamp() method we could be calling, however it's not avaiable in python2.
def to_epoch_timestamp(datetime_object):
    return (datetime_object - datetime(1970, 1, 1)).total_seconds()


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


class SyncToken:
    """ The SyncToken is used to persist state accross requests.
    When serialized over the response headers, the Kobo device will propagate the token onto following requests to the service.
    As an example use-case, the SyncToken is used to detect books that have been added to the library since the last time the device synced to the server.

    Attributes:
        books_last_created: Datetime representing the newest book that the device knows about.
        books_last_modified: Datetime representing the last modified book that the device knows about.
    """

    SYNC_TOKEN_HEADER = "x-kobo-synctoken"
    VERSION = "1-0-0"
    MIN_VERSION = "1-0-0"

    token_schema = {
        "type": "object",
        "properties": {"version": {"type": "string"}, "data": {"type": "object"},},
    }
    # This Schema doesn't contain enough information to detect and propagate book deletions from Calibre to the device.
    # A potential solution might be to keep a list of all known book uuids in the token, and look for any missing from the db.
    data_schema_v1 = {
        "type": "object",
        "properties": {
            "raw_kobo_store_token": {"type": "string"},
            "books_last_modified": {"type": "string"},
            "books_last_created": {"type": "string"},
        },
    }

    def __init__(
        self,
        raw_kobo_store_token="",
        books_last_created=datetime.min,
        books_last_modified=datetime.min,
    ):
        self.raw_kobo_store_token = raw_kobo_store_token
        self.books_last_created = books_last_created
        self.books_last_modified = books_last_modified

    @staticmethod
    def from_headers(headers):
        sync_token_header = headers.get(SyncToken.SYNC_TOKEN_HEADER, "")
        if sync_token_header == "":
            return SyncToken()

        # On the first sync from a Kobo device, we may receive the SyncToken
        # from the official Kobo store. Without digging too deep into it, that
        # token is of the form [b64encoded blob].[b64encoded blob 2]
        if "." in sync_token_header:
            return SyncToken(raw_kobo_store_token=sync_token_header)

        try:
            sync_token_json = json.loads(
                b64decode(sync_token_header + "=" * (-len(sync_token_header) % 4))
            )
            validate(sync_token_json, SyncToken.token_schema)
            if sync_token_json["version"] < SyncToken.MIN_VERSION:
                raise ValueError

            data_json = sync_token_json["data"]
            validate(sync_token_json, SyncToken.data_schema_v1)
        except (exceptions.ValidationError, ValueError) as e:
            log.error("Sync token contents do not follow the expected json schema.")
            return SyncToken()

        raw_kobo_store_token = data_json["raw_kobo_store_token"]
        try:
            books_last_modified = datetime.utcfromtimestamp(
                data_json["books_last_modified"]
            )
            books_last_created = datetime.utcfromtimestamp(
                data_json["books_last_created"]
            )
        except TypeError:
            log.error("SyncToken timestamps don't parse to a datetime.")
            return SyncToken(raw_kobo_store_token=raw_kobo_store_token)

        return SyncToken(
            raw_kobo_store_token=raw_kobo_store_token,
            books_last_created=books_last_created,
            books_last_modified=books_last_modified,
        )

    def set_kobo_store_header(self, store_headers):
        store_headers.set(SyncToken.SYNC_TOKEN_HEADER, self.raw_kobo_store_token)

    def merge_from_store_response(self, store_response):
        self.raw_kobo_store_token = store_response.headers.get(
            SyncToken.SYNC_TOKEN_HEADER, ""
        )

    def to_headers(self, headers):
        headers[SyncToken.SYNC_TOKEN_HEADER] = self.build_sync_token()

    def build_sync_token(self):
        token = {
            "version": SyncToken.VERSION,
            "data": {
                "raw_kobo_store_token": self.raw_kobo_store_token,
                "books_last_modified": to_epoch_timestamp(self.books_last_modified),
                "books_last_created": to_epoch_timestamp(self.books_last_created),
            },
        }
        return b64encode_json(token)


@kobo.route("/v1/library/sync")
@login_required
@download_required
def HandleSyncRequest():
    sync_token = SyncToken.from_headers(request.headers)
    log.info("Kobo library sync request received.")

    # TODO: Limit the number of books return per sync call, and rely on the sync-continuatation header
    # instead so that the device triggers another sync.

    new_books_last_modified = sync_token.books_last_modified
    new_books_last_created = sync_token.books_last_created
    entitlements = []

    # We reload the book database so that the user get's a fresh view of the library
    # in case of external changes (e.g: adding a book through Calibre).
    db.reconnect_db(config)

    # sqlite gives unexpected results when performing the last_modified comparison without the datetime cast.
    # It looks like it's treating the db.Books.last_modified field as a string and may fail
    # the comparison because of the +00:00 suffix.
    changed_entries = (
        db.session.query(db.Books)
        .join(db.Data)
        .filter(func.datetime(db.Books.last_modified) > sync_token.books_last_modified)
        .filter(db.Data.format.in_(KOBO_FORMATS))
        .all()
    )
    for book in changed_entries:
        entitlement = {
            "BookEntitlement": create_book_entitlement(book),
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
        new_books_last_created = max(book.timestamp, sync_token.books_last_modified)

    sync_token.books_last_created = new_books_last_created
    sync_token.books_last_modified = new_books_last_modified

    # Missing feature: Detect server-side book deletions.

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


def create_book_entitlement(book):
    book_uuid = book.uuid
    return {
        "Accessibility": "Full",
        "ActivePeriod": {"From": current_time(),},
        "Created": book.timestamp,
        "CrossRevisionId": book_uuid,
        "Id": book_uuid,
        "IsHiddenFromArchive": False,
        "IsLocked": False,
        # Setting this to true removes from the device.
        "IsRemoved": False,
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


@kobo.route(
    "/<book_uuid>/<horizontal>/<vertical>/<jpeg_quality>/<monochrome>/image.jpg"
)
def HandleCoverImageRequest(book_uuid, horizontal, vertical, jpeg_quality, monochrome):
    book_cover = helper.get_book_cover_with_uuid(
        book_uuid, use_generic_cover_on_failure=False
    )
    if not book_cover:
        return redirect(get_store_url_for_current_request(), 307)
    return book_cover


@kobo.route("")
def TopLevelEndpoint():
    return make_response(jsonify({}))


# TODO: Implement the following routes
@kobo.route("/v1/library/<dummy>", methods=["DELETE", "GET"])
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
        kobo_resources["image_url_quality_template"] = (
            calibre_web_url
            + "/{ImageId}/{Width}/{Height}/{Quality}/{IsGreyscale}/image.jpg"
        )
        kobo_resources["image_url_template"] = (
            calibre_web_url + "/{ImageId}/{Width}/{Height}/false/image.jpg"
        )

    return make_response(store_response_json, store_response.status_code)
