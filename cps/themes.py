# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2026
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

THEMES = (
    {
        "id": 0,
        "identifier": "standard",
        "label": "Standard Theme",
        "configurable": True,
        "css_files": (),
        "js_files": (),
        "body_class": "",
        "show_home_shortcuts": False,
        "profile_dropdown": False,
        "show_upload_loader": False
    },
    {
        "id": 1,
        "identifier": "caliblur",
        "label": "caliBlur! Dark Theme",
        "configurable": True,
        "css_files": (
            "css/caliBlur.css",
            "css/caliBlur_override.css"
        ),
        "js_files": (
            "js/libs/jquery.visible.min.js",
            "js/libs/compromise.min.js",
            "js/libs/readmore.min.js",
            "js/caliBlur.js"
        ),
        "body_class": "blur",
        "show_home_shortcuts": True,
        "profile_dropdown": True,
        "show_upload_loader": True
    },
    {
        "id": 2,
        "identifier": "simple",
        "label": "Simple Theme",
        "configurable": False,
        "css_files": (),
        "js_files": (),
        "body_class": "",
        "show_home_shortcuts": False,
        "profile_dropdown": False,
        "show_upload_loader": False
    }
)

THEMES_BY_ID = {theme["id"]: theme for theme in THEMES}
THEMES_BY_IDENTIFIER = {theme["identifier"]: theme for theme in THEMES}
DEFAULT_THEME = THEMES_BY_ID[0]
SIMPLE_THEME_IDENTIFIER = THEMES_BY_ID[2]["identifier"]


def get_available_themes():
    return [theme for theme in THEMES if theme["configurable"]]


def get_default_theme():
    return DEFAULT_THEME


def get_theme(theme_id):
    try:
        theme_id = int(theme_id)
    except (TypeError, ValueError):
        return DEFAULT_THEME
    return THEMES_BY_ID.get(theme_id, DEFAULT_THEME)


def is_valid_theme(theme_id):
    try:
        theme_id = int(theme_id)
    except (TypeError, ValueError):
        return False
    theme = THEMES_BY_ID.get(theme_id)
    return bool(theme and theme["configurable"])


def get_theme_identifier(theme_id, blueprint_name=None):
    if blueprint_name == "basic":
        return SIMPLE_THEME_IDENTIFIER
    return get_theme(theme_id)["identifier"]


def get_theme_by_identifier(identifier):
    return THEMES_BY_IDENTIFIER.get(identifier, DEFAULT_THEME)
