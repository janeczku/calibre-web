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
import json
import re
from typing import Dict, List
from urllib.parse import quote

import requests
from cps.services.Metadata import Metadata
from lxml.html import fromstring, tostring


def get_int_or_float(v):
    number_as_float = float(v)
    number_as_int = int(number_as_float)
    return number_as_int if number_as_float == number_as_int else number_as_float


def strip_accents(s):
    if s is None:
        return s
    else:
        symbols = (
            "öÖüÜóÓőŐúÚéÉáÁűŰíÍąĄćĆęĘłŁńŃóÓśŚźŹżŻ",
            "oOuUoOoOuUeEaAuUiIaAcCeElLnNoOsSzZzZ",
        )
        tr = dict([(ord(a), ord(b)) for (a, b) in zip(*symbols)])
        return s.translate(tr)  # .lower()


def sanitize_comments_html(html):
    from markdown2 import Markdown

    text = html2text(html)
    md = Markdown()
    html = md.convert(text)
    return html


def html2text(html):
    from html2text import HTML2Text
    import re

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
    SERIES = f"{CONTAINER}//span/a[contains(@href,'/cykl/')]"

    DETAILS = "//div[@id='book-details']"
    PUBLISH_DATE = "//dt[contains(@title,'Data pierwszego wydania"
    FIRST_PUBLISH_DATE = f"{DETAILS}{PUBLISH_DATE} oryginalnego')]{SIBLINGS}[1]/text()"
    FIRST_PUBLISH_DATE_PL = f"{DETAILS}{PUBLISH_DATE} polskiego')]{SIBLINGS}[1]/text()"
    TAGS = "//nav[@aria-label='breadcrumb']//a[contains(@href,'/ksiazki/k/')]/text()"
    RATING = "//meta[@property='books:rating:value']/@content"
    COVER = "//meta[@property='og:image']/@content"

    SUMMARY = "//script[@type='application/ld+json']//text()"

    def search(self, query, __):
        if self.active:
            result = requests.get(self._prepare_query(title=query))
            root = fromstring(result.text)
            matches = self._parse_search_results(root=root)
            if matches:
                for ind, match in enumerate(matches):
                    matches[ind] = self._parse_single_book(match=match)
            return matches

    def _prepare_query(self, title: str) -> str:
        query = ""
        characters_to_remove = "\?()\/"
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
            title_tokens = list(
                self.get_title_tokens(title, strip_joiners=False, strip_subtitle=True)
            )
        if title_tokens:
            tokens = [quote(t.encode("utf-8")) for t in title_tokens]
            query = query + "%20".join(tokens)
        if not query:
            return ""
        return f"{LubimyCzytac.BASE_URL}/szukaj/ksiazki?phrase={query}"

    def _parse_search_results(self, root) -> List[Dict]:
        matches = []
        results = root.xpath(LubimyCzytac.BOOK_SEARCH_RESULT_XPATH)
        for result in results:
            title = result.xpath(
                f"{LubimyCzytac.SINGLE_BOOK_RESULT_XPATH}"
                f"{LubimyCzytac.TITLE_TEXT_PATH}"
            )
            book_url = result.xpath(
                f"{LubimyCzytac.SINGLE_BOOK_RESULT_XPATH}" f"{LubimyCzytac.URL_PATH}"
            )
            authors = result.xpath(
                f"{LubimyCzytac.SINGLE_BOOK_RESULT_XPATH}"
                f"{LubimyCzytac.AUTHORS_PATH}"
            )

            if not title or not book_url or not authors:
                continue
            title = title[0].strip()
            book_url = LubimyCzytac.BASE_URL + book_url[0]
            book_id = book_url.replace(f"{LubimyCzytac.BASE_URL}/ksiazka/", "").split(
                "/"
            )[0]
            matches.append(
                {"id": book_id, "title": title, "authors": authors, "url": book_url}
            )
        return matches

    def _parse_single_book(self, match: Dict) -> Dict:
        url = match.get("url")
        result = requests.get(url)
        root = fromstring(result.text)
        match["series"], match["series_index"] = self._parse_series(root=root)
        match["tags"] = self._parse_tags(root=root)
        match["publisher"] = self._parse_publisher(root=root)
        match["publishedDate"] = self._parse_from_summary(
            root=root, attribute_name="datePublished"
        )
        match["rating"] = self._parse_rating(root=root)
        match["description"] = self._parse_description(root=root)
        match["cover"] = self._parse_cover(root=root)
        match["source"] = {
            "id": self.__id__,
            "description": self.__name__,
            "link": LubimyCzytac.BASE_URL,
        }
        match['languages'] = self._parse_languages(root=root)
        match["identifiers"] = {
            "isbn": self._parse_isbn(root=root),
            "lubimyczytac": match["id"],
        }
        return match

    def _parse_cover(self, root):
        imgcol_node = root.xpath('//meta[@property="og:image"]/@content')
        if imgcol_node:
            img_url = imgcol_node[0]
            return img_url

    def _parse_publisher(self, root):
        publisher = root.xpath(LubimyCzytac.PUBLISHER)
        if publisher:
            return publisher[0]
        else:
            return None

    def _parse_languages(self, root):
        lang = root.xpath(LubimyCzytac.LANGUAGES)
        languages = list()
        if lang:
            lang = lang[0].strip()
            if "polski" in lang:
                languages.append("Polish")
            if "angielski" in lang:
                languages.append("English")
        if not languages:
            return ['Polish']
        return languages

    def _parse_series(self, root):
        try:
            series_node = root.xpath(LubimyCzytac.SERIES)
            if series_node:
                series_lst = root.xpath(f"{LubimyCzytac.SERIES}/text()")
                if series_lst:
                    series_txt = series_lst
                else:
                    series_txt = None
            else:
                return (None, None)

            if series_txt:
                ser_string = [series_txt[0].replace("\n", "").strip()]
                ser_nazwa = ser_string
                for ser in ser_string:
                    if "tom " in ser:
                        ser_info = ser.split(" (tom ", 1)
                        ser_nazwa = ser.split(" (tom ")[0]
                        break

            if ser_info:
                series_index_unicode = ser_info[1]
                series_index_string = str(
                    series_index_unicode.replace(" ", "").replace(")", "")
                )
                # Sprawdzamy, czy cykl nie jest kompletem/pakietem tomów, np. 1-3
                if "-" in series_index_string:
                    series_index_string_temp = series_index_string.split("-", 1)
                    series_index_string = series_index_string_temp[0]
                if series_index_string.replace(".", "").isdigit() is True:
                    series_index = get_int_or_float(series_index_string)
                else:
                    series_index = 0
            else:
                series_index = 0
            series = ser_nazwa
            return (series, series_index)
        except:
            return (None, None)

    def _parse_tags(self, root):
        tags = None
        try:
            tags_from_genre = root.xpath(LubimyCzytac.TAGS)
            if tags_from_genre:
                tags = tags_from_genre
                tags = [w.replace(", itd.", " itd.") for w in tags]
                return tags
            else:
                return None
        except:
            return tags

    def _parse_from_summary(self, root, attribute_name: str) -> str:
        data = json.loads(root.xpath(LubimyCzytac.SUMMARY)[0])
        value = data.get(attribute_name)
        return value.strip() if value is not None else value

    def _parse_rating(self, root):
        rating_node = root.xpath(LubimyCzytac.RATING)
        if rating_node:
            rating_value = round(float((rating_node[0]).replace(",", ".")) / 2)
            return rating_value
        return None

    def _parse_date(self, root, xpath="first_publish"):
        options = {
            "first_publish": LubimyCzytac.FIRST_PUBLISH_DATE,
            "first_publish_pl": LubimyCzytac.FIRST_PUBLISH_DATE_PL,
        }
        path = options.get(xpath)
        from dateutil import parser

        data = root.xpath(path)
        if data:
            first_pub_date = data[0].strip()
            return parser.parse(first_pub_date)
        return None

    def _parse_isbn(self, root):
        isbn_node = root.xpath('//meta[@property="books:isbn"]/@content')[0]
        return isbn_node

    def _parse_description(self, root):
        comments = ""
        description_node = root.xpath(LubimyCzytac.DESCRIPTION)
        if description_node:
            for zrodla in root.xpath('//p[@class="source"]'):
                zrodla.getparent().remove(zrodla)
            comments = tostring(description_node[0], method="html")
            comments = sanitize_comments_html(comments)

        else:
            # try <meta>
            description_node = root.xpath('//meta[@property="og:description"]/@content')
            if description_node:
                comments = description_node[0]
                comments = sanitize_comments_html(comments)

        pages = self._parse_from_summary(root=root, attribute_name="numberOfPages")
        if pages:
            comments += f'<p id="strony">Książka ma {pages} stron(y).</p>'

        first_publish_date = self._parse_date(root=root)
        if first_publish_date:
            comments += f'<p id="pierwsze_wydanie">Data pierwszego wydania: {first_publish_date.strftime("%d.%m.%Y")}</p>'

        first_publish_date_pl = self._parse_date(root=root, xpath="first_publish_pl")
        if first_publish_date_pl:
            comments += f'<p id="pierwsze_wydanie_pl">Data pierwszego wydania w Polsce: {first_publish_date_pl.strftime("%d.%m.%Y")}</p>'

        return comments

    def get_title_tokens(self, title, strip_joiners=True, strip_subtitle=False):
        """
        Taken from https://github.com/kovidgoyal/calibre/blob/master/src/calibre/ebooks/metadata/sources/base.py.
        """
        # strip sub-titles
        if strip_subtitle:
            subtitle = re.compile(r"([\(\[\{].*?[\)\]\}]|[/:\\].*$)")
            if len(subtitle.sub("", title)) > 1:
                title = subtitle.sub("", title)

        title_patterns = [
            (re.compile(pat, re.IGNORECASE), repl)
            for pat, repl in [
                # Remove things like: (2010) (Omnibus) etc.
                (
                    r"(?i)[({\[](\d{4}|omnibus|anthology|hardcover|audiobook|audio\scd|paperback|turtleback|mass\s*market|edition|ed\.)[\])}]",
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
