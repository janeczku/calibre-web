#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import logging
# from logging.handlers import SMTPHandler, RotatingFileHandler
# import os
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

with open(os.path.join(config.get_main_dir, 'cps/translations/iso639.pickle'), 'rb') as f:
   language_table = cPickle.load(f)

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
    logging.getLogger("book_formats").addHandler(file_handler)
    logging.getLogger("book_formats").setLevel(config.config_log_level)
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
