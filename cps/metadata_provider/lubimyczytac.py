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
import datetime
import json
import re
from multiprocessing.pool import ThreadPool
from typing import List, Optional, Tuple, Union
from urllib.parse import quote

import requests
from dateutil import parser
from html2text import HTML2Text
from lxml.html import HtmlElement, fromstring, tostring
from markdown2 import Markdown

from cps import logger
from cps.isoLanguages import get_language_name
from cps.services.Metadata import MetaRecord, MetaSourceInfo, Metadata

log = logger.create()

SYMBOLS_TO_TRANSLATE = (
    "öÖüÜóÓőŐúÚéÉáÁűŰíÍąĄćĆęĘłŁńŃóÓśŚźŹżŻ",
    "oOuUoOoOuUeEaAuUiIaAcCeElLnNoOsSzZzZ",
)
SYMBOL_TRANSLATION_MAP = dict(
    [(ord(a), ord(b)) for (a, b) in zip(*SYMBOLS_TO_TRANSLATE)]
)


def get_int_or_float(value: str) -> Union[int, float]:
    number_as_float = float(value)
    number_as_int = int(number_as_float)
    return number_as_int if number_as_float == number_as_int else number_as_float


def strip_accents(s: Optional[str]) -> Optional[str]:
    return s.translate(SYMBOL_TRANSLATION_MAP) if s is not None else s


def sanitize_comments_html(html: str) -> str:
    text = html2text(html)
    md = Markdown()
    html = md.convert(text)
    return html


def html2text(html: str) -> str:
    # replace <u> tags with <span> as <u> becomes emphasis in html2text
    if isinstance(html, bytes):
        html = html.decode("utf-8")
    html = re.sub(
        r"<\s*(?P<solidus>/?)\s*[uU]\b(?P<rest>[^>]*)>",
        r"<\g<solidus>span\g<rest>>",
        html,
    )
    h2t = HTML2Text()
    h2t.body_width = 0
    h2t.single_line_break = True
    h2t.emphasis_mark = "*"
    return h2t.handle(html)


class LubimyCzytac(Metadata):
    __name__ = "LubimyCzytac.pl"
    __id__ = "lubimyczytac"

    BASE_URL = "https://lubimyczytac.pl"

    BOOK_SEARCH_RESULT_XPATH = (
        "*//div[@class='listSearch']//div[@class='authorAllBooks__single']"
    )
    SINGLE_BOOK_RESULT_XPATH = ".//div[contains(@class,'authorAllBooks__singleText')]"
    TITLE_PATH = "/div/a[contains(@class,'authorAllBooks__singleTextTitle')]"
    TITLE_TEXT_PATH = f"{TITLE_PATH}//text()"
    URL_PATH = f"{TITLE_PATH}/@href"
    AUTHORS_PATH = "/div/a[contains(@href,'autor')]//text()"

    SIBLINGS = "/following-sibling::dd"

    CONTAINER = "//section[@class='container book']"
    PUBLISHER = f"{CONTAINER}//dt[contains(text(),'Wydawnictwo:')]{SIBLINGS}/a/text()"
    LANGUAGES = f"{CONTAINER}//dt[contains(text(),'Język:')]{SIBLINGS}/text()"
    DESCRIPTION = f"{CONTAINER}//div[@class='collapse-content']"
    SERIES = f"{CONTAINER}//span/a[contains(@href,'/cykl/')]/text()"
    TRANSLATOR = f"{CONTAINER}//dt[contains(text(),'Tłumacz:')]{SIBLINGS}/a/text()"

    DETAILS = "//div[@id='book-details']"
    PUBLISH_DATE = "//dt[contains(@title,'Data pierwszego wydania"
    FIRST_PUBLISH_DATE = f"{DETAILS}{PUBLISH_DATE} oryginalnego')]{SIBLINGS}[1]/text()"
    FIRST_PUBLISH_DATE_PL = f"{DETAILS}{PUBLISH_DATE} polskiego')]{SIBLINGS}[1]/text()"
    TAGS = "//a[contains(@href,'/ksiazki/t/')]/text()"  # "//nav[@aria-label='breadcrumbs']//a[contains(@href,'/ksiazki/k/')]/span/text()"


    RATING = "//meta[@property='books:rating:value']/@content"
    COVER = "//meta[@property='og:image']/@content"
    ISBN = "//meta[@property='books:isbn']/@content"
    META_TITLE = "//meta[@property='og:description']/@content"

    SUMMARY = "//script[@type='application/ld+json']//text()"

    def search(
        self, query: str, generic_cover: str = "", locale: str = "en"
    ) -> Optional[List[MetaRecord]]:
        if self.active:
            try:
                result = requests.get(self._prepare_query(title=query))
                result.raise_for_status()
            except Exception as e:
                log.warning(e)
                return None
            root = fromstring(result.text)
            lc_parser = LubimyCzytacParser(root=root, metadata=self)
            matches = lc_parser.parse_search_results()
            if matches:
                with ThreadPool(processes=10) as pool:
                    final_matches = pool.starmap(
                        lc_parser.parse_single_book,
                        [(match, generic_cover, locale) for match in matches],
                    )
                return final_matches
            return matches

    def _prepare_query(self, title: str) -> str:
        query = ""
        characters_to_remove = r"\?()\/"
        pattern = "[" + characters_to_remove + "]"
        title = re.sub(pattern, "", title)
        title = title.replace("_", " ")
        if '"' in title or ",," in title:
            title = title.split('"')[0].split(",,")[0]

        if "/" in title:
            title_tokens = [
                token for token in title.lower().split(" ") if len(token) > 1
            ]
        else:
            title_tokens = list(self.get_title_tokens(title, strip_joiners=False))
        if title_tokens:
            tokens = [quote(t.encode("utf-8")) for t in title_tokens]
            query = query + "%20".join(tokens)
        if not query:
            return ""
        return f"{LubimyCzytac.BASE_URL}/szukaj/ksiazki?phrase={query}"


class LubimyCzytacParser:
    PAGES_TEMPLATE = "<p id='strony'>Książka ma {0} stron(y).</p>"
    TRANSLATOR_TEMPLATE = "<p id='translator'>Tłumacz: {0}</p>"
    PUBLISH_DATE_TEMPLATE = "<p id='pierwsze_wydanie'>Data pierwszego wydania: {0}</p>"
    PUBLISH_DATE_PL_TEMPLATE = (
        "<p id='pierwsze_wydanie'>Data pierwszego wydania w Polsce: {0}</p>"
    )

    def __init__(self, root: HtmlElement, metadata: Metadata) -> None:
        self.root = root
        self.metadata = metadata

    def parse_search_results(self) -> List[MetaRecord]:
        matches = []
        results = self.root.xpath(LubimyCzytac.BOOK_SEARCH_RESULT_XPATH)
        for result in results:
            title = self._parse_xpath_node(
                root=result,
                xpath=f"{LubimyCzytac.SINGLE_BOOK_RESULT_XPATH}"
                f"{LubimyCzytac.TITLE_TEXT_PATH}",
            )

            book_url = self._parse_xpath_node(
                root=result,
                xpath=f"{LubimyCzytac.SINGLE_BOOK_RESULT_XPATH}"
                f"{LubimyCzytac.URL_PATH}",
            )
            authors = self._parse_xpath_node(
                root=result,
                xpath=f"{LubimyCzytac.SINGLE_BOOK_RESULT_XPATH}"
                f"{LubimyCzytac.AUTHORS_PATH}",
                take_first=False,
            )
            if not all([title, book_url, authors]):
                continue
            matches.append(
                MetaRecord(
                    id=book_url.replace(f"/ksiazka/", "").split("/")[0],
                    title=title,
                    authors=[strip_accents(author) for author in authors],
                    url=LubimyCzytac.BASE_URL + book_url,
                    source=MetaSourceInfo(
                        id=self.metadata.__id__,
                        description=self.metadata.__name__,
                        link=LubimyCzytac.BASE_URL,
                    ),
                )
            )
        return matches

    def parse_single_book(
        self, match: MetaRecord, generic_cover: str, locale: str
    ) -> MetaRecord:
        try:
            response = requests.get(match.url)
            response.raise_for_status()
        except Exception as e:
            log.warning(e)
            return None
        self.root = fromstring(response.text)
        match.cover = self._parse_cover(generic_cover=generic_cover)
        match.description = self._parse_description()
        match.languages = self._parse_languages(locale=locale)
        match.publisher = self._parse_publisher()
        match.publishedDate = self._parse_from_summary(attribute_name="datePublished")
        match.rating = self._parse_rating()
        match.series, match.series_index = self._parse_series()
        match.tags = self._parse_tags()
        match.identifiers = {
            "isbn": self._parse_isbn(),
            "lubimyczytac": match.id,
        }
        return match

    def _parse_xpath_node(
        self,
        xpath: str,
        root: HtmlElement = None,
        take_first: bool = True,
        strip_element: bool = True,
    ) -> Optional[Union[str, List[str]]]:
        root = root if root is not None else self.root
        node = root.xpath(xpath)
        if not node:
            return None
        return (
            (node[0].strip() if strip_element else node[0])
            if take_first
            else [x.strip() for x in node]
        )

    def _parse_cover(self, generic_cover) -> Optional[str]:
        return (
            self._parse_xpath_node(xpath=LubimyCzytac.COVER, take_first=True)
            or generic_cover
        )

    def _parse_publisher(self) -> Optional[str]:
        return self._parse_xpath_node(xpath=LubimyCzytac.PUBLISHER, take_first=True)

    def _parse_languages(self, locale: str) -> List[str]:
        languages = list()
        lang = self._parse_xpath_node(xpath=LubimyCzytac.LANGUAGES, take_first=True)
        if lang:
            if "polski" in lang:
                languages.append("pol")
            if "angielski" in lang:
                languages.append("eng")
        return [get_language_name(locale, language) for language in languages]

    def _parse_series(self) -> Tuple[Optional[str], Optional[Union[float, int]]]:
        series_index = 0
        series = self._parse_xpath_node(xpath=LubimyCzytac.SERIES, take_first=True)
        if series:
            if "tom " in series:
                series_name, series_info = series.split(" (tom ", 1)
                series_info = series_info.replace(" ", "").replace(")", "")
                # Check if book is not a bundle, i.e. chapter 1-3
                if "-" in series_info:
                    series_info = series_info.split("-", 1)[0]
                if series_info.replace(".", "").isdigit() is True:
                    series_index = get_int_or_float(series_info)
                return series_name, series_index
        return None, None

    def _parse_tags(self) -> List[str]:
        tags = self._parse_xpath_node(xpath=LubimyCzytac.TAGS, take_first=False)
        if tags:
            return [
                strip_accents(w.replace(", itd.", " itd."))
                for w in tags
                if isinstance(w, str)
            ]
        return None

    def _parse_from_summary(self, attribute_name: str) -> Optional[str]:
        value = None
        summary_text = self._parse_xpath_node(xpath=LubimyCzytac.SUMMARY)
        if summary_text:
            data = json.loads(summary_text)
            value = data.get(attribute_name)
        return value.strip() if value is not None else value

    def _parse_rating(self) -> Optional[str]:
        rating = self._parse_xpath_node(xpath=LubimyCzytac.RATING)
        return round(float(rating.replace(",", ".")) / 2) if rating else rating

    def _parse_date(self, xpath="first_publish") -> Optional[datetime.datetime]:
        options = {
            "first_publish": LubimyCzytac.FIRST_PUBLISH_DATE,
            "first_publish_pl": LubimyCzytac.FIRST_PUBLISH_DATE_PL,
        }
        date = self._parse_xpath_node(xpath=options.get(xpath))
        return parser.parse(date) if date else None

    def _parse_isbn(self) -> Optional[str]:
        return self._parse_xpath_node(xpath=LubimyCzytac.ISBN)

    def _parse_description(self) -> str:
        description = ""
        description_node = self._parse_xpath_node(
            xpath=LubimyCzytac.DESCRIPTION, strip_element=False
        )
        if description_node is not None:
            for source in self.root.xpath('//p[@class="source"]'):
                source.getparent().remove(source)
            description = tostring(description_node, method="html")
            description = sanitize_comments_html(description)

        else:
            description_node = self._parse_xpath_node(xpath=LubimyCzytac.META_TITLE)
            if description_node is not None:
                description = description_node
                description = sanitize_comments_html(description)
        description = self._add_extra_info_to_description(description=description)
        return description

    def _add_extra_info_to_description(self, description: str) -> str:
        pages = self._parse_from_summary(attribute_name="numberOfPages")
        if pages:
            description += LubimyCzytacParser.PAGES_TEMPLATE.format(pages)

        first_publish_date = self._parse_date()
        if first_publish_date:
            description += LubimyCzytacParser.PUBLISH_DATE_TEMPLATE.format(
                first_publish_date.strftime("%d.%m.%Y")
            )

        first_publish_date_pl = self._parse_date(xpath="first_publish_pl")
        if first_publish_date_pl:
            description += LubimyCzytacParser.PUBLISH_DATE_PL_TEMPLATE.format(
                first_publish_date_pl.strftime("%d.%m.%Y")
            )
        translator = self._parse_xpath_node(xpath=LubimyCzytac.TRANSLATOR)
        if translator:
            description += LubimyCzytacParser.TRANSLATOR_TEMPLATE.format(translator)


        return description
