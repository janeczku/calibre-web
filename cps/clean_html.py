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
import re

log = logger.create()

CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

try:
    import nh3
    from nh3 import clean as clean_html
    bleach = False
    BASE_ALLOWED_TAGS = nh3.ALLOWED_TAGS
    BASE_ALLOWED_ATTRIBUTES = nh3.ALLOWED_ATTRIBUTES
except ImportError:
    # at least bleach 6.0 is needed -> incomplatible change from list arguments to set arguments
    from bleach import clean as clean_html
    from bleach.sanitizer import ALLOWED_ATTRIBUTES as BASE_ALLOWED_ATTRIBUTES
    from bleach.sanitizer import ALLOWED_TAGS as BASE_ALLOWED_TAGS
    bleach = True

ALLOWED_TAGS = set(BASE_ALLOWED_TAGS) | {"p", "span", "div", "pre", "br", "h1", "h2", "h3", "h4", "h5", "h6", "img"}
ALLOWED_ATTRIBUTES = {
    key: set(value) for key, value in BASE_ALLOWED_ATTRIBUTES.items()
}
ALLOWED_ATTRIBUTES["*"] = set(ALLOWED_ATTRIBUTES.get("*", set())) | {"class", "style"}
ALLOWED_ATTRIBUTES["a"] = set(ALLOWED_ATTRIBUTES.get("a", set())) | {"href", "title", "rel"}
ALLOWED_ATTRIBUTES["img"] = set(ALLOWED_ATTRIBUTES.get("img", set())) | {"src", "alt", "title", "width", "height"}


def _normalize_html_input(unsafe_text):
    return CONTROL_CHAR_RE.sub("", unsafe_text)


def clean_string(unsafe_text, book_id=0):
    try:
        unsafe_text = _normalize_html_input(unsafe_text)
        if bleach:
            safe_text = clean_html(unsafe_text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        else:
            safe_text = clean_html(unsafe_text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, link_rel=None)
    except ParserError as e:
        log.error("Comments of book {} are corrupted: {}".format(book_id, e))
        safe_text = ""
    except TypeError as e:
        log.error("Comments can't be parsed, maybe 'lxml' is too new, try installing 'bleach': {}".format(e))
        safe_text = ""
    return safe_text
