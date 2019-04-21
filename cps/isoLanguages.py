#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2019 pwr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.

try:
    from iso639 import languages, __version__
    get = languages.get
except ImportError:
    from pycountry import languages as pyc_languages
    try:
        import pkg_resources
        __version__ = pkg_resources.get_distribution('pycountry').version + ' (PyCountry)'
        del pkg_resources
    except (ImportError, Exception):
        __version__ = "? (PyCountry)"

    def _copy_fields(l):
        l.part1 = l.alpha_2
        l.part3 = l.alpha_3
        return l

    def get(name=None, part1=None, part3=None):
        if (part3 is not None):
            return _copy_fields(pyc_languages.get(alpha_3=part3))
        if (part1 is not None):
            return _copy_fields(pyc_languages.get(alpha_2=part1))
        if (name is not None):
            return _copy_fields(pyc_languages.get(name=name))
