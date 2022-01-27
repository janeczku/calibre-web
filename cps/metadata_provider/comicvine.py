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

import requests
from cps.services.Metadata import Metadata


class ComicVine(Metadata):
    __name__ = "ComicVine"
    __id__ = "comicvine"

    def search(self, query, generic_cover=""):
        val = list()
        apikey = "57558043c53943d5d1e96a9ad425b0eb85532ee6"
        if self.active:
            headers = {
                'User-Agent': 'Not Evil Browser'
            }

            result = requests.get("https://comicvine.gamespot.com/api/search?api_key="
                                  + apikey + "&resources=issue&query=" + query + "&sort=name:desc&format=json", headers=headers)
            for r in result.json().get('results'):
                seriesTitle = r['volume'].get('name', "")
                if r.get('store_date'):
                    dateFomers = r.get('store_date')
                else:
                    dateFomers = r.get('date_added')
                v = dict()
                v['id'] = r['id']
                v['title'] = seriesTitle + " #" + r.get('issue_number', "0") + " - " + ( r.get('name', "") or "")
                v['authors'] = r.get('authors', [])
                v['description'] = r.get('description', "")
                v['publisher'] = ""
                v['publishedDate'] = dateFomers
                v['tags'] = ["Comics", seriesTitle]
                v['rating'] = 0
                v['series'] = seriesTitle
                v['cover'] = r['image'].get('original_url')
                v['source'] = {
                    "id": self.__id__,
                    "description": "ComicVine Books",
                    "link": "https://comicvine.gamespot.com/"
                }
                v['url'] = r.get('site_detail_url', "")
                val.append(v)
        return val


