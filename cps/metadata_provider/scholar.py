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

from scholarly import scholarly

from cps.services.Metadata import Metadata

class scholar(Metadata):
    __name__ = "Google Scholar"
    __id__ = "googlescholar"

    def search(self, query, generic_cover=""):
        val = list()
        if self.active:
            scholar_gen = scholarly.search_pubs(' '.join(query.split('+')))
            i = 0
            for publication in scholar_gen:
                v = dict()
                v['id'] = publication['url_scholarbib'].split(':')[1]
                v['title'] = publication['bib'].get('title')
                v['authors'] = publication['bib'].get('author', [])
                v['description'] = publication['bib'].get('abstract', "")
                v['publisher'] = publication['bib'].get('venue', "")
                if publication['bib'].get('pub_year'):
                    v['publishedDate'] = publication['bib'].get('pub_year')+"-01-01"
                else:
                    v['publishedDate'] = ""
                v['tags'] = []
                v['rating'] = 0
                v['series'] = ""
                v['cover'] = ""
                v['url'] = publication.get('pub_url') or publication.get('eprint_url') or "",
                v['source'] = {
                    "id": self.__id__,
                    "description": "Google Scholar",
                    "link": "https://scholar.google.com/"
                }
                val.append(v)
                i += 1
                if (i >= 10):
                    break
        return val



