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

# ComicVine api document: https://comicvine.gamespot.com/api/documentation
from typing import Dict, List, Optional
from urllib.parse import quote

import requests
from cps import logger
from cps.services.Metadata import MetaRecord, MetaSourceInfo, Metadata

log = logger.create()


class ComicVine(Metadata):
    __name__ = "ComicVine"
    __id__ = "comicvine"
    DESCRIPTION = "ComicVine Books"
    META_URL = "https://comicvine.gamespot.com/"
    API_KEY = "57558043c53943d5d1e96a9ad425b0eb85532ee6"
    BASE_URL = (
        f"https://comicvine.gamespot.com/api/search?api_key={API_KEY}"
        f"&resources=issue&query="
    )
    QUERY_PARAMS = "&sort=name:desc&format=json"
    HEADERS = {"User-Agent": "Not Evil Browser"}

    def search(
        self, query: str, generic_cover: str = "", locale: str = "en"
    ) -> Optional[List[MetaRecord]]:
        val = list()
        if self.active:
            title_tokens = list(self.get_title_tokens(query, strip_joiners=False))
            if title_tokens:
                tokens = [quote(t.encode("utf-8")) for t in title_tokens]
                query = "%20".join(tokens)
            try:
                result = requests.get(
                    f"{ComicVine.BASE_URL}{query}{ComicVine.QUERY_PARAMS}",
                    headers=ComicVine.HEADERS,
                )
                result.raise_for_status()
            except Exception as e:
                log.warning(e)
                return None
            for result in result.json()["results"]:
                match = self._parse_search_result(
                    result=result, generic_cover=generic_cover, locale=locale
                )
                val.append(match)
        return val

    def _parse_search_result(
        self, result: Dict, generic_cover: str, locale: str
    ) -> MetaRecord:
        series = result["volume"].get("name", "")
        series_index = result.get("issue_number", 0)
        issue_name = result.get("name", "")
        match = MetaRecord(
            id=result["id"],
            title=f"{series}#{series_index} - {issue_name}",
            authors=result.get("authors", []),
            url=result.get("site_detail_url", ""),
            source=MetaSourceInfo(
                id=self.__id__,
                description=ComicVine.DESCRIPTION,
                link=ComicVine.META_URL,
            ),
            series=series,
        )
        match.cover = result["image"].get("original_url", generic_cover)
        match.description = result.get("description", "")
        match.publishedDate = result.get("store_date", result.get("date_added"))
        match.series_index = series_index
        match.tags = ["Comics", series]
        match.identifiers = {"comicvine": match.id}
        return match
