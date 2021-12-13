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
import abc
from typing import Dict, List, Optional, TypedDict, Union


class Metadata:
    __name__ = "Generic"
    __id__ = "generic"

    def __init__(self):
        self.active = True

    def set_status(self, state):
        self.active = state

    @abc.abstractmethod
    def search(self, query: str, generic_cover: str):
        pass


class MetaSourceInfo(TypedDict):
    id: str
    description: str
    link: str


class MetaRecord(TypedDict):
    id: Union[str, int]
    title: str
    authors: List[str]
    url: str
    cover: str
    series: Optional[str]
    series_index: Optional[Union[int, float]]
    tags: Optional[List[str]]
    publisher: Optional[str]
    publishedDate: Optional[str]
    rating: Optional[int]
    description: Optional[str]
    source: MetaSourceInfo
    languages: Optional[List[str]]
    identifiers: Dict[str, Union[str, int]]
