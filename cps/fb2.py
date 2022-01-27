# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018 lemmsh, cervinko, OzzieIsaacs
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

from lxml import etree

from .constants import BookMeta


def get_fb2_info(tmp_file_path, original_file_extension):

    ns = {
        'fb': 'http://www.gribuser.ru/xml/fictionbook/2.0',
        'l': 'http://www.w3.org/1999/xlink',
    }

    fb2_file = open(tmp_file_path, encoding="utf-8")
    tree = etree.fromstring(fb2_file.read().encode())

    authors = tree.xpath('/fb:FictionBook/fb:description/fb:title-info/fb:author', namespaces=ns)

    def get_author(element):
        last_name = element.xpath('fb:last-name/text()', namespaces=ns)
        if len(last_name):
            last_name = last_name[0]
        else:
            last_name = u''
        middle_name = element.xpath('fb:middle-name/text()', namespaces=ns)
        if len(middle_name):
            middle_name = middle_name[0]
        else:
            middle_name = u''
        first_name = element.xpath('fb:first-name/text()', namespaces=ns)
        if len(first_name):
            first_name = first_name[0]
        else:
            first_name = u''
        return (first_name + u' '
                + middle_name + u' '
                + last_name)

    author = str(", ".join(map(get_author, authors)))

    title = tree.xpath('/fb:FictionBook/fb:description/fb:title-info/fb:book-title/text()', namespaces=ns)
    if len(title):
        title = str(title[0])
    else:
        title = u''
    description = tree.xpath('/fb:FictionBook/fb:description/fb:publish-info/fb:book-name/text()', namespaces=ns)
    if len(description):
        description = str(description[0])
    else:
        description = u''

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title,
        author=author,
        cover=None,
        description=description,
        tags="",
        series="",
        series_id="",
        languages="",
        publisher="")
