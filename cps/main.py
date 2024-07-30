# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2022 OzzieIsaacs
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

import sys

from . import create_app, limiter
from .jinjia import jinjia
from flask import request


def request_username():
    return request.authorization.username


def main():
    app = create_app()

    from .web import web
    from .opds import opds
    from .admin import admi
    from .gdrive import gdrive
    from .editbooks import editbook
    from .about import about
    from .search import search
    from .search_metadata import meta
    from .shelf import shelf
    from .tasks_status import tasks
    from .error_handler import init_errorhandler
    from .remotelogin import remotelogin
    try:
        from .kobo import kobo, get_kobo_activated
        from .kobo_auth import kobo_auth
        from flask_limiter.util import get_remote_address
        kobo_available = get_kobo_activated()
    except (ImportError, AttributeError):  # Catch also error for not installed flask-WTF (missing csrf decorator)
        kobo_available = False
        kobo = kobo_auth = get_remote_address = None

    try:
        from .oauth_bb import oauth
        oauth_available = True
    except ImportError:
        oauth_available = False
        oauth = None

    from . import web_server
    init_errorhandler()

    app.register_blueprint(search)
    app.register_blueprint(tasks)
    app.register_blueprint(web)
    app.register_blueprint(opds)
    limiter.limit("3/minute", key_func=request_username)(opds)
    app.register_blueprint(jinjia)
    app.register_blueprint(about)
    app.register_blueprint(shelf)
    app.register_blueprint(admi)
    app.register_blueprint(remotelogin)
    app.register_blueprint(meta)
    app.register_blueprint(gdrive)
    app.register_blueprint(editbook)
    if kobo_available:
        app.register_blueprint(kobo)
        app.register_blueprint(kobo_auth)
        limiter.limit("3/minute", key_func=get_remote_address)(kobo)
    if oauth_available:
        app.register_blueprint(oauth)
    success = web_server.start()
    sys.exit(0 if success else 1)
