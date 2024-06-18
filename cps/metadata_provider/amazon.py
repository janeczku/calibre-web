# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2022 quarz12
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

import concurrent.futures
import requests
from bs4 import BeautifulSoup as BS  # requirement
from typing import List, Optional

try:
    import cchardet #optional for better speed
except ImportError:
    pass

from cps.services.Metadata import MetaRecord, MetaSourceInfo, Metadata
import cps.logger as logger

#from time import time
from operator import itemgetter
log = logger.create()


class Amazon(Metadata):
    __name__ = "Amazon"
    __id__ = "amazon"
    headers = {'upgrade-insecure-requests': '1',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
               'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
               'sec-gpc': '1',
               'sec-fetch-site': 'none',
               'sec-fetch-mode': 'navigate',
               'sec-fetch-user': '?1',
               'sec-fetch-dest': 'document',
               'accept-encoding': 'gzip, deflate, br',
               'accept-language': 'en-US,en;q=0.9'}
    session = requests.Session()
    session.headers=headers

    def search(
        self, query: str, generic_cover: str = "", locale: str = "en"
    ) -> Optional[List[MetaRecord]]:
        #timer=time()
        def inner(link, index) -> [dict, int]:
            with self.session as session:
                try:
                    r = session.get(f"https://www.amazon.com/{link}")
                    r.raise_for_status()
                except Exception as ex:
                    log.warning(ex)
                    return None
                long_soup = BS(r.text, "lxml")  #~4sec :/
                soup2 = long_soup.find("div", attrs={"cel_widget_id": "dpx-books-ppd_csm_instrumentation_wrapper"})
                if soup2 is None:
                    return None
                try:
                    match = MetaRecord(
                        title = "",
                        authors = "",
                        source=MetaSourceInfo(
                            id=self.__id__,
                            description="Amazon Books",
                            link="https://amazon.com/"
                        ),
                        url = f"https://www.amazon.com{link}",
                        #the more searches the slower, these are too hard to find in reasonable time or might not even exist
                        publisher= "",  # very unreliable
                        publishedDate= "",  # very unreliable
                        id = None,  # ?
                        tags = []  # dont exist on amazon
                    )

                    try:
                        match.description = "\n".join(
                            soup2.find("div", attrs={"data-feature-name": "bookDescription"}).stripped_strings)\
                                                .replace("\xa0"," ")[:-9].strip().strip("\n")
                    except (AttributeError, TypeError):
                        return None  # if there is no description it is not a book and therefore should be ignored
                    try:
                        match.title = soup2.find("span", attrs={"id": "productTitle"}).text
                    except (AttributeError, TypeError):
                        match.title = ""
                    try:
                        match.authors = [next(
                            filter(lambda i: i != " " and i != "\n" and not i.startswith("{"),
                                   x.findAll(string=True))).strip()
                                        for x in soup2.findAll("span", attrs={"class": "author"})]
                    except (AttributeError, TypeError, StopIteration):
                        match.authors = ""
                    try:
                        match.rating = int(
                            soup2.find("span", class_="a-icon-alt").text.split(" ")[0].split(".")[
                                0])  # first number in string
                    except (AttributeError, ValueError):
                        match.rating = 0
                    try:
                        match.cover = soup2.find("img", attrs={"class": "a-dynamic-image frontImage"})["src"]
                    except (AttributeError, TypeError):
                        match.cover = ""
                    return match, index
                except Exception as e:
                    log.error_or_exception(e)
                    return None

        val = list()
        if self.active:
            try:
                results = self.session.get(
                    f"https://www.amazon.com/s?k={query.replace(' ', '+')}&i=digital-text&sprefix={query.replace(' ', '+')}"
                    f"%2Cdigital-text&ref=nb_sb_noss",
                    headers=self.headers)
                results.raise_for_status()
            except requests.exceptions.HTTPError as e:
                log.error_or_exception(e)
                return []
            except Exception as e:
                log.warning(e)
                return []
            soup = BS(results.text, 'html.parser')
            links_list = [next(filter(lambda i: "digital-text" in i["href"], x.findAll("a")))["href"] for x in
                          soup.findAll("div", attrs={"data-component-type": "s-search-result"})]
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                fut = {executor.submit(inner, link, index) for index, link in enumerate(links_list[:5])}
                val = list(map(lambda x : x.result() ,concurrent.futures.as_completed(fut)))
        result = list(filter(lambda x: x, val))
        return [x[0] for x in sorted(result, key=itemgetter(1))] #sort by amazons listing order for best relevance
