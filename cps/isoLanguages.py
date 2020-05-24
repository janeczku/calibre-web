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

from __future__ import division, print_function, unicode_literals

from .iso_language_names import LANGUAGE_NAMES as _LANGUAGE_NAMES


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
        l.part1 = getattr(l, 'alpha_2', None)
        l.part3 = getattr(l, 'alpha_3', None)
        return l

    def get(name=None, part1=None, part3=None):
        if part3 is not None:
            return _copy_fields(pyc_languages.get(alpha_3=part3))
        if part1 is not None:
            return _copy_fields(pyc_languages.get(alpha_2=part1))
        if name is not None:
            return _copy_fields(pyc_languages.get(name=name))


def get_language_names(locale):
    return _LANGUAGE_NAMES.get(locale)


def get_language_name(locale, lang_code):
    return get_language_names(locale)[lang_code]


def get_language_codes(locale, language_names, remainder=None):
    language_names = set(x.strip().lower() for x in language_names if x)
    languages = list()
    for k, v in get_language_names(locale).items():
        v = v.lower()
        if v in language_names:
            languages.append(k)
            language_names.remove(v)
    if remainder is not None:
        remainder.extend(language_names)
    return languages
