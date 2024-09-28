# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs
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

from . import logger
from lxml.etree import ParserError

log = logger.create()

try:
    from nh3 import clean as clean_html
    from nh3 import ALLOWED_TAGS
    nh3 = True
except ImportError:
    nh3 = False


def clean_string(unsafe_text, book_id=0):
    try:
        if nh3:
            allowed_tags = list(ALLOWED_TAGS)
            allowed_tags.extend(["p", "span", "div", "pre", "br", "h1", "h2", "h3", "h4", "h5", "h6"])
            safe_text = clean_html(unsafe_text, tags=set(allowed_tags))
        else:
            safe_text = clean_html(unsafe_text)
    except ParserError as e:
        log.error("Comments of book {} are corrupted: {}".format(book_id, e))
        safe_text = ""
    except TypeError as e:
        log.error("Comments can't be parsed, maybe 'lxml' is too new, try installing 'nh3': {}".format(e))
        safe_text = ""
    return safe_text
