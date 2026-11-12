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
from flask_themes2 import IDENTIFIER, Theme, Themes, active_theme, packaged_themes_loader, static_file_url
from jinja2 import pass_context

from . import logger

log = logger.create()

DEFAULT_THEME = "standard"

# config_theme (integer) values used before themes were stored by identifier
LEGACY_THEME_IDS = {0: "standard", 1: "caliblur"}

_warned_missing = set()


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
    if identifier and identifier not in _warned_missing:
        _warned_missing.add(identifier)
        log.warning("Theme '%s' not found, using '%s'", identifier, DEFAULT_THEME)
    return loaded[DEFAULT_THEME]


def is_valid_theme(identifier):
    return identifier in _loaded_themes()


def get_theme_identifier(identifier, blueprint_name=None):
    if blueprint_name == "basic":
        return DEFAULT_THEME
    return get_theme(identifier).identifier


def theme_chain(theme):
    """The theme followed by its parent, grandparent, ... (options.parent)."""
    chain = [theme]
    parent = theme.options.get("parent")
    while parent:
        if parent in (t.identifier for t in chain):
            log.warning("Theme '%s': parent '%s' forms a cycle, ignored", chain[-1].identifier, parent)
            break
        if parent not in _loaded_themes():
            log.warning("Theme '%s': parent '%s' not found, ignored", chain[-1].identifier, parent)
            break
        chain.append(_loaded_themes()[parent])
        parent = chain[-1].options.get("parent")
    return chain


def resolve_template(identifier, templatename):
    """First theme in the chain of `identifier` that has the template, else standard."""
    for theme in theme_chain(get_theme(identifier)):
        if os.path.exists(os.path.join(theme.templates_path, templatename)):
            return "_themes/{}/{}".format(theme.identifier, templatename)
    return "_themes/{}/{}".format(DEFAULT_THEME, templatename)


@pass_context
def theme_template(ctx, templatename):
    """Jinja global ``theme()``."""
    return resolve_template(active_theme(ctx), templatename)


def theme_assets(theme, kind):
    """URLs of the static files listed in options[kind] of the theme and its ancestors, ancestors first."""
    return [static_file_url(t, filename)
            for t in reversed(theme_chain(theme)) for filename in t.options.get(kind, [])]


def theme_body_class(theme):
    return " ".join(c for c in (t.options.get("body_class") for t in reversed(theme_chain(theme))) if c)


def get_user_themes_dir(settings_path):
    """Folder with user-installed themes: $CALIBRE_THEMES_DIR, else 'themes' next to app.db."""
    return os.environ.get("CALIBRE_THEMES_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(settings_path)), "themes")


def user_themes_loader(app):
    """Flask-Themes2 loader for the user themes folder; never shadows a bundled theme."""
    path = app.config.get("CW_USER_THEMES_DIR")
    if not path or not os.path.isdir(path):
        return []
    bundled_path = os.path.join(app.root_path, "themes")
    bundled = set(os.listdir(bundled_path)) if os.path.isdir(bundled_path) else set()
    loaded = []
    for folder in sorted(os.listdir(path)):
        theme_path = os.path.join(path, folder)
        if not os.path.isdir(theme_path):
            continue
        try:
            theme = Theme(theme_path)
        except Exception as e:
            log.warning("Theme folder '%s' skipped: invalid info.json (%s)", folder, e)
            continue
        if theme.identifier != folder or not IDENTIFIER.match(folder):
            log.warning("Theme folder '%s' skipped: identifier must equal the folder name "
                        "and use only letters, digits and underscores", folder)
        elif folder in bundled:
            log.warning("Theme folder '%s' skipped: a bundled theme has the same identifier", folder)
        else:
            loaded.append(theme)
    return loaded


def init_app_themes(app, settings_path):
    app.config["CW_USER_THEMES_DIR"] = get_user_themes_dir(settings_path)
    log.info("Loading user themes from %s", app.config["CW_USER_THEMES_DIR"])
    Themes().init_themes(app, app_identifier="cps", loaders=[packaged_themes_loader, user_themes_loader])
    app.jinja_env.globals["theme"] = theme_template
    app.jinja_env.globals["theme_assets"] = theme_assets
    app.jinja_env.globals["theme_body_class"] = theme_body_class
