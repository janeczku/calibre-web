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

import os

from flask import current_app
from flask_themes2 import Themes, active_theme, static_file_url
from jinja2 import pass_context

from . import logger

log = logger.create()

DEFAULT_THEME = "standard"

# config_theme (integer) values used before themes were stored by identifier
LEGACY_THEME_IDS = {0: "standard", 1: "caliblur"}


def legacy_theme_identifier(theme_id):
    try:
        return LEGACY_THEME_IDS.get(int(theme_id), DEFAULT_THEME)
    except (TypeError, ValueError):
        return DEFAULT_THEME


def _loaded_themes():
    return current_app.theme_manager.themes


def get_available_themes():
    return sorted(_loaded_themes().values(), key=lambda theme: theme.name.lower())


def get_theme(identifier):
    loaded = _loaded_themes()
    if identifier in loaded:
        return loaded[identifier]
    if identifier:
        log.warning("Theme '%s' not found, using '%s'", identifier, DEFAULT_THEME)
    return loaded[DEFAULT_THEME]


def is_valid_theme(identifier):
    return identifier in _loaded_themes()


def get_theme_identifier(identifier, blueprint_name=None):
    if blueprint_name == "basic":
        return DEFAULT_THEME
    return get_theme(identifier).identifier


@pass_context
def theme_template(ctx, templatename):
    """Jinja global ``theme()``: the active theme's template, else the standard one."""
    theme = _loaded_themes().get(active_theme(ctx))
    if theme and os.path.exists(os.path.join(theme.templates_path, templatename)):
        return "_themes/{}/{}".format(theme.identifier, templatename)
    return "_themes/{}/{}".format(DEFAULT_THEME, templatename)


def theme_assets(theme, kind):
    """URLs of the theme's own static files listed in info.json options[kind]."""
    return [static_file_url(theme, filename) for filename in theme.options.get(kind, [])]


def init_app_themes(app):
    Themes().init_themes(app, app_identifier="cps")
    app.jinja_env.globals["theme"] = theme_template
    app.jinja_env.globals["theme_assets"] = theme_assets
