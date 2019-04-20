#!/usr/bin/env python
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

import mimetypes
from flask import Flask, request, g
from flask_login import LoginManager
from flask_babel import Babel
import cache_buster
from reverseproxy import ReverseProxied
import logging
from logging.handlers import RotatingFileHandler
from flask_principal import Principal
from babel.core import UnknownLocaleError
from babel import Locale as LC
from babel import negotiate_locale
import os
import ub
import sys
from ub import Config, Settings
try:
    import cPickle
except ImportError:
    import pickle as cPickle


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

lm = LoginManager()
lm.login_view = 'web.login'
lm.anonymous_user = ub.Anonymous


ub.init_db()
config = Config()

import db

try:
    with open(os.path.join(config.get_main_dir, 'cps/translations/iso639.pickle'), 'rb') as f:
        language_table = cPickle.load(f)
except cPickle.UnpicklingError as error:
    # app.logger.error("Can't read file cps/translations/iso639.pickle: %s", error)
    print("Can't read file cps/translations/iso639.pickle: %s" % error)
    sys.exit(1)


searched_ids = {}


from worker import WorkerThread
global_WorkerThread = WorkerThread()

from server import server
Server = server()

babel = Babel()

def create_app():
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    cache_buster.init_cache_busting(app)

    formatter = logging.Formatter(
        "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    try:
        file_handler = RotatingFileHandler(config.get_config_logfile(), maxBytes=50000, backupCount=2)
    except IOError:
        file_handler = RotatingFileHandler(os.path.join(config.get_main_dir, "calibre-web.log"),
                                           maxBytes=50000, backupCount=2)
        # ToDo: reset logfile value in config class
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(config.config_log_level)

    app.logger.info('Starting Calibre Web...')
    # logging.getLogger("uploader").addHandler(file_handler)
    # logging.getLogger("uploader").setLevel(config.config_log_level)
    Principal(app)
    lm.init_app(app)
    app.secret_key = os.getenv('SECRET_KEY', 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT')
    Server.init_app(app)
    db.setup_db()
    babel.init_app(app)
    global_WorkerThread.start()

    return app

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    # user = None
    if user is not None and hasattr(user, "locale"):
        if user.nickname != 'Guest':   # if the account is the guest account bypass the config lang settings
            return user.locale
    translations = [str(item) for item in babel.list_translations()] + ['en']
    preferred = list()
    for x in request.accept_languages.values():
        try:
            preferred.append(str(LC.parse(x.replace('-', '_'))))
        except (UnknownLocaleError, ValueError) as e:
            app.logger.debug("Could not parse locale: %s", e)
            preferred.append('en')
    return negotiate_locale(preferred, translations)


@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone

from updater import Updater
updater_thread = Updater()
