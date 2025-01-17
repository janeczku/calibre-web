import datetime as dt
import html
import json
import re
import time
from collections import defaultdict
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime

from typing import List, Optional
from urllib.parse import quote

import bs4
import requests
from bs4.element import ResultSet, Tag
from fake_headers import Headers

from cps import logger
from cps.services.Metadata import Metadata, MetaRecord, MetaSourceInfo

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


log = logger.create()


class GoodReads(Metadata):
    __name__ = "GoodReads"
    __id__ = "goodreads"
    DESCRIPTION = "GoodReads"
    META_URL = "https://www.goodreads.com/"
    BOOK_URL = "https://www.goodreads.com/book/show/"
    SEARCH_URL = "https://www.goodreads.com/search?q="
    ISBN_TYPE = "ISBN_13"

    def search(
        self, query: str, generic_cover: str = "", locale: str = "en"
    ) -> Optional[List[MetaRecord]]:
        val = list()
        if self.active:
            headers = Headers(os="mac", headers=True).generate()
            title_tokens = list(self.get_title_tokens(query, strip_joiners=False))
            if title_tokens:
                tokens = [quote(t.encode("utf-8")) for t in title_tokens]
                query = html.escape(" ".join(tokens))
            try:
                results = requests.get(
                    GoodReads.SEARCH_URL + query,
                    headers=headers,
                )
                results.raise_for_status()
            except Exception as e:
                log.warning(e)
                return []
            soup = bs4.BeautifulSoup(results.text, "html.parser")
            results: ResultSet = soup.find_all(
                "tr", dict(itemtype="http://schema.org/Book")
            )
            book_ids = [
                result.find("a", {"class": "bookTitle"})
                .get("href")
                .split("?", 1)[0]
                .removeprefix("/book/show/")
                for result in results
            ]
            with ThreadPoolExecutor(max_workers=5) as executor:
                futs = [
                    executor.submit(
                        GoodReads._parse_url, GoodReads.BOOK_URL + url, headers
                    )
                    for url in book_ids[:3]
                ]
                val = [fut.result() for fut in futs]

        return val

    @staticmethod
    def _parse_url(url: str, headers=None) -> MetaRecord:
        if headers is None:
            headers = Headers(os="mac", headers=True).generate()
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except ConnectionError:
            time.sleep(1)
            response = requests.get(url, headers=headers)
            response.raise_for_status()

        soup = bs4.BeautifulSoup(response.text, "html.parser")
        metadata = json.loads(soup.find("script", {"id": "__NEXT_DATA__"}).text)[
            "props"
        ]["pageProps"]["apolloState"]
        grouped_metadata = defaultdict(list)
        for k, v in metadata.items():
            if "__typename" in v:
                grouped_metadata[v["__typename"]].append(v)
        book = [book for book in grouped_metadata["Book"] if "title" in book][0]
        return MetaRecord(
            id=url.split("/")[-1],
            title=book["title"],
            authors=[
                re.sub(r"\s{2,}", " ", contributor["name"])
                for contributor in grouped_metadata["Contributor"]
                if "name" in contributor
            ],
            url=url,
            source=MetaSourceInfo(
                id=GoodReads.__id__,
                description=GoodReads.DESCRIPTION,
                link=GoodReads.META_URL,
            ),
            cover=book["imageUrl"],
            description=book['description({"stripped":true})'],
            series=metadata[book["bookSeries"][0]["series"]["__ref"]]["title"]
            if book["bookSeries"]
            else None,
            series_index=int(book["bookSeries"][0]["userPosition"])
            if book["bookSeries"]
            and re.match(r"^\d+$", book["bookSeries"][0]["userPosition"])
            else None,
            identifiers={
                k: v
                for k, v in {
                    "goodreads": url.split("/")[-1],
                    "asin": book["details"]["asin"],
                    "isbn": book["details"]["isbn"],
                    "isbn13": book["details"]["isbn13"],
                }.items()
                if v
            },
            publisher=book["details"]["publisher"],
            publishedDate=dt.date.fromtimestamp(
                book["details"]["publicationTime"] // 1_000
            ).strftime("%Y-%m-%d")
            if book["details"]["publicationTime"] is not None
            else None,
            rating=round(grouped_metadata["Work"][0]["stats"]["averageRating"]),
            languages=[book["details"]["language"]["name"]],
            tags=[genre["genre"]["name"] for genre in book["bookGenres"]],
        )

    @staticmethod
    def _parse_search_result(
        result: Tag, generic_cover: str, locale: str
    ) -> MetaRecord:
        book_title = result.find("a", {"class": "bookTitle"})
        book_id = book_title.get("href").removeprefix("/book/show/").split("?", 1)[0]
        return MetaRecord(
            id=book_id,
            title=book_title.text.strip(),
            authors=[
                re.sub(r"\s+", " ", tag.find("span", {"itemprop": "name"}).text)
                for tag in result.find_all("div", {"class": "authorName__container"})
            ],
            url=GoodReads.BOOK_URL + book_id,
            source=MetaSourceInfo(
                id=GoodReads.__id__,
                description=GoodReads.DESCRIPTION,
                link=GoodReads.META_URL,
            ),
            cover=result.find("img", {"class": "bookCover"}).get("src"),
            rating=round(
                float(
                    re.search(
                        r"\d\.\d\d", result.find("span", {"class": "minirating"}).text
                    ).group(0)
                )
            ),
            identifiers=dict(goodreads=book_id),
        )
