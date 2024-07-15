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
from base64 import b64decode, b64encode
from jsonschema import validate, exceptions
from datetime import datetime

from flask import json
from .. import logger


log = logger.create()


def b64encode_json(json_data):
    return b64encode(json.dumps(json_data).encode()).decode("utf-8")


# Python3 has a timestamp() method we could be calling, however it's not available in python2.
def to_epoch_timestamp(datetime_object):
    return (datetime_object - datetime(1970, 1, 1)).total_seconds()


def get_datetime_from_json(json_object, field_name):
    try:
        return datetime.utcfromtimestamp(json_object[field_name])
    except (KeyError, OSError, OverflowError):
        # OSError is thrown on Windows if timestamp is <1970 or >2038
        return datetime.min


class SyncToken:
    """ The SyncToken is used to persist state across requests.
    When serialized over the response headers, the Kobo device will propagate the token onto following
    requests to the service. As an example use-case, the SyncToken is used to detect books that have been added
    to the library since the last time the device synced to the server.

    Attributes:
        books_last_created: Datetime representing the newest book that the device knows about.
        books_last_modified: Datetime representing the last modified book that the device knows about.
    """

    SYNC_TOKEN_HEADER = "x-kobo-synctoken"  # nosec
    VERSION = "1-1-0"
    LAST_MODIFIED_ADDED_VERSION = "1-1-0"
    MIN_VERSION = "1-0-0"

    token_schema = {
        "type": "object",
        "properties": {"version": {"type": "string"}, "data": {"type": "object"}, },
    }
    # This Schema doesn't contain enough information to detect and propagate book deletions from Calibre to the device.
    # A potential solution might be to keep a list of all known book uuids in the token, and look for any missing
    # from the db.
    data_schema_v1 = {
        "type": "object",
        "properties": {
            "raw_kobo_store_token": {"type": "string"},
            "books_last_modified": {"type": "string"},
            "books_last_created": {"type": "string"},
            "archive_last_modified": {"type": "string"},
            "reading_state_last_modified": {"type": "string"},
            "tags_last_modified": {"type": "string"}
            # "books_last_id": {"type": "integer", "optional": True}
        },
    }

    def __init__(
        self,
        raw_kobo_store_token="",
        books_last_created=datetime.min,
        books_last_modified=datetime.min,
        archive_last_modified=datetime.min,
        reading_state_last_modified=datetime.min,
        tags_last_modified=datetime.min
        # books_last_id=-1
    ):  # nosec
        self.raw_kobo_store_token = raw_kobo_store_token
        self.books_last_created = books_last_created
        self.books_last_modified = books_last_modified
        self.archive_last_modified = archive_last_modified
        self.reading_state_last_modified = reading_state_last_modified
        self.tags_last_modified = tags_last_modified
        # self.books_last_id = books_last_id

    @staticmethod
    def from_headers(headers):
        sync_token_header = headers.get(SyncToken.SYNC_TOKEN_HEADER, "")
        if sync_token_header == "":  # nosec
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
        except (exceptions.ValidationError, ValueError):
            log.error("Sync token contents do not follow the expected json schema.")
            return SyncToken()

        raw_kobo_store_token = data_json["raw_kobo_store_token"]
        try:
            books_last_modified = get_datetime_from_json(data_json, "books_last_modified")
            books_last_created = get_datetime_from_json(data_json, "books_last_created")
            archive_last_modified = get_datetime_from_json(data_json, "archive_last_modified")
            reading_state_last_modified = get_datetime_from_json(data_json, "reading_state_last_modified")
            tags_last_modified = get_datetime_from_json(data_json, "tags_last_modified")
        except TypeError:
            log.error("SyncToken timestamps don't parse to a datetime.")
            return SyncToken(raw_kobo_store_token=raw_kobo_store_token)

        return SyncToken(
            raw_kobo_store_token=raw_kobo_store_token,
            books_last_created=books_last_created,
            books_last_modified=books_last_modified,
            archive_last_modified=archive_last_modified,
            reading_state_last_modified=reading_state_last_modified,
            tags_last_modified=tags_last_modified,
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
                "archive_last_modified": to_epoch_timestamp(self.archive_last_modified),
                "reading_state_last_modified": to_epoch_timestamp(self.reading_state_last_modified),
                "tags_last_modified": to_epoch_timestamp(self.tags_last_modified),
            },
        }
        return b64encode_json(token)

    def __str__(self):
        return "{},{},{},{},{},{}".format(self.books_last_created,
                                          self.books_last_modified,
                                          self.archive_last_modified,
                                          self.reading_state_last_modified,
                                          self.tags_last_modified,
                                          self.raw_kobo_store_token)
