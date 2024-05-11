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

try:
    # at least bleach 6.0 is needed -> incomplatible change from list arguments to set arguments
    from bleach import clean_text as clean_html
    BLEACH = True
except ImportError:
    try:
        BLEACH = False
        from nh3 import clean as clean_html
    except ImportError:
        try:
            BLEACH = False
            from lxml.html.clean import clean_html
        except ImportError:
            clean_html = None


log = logger.create()


def clean_string(unsafe_text, book_id=0):
    try:
        if BLEACH:
            safe_text = clean_html(unsafe_text, tags=set(), attributes=set())
        else:
            safe_text = clean_html(unsafe_text)
    except ParserError as e:
        log.error("Comments of book {} are corrupted: {}".format(book_id, e))
        safe_text = ""
    except TypeError as e:
        log.error("Comments can't be parsed, maybe 'lxml' is too new, try installing 'bleach': {}".format(e))
        safe_text = ""
    return safe_text
