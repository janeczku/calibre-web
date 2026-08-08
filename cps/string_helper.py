# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2024 OzzieIsaacs
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
_SPECIAL_WHITESPACE_CHARS = {"\x00", "\u200b", "\u200c", "\u200d", "\ufeff"}


def strip_whitespaces(text):
    if text is None:
        return ""
    if not isinstance(text, str):
        return text

    start = 0
    end = len(text)

    while start < end and (text[start].isspace() or text[start] in _SPECIAL_WHITESPACE_CHARS):
        start += 1

    while end > start and (text[end - 1].isspace() or text[end - 1] in _SPECIAL_WHITESPACE_CHARS):
        end -= 1

    return text[start:end]

