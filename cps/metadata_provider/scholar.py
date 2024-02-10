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
import itertools
from typing import Dict, List, Optional
from urllib.parse import quote, unquote

try:
    from fake_useragent.errors import FakeUserAgentError
except (ImportError):
    FakeUserAgentError = BaseException
try:
    from scholarly import scholarly
except FakeUserAgentError:
    raise ImportError("No module named 'scholarly'")

from cps import logger
from cps.services.Metadata import MetaRecord, MetaSourceInfo, Metadata

log = logger.create()


class scholar(Metadata):
    __name__ = "Google Scholar"
    __id__ = "googlescholar"
    META_URL = "https://scholar.google.com/"

    def search(
        self, query: str, generic_cover: str = "", locale: str = "en"
    ) -> Optional[List[MetaRecord]]:
        val = list()
        if self.active:
            title_tokens = list(self.get_title_tokens(query, strip_joiners=False))
            if title_tokens:
                tokens = [quote(t.encode("utf-8")) for t in title_tokens]
                query = " ".join(tokens)
            try:
                scholarly.set_timeout(20)
                scholarly.set_retries(2)
                scholar_gen = itertools.islice(scholarly.search_pubs(query), 10)
            except Exception as e:
                log.warning(e)
                return list()
            for result in scholar_gen:
                match = self._parse_search_result(
                    result=result, generic_cover="", locale=locale
                )
                val.append(match)
        return val

    def _parse_search_result(
        self, result: Dict, generic_cover: str, locale: str
    ) -> MetaRecord:
        match = MetaRecord(
            id=result.get("pub_url", result.get("eprint_url", "")),
            title=result["bib"].get("title"),
            authors=result["bib"].get("author", []),
            url=result.get("pub_url", result.get("eprint_url", "")),
            source=MetaSourceInfo(
                id=self.__id__, description=self.__name__, link=scholar.META_URL
            ),
        )

        match.cover = result.get("image", {}).get("original_url", generic_cover)
        match.description = unquote(result["bib"].get("abstract", ""))
        match.publisher = result["bib"].get("venue", "")
        match.publishedDate = result["bib"].get("pub_year") + "-01-01"
        match.identifiers = {"scholar": match.id}
        return match
