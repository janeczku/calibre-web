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


import requests
from cps.services.Metadata import Metadata

class Google(Metadata):
    __name__ = "Google"

    def search(self, query):
        if self.active:
            val = list()
            result = requests.get("https://www.googleapis.com/books/v1/volumes?q="+query.replace(" ","+"))
            for r in result.json()['items']:
                v = dict()
                v['id'] = r['id']
                v['title'] = r['volumeInfo']['title']
                v['authors'] = r['volumeInfo'].get('authors', [])
                v['description'] = r['volumeInfo'].get('description', "")
                v['publisher'] = r['volumeInfo'].get('publisher', "")
                v['publishedDate'] = r['volumeInfo'].get('publishedDate', "")
                v['tags'] = r['volumeInfo'].get('categories', [])
                v['rating'] = r['volumeInfo'].get('averageRating', 0)
                if r['volumeInfo'].get('imageLinks'):
                    v['cover'] = r['volumeInfo']['imageLinks']['thumbnail']
                else:
                    v['cover'] = "/../../../static/generic_cover.jpg"
                v['source'] = {
                    "id": "google",
                    "description": "Google Books",
                    "link": "https://books.google.com/"}
                v['url'] = ""
                val.append(v)
            return val


