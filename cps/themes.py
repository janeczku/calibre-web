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
        "label": "Standard Theme",
        "css_files": (),
        "js_files": (),
        "body_class": "",
        "show_home_shortcuts": False,
        "profile_dropdown": False,
        "login_extra_buttons": False,
        "show_upload_loader": False
    },
    {
        "id": 1,
        "label": "caliBlur! Dark Theme",
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
        "login_extra_buttons": True,
        "show_upload_loader": True
    }
)

THEMES_BY_ID = {theme["id"]: theme for theme in THEMES}


def get_available_themes():
    return THEMES


def get_theme(theme_id):
    try:
        theme_id = int(theme_id)
    except (TypeError, ValueError):
        theme_id = 0
    return THEMES_BY_ID.get(theme_id, THEMES_BY_ID[0])


def is_valid_theme(theme_id):
    try:
        theme_id = int(theme_id)
    except (TypeError, ValueError):
        return False
    return theme_id in THEMES_BY_ID
