# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, pwr
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

import time
from functools import reduce
import requests

from goodreads.client import GoodreadsClient
from goodreads.request import GoodreadsRequest
import xmltodict

try:
    import Levenshtein
except ImportError:
    Levenshtein = False

from .. import logger
from ..clean_html import clean_string


class my_GoodreadsClient(GoodreadsClient):

    def request(self, *args, **kwargs):
        """Create a GoodreadsRequest object and make that request"""
        req = my_GoodreadsRequest(self, *args, **kwargs)
        return req.request()


class GoodreadsRequestException(Exception):
    def __init__(self, error_msg, url):
        self.error_msg = error_msg
        self.url = url

    def __str__(self):
        return self.url, ':', self.error_msg


class my_GoodreadsRequest(GoodreadsRequest):

    def request(self):
        resp = requests.get(self.host+self.path, params=self.params,
                            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) "
                                                   "Gecko/20100101 Firefox/125.0"})
        if resp.status_code != 200:
            raise GoodreadsRequestException(resp.reason, self.path)
        if self.req_format == 'xml':
            data_dict = xmltodict.parse(resp.content)
            return data_dict['GoodreadsResponse']
        else:
            raise Exception("Invalid format")


log = logger.create()
_client = None  # type: GoodreadsClient

# GoodReads TOS allows for 24h caching of data
_CACHE_TIMEOUT = 23 * 60 * 60  # 23 hours (in seconds)
_AUTHORS_CACHE = {}


def connect(key=None, enabled=True):
    global _client

    if not enabled or not key:
        _client = None
        return

    if _client:
        # make sure the configuration has not changed since last we used the client
        if _client.client_key != key:
            _client = None

    if not _client:
        _client = my_GoodreadsClient(key, None)


def get_author_info(author_name):
    now = time.time()
    author_info = _AUTHORS_CACHE.get(author_name, None)
    if author_info:
        if now < author_info._timestamp + _CACHE_TIMEOUT:
            return author_info
        # clear expired entries
        del _AUTHORS_CACHE[author_name]

    if not _client:
        log.warning("failed to get a Goodreads client")
        return

    try:
        author_info = _client.find_author(author_name=author_name)
    except Exception as ex:
        # Skip goodreads, if site is down/inaccessible
        log.warning('Goodreads website is down/inaccessible? %s', ex.__str__())
        return

    if author_info:
        author_info._timestamp = now
        author_info.safe_about = clean_string(author_info.about)
        _AUTHORS_CACHE[author_name] = author_info
    return author_info


def get_other_books(author_info, library_books=None):
    # Get all identifiers (ISBN, Goodreads, etc) and filter author's books by that list so we show fewer duplicates
    # Note: Not all images will be shown, even though they're available on Goodreads.com.
    #       See https://www.goodreads.com/topic/show/18213769-goodreads-book-images

    if not author_info:
        return

    identifiers = []
    library_titles = []
    if library_books:
        identifiers = list(
            reduce(lambda acc, book: acc + [i.val for i in book.identifiers if i.val], library_books, []))
        library_titles = [book.title for book in library_books]

    for book in author_info.books:
        if book.isbn in identifiers:
            continue
        if isinstance(book.gid, int):
            if book.gid in identifiers:
                continue
        else:
            if book.gid["#text"] in identifiers:
                continue

        if Levenshtein and library_titles:
            goodreads_title = book._book_dict['title_without_series']
            if any(Levenshtein.ratio(goodreads_title, title) > 0.7 for title in library_titles):
                continue

        yield book
