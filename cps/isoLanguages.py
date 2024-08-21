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
import sys

from .iso_language_names import LANGUAGE_NAMES as _LANGUAGE_NAMES
from . import logger
from .string_helper import strip_whitespaces

log = logger.create()


try:
    from iso639 import languages
    # iso_version = importlib.metadata.version("iso639")
    get = languages.get
    try:
        if sys.version_info >= (3, 12):
            import pkg_resources
    except ImportError:
        print("Python 3.12 isn't compatible with iso-639. Please install pycountry.")
except ImportError as ex:
    from pycountry import languages as pyc_languages
    #try:
    #    iso_version = importlib.metadata.version("pycountry") + ' (PyCountry)'
    #except (ImportError, Exception):
    #    iso_version = "?" + ' (PyCountry)'

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
    names = _LANGUAGE_NAMES.get(str(locale))
    if names is None:
        names = _LANGUAGE_NAMES.get(locale.language)
    return names


def get_language_name(locale, lang_code):
    UNKNOWN_TRANSLATION = "Unknown"
    names = get_language_names(locale)
    if names is None:
        log.error(f"Missing language names for locale: {str(locale)}/{locale.language}")
        return UNKNOWN_TRANSLATION

    name = names.get(lang_code, UNKNOWN_TRANSLATION)
    if name == UNKNOWN_TRANSLATION:
        log.error("Missing translation for language name: {}".format(lang_code))

    return name


def get_language_code_from_name(locale, language_names, remainder=None):
    language_names = set(strip_whitespaces(x).lower() for x in language_names if x)
    lang = list()
    for key, val in get_language_names(locale).items():
        val = val.lower()
        if val in language_names:
            lang.append(key)
            language_names.remove(val)
    if remainder is not None and language_names:
        remainder.extend(language_names)
    return lang


def get_valid_language_codes_from_code(locale, language_names, remainder=None):
    lang = list()
    if "" in language_names:
        language_names.remove("")
    for k, __ in get_language_names(locale).items():
        if k in language_names:
            lang.append(k)
            language_names.remove(k)
    if remainder is not None and len(language_names):
        remainder.extend(language_names)
    return lang


def get_lang3(lang):
    try:
        if len(lang) == 2:
            ret_value = get(part1=lang).part3
        elif len(lang) == 3:
            ret_value = lang
        else:
            ret_value = ""
    except KeyError:
        ret_value = lang
    return ret_value
