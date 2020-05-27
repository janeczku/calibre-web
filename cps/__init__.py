# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, cervinko, jkrehm, bodybybuddha, ok11,
#                            andy29485, idalin, Kyosfonica, wuqi, Kennyl, lemmsh,
#                            falgh1, grunjol, csitko, ytils, xybydy, trasba, vrabe,
#                            ruben-herold, marblepebble, JackED42, SiphonSquirrel,
#                            apetresc, nanu-c, mutschler
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

from __future__ import division, print_function, unicode_literals
import sys
import os
import mimetypes

from babel import Locale as LC
from babel import negotiate_locale
from babel.core import UnknownLocaleError
from flask import Flask, request, g
from flask_login import LoginManager
from flask_babel import Babel
from flask_principal import Principal

from . import config_sql, logger, cache_buster, cli, ub, db
from .reverseproxy import ReverseProxied
from .server import WebServer


mimetypes.init()
mimetypes.add_type('application/xhtml+xml', '.xhtml')
mimetypes.add_type('application/epub+zip', '.epub')
mimetypes.add_type('application/fb2+zip', '.fb2')
mimetypes.add_type('application/x-mobipocket-ebook', '.mobi')
mimetypes.add_type('application/x-mobipocket-ebook', '.prc')
mimetypes.add_type('application/vnd.amazon.ebook', '.azw')
mimetypes.add_type('application/x-cbr', '.cbr')
mimetypes.add_type('application/x-cbz', '.cbz')
mimetypes.add_type('application/x-cbt', '.cbt')
mimetypes.add_type('image/vnd.djvu', '.djvu')
mimetypes.add_type('application/mpeg', '.mpeg')
mimetypes.add_type('application/mpeg', '.mp3')
mimetypes.add_type('application/mp4', '.m4a')
mimetypes.add_type('application/mp4', '.m4b')
mimetypes.add_type('application/ogg', '.ogg')
mimetypes.add_type('application/ogg', '.oga')

app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    REMEMBER_COOKIE_SAMESITE='Lax',  # will be available in flask-login 0.5.1 earliest
)


lm = LoginManager()
lm.login_view = 'web.login'
lm.anonymous_user = ub.Anonymous
lm.session_protection = 'strong'

ub.init_db(cli.settingspath)
# pylint: disable=no-member
config = config_sql.load_configuration(ub.session)

searched_ids = {}
web_server = WebServer()

babel = Babel()
_BABEL_TRANSLATIONS = set()

log = logger.create()

from . import services

calibre_db = db.CalibreDB()

def create_app():
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    # For python2 convert path to unicode
    if sys.version_info < (3, 0):
        app.static_folder = app.static_folder.decode('utf-8')
        app.root_path = app.root_path.decode('utf-8')
        app.instance_path = app.instance_path .decode('utf-8')

    cache_buster.init_cache_busting(app)

    log.info('Starting Calibre Web...')
    Principal(app)
    lm.init_app(app)
    app.secret_key = os.getenv('SECRET_KEY', config_sql.get_flask_session_key(ub.session))

    web_server.init_app(app, config)
    calibre_db.setup_db(config, cli.settingspath)
    calibre_db.start()

    babel.init_app(app)
    _BABEL_TRANSLATIONS.update(str(item) for item in babel.list_translations())
    _BABEL_TRANSLATIONS.add('en')

    if services.ldap:
        services.ldap.init_app(app, config)
    if services.goodreads_support:
        services.goodreads_support.connect(config.config_goodreads_api_key,
                                           config.config_goodreads_api_secret,
                                           config.config_use_goodreads)

    return app

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    # user = None
    if user is not None and hasattr(user, "locale"):
        if user.nickname != 'Guest':   # if the account is the guest account bypass the config lang settings
            return user.locale

    preferred = list()
    if request.accept_languages:
        for x in request.accept_languages.values():
            try:
                preferred.append(str(LC.parse(x.replace('-', '_'))))
            except (UnknownLocaleError, ValueError) as e:
                log.debug('Could not parse locale "%s": %s', x, e)

    return negotiate_locale(preferred or ['en'], _BABEL_TRANSLATIONS)


@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    return user.timezone if user else None

from .updater import Updater
updater_thread = Updater()
updater_thread.start()
