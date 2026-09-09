# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2021 OzzieIsaacs
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
import abc
import dataclasses
import os
import re
from typing import Dict, Generator, List, Optional, Tuple, Union
from urllib.parse import urlsplit

from cps import constants


@dataclasses.dataclass
class MetaSourceInfo:
    id: str
    description: str
    link: str


@dataclasses.dataclass
class MetaRecord:
    id: Union[str, int]
    title: str
    authors: List[str]
    url: str
    source: MetaSourceInfo
    cover: str = os.path.join(constants.STATIC_DIR, 'generic_cover.jpg')
    description: Optional[str] = ""
    series: Optional[str] = None
    series_index: Optional[Union[int, float]] = 0
    identifiers: Dict[str, Union[str, int]] = dataclasses.field(default_factory=dict)
    publisher: Optional[str] = None
    publishedDate: Optional[str] = None
    rating: Optional[int] = 0
    languages: Optional[List[str]] = dataclasses.field(default_factory=list)
    tags: Optional[List[str]] = dataclasses.field(default_factory=list)


# Metadata providers that declare COVER_HOSTS, registered when their class is created
_cover_header_providers: List[type] = []


def cover_headers_for(url: str) -> Dict[str, str]:
    """Extra HTTP headers needed to download the cover image at url, or {} if none
    of the metadata providers claims that host (see Metadata.COVER_HOSTS)"""
    if not url:
        return {}
    for provider in _cover_header_providers:
        headers = provider.cover_headers(url)
        if headers:
            return headers
    return {}


class Metadata:
    __name__ = "Generic"
    __id__ = "generic"
    # Some cover image hosts refuse "hot-linked" downloads (e.g. they check the
    # Referer header). A provider can list the host suffixes of its cover images
    # in COVER_HOSTS and the headers needed to fetch them in COVER_HEADERS.
    # Calibre-Web then sends these headers when it downloads such a cover and
    # serves the cover preview in the metadata dialog via /metadata/cover_proxy.
    COVER_HOSTS: Tuple[str, ...] = ()
    COVER_HEADERS: Dict[str, str] = {}

    def __init__(self):
        self.active = True

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.COVER_HOSTS:
            _cover_header_providers.append(cls)

    @classmethod
    def cover_headers(cls, url: str) -> Dict[str, str]:
        """Headers needed to download the cover at url, or {} if this provider
        does not handle the host of url"""
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            return {}
        for suffix in cls.COVER_HOSTS:
            suffix = suffix.lower()
            if host == suffix or host.endswith("." + suffix):
                return dict(cls.COVER_HEADERS)
        return {}

    def set_status(self, state):
        self.active = state

    @abc.abstractmethod
    def search(
        self, query: str, generic_cover: str = "", locale: str = "en"
    ) -> Optional[List[MetaRecord]]:
        pass

    @staticmethod
    def get_title_tokens(
        title: str, strip_joiners: bool = True
    ) -> Generator[str, None, None]:
        """
        Taken from calibre source code
        It's a simplified (cut out what is unnecessary) version of
        https://github.com/kovidgoyal/calibre/blob/99d85b97918625d172227c8ffb7e0c71794966c0/
        src/calibre/ebooks/metadata/sources/base.py#L363-L367
        (src/calibre/ebooks/metadata/sources/base.py - lines 363-398)
        """
        title_patterns = [
            (re.compile(pat, re.IGNORECASE), repl)
            for pat, repl in [
                # Remove things like: (2010) (Omnibus) etc.
                (
                    r"(?i)[({\[](\d{4}|omnibus|anthology|hardcover|"
                    r"audiobook|audio\scd|paperback|turtleback|"
                    r"mass\s*market|edition|ed\.)[\])}]",
                    "",
                ),
                # Remove any strings that contain the substring edition inside
                # parentheses
                (r"(?i)[({\[].*?(edition|ed.).*?[\]})]", ""),
                # Remove commas used a separators in numbers
                (r"(\d+),(\d+)", r"\1\2"),
                # Remove hyphens only if they have whitespace before them
                (r"(\s-)", " "),
                # Replace other special chars with a space
                (r"""[:,;!@$%^&*(){}.`~"\s\[\]/]《》「」“”""", " "),
            ]
        ]

        for pat, repl in title_patterns:
            title = pat.sub(repl, title)

        tokens = title.split()
        for token in tokens:
            token = token.strip().strip('"').strip("'")
            if token and (
                not strip_joiners or token.lower() not in ("a", "and", "the", "&")
            ):
                yield token
