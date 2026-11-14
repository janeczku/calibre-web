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
import re

from flask import current_app
from flask_babel import lazy_gettext as N_

from . import logger, themes

log = logger.create()

MAX_ZIP_BYTES = 20 * 1024 * 1024
MAX_ENTRIES = 2000
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_INFO_BYTES = 64 * 1024
STAGE_TTL = 30 * 60
MAX_REDIRECTS = 5
MAX_VERSION_LEN = 32

GITHUB_API_VERSION = "2026-03-10"
GITHUB_HOSTS = {"api.github.com", "github.com", "codeload.github.com",
                "objects.githubusercontent.com", "release-assets.githubusercontent.com"}

_REPOSITORY_RE = re.compile(r"^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})/?$")
_VERSION_RE = re.compile(r"^\d+(\.\d+)*$")

_warned_repository = set()


class ThemeInstallError(Exception):
    def __init__(self, code, message):
        super().__init__(code)
        self.code = code
        self.message = message


def parse_version(value):
    """Numeric tuple of a version like '1.2' or 'v1.2.0' (trailing zeros dropped), else None."""
    if not isinstance(value, str):
        return None
    if value[:1] in ("v", "V"):
        value = value[1:]
    if not _VERSION_RE.match(value):
        return None
    parts = [int(p) for p in value.split(".")]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def is_newer(latest, installed):
    latest, installed = parse_version(latest), parse_version(installed)
    return latest is not None and installed is not None and latest > installed


def display_version(value):
    if isinstance(value, str):
        return value[:MAX_VERSION_LEN]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def parse_repository(value):
    """(owner, repo) of a https://github.com/owner/repo URL, else None."""
    if not isinstance(value, str):
        return None
    match = _REPOSITORY_RE.match(value)
    if not match:
        return None
    owner, repo = match.groups()
    if repo.endswith(".git"):
        repo = repo[:-4]
    return (owner, repo) if repo else None


def bundled_identifiers():
    path = os.path.join(current_app.root_path, "themes")
    return set(os.listdir(path)) if os.path.isdir(path) else set()


def installed_themes():
    bundled_path = os.path.join(current_app.root_path, "themes")
    rows = []
    for theme in themes.get_available_themes():
        raw = theme.info.get("repository")
        parsed = parse_repository(raw)
        if raw is not None and parsed is None and theme.identifier not in _warned_repository:
            _warned_repository.add(theme.identifier)
            log.warning("Theme '%s': invalid 'repository' in info.json, ignored", theme.identifier)
        rows.append({
            "identifier": theme.identifier,
            "name": theme.name,
            "version": display_version(theme.info.get("version")),
            "bundled": os.path.dirname(os.path.abspath(theme.path)) == bundled_path,
            "repository": "https://github.com/{}/{}".format(*parsed) if parsed else None,
        })
    return rows
