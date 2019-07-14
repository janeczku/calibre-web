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

from . import constants, logger, cache_buster, cli, config_sql, ub, db, services
from .reverseproxy import ReverseProxied
from .server import WebServer


_mimetypes_txt = os.path.join(constants.STATIC_DIR, 'mimetypes.txt')
mimetypes.init((_mimetypes_txt,))


lm = LoginManager()
lm.login_view = 'web.login'
lm.anonymous_user = ub.Anonymous


ub.init_db(cli.settingspath)
# pylint: disable=no-member
config = config_sql.load_configuration(ub.session)

searched_ids = {}
web_server = WebServer()

babel = Babel()
_BABEL_TRANSLATIONS = set()

log = logger.create()


def create_app():
    app = Flask(__name__)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    # For python2 convert path to unicode
    if constants.PY2:
        app.static_folder = app.static_folder.decode('utf-8')
        app.root_path = app.root_path.decode('utf-8')
        app.instance_path = app.instance_path .decode('utf-8')

    cache_buster.init_cache_busting(app)

    log.info('Starting Calibre Web...')
    Principal(app)
    lm.init_app(app)
    app.secret_key = os.getenv('SECRET_KEY', 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT')

    web_server.init_app(app, config)
    db.setup_db(config)

    babel.init_app(app)
    _BABEL_TRANSLATIONS.update(str(item) for item in babel.list_translations())
    _BABEL_TRANSLATIONS.add('en')

    if services.ldap:
        services.ldap.init_app(app, config)
    if services.goodreads:
        services.goodreads.connect(config.config_goodreads_api_key, config.config_goodreads_api_secret, config.config_use_goodreads)

    return app

@babel.localeselector
def negociate_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    # user = None
    if user is not None and hasattr(user, "locale"):
        if user.nickname != 'Guest':   # if the account is the guest account bypass the config lang settings
            return user.locale

    preferred = set()
    if request.accept_languages:
        for x in request.accept_languages.values():
            try:
                preferred.add(str(LC.parse(x.replace('-', '_'))))
            except (UnknownLocaleError, ValueError) as e:
                log.warning('Could not parse locale "%s": %s', x, e)
                # preferred.append('en')

    return negotiate_locale(preferred or ['en'], _BABEL_TRANSLATIONS)


def get_locale():
    return request._locale


@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    return user.timezone if user else None

from .updater import Updater
updater_thread = Updater()


def main():
    app = create_app()
    with app.app_context():
        from cps.web import web as _web
        app.register_blueprint(_web)

        from cps.opds import opds as _web_opds
        app.register_blueprint(_web_opds)

        from cps.jinjia import jinjia as _web_jinjia
        app.register_blueprint(_web_jinjia)

        from cps.about import about as _web_about
        app.register_blueprint(_web_about)

        from cps.shelf import shelf as _web_shelf
        app.register_blueprint(_web_shelf)

        from cps.admin import admi as _web_admin
        app.register_blueprint(_web_admin)

        from cps.gdrive import gdrive as _web_gdrive
        app.register_blueprint(_web_gdrive)

        from cps.editbooks import editbook as _web_editbook
        app.register_blueprint(_web_editbook)

        from cps.oauth_bb import oauth as _web_oauth

    success = web_server.start()
    sys.exit(0 if success else 1)
