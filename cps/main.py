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
from flask import request, redirect, url_for


def request_username():
    return request.authorization.username if request.authorization else ""


def main():
    app = create_app()

    from .web import web
    from .basic import basic
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
    from .api_v1 import api_v1
    from .spa import spa
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
    app.register_blueprint(basic)
    limiter.limit("3/minute", key_func=request_username)(opds)
    app.register_blueprint(opds)
    app.register_blueprint(jinjia)
    app.register_blueprint(about)
    app.register_blueprint(shelf)
    app.register_blueprint(admi)
    app.register_blueprint(remotelogin)
    app.register_blueprint(meta)
    app.register_blueprint(gdrive)
    app.register_blueprint(editbook)
    app.register_blueprint(api_v1)
    app.register_blueprint(spa)
    if kobo_available:
        limiter.limit("3/minute", key_func=get_remote_address)(kobo)
        app.register_blueprint(kobo)
        app.register_blueprint(kobo_auth)
    if oauth_available:
        app.register_blueprint(oauth)

    @app.before_request
    def redirect_to_spa():
        if request.method != 'GET':
            return
            
        path = request.path
        
        # Keep API, static, media, and download endpoints untouched
        if (path.startswith('/api/') or 
            path.startswith('/ajax/') or 
            path.startswith('/opds/') or 
            path.startswith('/kobo/') or 
            path.startswith('/static/') or 
            path.startswith('/spa') or
            path.startswith('/cover/') or
            path.startswith('/series_cover/') or
            path.startswith('/download/') or
            path.startswith('/read/') or
            path in ('/favicon.ico', '/robots.txt', '/apple-touch-icon.png')):
            return

        # Explicit redirects
        if path == '/login':
            return redirect('/spa/login')
        elif path == '/register':
            return redirect('/spa/register')
        elif path.startswith('/admin/config') or path.startswith('/admin/dbconfig'):
            return redirect('/spa/config')
        elif path.startswith('/admin'):
            return redirect('/spa/admin')
        elif path.startswith('/edit/'):
            parts = path.split('/')
            if len(parts) >= 3 and parts[2].isdigit():
                return redirect(f'/spa/edit/{parts[2]}')
            return redirect('/spa')
        
        return redirect('/spa')

    success = web_server.start()
    sys.exit(0 if success else 1)

