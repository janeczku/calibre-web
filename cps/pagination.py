# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, cervinko, jkrehm, bodybybuddha, ok11,
#                            andy29485, idalin, Kyosfonica, wuqi, Kennyl, lemmsh,
#                            falgh1, grunjol, csitko, ytils, xybydy, trasba, vrabe,
#                            ruben-herold, marblepebble, JackED42, SiphonSquirrel,
#                            apetresc, nanu-c, mutschler
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

from math import ceil


# simple pagination for the feed
class Pagination(object):
    def __init__(self, page, per_page, total_count):
        self.page = int(page)
        self.per_page = int(per_page)
        self.total_count = int(total_count)

    @property
    def next_offset(self):
        return int(self.page * self.per_page)

    @property
    def previous_offset(self):
        return int((self.page - 2) * self.per_page)

    @property
    def last_offset(self):
        last = int(self.total_count) - int(self.per_page)
        if last < 0:
            last = 0
        return int(last)

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    # right_edge: last right_edges count of all pages are shown as number, means, if 10 pages are paginated -> 9,10 shwn
    # left_edge: first left_edges count of all pages are shown as number                                    -> 1,2 shwn
    # left_current: left_current count below current page are shown as number, means if current page 5      -> 3,4 shwn
    # left_current: right_current count above current page are shown as number, means if current page 5     -> 6,7 shwn
    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=4, right_edge=2):
        last = 0
        left_current = self.page - left_current - 1
        right_current = self.page + right_current + 1
        right_edge = self.pages - right_edge
        for num in range(1, (self.pages + 1)):
            if num <= left_edge or (left_current < num < right_current) or num > right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num
