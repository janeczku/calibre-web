#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import logging
# from logging.handlers import SMTPHandler, RotatingFileHandler
# import os

from flask import Flask# , request, current_app
from flask_login import LoginManager
from flask_babel import Babel # , lazy_gettext as _l
import cache_buster
from reverseproxy import ReverseProxied
import logging
from logging.handlers import RotatingFileHandler
from flask_principal import Principal
# from flask_sqlalchemy import SQLAlchemy
import os
import ub
from ub import Config, Settings
import cPickle


# Normal
babel = Babel()
lm = LoginManager()
lm.login_view = 'web.login'
lm.anonymous_user = ub.Anonymous



ub_session = ub.session
# ub_session.start()
config = Config()


import db

with open(os.path.join(config.get_main_dir, 'cps/translations/iso639.pickle'), 'rb') as f:
   language_table = cPickle.load(f)

searched_ids = {}


from worker import WorkerThread

global_WorkerThread = WorkerThread()

from server import server
Server = server()


def create_app():
    app = Flask(__name__)
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
    babel.init_app(app)
    app.secret_key = os.getenv('SECRET_KEY', 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT')
    Server.init_app(app)
    db.setup_db()
    global_WorkerThread.start()

    # app.config.from_object(config_class)
    # db.init_app(app)
    # login.init_app(app)


    return app
