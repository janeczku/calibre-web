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

apikey = "57558043c53943d5d1e96a9ad425b0eb85532ee6"

class ComicVine(Metadata):
    __name__ = "ComicVine"

    def search(self, query):
        if self.active:
            headers = {
                'User-Agent': 'Not Evil Browser' # ,
            }
            result = requests.get("https://comicvine.gamespot.com/api/search?api_key="
                                  + apikey + "&resources=issue&query=" + query + "&sort=name:desc&format=json", headers=headers)
            return [result.json()['results']]


