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

# Google Books api document: https://developers.google.com/books/docs/v1/using
from typing import Dict, List, Optional
from urllib.parse import quote
from datetime import datetime

import requests

from cps import logger
from cps.isoLanguages import get_lang3, get_language_name
from cps.services.Metadata import MetaRecord, MetaSourceInfo, Metadata

log = logger.create()


class Google(Metadata):
    __name__ = "Google"
    __id__ = "google"
    DESCRIPTION = "Google Books"
    META_URL = "https://books.google.com/"
    BOOK_URL = "https://books.google.com/books?id="
    SEARCH_URL = "https://www.googleapis.com/books/v1/volumes?q="
    ISBN_TYPE = "ISBN_13"

    def search(
        self, query: str, generic_cover: str = "", locale: str = "en"
    ) -> Optional[List[MetaRecord]]:
        val = list()    
        if self.active:

            title_tokens = list(self.get_title_tokens(query, strip_joiners=False))
            if title_tokens:
                tokens = [quote(t.encode("utf-8")) for t in title_tokens]
                query = "+".join(tokens)
            try:
                results = requests.get(Google.SEARCH_URL + query)
                results.raise_for_status()
            except Exception as e:
                log.warning(e)
                return None
            for result in results.json().get("items", []):
                val.append(
                    self._parse_search_result(
                        result=result, generic_cover=generic_cover, locale=locale
                    )
                )
        return val

    def _parse_search_result(
        self, result: Dict, generic_cover: str, locale: str
    ) -> MetaRecord:
        match = MetaRecord(
            id=result["id"],
            title=result["volumeInfo"]["title"],
            authors=result["volumeInfo"].get("authors", []),
            url=Google.BOOK_URL + result["id"],
            source=MetaSourceInfo(
                id=self.__id__,
                description=Google.DESCRIPTION,
                link=Google.META_URL,
            ),
        )

        match.cover = self._parse_cover(result=result, generic_cover=generic_cover)
        match.description = result["volumeInfo"].get("description", "")
        match.languages = self._parse_languages(result=result, locale=locale)
        match.publisher = result["volumeInfo"].get("publisher", "")
        try:
            datetime.strptime(result["volumeInfo"].get("publishedDate", ""), "%Y-%m-%d")
            match.publishedDate = result["volumeInfo"].get("publishedDate", "")
        except ValueError:
            match.publishedDate = ""
        match.rating = result["volumeInfo"].get("averageRating", 0)
        match.series, match.series_index = "", 1
        match.tags = result["volumeInfo"].get("categories", [])

        match.identifiers = {"google": match.id}
        match = self._parse_isbn(result=result, match=match)
        return match

    @staticmethod
    def _parse_isbn(result: Dict, match: MetaRecord) -> MetaRecord:
        identifiers = result["volumeInfo"].get("industryIdentifiers", [])
        for identifier in identifiers:
            if identifier.get("type") == Google.ISBN_TYPE:
                match.identifiers["isbn"] = identifier.get("identifier")
                break
        return match

    @staticmethod
    def _parse_cover(result: Dict, generic_cover: str) -> str:
        if result["volumeInfo"].get("imageLinks"):
            cover_url = result["volumeInfo"]["imageLinks"]["thumbnail"]
            
            # strip curl in cover
            cover_url = cover_url.replace("&edge=curl", "")
            
            # request 800x900 cover image (higher resolution)
            cover_url += "&fife=w800-h900"
            
            return cover_url.replace("http://", "https://")
        return generic_cover

    @staticmethod
    def _parse_languages(result: Dict, locale: str) -> List[str]:
        language_iso2 = result["volumeInfo"].get("language", "")
        languages = (
            [get_language_name(locale, get_lang3(language_iso2))]
            if language_iso2
            else []
        )
        return languages
