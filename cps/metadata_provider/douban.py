# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2022 xlivevil
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
import re
from concurrent import futures
from typing import List, Optional

import requests
from html2text import HTML2Text
from lxml import etree

from cps import logger
from cps.services.Metadata import Metadata, MetaRecord, MetaSourceInfo

log = logger.create()


def html2text(html: str) -> str:

    h2t = HTML2Text()
    h2t.body_width = 0
    h2t.single_line_break = True
    h2t.emphasis_mark = "*"
    return h2t.handle(html)


class Douban(Metadata):
    __name__ = "豆瓣"
    __id__ = "douban"
    DESCRIPTION = "豆瓣"
    META_URL = "https://book.douban.com/"
    SEARCH_JSON_URL = "https://www.douban.com/j/search"
    SEARCH_URL = "https://www.douban.com/search"

    ID_PATTERN = re.compile(r"sid: (?P<id>\d+),")
    AUTHORS_PATTERN = re.compile(r"作者|译者")
    PUBLISHER_PATTERN = re.compile(r"出版社")
    SUBTITLE_PATTERN = re.compile(r"副标题")
    PUBLISHED_DATE_PATTERN = re.compile(r"出版年")
    SERIES_PATTERN = re.compile(r"丛书")
    IDENTIFIERS_PATTERN = re.compile(r"ISBN|统一书号")
    CRITERIA_PATTERN = re.compile("criteria = '(.+)'")

    TITTLE_XPATH = "//span[@property='v:itemreviewed']"
    COVER_XPATH = "//a[@class='nbg']"
    INFO_XPATH = "//*[@id='info']//span[@class='pl']"
    TAGS_XPATH = "//a[contains(@class, 'tag')]"
    DESCRIPTION_XPATH = "//div[@id='link-report']//div[@class='intro']"
    RATING_XPATH = "//div[@class='rating_self clearfix']/strong"

    session = requests.Session()
    session.headers = {
        'user-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.56',
    }

    def search(self,
               query: str,
               generic_cover: str = "",
               locale: str = "en") -> List[MetaRecord]:
        val = []
        if self.active:
            log.debug(f"start searching {query} on douban")
            if title_tokens := list(
                    self.get_title_tokens(query, strip_joiners=False)):
                query = "+".join(title_tokens)

            book_id_list = self._get_book_id_list_from_html(query)

            if not book_id_list:
                log.debug("No search results in Douban")
                return []

            with futures.ThreadPoolExecutor(
                    max_workers=5, thread_name_prefix='douban') as executor:

                fut = [
                    executor.submit(self._parse_single_book, book_id,
                                    generic_cover) for book_id in book_id_list
                ]

                val = [
                    future.result() for future in futures.as_completed(fut)
                    if future.result()
                ]

        return val

    def _get_book_id_list_from_html(self, query: str) -> List[str]:
        try:
            r = self.session.get(self.SEARCH_URL,
                                 params={
                                     "cat": 1001,
                                     "q": query
                                 })
            r.raise_for_status()

        except Exception as e:
            log.warning(e)
            return []

        html = etree.HTML(r.content.decode("utf8"))
        result_list = html.xpath(self.COVER_XPATH)

        return [
            self.ID_PATTERN.search(item.get("onclick")).group("id")
            for item in result_list[:10]
            if self.ID_PATTERN.search(item.get("onclick"))
        ]

    def _get_book_id_list_from_json(self, query: str) -> List[str]:
        try:
            r = self.session.get(self.SEARCH_JSON_URL,
                                 params={
                                     "cat": 1001,
                                     "q": query
                                 })
            r.raise_for_status()

        except Exception as e:
            log.warning(e)
            return []

        results = r.json()
        if results["total"] == 0:
            return []

        return [
            self.ID_PATTERN.search(item).group("id")
            for item in results["items"][:10] if self.ID_PATTERN.search(item)
        ]

    def _parse_single_book(self,
                           id: str,
                           generic_cover: str = "") -> Optional[MetaRecord]:
        url = f"https://book.douban.com/subject/{id}/"
        log.debug(f"start parsing {url}")

        try:
            r = self.session.get(url)
            r.raise_for_status()
        except Exception as e:
            log.warning(e)
            return None

        match = MetaRecord(
            id=id,
            title="",
            authors=[],
            url=url,
            source=MetaSourceInfo(
                id=self.__id__,
                description=self.DESCRIPTION,
                link=self.META_URL,
            ),
        )

        decode_content = r.content.decode("utf8")
        html = etree.HTML(decode_content)

        match.title = html.xpath(self.TITTLE_XPATH)[0].text
        match.cover = html.xpath(
            self.COVER_XPATH)[0].attrib["href"] or generic_cover
        try:
            rating_num = float(html.xpath(self.RATING_XPATH)[0].text.strip())
        except Exception:
            rating_num = 0
        match.rating = int(-1 * rating_num // 2 * -1) if rating_num else 0

        tag_elements = html.xpath(self.TAGS_XPATH)
        if len(tag_elements):
            match.tags = [tag_element.text for tag_element in tag_elements]
        else:
            match.tags = self._get_tags(decode_content)

        description_element = html.xpath(self.DESCRIPTION_XPATH)
        if len(description_element):
            match.description = html2text(
                etree.tostring(description_element[-1]).decode("utf8"))

        info = html.xpath(self.INFO_XPATH)

        for element in info:
            text = element.text
            if self.AUTHORS_PATTERN.search(text):
                next_element = element.getnext()
                while next_element is not None and next_element.tag != "br":
                    match.authors.append(next_element.text)
                    next_element = next_element.getnext()
            elif self.PUBLISHER_PATTERN.search(text):
                if publisher := element.tail.strip():
                    match.publisher = publisher
                else:
                    match.publisher = element.getnext().text
            elif self.SUBTITLE_PATTERN.search(text):
                match.title = f'{match.title}:{element.tail.strip()}'
            elif self.PUBLISHED_DATE_PATTERN.search(text):
                match.publishedDate = self._clean_date(element.tail.strip())
            elif self.SERIES_PATTERN.search(text):
                match.series = element.getnext().text
            elif i_type := self.IDENTIFIERS_PATTERN.search(text):
                match.identifiers[i_type.group()] = element.tail.strip()

        return match

    @staticmethod
    def _clean_date(date: str) -> str:
        """
        Clean up the date string to be in the format YYYY-MM-DD

        Examples of possible patterns:
            '2014-7-16', '1988年4月', '1995-04', '2021-8', '2020-12-1', '1996年',
            '1972', '2004/11/01', '1959年3月北京第1版第1印'
        """
        year = date[:4]
        moon = "01"
        day = "01"

        if len(date) > 5:
            digit = []
            ls = []
            for i in range(5, len(date)):
                if date[i].isdigit():
                    digit.append(date[i])
                elif digit:
                    ls.append("".join(digit) if len(digit) ==
                              2 else f"0{digit[0]}")
                    digit = []
            if digit:
                ls.append("".join(digit) if len(digit) ==
                          2 else f"0{digit[0]}")

            moon = ls[0]
            if len(ls) > 1:
                day = ls[1]

        return f"{year}-{moon}-{day}"

    def _get_tags(self, text: str) -> List[str]:
        tags = []
        if criteria := self.CRITERIA_PATTERN.search(text):
            tags.extend(
                item.replace('7:', '') for item in criteria.group().split('|')
                if item.startswith('7:'))

        return tags
