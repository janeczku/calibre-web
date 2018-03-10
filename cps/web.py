#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from pydrive.auth import GoogleAuth
    from googleapiclient.errors import HttpError
    gdrive_support = True
except ImportError:
    gdrive_support = False

try:
    from goodreads.client import GoodreadsClient
    goodreads_support = True
except ImportError:
    goodreads_support = False

try:
    import Levenshtein
    levenshtein_support = True
except ImportError:
    levenshtein_support = False

try:
    from functools import reduce
except ImportError:
    pass  # We're not using Python 3

import mimetypes
import logging
from logging.handlers import RotatingFileHandler
import textwrap
from flask import (Flask, render_template, request, Response, redirect,
                   url_for, send_from_directory, make_response, g, flash,
                   abort, Markup, stream_with_context)
from flask import __version__ as flaskVersion
import cache_buster
import ub
from ub import config
import helper
import os
import errno
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import false
from sqlalchemy.exc import IntegrityError
from sqlalchemy import __version__ as sqlalchemyVersion
from math import ceil
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_principal import Principal
from flask_principal import __version__ as flask_principalVersion
from flask_babel import Babel
from flask_babel import gettext as _
import requests
import zipfile
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.datastructures import Headers
from babel import Locale as LC
from babel import negotiate_locale
from babel import __version__ as babelVersion
from babel.dates import format_date, format_datetime
from functools import wraps
import base64
from sqlalchemy.sql import *
import json
import datetime
from iso639 import languages as isoLanguages
from iso639 import __version__ as iso639Version
from uuid import uuid4
import os.path
import sys
import subprocess
import re
import db
from shutil import move, copyfile
from tornado.ioloop import IOLoop
import shutil
import gdriveutils
import tempfile
import hashlib
from redirect import redirect_back, is_safe_url

from tornado import version as tornadoVersion
from socket import error as SocketError

try:
    from urllib.parse import quote
    from imp import reload
except ImportError:
    from urllib import quote

try:
    from flask_login import __version__ as flask_loginVersion
except ImportError:
    from flask_login.__about__ import __version__ as flask_loginVersion

import time

current_milli_time = lambda: int(round(time.time() * 1000))


# Global variables
gdrive_watch_callback_token = 'target=calibreweb-watch_files'
global_task = None

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'epub', 'mobi', 'azw', 'azw3', 'cbr', 'cbz', 'cbt', 'djvu', 'prc', 'doc', 'docx', 'fb2'])


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Also, the decorated class cannot be
    inherited from. Other than that, there are no restrictions that apply
    to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)


@Singleton
class Gauth:
    def __init__(self):
        self.auth = GoogleAuth(settings_file='settings.yaml')


@Singleton
class Gdrive:
    def __init__(self):
        self.drive = gdriveutils.getDrive(gauth=Gauth.Instance().auth)


class ReverseProxied(object):
    """Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    Code courtesy of: http://flask.pocoo.org/snippets/35/

    In nginx:
    location /myprefix {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }
    """

    def __init__(self, application):
        self.app = application

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ.get('PATH_INFO', '')
            if path_info and path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        server = environ.get('HTTP_X_FORWARDED_SERVER', '')
        if server:
            environ['HTTP_HOST'] = server
        return self.app(environ, start_response)


# Main code
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

app = (Flask(__name__))
app.wsgi_app = ReverseProxied(app.wsgi_app)
cache_buster.init_cache_busting(app)

gevent_server = None

formatter = logging.Formatter(
    "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
file_handler = RotatingFileHandler(config.get_config_logfile(), maxBytes=50000, backupCount=2)
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
app.logger.setLevel(config.config_log_level)

app.logger.info('Starting Calibre Web...')
logging.getLogger("book_formats").addHandler(file_handler)
logging.getLogger("book_formats").setLevel(config.config_log_level)

Principal(app)

babel = Babel(app)

import uploader

lm = LoginManager(app)
lm.init_app(app)
lm.login_view = 'login'
lm.anonymous_user = ub.Anonymous
app.secret_key = os.getenv('SECRET_KEY', 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT')
db.setup_db()

if config.config_log_level == logging.DEBUG:
    logging.getLogger("sqlalchemy.engine").addHandler(file_handler)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.pool").addHandler(file_handler)
    logging.getLogger("sqlalchemy.pool").setLevel(config.config_log_level)
    logging.getLogger("sqlalchemy.orm").addHandler(file_handler)
    logging.getLogger("sqlalchemy.orm").setLevel(config.config_log_level)


def is_gdrive_ready():
    return os.path.exists('settings.yaml') and os.path.exists('gdrive_credentials')


@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    if user is not None and hasattr(user, "locale"):
        return user.locale
    translations = [item.language for item in babel.list_translations()] + ['en']
    preferred = [x.replace('-', '_') for x in request.accept_languages.values()]
    return negotiate_locale(preferred, translations)


@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone


@lm.user_loader
def load_user(user_id):
    return ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()


@lm.header_loader
def load_user_from_header(header_val):
    if header_val.startswith('Basic '):
        header_val = header_val.replace('Basic ', '', 1)
    basic_username = basic_password = ''
    try:
        header_val = base64.b64decode(header_val)
        basic_username = header_val.split(':')[0]
        basic_password = header_val.split(':')[1]
    except TypeError:
        pass
    user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == basic_username.lower()).first()
    if user and check_password_hash(user.password, basic_password):
        return user
    return


def check_auth(username, password):
    user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == username.lower()).first()
    return bool(user and check_password_hash(user.password, password))


def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def updateGdriveCalibreFromLocal():
    gdriveutils.backupCalibreDbAndOptionalDownload(Gdrive.Instance().drive)
    gdriveutils.copyToDrive(Gdrive.Instance().drive, config.config_calibre_dir, False, True)
    for x in os.listdir(config.config_calibre_dir):
        if os.path.isdir(os.path.join(config.config_calibre_dir, x)):
            shutil.rmtree(os.path.join(config.config_calibre_dir, x))


def requires_basic_auth_if_no_ano(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if config.config_anonbrowse != 1:
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
        return f(*args, **kwargs)

    return decorated


# simple pagination for the feed
class Pagination(object):
    def __init__(self, page, per_page, total_count):
        self.page = int(page)
        self.per_page = int(per_page)
        self.total_count = int(total_count)

    @property
    def next_offset(self):
        return int(self.page * self.per_page)

    @property
    def previous_offset(self):
        return int((self.page - 2) * self.per_page)

    @property
    def last_offset(self):
        last = int(self.total_count) - int(self.per_page)
        if last < 0:
            last = 0
        return int(last)

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(self.pages, (self.pages + 1)):  # ToDo: can be simplified
            if num <= left_edge or (num > self.page - left_current - 1 and num < self.page + right_current) \
                    or num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


# pagination links in jinja
def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


app.jinja_env.globals['url_for_other_page'] = url_for_other_page


def login_required_if_no_ano(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if config.config_anonbrowse == 1:
            return func(*args, **kwargs)
        return login_required(func)(*args, **kwargs)
    return decorated_view


def remote_login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if config.config_remote_login:
            return f(*args, **kwargs)
        if request.is_xhr:
            data = {'status': 'error', 'message': 'Forbidden'}
            response = make_response(json.dumps(data, ensure_ascii=false))
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return response, 403
        abort(403)

    return inner


# custom jinja filters
@app.template_filter('shortentitle')
def shortentitle_filter(s):
    if len(s) > 60:
        s = s.split(':', 1)[0]
        if len(s) > 60:
            s = textwrap.wrap(s, 60, break_long_words=False)[0] + ' [...]'
    return s


@app.template_filter('mimetype')
def mimetype_filter(val):
    try:
        s = mimetypes.types_map['.' + val]
    except Exception:
        s = 'application/octet-stream'
    return s


@app.template_filter('formatdate')
def formatdate_filter(val):
    conformed_timestamp = re.sub(r"[:]|([-](?!((\d{2}[:]\d{2})|(\d{4}))$))", '', val)
    formatdate = datetime.datetime.strptime(conformed_timestamp[:15], "%Y%m%d %H%M%S")
    return format_date(formatdate, format='medium', locale=get_locale())


@app.template_filter('formatdateinput')
def format_date_input(val):
    conformed_timestamp = re.sub(r"[:]|([-](?!((\d{2}[:]\d{2})|(\d{4}))$))", '', val)
    date_obj = datetime.datetime.strptime(conformed_timestamp[:15], "%Y%m%d %H%M%S")
    input_date = date_obj.isoformat().split('T', 1)[0]  # Hack to support dates <1900
    return '' if input_date == "0101-01-01" else input_date


@app.template_filter('strftime')
def timestamptodate(date, fmt=None):
    date = datetime.datetime.fromtimestamp(
        int(date)/1000
    )
    native = date.replace(tzinfo=None)
    if fmt:
        time_format = fmt
    else:
        time_format = '%d %m %Y - %H:%S'
    return native.strftime(time_format)


@app.template_filter('yesno')
def yesno(value, yes, no):
    return yes if value else no


def admin_required(f):
    """
    Checks if current_user.role == 1
    """

    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_admin():
            return f(*args, **kwargs)
        abort(403)

    return inner


def unconfigured(f):
    """
    Checks if current_user.role == 1
    """

    @wraps(f)
    def inner(*args, **kwargs):
        if not config.db_configured:
            return f(*args, **kwargs)
        abort(403)

    return inner


def download_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_download() or current_user.role_admin():
            return f(*args, **kwargs)
        abort(403)

    return inner


def upload_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_upload() or current_user.role_admin():
            return f(*args, **kwargs)
        abort(403)

    return inner


def edit_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_edit() or current_user.role_admin():
            return f(*args, **kwargs)
        abort(403)

    return inner


# Language and content filters
def common_filters():
    if current_user.filter_language() != "all":
        lang_filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        lang_filter = true()
    content_rating_filter = false() if current_user.mature_content else \
        db.Books.tags.any(db.Tags.name.in_(config.mature_content_tags()))
    return and_(lang_filter, ~content_rating_filter)


# Fill indexpage with all requested data from database
def fill_indexpage(page, database, db_filter, order):
    if current_user.show_detail_random():
        random = db.session.query(db.Books).filter(common_filters())\
            .order_by(func.random()).limit(config.config_random_books)
    else:
        random = false
    off = int(int(config.config_books_per_page) * (page - 1))
    pagination = Pagination(page, config.config_books_per_page,
                            len(db.session.query(database)
                                .filter(db_filter).filter(common_filters()).all()))
    entries = db.session.query(database).filter(db_filter).filter(common_filters())\
        .order_by(order).offset(off).limit(config.config_books_per_page)
    return entries, random, pagination


def modify_database_object(input_elements, db_book_object, db_object, db_session, db_type):
    input_elements = [x for x in input_elements if x != '']
    # we have all input element (authors, series, tags) names now
    # 1. search for elements to remove
    del_elements = []
    for c_elements in db_book_object:
        found = False
        if db_type == 'languages':
            type_elements = c_elements.lang_code
        elif db_type == 'custom':
            type_elements = c_elements.value
        else:
            type_elements = c_elements.name
        for inp_element in input_elements:
            if inp_element == type_elements:
                found = True
                break
        # if the element was not found in the new list, add it to remove list
        if not found:
            del_elements.append(c_elements)
        # 2. search for elements that need to be added
    add_elements = []
    for inp_element in input_elements:
        found = False
        for c_elements in db_book_object:
            if db_type == 'languages':
                type_elements = c_elements.lang_code
            elif db_type == 'custom':
                type_elements = c_elements.value
            else:
                type_elements = c_elements.name
            if inp_element == type_elements:
                found = True
                break
        if not found:
            add_elements.append(inp_element)
    # if there are elements to remove, we remove them now
    if len(del_elements) > 0:
        for del_element in del_elements:
            db_book_object.remove(del_element)
            if len(del_element.books) == 0:
                db_session.delete(del_element)
    # if there are elements to add, we add them now!
    if len(add_elements) > 0:
        if db_type == 'languages':
            db_filter = db_object.lang_code
        elif db_type == 'custom':
            db_filter = db_object.value
        else:
            db_filter = db_object.name
        for add_element in add_elements:
            # check if a element with that name exists
            new_element = db_session.query(db_object).filter(db_filter == add_element).first()
            # if no element is found add it
            if new_element is None:
                if db_type == 'author':
                    new_element = db_object(add_element, add_element.replace('|', ','), "")
                elif db_type == 'series':
                    new_element = db_object(add_element, add_element)
                elif db_type == 'custom':
                    new_element = db_object(value=add_element)
                else:  # db_type should be tag, or languages
                    new_element = db_object(add_element)
                db_session.add(new_element)
                new_element = db.session.query(db_object).filter(db_filter == add_element).first()
            # add element to book
            db_book_object.append(new_element)

def render_title_template(*args, **kwargs):
    return render_template(instance=config.config_calibre_web_title, *args, **kwargs)


@app.before_request
def before_request():
    if ub.DEVELOPMENT:
        reload(ub)
    g.user = current_user
    g.allow_registration = config.config_public_reg
    g.allow_upload = config.config_uploading
    g.public_shelfes = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1).order_by(ub.Shelf.name).all()
    if not config.db_configured and request.endpoint not in ('basic_configuration', 'login') and '/static/' not in request.path:
        return redirect(url_for('basic_configuration'))


# Routing functions

@app.route("/opds")
@requires_basic_auth_if_no_ano
def feed_index():
    xml = render_title_template('index.xml')
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/osd")
@requires_basic_auth_if_no_ano
def feed_osd():
    xml = render_title_template('osd.xml', lang='de-DE')
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response


@app.route("/opds/search/<query>")
@requires_basic_auth_if_no_ano
def feed_cc_search(query):
    return feed_search(query.strip())


@app.route("/opds/search", methods=["GET"])
@requires_basic_auth_if_no_ano
def feed_normal_search():
    return feed_search(request.args.get("query").strip())


def feed_search(term):
    if term:
        term = term.strip().lower()
        db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
        entries = db.session.query(db.Books).filter(common_filters()).filter(
            db.or_(db.Books.tags.any(db.Tags.name.ilike("%" + term + "%")),
            db.Books.series.any(db.Series.name.ilike("%" + term + "%")),
            db.Books.authors.any(db.Authors.name.ilike("%" + term + "%")),
            db.Books.publishers.any(db.Publishers.name.ilike("%" + term + "%")),
            db.Books.title.ilike("%" + term + "%"))).all()
        entriescount = len(entries) if len(entries) > 0 else 1
        pagination = Pagination(1, entriescount, entriescount)
        xml = render_title_template('feed.xml', searchterm=term, entries=entries, pagination=pagination)
    else:
        xml = render_title_template('feed.xml', searchterm="")
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/new")
@requires_basic_auth_if_no_ano
def feed_new():
    off = request.args.get("offset")
    if not off:
        off = 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                                                 db.Books, True, db.Books.timestamp.desc())
    xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/discover")
@requires_basic_auth_if_no_ano
def feed_discover():
    entries = db.session.query(db.Books).filter(common_filters()).order_by(func.random())\
        .limit(config.config_books_per_page)
    pagination = Pagination(1, config.config_books_per_page, int(config.config_books_per_page))
    xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/rated")
@requires_basic_auth_if_no_ano
def feed_best_rated():
    off = request.args.get("offset")
    if not off:
        off = 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.ratings.any(db.Ratings.rating > 9), db.Books.timestamp.desc())
    xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/hot")
@requires_basic_auth_if_no_ano
def feed_hot():
    off = request.args.get("offset")
    if not off:
        off = 0
    all_books = ub.session.query(ub.Downloads, ub.func.count(ub.Downloads.book_id)).order_by(
        ub.func.count(ub.Downloads.book_id).desc()).group_by(ub.Downloads.book_id)
    hot_books = all_books.offset(off).limit(config.config_books_per_page)
    entries = list()
    for book in hot_books:
        downloadBook = db.session.query(db.Books).filter(db.Books.id == book.Downloads.book_id).first()
        if downloadBook:
            entries.append(
                db.session.query(db.Books).filter(common_filters())
                .filter(db.Books.id == book.Downloads.book_id).first()
            )
        else:
            ub.session.query(ub.Downloads).filter(book.Downloads.book_id == ub.Downloads.book_id).delete()
            ub.session.commit()
    numBooks = entries.__len__()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page, numBooks)
    xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/author")
@requires_basic_auth_if_no_ano
def feed_authorindex():
    off = request.args.get("offset")
    if not off:
        off = 0
    entries = db.session.query(db.Authors).join(db.books_authors_link).join(db.Books).filter(common_filters())\
        .group_by('books_authors_link.author').order_by(db.Authors.sort).limit(config.config_books_per_page).offset(off)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Authors).all()))
    xml = render_title_template('feed.xml', listelements=entries, folder='feed_author', pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/author/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_author(book_id):
    off = request.args.get("offset")
    if not off:
        off = 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.authors.any(db.Authors.id == book_id), db.Books.timestamp.desc())
    xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/category")
@requires_basic_auth_if_no_ano
def feed_categoryindex():
    off = request.args.get("offset")
    if not off:
        off = 0
    entries = db.session.query(db.Tags).join(db.books_tags_link).join(db.Books).filter(common_filters())\
        .group_by('books_tags_link.tag').order_by(db.Tags.name).offset(off).limit(config.config_books_per_page)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Tags).all()))
    xml = render_title_template('feed.xml', listelements=entries, folder='feed_category', pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/category/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_category(book_id):
    off = request.args.get("offset")
    if not off:
        off = 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.tags.any(db.Tags.id == book_id), db.Books.timestamp.desc())
    xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/series")
@requires_basic_auth_if_no_ano
def feed_seriesindex():
    off = request.args.get("offset")
    if not off:
        off = 0
    entries = db.session.query(db.Series).join(db.books_series_link).join(db.Books).filter(common_filters())\
        .group_by('books_series_link.series').order_by(db.Series.sort).offset(off).all()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Series).all()))
    xml = render_title_template('feed.xml', listelements=entries, folder='feed_series', pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/series/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_series(book_id):
    off = request.args.get("offset")
    if not off:
        off = 0
    entries, random, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.series.any(db.Series.id == book_id), db.Books.series_index)
    xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/shelfindex/", defaults={'public': 0})
@app.route("/opds/shelfindex/<string:public>")
@requires_basic_auth_if_no_ano
def feed_shelfindex(public):
    off = request.args.get("offset")
    if not off:
        off = 0
    if public is not 0:
        shelf = g.public_shelfes
        number = len(shelf)
    else:
        shelf = g.user.shelf
        number = shelf.count()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            number)
    xml = render_title_template('feed.xml', listelements=shelf, folder='feed_shelf', pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@app.route("/opds/shelf/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_shelf(book_id):
    off = request.args.get("offset")
    if not off:
        off = 0
    if current_user.is_anonymous:
        shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1, ub.Shelf.id == book_id).first()
    else:
        shelf = ub.session.query(ub.Shelf).filter(ub.or_(ub.and_(ub.Shelf.user_id == int(current_user.id),
                                                                 ub.Shelf.id == book_id),
                                                         ub.and_(ub.Shelf.is_public == 1,
                                                                 ub.Shelf.id == book_id))).first()
    result = list()
    # user is allowed to access shelf
    if shelf:
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == book_id).order_by(
            ub.BookShelf.order.asc()).all()
        for book in books_in_shelf:
            cur_book = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
            result.append(cur_book)
        pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                                len(result))
        xml = render_title_template('feed.xml', entries=result, pagination=pagination)
        response = make_response(xml)
        response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
        return response

def partial(total_byte_len, part_size_limit):
    s = []
    for p in range(0, total_byte_len, part_size_limit):
        last = min(total_byte_len - 1, p + part_size_limit - 1)
        s.append([p, last])
    return s


def do_gdrive_download(df, headers):
    total_size = int(df.metadata.get('fileSize'))
    download_url = df.metadata.get('downloadUrl')
    s = partial(total_size, 1024 * 1024)  # I'm downloading BIG files, so 100M chunk size is fine for me

    def stream():
        for byte in s:
            headers = {"Range": 'bytes=%s-%s' % (byte[0], byte[1])}
            resp, content = df.auth.Get_Http_Object().request(download_url, headers=headers)
            if resp.status == 206:
                yield content
            else:
                app.logger.info('An error occurred: %s' % resp)
                return
    return Response(stream_with_context(stream()), headers=headers)


@app.route("/opds/download/<book_id>/<book_format>/")
@requires_basic_auth_if_no_ano
@download_required
def get_opds_download_link(book_id, book_format):
    startTime = time.time()
    book_format = book_format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == book_format.upper()).first()
    app.logger.info(data.name)
    if current_user.is_authenticated:
        helper.update_download(book_id, int(current_user.id))
    file_name = book.title
    if len(book.authors) > 0:
        file_name = book.authors[0].name + '_' + file_name
    file_name = helper.get_valid_filename(file_name)
    headers = Headers()
    headers["Content-Disposition"] = "attachment; filename*=UTF-8''%s.%s" % (quote(file_name.encode('utf8')), book_format)
    try:
        headers["Content-Type"] = mimetypes.types_map['.' + book_format]
    except KeyError:
        headers["Content-Type"] = "application/octet-stream"
    app.logger.info(time.time() - startTime)
    startTime = time.time()
    if config.config_use_google_drive:
        app.logger.info(time.time() - startTime)
        df = gdriveutils.getFileFromEbooksFolder(Gdrive.Instance().drive, book.path, data.name + "." + book_format)
        return do_gdrive_download(df, headers)
    else:
        response = make_response(send_from_directory(os.path.join(config.config_calibre_dir, book.path), data.name + "." + book_format))
        response.headers = headers
        return response


@app.route("/ajax/book/<string:uuid>")
@requires_basic_auth_if_no_ano
def get_metadata_calibre_companion(uuid):
    entry = db.session.query(db.Books).filter(db.Books.uuid.like("%" + uuid + "%")).first()
    if entry is not None:
        js = render_template('json.txt', entry=entry)
        response = make_response(js)
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response
    else:
        return ""


@app.route("/get_authors_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_authors_json():
    if request.method == "GET":
        query = request.args.get('q')
        # entries = db.session.execute("select name from authors where name like '%" + query + "%'")
        entries = db.session.query(db.Authors).filter(db.Authors.name.ilike("%" + query + "%")).all()
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@app.route("/get_tags_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_tags_json():
    if request.method == "GET":
        query = request.args.get('q')
        # entries = db.session.execute("select name from tags where name like '%" + query + "%'")
        entries = db.session.query(db.Tags).filter(db.Tags.name.ilike("%" + query + "%")).all()
        # for x in entries:
        #    alfa = dict(name=x.name)
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@app.route("/get_update_status", methods=['GET'])
@login_required_if_no_ano
def get_update_status():
    status = {}
    if request.method == "GET":
        # should be automatically replaced by git with current commit hash
        commit_id = '$Format:%H$'
        commit = requests.get('https://api.github.com/repos/janeczku/calibre-web/git/refs/heads/master').json()
        if "object" in commit and commit['object']['sha'] != commit_id:
            status['status'] = True
            commitdate = requests.get('https://api.github.com/repos/janeczku/calibre-web/git/commits/'+commit['object']['sha']).json()
            if "committer" in commitdate:
                form_date=datetime.datetime.strptime(commitdate['committer']['date'],"%Y-%m-%dT%H:%M:%SZ")
                status['commit'] = format_datetime(form_date, format='short', locale=get_locale())
            else:
                status['commit'] = u'Unknown'
        else:
            status['status'] = False
    return json.dumps(status)


@app.route("/get_updater_status", methods=['GET', 'POST'])
@login_required
@admin_required
def get_updater_status():
    status = {}
    if request.method == "POST":
        commit = request.form.to_dict()
        if "start" in commit and commit['start'] == 'True':
            text = {
                "1": _(u'Requesting update package'),
                "2": _(u'Downloading update package'),
                "3": _(u'Unzipping update package'),
                "4": _(u'Files are replaced'),
                "5": _(u'Database connections are closed'),
                "6": _(u'Server is stopped'),
                "7": _(u'Update finished, please press okay and reload page')
            }
            status['text'] = text
            helper.updater_thread = helper.Updater()
            helper.updater_thread.start()
            status['status'] = helper.updater_thread.get_update_status()
    elif request.method == "GET":
        try:
            status['status'] = helper.updater_thread.get_update_status()
        except Exception:
            status['status'] = 7
    return json.dumps(status)


@app.route("/get_languages_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_languages_json():
    if request.method == "GET":
        query = request.args.get('q').lower()
        languages = db.session.query(db.Languages).all()
        for lang in languages:
            try:
                cur_l = LC.parse(lang.lang_code)
                lang.name = cur_l.get_language_name(get_locale())
            except Exception:
                lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
        entries = [s for s in languages if query in s.name.lower()]
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@app.route("/get_series_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_series_json():
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.query(db.Series).filter(db.Series.name.ilike("%" + query + "%")).all()
        # entries = db.session.execute("select name from series where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@app.route("/get_matching_tags", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_matching_tags():
    tag_dict = {'tags': []}
    if request.method == "GET":
        q = db.session.query(db.Books)
        author_input = request.args.get('author_name')
        title_input = request.args.get('book_title')
        include_tag_inputs = request.args.getlist('include_tag')
        exclude_tag_inputs = request.args.getlist('exclude_tag')
        q = q.filter(db.Books.authors.any(db.Authors.name.ilike("%" + author_input + "%")),
                     db.Books.title.ilike("%" + title_input + "%"))
        if len(include_tag_inputs) > 0:
            for tag in include_tag_inputs:
                q = q.filter(db.Books.tags.any(db.Tags.id == tag))
        if len(exclude_tag_inputs) > 0:
            for tag in exclude_tag_inputs:
                q = q.filter(not_(db.Books.tags.any(db.Tags.id == tag)))
        for book in q:
            for tag in book.tags:
                if tag.id not in tag_dict['tags']:
                    tag_dict['tags'].append(tag.id)
    json_dumps = json.dumps(tag_dict)
    return json_dumps


@app.route("/", defaults={'page': 1})
@app.route('/page/<int:page>')
@login_required_if_no_ano
def index(page):
    entries, random, pagination = fill_indexpage(page, db.Books, True, db.Books.timestamp.desc())
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Recently Added Books"))


@app.route('/books/newest', defaults={'page': 1})
@app.route('/books/newest/page/<int:page>')
@login_required_if_no_ano
def newest_books(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, db.Books.pubdate.desc())
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Newest Books"))
    else:
        abort(404)


@app.route('/books/oldest', defaults={'page': 1})
@app.route('/books/oldest/page/<int:page>')
@login_required_if_no_ano
def oldest_books(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, db.Books.pubdate)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Oldest Books"))
    else:
        abort(404)


@app.route('/books/a-z', defaults={'page': 1})
@app.route('/books/a-z/page/<int:page>')
@login_required_if_no_ano
def titles_ascending(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, db.Books.sort)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Books (A-Z)"))
    else:
        abort(404)


@app.route('/books/z-a', defaults={'page': 1})
@app.route('/books/z-a/page/<int:page>')
@login_required_if_no_ano
def titles_descending(page):
    entries, random, pagination = fill_indexpage(page, db.Books, True, db.Books.sort.desc())
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Books (Z-A)"))


@app.route("/hot", defaults={'page': 1})
@app.route('/hot/page/<int:page>')
@login_required_if_no_ano
def hot_books(page):
    if current_user.show_hot_books():
        if current_user.show_detail_random():
            random = db.session.query(db.Books).filter(common_filters())\
                .order_by(func.random()).limit(config.config_random_books)
        else:
            random = false
        off = int(int(config.config_books_per_page) * (page - 1))
        all_books = ub.session.query(ub.Downloads, ub.func.count(ub.Downloads.book_id)).order_by(
            ub.func.count(ub.Downloads.book_id).desc()).group_by(ub.Downloads.book_id)
        hot_books = all_books.offset(off).limit(config.config_books_per_page)
        entries = list()
        for book in hot_books:
            downloadBook = db.session.query(db.Books).filter(common_filters()).filter(db.Books.id == book.Downloads.book_id).first()
            if downloadBook:
                entries.append(downloadBook)
            else:
                ub.session.query(ub.Downloads).filter(book.Downloads.book_id == ub.Downloads.book_id).delete()
                ub.session.commit()
        numBooks = entries.__len__()
        pagination = Pagination(page, config.config_books_per_page, numBooks)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Hot Books (most downloaded)"))
    else:
       abort(404)


@app.route("/rated", defaults={'page': 1})
@app.route('/rated/page/<int:page>')
@login_required_if_no_ano
def best_rated_books(page):
    if current_user.show_best_rated_books():
        entries, random, pagination = fill_indexpage(page, db.Books, db.Books.ratings.any(db.Ratings.rating > 9),
                                                     db.Books.timestamp.desc())
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Best rated books"))
    abort(404)


@app.route("/discover", defaults={'page': 1})
@app.route('/discover/page/<int:page>')
@login_required_if_no_ano
def discover(page):
    if current_user.show_random_books():
        entries, __, pagination = fill_indexpage(page, db.Books, True, func.randomblob(2))
        pagination = Pagination(1, config.config_books_per_page, config.config_books_per_page)
        return render_title_template('discover.html', entries=entries, pagination=pagination, title=_(u"Random Books"))
    else:
        abort(404)


@app.route("/author")
@login_required_if_no_ano
def author_list():
    if current_user.show_author():
        entries = db.session.query(db.Authors, func.count('books_authors_link.book').label('count'))\
            .join(db.books_authors_link).join(db.Books).filter(common_filters())\
            .group_by('books_authors_link.author').order_by(db.Authors.sort).all()
        for entry in entries:
            entry.Authors.name = entry.Authors.name.replace('|', ',')
        return render_title_template('list.html', entries=entries, folder='author', title=_(u"Author list"))
    else:
        abort(404)


@app.route("/author/<int:book_id>", defaults={'page': 1})
@app.route("/author/<int:book_id>/<int:page>'")
@login_required_if_no_ano
def author(book_id, page):
    entries, __, pagination = fill_indexpage(page, db.Books, db.Books.authors.any(db.Authors.id == book_id),
                                                 db.Books.timestamp.desc())
    if entries is None:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))

    name = (db.session.query(db.Authors).filter(db.Authors.id == book_id).first().name).replace('|', ',')

    author_info = None
    other_books = []
    if goodreads_support and config.config_use_goodreads:
        gc = GoodreadsClient(config.config_goodreads_api_key, config.config_goodreads_api_secret)
        author_info = gc.find_author(author_name=name)
        other_books = get_unique_other_books(entries.all(), author_info.books)

    return render_title_template('author.html', entries=entries, pagination=pagination,
                                 title=name, author=author_info, other_books=other_books)


def get_unique_other_books(library_books, author_books):
    # Get all identifiers (ISBN, Goodreads, etc) and filter author's books by that list so we show fewer duplicates
    # Note: Not all images will be shown, even though they're available on Goodreads.com.
    #       See https://www.goodreads.com/topic/show/18213769-goodreads-book-images
    identifiers = reduce(lambda acc, book: acc + map(lambda identifier: identifier.val, book.identifiers), library_books, [])
    other_books = filter(lambda book: book.isbn not in identifiers and book.gid["#text"] not in identifiers, author_books)

    # Fuzzy match book titles
    if levenshtein_support:
        library_titles = reduce(lambda acc, book: acc + [book.title], library_books, [])
        other_books = filter(lambda author_book: not filter(
            lambda library_book:
            Levenshtein.ratio(re.sub(r"\(.*\)", "", author_book.title), library_book) > 0.7,  # Remove items in parentheses before comparing
            library_titles
        ), other_books)

    return other_books


@app.route("/series")
@login_required_if_no_ano
def series_list():
    if current_user.show_series():
        entries = db.session.query(db.Series, func.count('books_series_link.book').label('count'))\
            .join(db.books_series_link).join(db.Books).filter(common_filters())\
            .group_by('books_series_link.series').order_by(db.Series.sort).all()
        return render_title_template('list.html', entries=entries, folder='series', title=_(u"Series list"))
    else:
        abort(404)


@app.route("/series/<int:book_id>/", defaults={'page': 1})
@app.route("/series/<int:book_id>/<int:page>'")
@login_required_if_no_ano
def series(book_id, page):
    entries, random, pagination = fill_indexpage(page, db.Books, db.Books.series.any(db.Series.id == book_id),
                                                 db.Books.series_index)
    name = db.session.query(db.Series).filter(db.Series.id == book_id).first().name
    if entries:
        return render_title_template('index.html', random=random, pagination=pagination, entries=entries,
                                     title=_(u"Series: %(serie)s", serie=name))
    else:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))


@app.route("/language")
@login_required_if_no_ano
def language_overview():
    if current_user.show_language():
        if current_user.filter_language() == u"all":
            languages = db.session.query(db.Languages).all()
            for lang in languages:
                try:
                    cur_l = LC.parse(lang.lang_code)
                    lang.name = cur_l.get_language_name(get_locale())
                except Exception:
                    lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
        else:
            try:
                cur_l = LC.parse(current_user.filter_language())
            except Exception:
                cur_l = None
            languages = db.session.query(db.Languages).filter(
                db.Languages.lang_code == current_user.filter_language()).all()
            if cur_l:
                languages[0].name = cur_l.get_language_name(get_locale())
            else:
                languages[0].name = _(isoLanguages.get(part3=languages[0].lang_code).name)
        lang_counter = db.session.query(db.books_languages_link,
                                        func.count('books_languages_link.book').label('bookcount')).group_by(
            'books_languages_link.lang_code').all()
        return render_title_template('languages.html', languages=languages, lang_counter=lang_counter,
                                     title=_(u"Available languages"))
    else:
        abort(404)


@app.route("/language/<name>", defaults={'page': 1})
@app.route('/language/<name>/page/<int:page>')
@login_required_if_no_ano
def language(name, page):
    entries, random, pagination = fill_indexpage(page, db.Books, db.Books.languages.any(db.Languages.lang_code == name),
                                                 db.Books.timestamp.desc())
    try:
        cur_l = LC.parse(name)
        name = cur_l.get_language_name(get_locale())
    except Exception:
        name = _(isoLanguages.get(part3=name).name)
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Language: %(name)s", name=name))


@app.route("/category")
@login_required_if_no_ano
def category_list():
    if current_user.show_category():
        entries = db.session.query(db.Tags, func.count('books_tags_link.book').label('count'))\
            .join(db.books_tags_link).join(db.Books).order_by(db.Tags.name).filter(common_filters())\
            .group_by('books_tags_link.tag').all()
        return render_title_template('list.html', entries=entries, folder='category', title=_(u"Category list"))
    else:
        abort(404)


@app.route("/category/<int:book_id>", defaults={'page': 1})
@app.route('/category/<int:book_id>/<int:page>')
@login_required_if_no_ano
def category(book_id, page):
    entries, random, pagination = fill_indexpage(page, db.Books, db.Books.tags.any(db.Tags.id == book_id),
                                                 db.Books.timestamp.desc())

    name = db.session.query(db.Tags).filter(db.Tags.id == book_id).first().name
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Category: %(name)s", name=name))


@app.route("/ajax/toggleread/<int:book_id>", methods=['POST'])
@login_required
def toggle_read(book_id):
    book = ub.session.query(ub.ReadBook).filter(ub.and_(ub.ReadBook.user_id == int(current_user.id),
                                                                   ub.ReadBook.book_id == book_id)).first()
    if book:
        book.is_read = not book.is_read
    else:
        readBook = ub.ReadBook()
        readBook.user_id = int(current_user.id)
        readBook.book_id = book_id
        readBook.is_read = True
        book = readBook
    ub.session.merge(book)
    ub.session.commit()
    return ""


@app.route("/book/<int:book_id>")
@login_required_if_no_ano
def show_book(book_id):
    entries = db.session.query(db.Books).filter(db.Books.id == book_id).filter(common_filters()).first()
    if entries:
        for index in range(0, len(entries.languages)):
            try:
                entries.languages[index].language_name = LC.parse(entries.languages[index].lang_code).get_language_name(
                    get_locale())
            except Exception:
                entries.languages[index].language_name = _(
                    isoLanguages.get(part3=entries.languages[index].lang_code).name)
        tmpcc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()

        if config.config_columns_to_ignore:
            cc = []
            for col in tmpcc:
                r = re.compile(config.config_columns_to_ignore)
                if r.match(col.label):
                    cc.append(col)
        else:
            cc = tmpcc
        book_in_shelfs = []
        shelfs = ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book_id).all()
        for entry in shelfs:
            book_in_shelfs.append(entry.shelf)

        if not current_user.is_anonymous:
            matching_have_read_book = ub.session.query(ub.ReadBook).filter(ub.and_(ub.ReadBook.user_id == int(current_user.id),
                                                                   ub.ReadBook.book_id == book_id)).all()
            have_read = len(matching_have_read_book) > 0 and matching_have_read_book[0].is_read
        else:
            have_read = None

        return render_title_template('detail.html', entry=entries, cc=cc, is_xhr=request.is_xhr,
                                     title=entries.title, books_shelfs=book_in_shelfs, have_read=have_read)
    else:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))


@app.route("/ajax/bookmark/<int:book_id>/<book_format>", methods=['POST'])
@login_required
def bookmark(book_id, book_format):
    bookmark_key = request.form["bookmark"]
    ub.session.query(ub.Bookmark).filter(ub.and_(ub.Bookmark.user_id == int(current_user.id),
                                                 ub.Bookmark.book_id == book_id,
                                                 ub.Bookmark.format == book_format)).delete()
    if not bookmark_key:
        ub.session.commit()
        return "", 204

    bookmark = ub.Bookmark(user_id=current_user.id,
                           book_id=book_id,
                           format=book_format,
                           bookmark_key=bookmark_key)
    ub.session.merge(bookmark)
    ub.session.commit()
    return "", 201


@app.route("/admin")
@login_required
def admin_forbidden():
    abort(403)


@app.route("/stats")
@login_required
def stats():
    counter = len(db.session.query(db.Books).all())
    authors = len(db.session.query(db.Authors).all())
    categorys = len(db.session.query(db.Tags).all())
    series = len(db.session.query(db.Series).all())
    versions = uploader.book_formats.get_versions()
    vendorpath = os.path.join(config.get_main_dir, "vendor")
    if sys.platform == "win32":
        kindlegen = os.path.join(vendorpath, u"kindlegen.exe")
    else:
        kindlegen = os.path.join(vendorpath, u"kindlegen")
    versions['KindlegenVersion'] = _('not installed')
    if os.path.exists(kindlegen):
        try:
            p = subprocess.Popen(kindlegen, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.wait()
            for lines in p.stdout.readlines():
                if isinstance(lines, bytes):
                    lines = lines.decode('utf-8')
                if re.search('Amazon kindlegen\(', lines):
                    versions['KindlegenVersion'] = lines
        except Exception:
            versions['KindlegenVersion'] = _(u'Excecution permissions missing')
    versions['PythonVersion'] = sys.version
    versions['babel'] = babelVersion
    versions['sqlalchemy'] = sqlalchemyVersion
    versions['flask'] = flaskVersion
    versions['flasklogin'] = flask_loginVersion
    versions['flask_principal'] = flask_principalVersion
    versions['tornado'] = tornadoVersion
    versions['iso639'] = iso639Version
    versions['requests'] = requests.__version__
    versions['pysqlite'] = db.engine.dialect.dbapi.version
    versions['sqlite'] = db.engine.dialect.dbapi.sqlite_version

    return render_title_template('stats.html', bookcounter=counter, authorcounter=authors, versions=versions,
                                 categorycounter=categorys, seriecounter=series, title=_(u"Statistics"))


@app.route("/delete/<int:book_id>/")
@login_required
def delete_book(book_id):
    if current_user.role_delete_books():
        book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
        if book:
            # delete book from Shelfs, Downloads, Read list
            ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book_id).delete()
            ub.session.query(ub.ReadBook).filter(ub.ReadBook.book_id == book_id).delete()
            ub.session.query(ub.Downloads).filter(ub.Downloads.book_id == book_id).delete()
            ub.session.commit()

            if config.config_use_google_drive:
                helper.delete_book_gdrive(book)  # ToDo really delete file
            else:
                helper.delete_book(book, config.config_calibre_dir)
            # check if only this book links to:
            # author, language, series, tags, custom columns
            modify_database_object([u''], book.authors, db.Authors, db.session, 'author')
            modify_database_object([u''], book.tags, db.Tags, db.session, 'tags')
            modify_database_object([u''], book.series, db.Series, db.session, 'series')
            modify_database_object([u''], book.languages, db.Languages, db.session, 'languages')
            modify_database_object([u''], book.publishers, db.Publishers, db.session, 'series')

            cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
            for c in cc:
                cc_string = "custom_column_" + str(c.id)
                if not c.is_multiple:
                    if len(getattr(book, cc_string)) > 0:
                        if c.datatype == 'bool' or c.datatype == 'integer':
                            del_cc = getattr(book, cc_string)[0]
                            getattr(book, cc_string).remove(del_cc)
                            db.session.delete(del_cc)
                        elif c.datatype == 'rating':
                            del_cc = getattr(book, cc_string)[0]
                            getattr(book, cc_string).remove(del_cc)
                            if len(del_cc.books) == 0:
                                db.session.delete(del_cc)
                        else:
                            del_cc = getattr(book, cc_string)[0]
                            getattr(book, cc_string).remove(del_cc)
                            db.session.delete(del_cc)
                else:
                    modify_database_object([u''], getattr(book, cc_string), db.cc_classes[c.id], db.session, 'custom')
            db.session.query(db.Books).filter(db.Books.id == book_id).delete()
            db.session.commit()
        else:
            # book not foundß
            app.logger.info('Book with id "'+str(book_id)+'" could not be deleted')
    return redirect(url_for('index'))


@app.route("/gdrive/authenticate")
@login_required
@admin_required
def authenticate_google_drive():
    authUrl = Gauth.Instance().auth.GetAuthUrl()
    return redirect(authUrl)


@app.route("/gdrive/callback")
def google_drive_callback():
    auth_code = request.args.get('code')
    credentials = Gauth.Instance().auth.flow.step2_exchange(auth_code)
    with open('gdrive_credentials', 'w') as f:
        f.write(credentials.to_json())
    return redirect(url_for('configuration'))


@app.route("/gdrive/watch/subscribe")
@login_required
@admin_required
def watch_gdrive():
    if not config.config_google_drive_watch_changes_response:
        address = '%s/gdrive/watch/callback' % config.config_google_drive_calibre_url_base
        notification_id = str(uuid4())
        result = gdriveutils.watchChange(Gdrive.Instance().drive, notification_id,
                               'web_hook', address, gdrive_watch_callback_token, current_milli_time() + 604800*1000)
        print (result)
        settings = ub.session.query(ub.Settings).first()
        settings.config_google_drive_watch_changes_response = json.dumps(result)
        ub.session.merge(settings)
        ub.session.commit()
        settings = ub.session.query(ub.Settings).first()
        config.loadSettings()

        print (settings.config_google_drive_watch_changes_response)

    return redirect(url_for('configuration'))


@app.route("/gdrive/watch/revoke")
@login_required
@admin_required
def revoke_watch_gdrive():
    last_watch_response = config.config_google_drive_watch_changes_response
    if last_watch_response:
        try:
            gdriveutils.stopChannel(Gdrive.Instance().drive, last_watch_response['id'], last_watch_response['resourceId'])
        except HttpError:
            pass
        settings = ub.session.query(ub.Settings).first()
        settings.config_google_drive_watch_changes_response = None
        ub.session.merge(settings)
        ub.session.commit()
        config.loadSettings()
    return redirect(url_for('configuration'))


@app.route("/gdrive/watch/callback", methods=['GET', 'POST'])
def on_received_watch_confirmation():
    app.logger.info(request.headers)
    if request.headers.get('X-Goog-Channel-Token') == gdrive_watch_callback_token \
            and request.headers.get('X-Goog-Resource-State') == 'change' \
            and request.data:

        data = request.data

        def updateMetaData():
            app.logger.info('Change received from gdrive')
            app.logger.info(data)
            try:
                j = json.loads(data)
                app.logger.info('Getting change details')
                response = gdriveutils.getChangeById(Gdrive.Instance().drive, j['id'])
                app.logger.info(response)
                if response:
                    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
                    if not response['deleted'] and response['file']['title'] == 'metadata.db' and response['file']['md5Checksum'] != md5(dbpath):
                        tmpDir = tempfile.gettempdir()
                        app.logger.info('Database file updated')
                        copyfile(dbpath, os.path.join(tmpDir, "metadata.db_" + str(current_milli_time())))
                        app.logger.info('Backing up existing and downloading updated metadata.db')
                        gdriveutils.downloadFile(Gdrive.Instance().drive, None, "metadata.db", os.path.join(tmpDir, "tmp_metadata.db"))
                        app.logger.info('Setting up new DB')
                        os.rename(os.path.join(tmpDir, "tmp_metadata.db"), dbpath)
                        db.setup_db()
            except Exception as e:
                app.logger.exception(e)

        updateMetaData()
    return ''


@app.route("/shutdown")
@login_required
@admin_required
def shutdown():
    # global global_task
    task = int(request.args.get("parameter").strip())
    helper.global_task = task
    if task == 1 or task == 0:  # valid commandos received
        # close all database connections
        db.session.close()
        db.engine.dispose()
        ub.session.close()
        ub.engine.dispose()
        # stop tornado server
        server = IOLoop.instance()
        server.add_callback(server.stop)
        showtext = {}
        if task == 0:
            showtext['text'] = _(u'Server restarted, please reload page')
        else:
            showtext['text'] = _(u'Performing shutdown of server, please close window')
        return json.dumps(showtext)
    else:
        if task == 2:
            db.session.close()
            db.engine.dispose()
            db.setup_db()
            return json.dumps({})
        abort(404)


@app.route("/update")
@login_required
@admin_required
def update():
    helper.updater_thread = helper.Updater()
    flash(_(u"Update done"), category="info")
    return abort(404)


@app.route("/search", methods=["GET"])
@login_required_if_no_ano
def search():
    term = request.args.get("query").strip().lower()

    if term:
        db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
        entries = db.session.query(db.Books).filter(common_filters()).filter(
            db.or_(db.Books.tags.any(db.Tags.name.ilike("%" + term + "%")),
            db.Books.series.any(db.Series.name.ilike("%" + term + "%")),
            db.Books.authors.any(db.Authors.name.ilike("%" + term + "%")),
            db.Books.publishers.any(db.Publishers.name.ilike("%" + term + "%")),
            db.Books.title.ilike("%" + term + "%"))).all()

        # entries = db.session.query(db.Books).with_entities(db.Books.title).filter(db.Books.title.ilike("%" + term + "%")).all()
        # result = db.session.execute("select name from authors where lower(name) like '%" + term.lower() + "%'")
        # entries = result.fetchall()
        # result.close()
        return render_title_template('search.html', searchterm=term, entries=entries)
    else:
        return render_title_template('search.html', searchterm="")


@app.route("/advanced_search", methods=["GET"])
@login_required_if_no_ano
def advanced_search():
    if request.method == 'GET':
        db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
        q = db.session.query(db.Books)
        include_tag_inputs = request.args.getlist('include_tag')
        exclude_tag_inputs = request.args.getlist('exclude_tag')
        include_series_inputs = request.args.getlist('include_serie')
        exclude_series_inputs = request.args.getlist('exclude_serie')
        include_languages_inputs = request.args.getlist('include_language')
        exclude_languages_inputs = request.args.getlist('exclude_language')

        author_name = request.args.get("author_name")
        book_title = request.args.get("book_title")
        publisher = request.args.get("publisher")
        if author_name: author_name = author_name.strip().lower()
        if book_title: book_title = book_title.strip().lower()
        if publisher: publisher = publisher.strip().lower()
        if include_tag_inputs or exclude_tag_inputs or include_series_inputs or exclude_series_inputs or \
                include_languages_inputs or exclude_languages_inputs or author_name or book_title or publisher:
            searchterm = []
            searchterm.extend((author_name, book_title, publisher))
            tag_names = db.session.query(db.Tags).filter(db.Tags.id.in_(include_tag_inputs)).all()
            searchterm.extend(tag.name for tag in tag_names)
            # searchterm = " + ".join(filter(None, searchterm))
            serie_names = db.session.query(db.Series).filter(db.Series.id.in_(include_series_inputs)).all()
            searchterm.extend(serie.name for serie in serie_names)
            language_names = db.session.query(db.Languages).filter(db.Languages.id.in_(include_languages_inputs)).all()
            for lang in language_names:
                try:
                    cur_l = LC.parse(lang.lang_code)
                    lang.name = cur_l.get_language_name(get_locale())
                except Exception:
                    lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
            searchterm.extend(language.name for language in language_names)
            searchterm = " + ".join(filter(None, searchterm))
            q = q.filter()
            if author_name:
                q = q.filter(db.Books.authors.any(db.Authors.name.ilike("%" + author_name + "%")))
            if book_title:
                q = q.filter(db.Books.title.ilike("%" + book_title + "%"))
            if publisher:
                q = q.filter(db.Books.publishers.any(db.Publishers.name.ilike("%" + publisher + "%")))
            for tag in include_tag_inputs:
                q = q.filter(db.Books.tags.any(db.Tags.id == tag))
            for tag in exclude_tag_inputs:
                q = q.filter(not_(db.Books.tags.any(db.Tags.id == tag)))
            for serie in include_series_inputs:
                q = q.filter(db.Books.series.any(db.Series.id == serie))
            for serie in exclude_series_inputs:
                q = q.filter(not_(db.Books.series.any(db.Series.id == serie)))
            if current_user.filter_language() != "all":
                q = q.filter(db.Books.languages.any(db.Languages.lang_code == current_user.filter_language()))
            else:
                for language in include_languages_inputs:
                    q = q.filter(db.Books.languages.any(db.Languages.id == language))
                for language in exclude_languages_inputs:
                    q = q.filter(not_(db.Books.series.any(db.Languages.id == language)))
            q = q.all()
            return render_title_template('search.html', searchterm=searchterm, entries=q, title=_(u"search"))
    tags = db.session.query(db.Tags).order_by(db.Tags.name).all()
    series = db.session.query(db.Series).order_by(db.Series.name).all()
    if current_user.filter_language() == u"all":
        languages = db.session.query(db.Languages).all()
        for lang in languages:
            try:
                cur_l = LC.parse(lang.lang_code)
                lang.name = cur_l.get_language_name(get_locale())
            except Exception:
                lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    else:
        languages = None
    return render_title_template('search_form.html', tags=tags, languages=languages, series=series, title=_(u"search"))


def get_cover_via_gdrive(cover_path):
    df = gdriveutils.getFileFromEbooksFolder(Gdrive.Instance().drive, cover_path, 'cover.jpg')
    if not gdriveutils.session.query(gdriveutils.PermissionAdded).filter(gdriveutils.PermissionAdded.gdrive_id == df['id']).first():
        df.GetPermissions()
        df.InsertPermission({
                        'type': 'anyone',
                        'value': 'anyone',
                        'role': 'reader',
                        'withLink': True})
        permissionAdded = gdriveutils.PermissionAdded()
        permissionAdded.gdrive_id = df['id']
        gdriveutils.session.add(permissionAdded)
        gdriveutils.session.commit()
    return df.metadata.get('webContentLink')


@app.route("/cover/<path:cover_path>")
@login_required_if_no_ano
def get_cover(cover_path):
    if config.config_use_google_drive:
        return redirect(get_cover_via_gdrive(cover_path))
    else:
        return send_from_directory(os.path.join(config.config_calibre_dir, cover_path), "cover.jpg")


@app.route("/show/<book_id>/<book_format>")
@login_required_if_no_ano
def serve_book(book_id, book_format):
    book_format = book_format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == book_format.upper()).first()
    app.logger.info(data.name)
    if config.config_use_google_drive:
        headers = Headers()
        try:
            headers["Content-Type"] = mimetypes.types_map['.' + book_format]
        except KeyError:
            headers["Content-Type"] = "application/octet-stream"
        df = gdriveutils.getFileFromEbooksFolder(Gdrive.Instance().drive, book.path, data.name + "." + book_format)
        return do_gdrive_download(df, headers)
    else:
        return send_from_directory(os.path.join(config.config_calibre_dir, book.path), data.name + "." + book_format)


@app.route("/opds/thumb_240_240/<path:book_id>")
@app.route("/opds/cover_240_240/<path:book_id>")
@app.route("/opds/cover_90_90/<path:book_id>")
@app.route("/opds/cover/<path:book_id>")
@requires_basic_auth_if_no_ano
def feed_get_cover(book_id):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    if config.config_use_google_drive:
        return redirect(get_cover_via_gdrive(book.path))
    else:
        return send_from_directory(os.path.join(config.config_calibre_dir, book.path), "cover.jpg")


def render_read_books(page, are_read, as_xml=False):
    readBooks = ub.session.query(ub.ReadBook).filter(ub.ReadBook.user_id == int(current_user.id)).filter(ub.ReadBook.is_read == True).all()
    readBookIds = [x.book_id for x in readBooks]
    if are_read:
        db_filter = db.Books.id.in_(readBookIds)
    else:
        db_filter = ~db.Books.id.in_(readBookIds)

    entries, random, pagination = fill_indexpage(page, db.Books,
        db_filter, db.Books.timestamp.desc())

    if as_xml:
        xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
        response = make_response(xml)
        response.headers["Content-Type"] = "application/xml"
        return response
    else:
        if are_read:
            name = _(u'Read Books') + ' (' + str(len(readBookIds)) + ')'
        else:
            total_books = db.session.query(func.count(db.Books.id)).scalar()
            name = _(u'Unread Books') + ' (' + str(total_books - len(readBookIds)) + ')'
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                title=_(name, name=name))


@app.route("/opds/readbooks/")
@login_required_if_no_ano
def feed_read_books():
    off = request.args.get("offset")
    if not off:
        off = 0
    return render_read_books(int(off) / (int(config.config_books_per_page)) + 1, True, True)


@app.route("/readbooks/", defaults={'page': 1})
@app.route("/readbooks/<int:page>'")
@login_required_if_no_ano
def read_books(page):
    return render_read_books(page, True)


@app.route("/opds/unreadbooks/")
@login_required_if_no_ano
def feed_unread_books():
    off = request.args.get("offset")
    if not off:
        off = 0
    return render_read_books(int(off) / (int(config.config_books_per_page)) + 1, False, True)


@app.route("/unreadbooks/", defaults={'page': 1})
@app.route("/unreadbooks/<int:page>'")
@login_required_if_no_ano
def unread_books(page):
    return render_read_books(page, False)


@app.route("/read/<int:book_id>/<book_format>")
@login_required_if_no_ano
def read_book(book_id, book_format):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    if not book:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))

    book_dir = os.path.join(config.get_main_dir, "cps", "static", str(book_id))
    if not os.path.exists(book_dir):
        os.mkdir(book_dir)
    bookmark = None
    if current_user.is_authenticated:
        bookmark = ub.session.query(ub.Bookmark).filter(ub.and_(ub.Bookmark.user_id == int(current_user.id),
                                                            ub.Bookmark.book_id == book_id,
                                                            ub.Bookmark.format == book_format.upper())).first()
    if book_format.lower() == "epub":
        # check if mimetype file is exists
        mime_file = str(book_id) + "/mimetype"
        if not os.path.exists(mime_file):
            epub_file = os.path.join(config.config_calibre_dir, book.path, book.data[0].name) + ".epub"
            if not os.path.isfile(epub_file):
                raise ValueError('Error opening eBook. File does not exist: ', epub_file)
            zfile = zipfile.ZipFile(epub_file)
            for name in zfile.namelist():
                (dirName, fileName) = os.path.split(name)
                newDir = os.path.join(book_dir, dirName)
                if not os.path.exists(newDir):
                    try:
                        os.makedirs(newDir)
                    except OSError as exception:
                        if not exception.errno == errno.EEXIST:
                            raise
                if fileName:
                    fd = open(os.path.join(newDir, fileName), "wb")
                    fd.write(zfile.read(name))
                    fd.close()
            zfile.close()
        return render_title_template('read.html', bookid=book_id, title=_(u"Read a Book"), bookmark=bookmark)
    elif book_format.lower() == "pdf":
        return render_title_template('readpdf.html', pdffile=book_id, title=_(u"Read a Book"))
    elif book_format.lower() == "txt":
        return render_title_template('readtxt.html', txtfile=book_id, title=_(u"Read a Book"))
    else:
        for fileext in ["cbr", "cbt", "cbz"]:
            if book_format.lower() == fileext:
                all_name = str(book_id) + "/" + book.data[0].name + "." + fileext
                tmp_file = os.path.join(book_dir, book.data[0].name) + "." + fileext
                if not os.path.exists(all_name):
                    cbr_file = os.path.join(config.config_calibre_dir, book.path, book.data[0].name) + "." + fileext
                    copyfile(cbr_file, tmp_file)
                return render_title_template('readcbr.html', comicfile=all_name, title=_(u"Read a Book"))


@app.route("/download/<int:book_id>/<book_format>")
@login_required_if_no_ano
@download_required
def get_download_link(book_id, book_format):
    book_format = book_format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == book_format.upper()).first()
    if data:
        # collect downloaded books only for registered user and not for anonymous user
        if current_user.is_authenticated:
            helper.update_download(book_id, int(current_user.id))
        file_name = book.title
        if len(book.authors) > 0:
            file_name = book.authors[0].name + '_' + file_name
        file_name = helper.get_valid_filename(file_name)
        headers = Headers()
        try:
            headers["Content-Type"] = mimetypes.types_map['.' + book_format]
        except KeyError:
            headers["Content-Type"] = "application/octet-stream"
        headers["Content-Disposition"] = "attachment; filename*=UTF-8''%s.%s" % (quote(file_name.encode('utf-8')), book_format)
        if config.config_use_google_drive:
            df = gdriveutils.getFileFromEbooksFolder(Gdrive.Instance().drive, book.path, '%s.%s' % (data.name, book_format))
            return do_gdrive_download(df, headers)
        else:
            response = make_response(send_from_directory(os.path.join(config.config_calibre_dir, book.path), data.name + "." + book_format))
            response.headers = headers
            return response
    else:
        abort(404)


@app.route("/download/<int:book_id>/<book_format>/<anyname>")
@login_required_if_no_ano
@download_required
def get_download_link_ext(book_id, book_format, anyname):
    return get_download_link(book_id, book_format)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if not config.config_public_reg:
        abort(404)
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == "POST":
        to_save = request.form.to_dict()
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template('register.html', title=_(u"register"))

        existing_user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == to_save["nickname"].lower()).first()
        existing_email = ub.session.query(ub.User).filter(ub.User.email == to_save["email"]).first()
        if not existing_user and not existing_email:
            content = ub.User()
            content.password = generate_password_hash(to_save["password"])
            content.nickname = to_save["nickname"]
            content.email = to_save["email"]
            content.role = config.config_default_role
            content.sidebar_view = config.config_default_show
            try:
                ub.session.add(content)
                ub.session.commit()
            except Exception:
                ub.session.rollback()
                flash(_(u"An unknown error occured. Please try again later."), category="error")
                return render_title_template('register.html', title=_(u"register"))
            flash("Your account has been created. Please login.", category="success")
            return redirect(url_for('login'))
        else:
            flash(_(u"This username or email address is already in use."), category="error")
            return render_title_template('register.html', title=_(u"register"))

    return render_title_template('register.html', title=_(u"register"))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not config.db_configured:
        return redirect(url_for('basic_configuration'))
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        form = request.form.to_dict()
        user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == form['username'].strip().lower()).first()

        if user and check_password_hash(user.password, form['password']):
            login_user(user, remember=True)

            flash(_(u"you are now logged in as: '%(nickname)s'", nickname=user.nickname), category="success")
            return redirect_back(url_for("index"))
        else:
            ipAdress = request.headers.get('X-Forwarded-For', request.remote_addr)
            app.logger.info('Login failed for user "' + form['username'] + '" IP-adress: ' + ipAdress)
            flash(_(u"Wrong Username or Password"), category="error")

    next_url = request.args.get('next')
    if next_url is None or not is_safe_url(next_url):
        next_url = url_for('index')

    return render_title_template('login.html', title=_(u"login"), next_url=next_url,
                                 remote_login=config.config_remote_login)


@app.route('/logout')
@login_required
def logout():
    if current_user is not None and current_user.is_authenticated:
        logout_user()
    return redirect(url_for('login'))


@app.route('/remote/login')
@remote_login_required
def remote_login():
    auth_token = ub.RemoteAuthToken()
    ub.session.add(auth_token)
    ub.session.commit()

    verify_url = url_for('verify_token', token=auth_token.auth_token, _external=true)

    return render_title_template('remote_login.html', title=_(u"login"), token=auth_token.auth_token,
                                 verify_url=verify_url)


@app.route('/verify/<token>')
@remote_login_required
@login_required
def verify_token(token):
    auth_token = ub.session.query(ub.RemoteAuthToken).filter(ub.RemoteAuthToken.auth_token == token).first()

    # Token not found
    if auth_token is None:
        flash(_(u"Token not found"), category="error")
        return redirect(url_for('index'))

    # Token expired
    if datetime.datetime.now() > auth_token.expiration:
        ub.session.delete(auth_token)
        ub.session.commit()

        flash(_(u"Token has expired"), category="error")
        return redirect(url_for('index'))

    # Update token with user information
    auth_token.user_id = current_user.id
    auth_token.verified = True
    ub.session.commit()

    flash(_(u"Success! Please return to your device"), category="success")
    return redirect(url_for('index'))


@app.route('/ajax/verify_token', methods=['POST'])
@remote_login_required
def token_verified():
    token = request.form['token']
    auth_token = ub.session.query(ub.RemoteAuthToken).filter(ub.RemoteAuthToken.auth_token == token).first()

    data = {}

    # Token not found
    if auth_token is None:
        data['status'] = 'error'
        data['message'] = _(u"Token not found")

    # Token expired
    elif datetime.datetime.now() > auth_token.expiration:
        ub.session.delete(auth_token)
        ub.session.commit()

        data['status'] = 'error'
        data['message'] = _(u"Token has expired")

    elif not auth_token.verified:
        data['status'] = 'not_verified'

    else:
        user = ub.session.query(ub.User).filter(ub.User.id == auth_token.user_id).first()
        login_user(user)

        ub.session.delete(auth_token)
        ub.session.commit()

        data['status'] = 'success'
        flash(_(u"you are now logged in as: '%(nickname)s'", nickname=user.nickname), category="success")

    response = make_response(json.dumps(data, ensure_ascii=false))
    response.headers["Content-Type"] = "application/json; charset=utf-8"

    return response


@app.route('/send/<int:book_id>')
@login_required
@download_required
def send_to_kindle(book_id):
    settings = ub.get_mail_settings()
    if settings.get("mail_server", "mail.example.com") == "mail.example.com":
        flash(_(u"Please configure the SMTP mail settings first..."), category="error")
    elif current_user.kindle_mail:
        result = helper.send_mail(book_id, current_user.kindle_mail, config.config_calibre_dir)
        if result is None:
            flash(_(u"Book successfully send to %(kindlemail)s", kindlemail=current_user.kindle_mail),
                  category="success")
            helper.update_download(book_id, int(current_user.id))
        else:
            flash(_(u"There was an error sending this book: %(res)s", res=result), category="error")
    else:
        flash(_(u"Please configure your kindle email address first..."), category="error")
    return redirect(request.environ["HTTP_REFERER"])


@app.route("/shelf/add/<int:shelf_id>/<int:book_id>")
@login_required
def add_to_shelf(shelf_id, book_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if shelf is None:
        app.logger.info("Invalid shelf specified")
        if not request.is_xhr:
            return redirect(url_for('index'))
        return "Invalid shelf specified", 400

    if not shelf.is_public and not shelf.user_id == int(current_user.id):
        app.logger.info("Sorry you are not allowed to add a book to the the shelf: %s" % shelf.name)
        if not request.is_xhr:
            return redirect(url_for('index'))
        return "Sorry you are not allowed to add a book to the the shelf: %s" % shelf.name, 403

    if shelf.is_public and not current_user.role_edit_shelfs():
        app.logger.info("User is not allowed to edit public shelves")
        if not request.is_xhr:
            return redirect(url_for('index'))
        return "User is not allowed to edit public shelves", 403

    book_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id,
                                          ub.BookShelf.book_id == book_id).first()
    if book_in_shelf:
        app.logger.info("Book is already part of the shelf: %s" % shelf.name)
        if not request.is_xhr:
            return redirect(url_for('index'))
        return "Book is already part of the shelf: %s" % shelf.name, 400

    maxOrder = ub.session.query(func.max(ub.BookShelf.order)).filter(ub.BookShelf.shelf == shelf_id).first()
    if maxOrder[0] is None:
        maxOrder = 0
    else:
        maxOrder = maxOrder[0]

    ins = ub.BookShelf(shelf=shelf.id, book_id=book_id, order=maxOrder + 1)
    ub.session.add(ins)
    ub.session.commit()
    if not request.is_xhr:
        flash(_(u"Book has been added to shelf: %(sname)s", sname=shelf.name), category="success")
        return redirect(request.environ["HTTP_REFERER"])
    return "", 204


@app.route("/shelf/remove/<int:shelf_id>/<int:book_id>")
@login_required
def remove_from_shelf(shelf_id, book_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if shelf is None:
        app.logger.info("Invalid shelf specified")
        if not request.is_xhr:
            return redirect(url_for('index'))
        return "Invalid shelf specified", 400

    # if shelf is public and use is allowed to edit shelfs, or if shelf is private and user is owner
    # allow editing shelfs
    # result   shelf public   user allowed    user owner
    #   false        1             0             x
    #   true         1             1             x
    #   true         0             x             1
    #   false        0             x             0

    if (not shelf.is_public and shelf.user_id == int(current_user.id)) \
            or (shelf.is_public and current_user.role_edit_shelfs()):
        book_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id,
                                                           ub.BookShelf.book_id == book_id).first()

        if book_shelf is None:
            app.logger.info("Book already removed from shelf")
            if not request.is_xhr:
                return redirect(url_for('index'))
            return "Book already removed from shelf", 410

        ub.session.delete(book_shelf)
        ub.session.commit()

        if not request.is_xhr:
            flash(_(u"Book has been removed from shelf: %(sname)s", sname=shelf.name), category="success")
            return redirect(request.environ["HTTP_REFERER"])
        return "", 204
    else:
        app.logger.info("Sorry you are not allowed to remove a book from this shelf: %s" % shelf.name)
        if not request.is_xhr:
            flash(_(u"Sorry you are not allowed to remove a book from this shelf: %(sname)s", sname=shelf.name), category="error")
            return redirect(url_for('index'))
        return "Sorry you are not allowed to remove a book from this shelf: %s" % shelf.name, 403



@app.route("/shelf/create", methods=["GET", "POST"])
@login_required
def create_shelf():
    shelf = ub.Shelf()
    if request.method == "POST":
        to_save = request.form.to_dict()
        if "is_public" in to_save:
            shelf.is_public = 1
        shelf.name = to_save["title"]
        shelf.user_id = int(current_user.id)
        existing_shelf = ub.session.query(ub.Shelf).filter(
            or_((ub.Shelf.name == to_save["title"]) & (ub.Shelf.is_public == 1),
                (ub.Shelf.name == to_save["title"]) & (ub.Shelf.user_id == int(current_user.id)))).first()
        if existing_shelf:
            flash(_(u"A shelf with the name '%(title)s' already exists.", title=to_save["title"]), category="error")
        else:
            try:
                ub.session.add(shelf)
                ub.session.commit()
                flash(_(u"Shelf %(title)s created", title=to_save["title"]), category="success")
            except Exception:
                flash(_(u"There was an error"), category="error")
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"create a shelf"))
    else:
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"create a shelf"))


@app.route("/shelf/edit/<int:shelf_id>", methods=["GET", "POST"])
@login_required
def edit_shelf(shelf_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if request.method == "POST":
        to_save = request.form.to_dict()
        existing_shelf = ub.session.query(ub.Shelf).filter(
            or_((ub.Shelf.name == to_save["title"]) & (ub.Shelf.is_public == 1),
                (ub.Shelf.name == to_save["title"]) & (ub.Shelf.user_id == int(current_user.id)))).filter(
            ub.Shelf.id != shelf_id).first()
        if existing_shelf:
            flash(_(u"A shelf with the name '%(title)s' already exists.", title=to_save["title"]), category="error")
        else:
            shelf.name = to_save["title"]
            if "is_public" in to_save:
                shelf.is_public = 1
            else:
                shelf.is_public = 0
            try:
                ub.session.commit()
                flash(_(u"Shelf %(title)s changed", title=to_save["title"]), category="success")
            except Exception:
                flash(_(u"There was an error"), category="error")
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"Edit a shelf"))
    else:
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"Edit a shelf"))


@app.route("/shelf/delete/<int:shelf_id>")
@login_required
def delete_shelf(shelf_id):
    cur_shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    deleted = false
    if current_user.role_admin():
        deleted = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).delete()
    else:
        if (not cur_shelf.is_public and cur_shelf.user_id == int(current_user.id)) \
                or (cur_shelf.is_public and current_user.role_edit_shelfs()):
            deleted = ub.session.query(ub.Shelf).filter(ub.or_(ub.and_(ub.Shelf.user_id == int(current_user.id),
                                                                   ub.Shelf.id == shelf_id),
                                                           ub.and_(ub.Shelf.is_public == 1,
                                                                   ub.Shelf.id == shelf_id))).delete()

    if deleted:
        ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).delete()
        ub.session.commit()
        app.logger.info(_(u"successfully deleted shelf %(name)s", name=cur_shelf.name, category="success"))
    return redirect(url_for('index'))


@app.route("/shelf/<int:shelf_id>")
@login_required_if_no_ano
def show_shelf(shelf_id):
    if current_user.is_anonymous:
        shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1, ub.Shelf.id == shelf_id).first()
    else:
        shelf = ub.session.query(ub.Shelf).filter(ub.or_(ub.and_(ub.Shelf.user_id == int(current_user.id),
                                                                 ub.Shelf.id == shelf_id),
                                                         ub.and_(ub.Shelf.is_public == 1,
                                                                 ub.Shelf.id == shelf_id))).first()
    result = list()
    # user is allowed to access shelf
    if shelf:
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).order_by(
            ub.BookShelf.order.asc()).all()
        for book in books_in_shelf:
            cur_book = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
            result.append(cur_book)
        return render_title_template('shelf.html', entries=result, title=_(u"Shelf: '%(name)s'", name=shelf.name),
                                 shelf=shelf)
    else:
        flash(_(u"Error opening shelf. Shelf does not exist or is not accessible"), category="error")
        return redirect(url_for("index"))


@app.route("/shelf/order/<int:shelf_id>", methods=["GET", "POST"])
@login_required
def order_shelf(shelf_id):
    if request.method == "POST":
        to_save = request.form.to_dict()
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).order_by(
            ub.BookShelf.order.asc()).all()
        counter = 0
        for book in books_in_shelf:
            setattr(book, 'order', to_save[str(book.book_id)])
            counter += 1
        ub.session.commit()
    if current_user.is_anonymous:
        shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1, ub.Shelf.id == shelf_id).first()
    else:
        shelf = ub.session.query(ub.Shelf).filter(ub.or_(ub.and_(ub.Shelf.user_id == int(current_user.id),
                                                                 ub.Shelf.id == shelf_id),
                                                         ub.and_(ub.Shelf.is_public == 1,
                                                                 ub.Shelf.id == shelf_id))).first()
    result = list()
    if shelf:
        books_in_shelf2 = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id) \
            .order_by(ub.BookShelf.order.asc()).all()
        for book in books_in_shelf2:
            cur_book = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
            result.append(cur_book)
    return render_title_template('shelf_order.html', entries=result,
                                 title=_(u"Change order of Shelf: '%(name)s'", name=shelf.name), shelf=shelf)


@app.route("/me", methods=["GET", "POST"])
@login_required
def profile():
    content = ub.session.query(ub.User).filter(ub.User.id == int(current_user.id)).first()
    downloads = list()
    languages = db.session.query(db.Languages).all()
    for lang in languages:
        try:
            cur_l = LC.parse(lang.lang_code)
            lang.name = cur_l.get_language_name(get_locale())
        except Exception:
            lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    translations = babel.list_translations() + [LC('en')]
    for book in content.downloads:
        downloadBook = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
        if downloadBook:
            downloads.append(db.session.query(db.Books).filter(db.Books.id == book.book_id).first())
        else:
            ub.session.query(ub.Downloads).filter(book.book_id == ub.Downloads.book_id).delete()
            ub.session.commit()
    if request.method == "POST":
        to_save = request.form.to_dict()
        content.random_books = 0
        if current_user.role_passwd() or current_user.role_admin():
            if to_save["password"]:
                content.password = generate_password_hash(to_save["password"])
        if "kindle_mail" in to_save and to_save["kindle_mail"] != content.kindle_mail:
            content.kindle_mail = to_save["kindle_mail"]
        if to_save["email"] and to_save["email"] != content.email:
            content.email = to_save["email"]
        if "show_random" in to_save and to_save["show_random"] == "on":
            content.random_books = 1
        if "default_language" in to_save:
            content.default_language = to_save["default_language"]
        if to_save["locale"]:
            content.locale = to_save["locale"]
        content.sidebar_view = 0
        if "show_random" in to_save:
            content.sidebar_view += ub.SIDEBAR_RANDOM
        if "show_language" in to_save:
            content.sidebar_view += ub.SIDEBAR_LANGUAGE
        if "show_series" in to_save:
            content.sidebar_view += ub.SIDEBAR_SERIES
        if "show_category" in to_save:
            content.sidebar_view += ub.SIDEBAR_CATEGORY
        if "show_recent" in to_save:
            content.sidebar_view += ub.SIDEBAR_RECENT
        if "show_sorted" in to_save:
            content.sidebar_view += ub.SIDEBAR_SORTED
        if "show_hot" in to_save:
            content.sidebar_view += ub.SIDEBAR_HOT
        if "show_best_rated" in to_save:
            content.sidebar_view += ub.SIDEBAR_BEST_RATED
        if "show_author" in to_save:
            content.sidebar_view += ub.SIDEBAR_AUTHOR
        if "show_read_and_unread" in to_save:
            content.sidebar_view += ub.SIDEBAR_READ_AND_UNREAD
        if "show_detail_random" in to_save:
            content.sidebar_view += ub.DETAIL_RANDOM

        content.mature_content = "show_mature_content" in to_save

        try:
            ub.session.commit()
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"Found an existing account for this email address."), category="error")
            return render_title_template("user_edit.html", content=content, downloads=downloads,
                                         title=_(u"%(name)s's profile", name=current_user.nickname))
        flash(_(u"Profile updated"), category="success")
    return render_title_template("user_edit.html", translations=translations, profile=1, languages=languages,
                                 content=content,
                                 downloads=downloads, title=_(u"%(name)s's profile", name=current_user.nickname))


@app.route("/admin/view")
@login_required
@admin_required
def admin():
    commit = '$Format:%cI$'
    if commit.startswith("$"):
        commit = _(u'Unknown')
    else:
        form_date = datetime.datetime.strptime(commit[:19], "%Y-%m-%dT%H:%M:%S")
        if len(commit) > 19:    # check if string has timezone
            if commit[19] == '+':
                form_date -= datetime.timedelta(hours=int(commit[20:22]), minutes=int(commit[23:]))
            elif commit[19] == '-':
                form_date += datetime.timedelta(hours=int(commit[20:22]), minutes=int(commit[23:]))
        commit = format_datetime(form_date, format='short', locale=get_locale())

    content = ub.session.query(ub.User).all()
    settings = ub.session.query(ub.Settings).first()
    return render_title_template("admin.html", content=content, email=settings, config=config, commit=commit,
                                 development=ub.DEVELOPMENT, title=_(u"Admin page"))


@app.route("/admin/config", methods=["GET", "POST"])
@login_required
@admin_required
def configuration():
    return configuration_helper(0)


@app.route("/config", methods=["GET", "POST"])
@unconfigured
def basic_configuration():
    return configuration_helper(1)


def configuration_helper(origin):
    # global global_task
    reboot_required = False
    db_change = False
    success = False
    if request.method == "POST":
        to_save = request.form.to_dict()
        content = ub.session.query(ub.Settings).first()  # type: ub.Settings
        if "config_calibre_dir" in to_save:
            if content.config_calibre_dir != to_save["config_calibre_dir"]:
                content.config_calibre_dir = to_save["config_calibre_dir"]
                db_change = True
        # Google drive setup
        create_new_yaml = False
        if "config_google_drive_client_id" in to_save:
            if content.config_google_drive_client_id != to_save["config_google_drive_client_id"]:
                content.config_google_drive_client_id = to_save["config_google_drive_client_id"]
                create_new_yaml = True
        if "config_google_drive_client_secret" in to_save:
            if content.config_google_drive_client_secret != to_save["config_google_drive_client_secret"]:
                content.config_google_drive_client_secret = to_save["config_google_drive_client_secret"]
                create_new_yaml = True
        if "config_google_drive_calibre_url_base" in to_save:
            if to_save['config_google_drive_calibre_url_base'].endswith('/'):
                to_save['config_google_drive_calibre_url_base'] = to_save['config_google_drive_calibre_url_base'][:-1]
            if content.config_google_drive_calibre_url_base != to_save["config_google_drive_calibre_url_base"]:
                content.config_google_drive_calibre_url_base = to_save["config_google_drive_calibre_url_base"]
                create_new_yaml = True
        if ("config_use_google_drive" in to_save and not content.config_use_google_drive) or ("config_use_google_drive" not in to_save and content.config_use_google_drive):
            content.config_use_google_drive = "config_use_google_drive" in to_save
            db_change = True
        if not content.config_use_google_drive:
            create_new_yaml = False
        if create_new_yaml:
            with open('settings.yaml', 'w') as f:
                with open('gdrive_template.yaml', 'r') as t:
                    f.write(t.read() % {'client_id': content.config_google_drive_client_id,
                            'client_secret': content.config_google_drive_client_secret,
                            "redirect_uri": content.config_google_drive_calibre_url_base + '/gdrive/callback'})
        if "config_google_drive_folder" in to_save:
            if content.config_google_drive_folder != to_save["config_google_drive_folder"]:
                content.config_google_drive_folder = to_save["config_google_drive_folder"]
                db_change = True
        ##
        if "config_port" in to_save:
            if content.config_port != int(to_save["config_port"]):
                content.config_port = int(to_save["config_port"])
                reboot_required = True
        if "config_calibre_web_title" in to_save:
            content.config_calibre_web_title = to_save["config_calibre_web_title"]
        if "config_columns_to_ignore" in to_save:
            content.config_columns_to_ignore = to_save["config_columns_to_ignore"]
        if "config_title_regex" in to_save:
            if content.config_title_regex != to_save["config_title_regex"]:
                content.config_title_regex = to_save["config_title_regex"]
                reboot_required = True
        if "config_log_level" in to_save:
            content.config_log_level = int(to_save["config_log_level"])
        if "config_random_books" in to_save:
            content.config_random_books = int(to_save["config_random_books"])
        if "config_books_per_page" in to_save:
            content.config_books_per_page = int(to_save["config_books_per_page"])
        content.config_uploading = 0
        content.config_anonbrowse = 0
        content.config_public_reg = 0
        if "config_uploading" in to_save and to_save["config_uploading"] == "on":
            content.config_uploading = 1
        if "config_anonbrowse" in to_save and to_save["config_anonbrowse"] == "on":
            content.config_anonbrowse = 1
        if "config_public_reg" in to_save and to_save["config_public_reg"] == "on":
            content.config_public_reg = 1

        # Remote login configuration
        content.config_remote_login = ("config_remote_login" in to_save and to_save["config_remote_login"] == "on")
        if not content.config_remote_login:
            ub.session.query(ub.RemoteAuthToken).delete()

        # Goodreads configuration
        content.config_use_goodreads = ("config_use_goodreads" in to_save and to_save["config_use_goodreads"] == "on")
        if "config_goodreads_api_key" in to_save:
            content.config_goodreads_api_key = to_save["config_goodreads_api_key"]
        if "config_goodreads_api_secret" in to_save:
            content.config_goodreads_api_secret = to_save["config_goodreads_api_secret"]

        # Mature Content configuration
        if "config_mature_content_tags" in to_save:
            content.config_mature_content_tags = to_save["config_mature_content_tags"].strip()

        # Default user configuration
        content.config_default_role = 0
        if "admin_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_ADMIN
        if "download_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_DOWNLOAD
        if "upload_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_UPLOAD
        if "edit_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_EDIT
        if "delete_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_DELETE_BOOKS
        if "passwd_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_PASSWD
        if "passwd_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_EDIT_SHELFS
        content.config_default_show = 0
        if "show_detail_random" in to_save:
            content.config_default_show = content.config_default_show + ub.DETAIL_RANDOM
        if "show_language" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_LANGUAGE
        if "show_series" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_SERIES
        if "show_category" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_CATEGORY
        if "show_hot" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_HOT
        if "show_random" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_RANDOM
        if "show_author" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_AUTHOR
        if "show_best_rated" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_BEST_RATED
        if "show_read_and_unread" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_READ_AND_UNREAD
        if "show_recent" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_RECENT
        if "show_sorted" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_SORTED
        if content.config_logfile != to_save["config_logfile"]:
            # check valid path, only path or file
            if os.path.dirname(to_save["config_logfile"]):
                if os.path.exists(os.path.dirname(to_save["config_log_level"])):
                    content.config_logfile = to_save["config_logfile"]
                else:
                    ub.session.commit()
                    flash(_(u'Logfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", content=config, origin=origin,
                                                 gdrive=gdrive_support,
                                                 goodreads=goodreads_support, title=_(u"Basic Configuration"))
            else:
                content.config_logfile = to_save["config_logfile"]
            reboot_required = True
        try:
            if content.config_use_google_drive and is_gdrive_ready() and not os.path.exists(config.config_calibre_dir + "/metadata.db"):
                gdriveutils.downloadFile(Gdrive.Instance().drive, None, "metadata.db", config.config_calibre_dir + "/metadata.db")
            if db_change:
                if config.db_configured:
                    db.session.close()
                    db.engine.dispose()
            ub.session.commit()
            flash(_(u"Calibre-web configuration updated"), category="success")
            config.loadSettings()
            app.logger.setLevel(config.config_log_level)
            logging.getLogger("book_formats").setLevel(config.config_log_level)
        except e:
            flash(e, category="error")
            return render_title_template("config_edit.html", content=config, origin=origin, gdrive=gdrive_support,
                                         goodreads=goodreads_support, title=_(u"Basic Configuration"))
        if db_change:
            reload(db)
            if not db.setup_db():
                flash(_(u'DB location is not valid, please enter correct path'), category="error")
                return render_title_template("config_edit.html", content=config, origin=origin, gdrive=gdrive_support,
                                             goodreads=goodreads_support, title=_(u"Basic Configuration"))
        if reboot_required:
            # db.engine.dispose() # ToDo verify correct
            ub.session.close()
            ub.engine.dispose()
            # stop tornado server
            server = IOLoop.instance()
            server.add_callback(server.stop)
            helper.global_task = 0
            app.logger.info('Reboot required, restarting')
        if origin:
            success = True
    return render_title_template("config_edit.html", origin=origin, success=success, content=config,
                                 show_authenticate_google_drive=not is_gdrive_ready(), gdrive=gdrive_support,
                                 goodreads=goodreads_support, title=_(u"Basic Configuration"))


@app.route("/admin/user/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_user():
    content = ub.User()
    languages = db.session.query(db.Languages).all()
    for lang in languages:
        try:
            cur_l = LC.parse(lang.lang_code)
            lang.name = cur_l.get_language_name(get_locale())
        except Exception:
            lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    translations = [LC('en')] + babel.list_translations()
    if request.method == "POST":
        to_save = request.form.to_dict()
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         title=_(u"Add new user"))
        content.password = generate_password_hash(to_save["password"])
        content.nickname = to_save["nickname"]
        content.email = to_save["email"]
        content.default_language = to_save["default_language"]
        content.mature_content = "show_mature_content" in to_save
        if "locale" in to_save:
            content.locale = to_save["locale"]
        content.sidebar_view = 0
        if "show_random" in to_save:
            content.sidebar_view += ub.SIDEBAR_RANDOM
        if "show_language" in to_save:
            content.sidebar_view += ub.SIDEBAR_LANGUAGE
        if "show_series" in to_save:
            content.sidebar_view += ub.SIDEBAR_SERIES
        if "show_category" in to_save:
            content.sidebar_view += ub.SIDEBAR_CATEGORY
        if "show_hot" in to_save:
            content.sidebar_view += ub.SIDEBAR_HOT
        if "show_read_and_unread" in to_save:
            content.sidebar_view += ub.SIDEBAR_READ_AND_UNREAD
        if "show_best_rated" in to_save:
            content.sidebar_view += ub.SIDEBAR_BEST_RATED
        if "show_author" in to_save:
            content.sidebar_view += ub.SIDEBAR_AUTHOR
        if "show_detail_random" in to_save:
            content.sidebar_view += ub.DETAIL_RANDOM
        content.role = 0
        if "admin_role" in to_save:
            content.role = content.role + ub.ROLE_ADMIN
        if "download_role" in to_save:
            content.role = content.role + ub.ROLE_DOWNLOAD
        if "upload_role" in to_save:
            content.role = content.role + ub.ROLE_UPLOAD
        if "edit_role" in to_save:
            content.role = content.role + ub.ROLE_DELETE_BOOKS
        if "delete_role" in to_save:
            content.role = content.role + ub.ROLE_EDIT
        if "passwd_role" in to_save:
            content.role = content.role + ub.ROLE_PASSWD
        if "edit_shelf_role" in to_save:
            content.role = content.role + ub.ROLE_EDIT_SHELFS
        try:
            ub.session.add(content)
            ub.session.commit()
            flash(_(u"User '%(user)s' created", user=content.nickname), category="success")
            return redirect(url_for('admin'))
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"Found an existing account for this email address or nickname."), category="error")
    else:
        content.role = config.config_default_role
        content.sidebar_view = config.config_default_show
    return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                 languages=languages, title=_(u"Add new user"))


@app.route("/admin/mailsettings", methods=["GET", "POST"])
@login_required
@admin_required
def edit_mailsettings():
    content = ub.session.query(ub.Settings).first()
    if request.method == "POST":
        to_save = request.form.to_dict()
        content.mail_server = to_save["mail_server"]
        content.mail_port = int(to_save["mail_port"])
        content.mail_login = to_save["mail_login"]
        content.mail_password = to_save["mail_password"]
        content.mail_from = to_save["mail_from"]
        content.mail_use_ssl = int(to_save["mail_use_ssl"])
        try:
            ub.session.commit()
            flash(_(u"Mail settings updated"), category="success")
        except e:
            flash(e, category="error")
        if "test" in to_save and to_save["test"]:
            if current_user.kindle_mail:
                result = helper.send_test_mail(current_user.kindle_mail)
                if result is None:
                    flash(_(u"Test E-Mail successfully send to %(kindlemail)s", kindlemail=current_user.kindle_mail),
                          category="success")
                else:
                    flash(_(u"There was an error sending the Test E-Mail: %(res)s", res=result), category="error")
            else:
                flash(_(u"Please configure your kindle email address first..."), category="error")
        else:
            flash(_(u"E-Mail settings updated"), category="success")
    return render_title_template("email_edit.html", content=content, title=_(u"Edit mail settings"))


@app.route("/admin/user/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    content = ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()  # type: ub.User
    downloads = list()
    languages = db.session.query(db.Languages).all()
    for lang in languages:
        try:
            cur_l = LC.parse(lang.lang_code)
            lang.name = cur_l.get_language_name(get_locale())
        except Exception:
            lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    translations = babel.list_translations() + [LC('en')]
    for book in content.downloads:
        downloadBook = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
        if downloadBook:
            downloads.append(db.session.query(db.Books).filter(db.Books.id == book.book_id).first())
        else:
            ub.session.query(ub.Downloads).filter(book.book_id == ub.Downloads.book_id).delete()
            ub.session.commit()
    if request.method == "POST":
        to_save = request.form.to_dict()
        if "delete" in to_save:
            ub.session.query(ub.User).filter(ub.User.id == content.id).delete()
            ub.session.commit()
            flash(_(u"User '%(nick)s' deleted", nick=content.nickname), category="success")
            return redirect(url_for('admin'))
        else:
            if "password" in to_save and to_save["password"]:
                content.password = generate_password_hash(to_save["password"])

            if "admin_role" in to_save and not content.role_admin():
                content.role = content.role + ub.ROLE_ADMIN
            elif "admin_role" not in to_save and content.role_admin():
                content.role = content.role - ub.ROLE_ADMIN

            if "download_role" in to_save and not content.role_download():
                content.role = content.role + ub.ROLE_DOWNLOAD
            elif "download_role" not in to_save and content.role_download():
                content.role = content.role - ub.ROLE_DOWNLOAD

            if "upload_role" in to_save and not content.role_upload():
                content.role = content.role + ub.ROLE_UPLOAD
            elif "upload_role" not in to_save and content.role_upload():
                content.role = content.role - ub.ROLE_UPLOAD

            if "edit_role" in to_save and not content.role_edit():
                content.role = content.role + ub.ROLE_EDIT
            elif "edit_role" not in to_save and content.role_edit():
                content.role = content.role - ub.ROLE_EDIT

            if "delete_role" in to_save and not content.role_delete_books():
                content.role = content.role + ub.ROLE_DELETE_BOOKS
            elif "delete_role" not in to_save and content.role_delete_books():
                content.role = content.role - ub.ROLE_DELETE_BOOKS

            if "passwd_role" in to_save and not content.role_passwd():
                content.role = content.role + ub.ROLE_PASSWD
            elif "passwd_role" not in to_save and content.role_passwd():
                content.role = content.role - ub.ROLE_PASSWD

            if "edit_shelf_role" in to_save and not content.role_edit_shelfs():
                content.role = content.role + ub.ROLE_EDIT_SHELFS
            elif "edit_shelf_role" not in to_save and content.role_edit_shelfs():
                content.role = content.role - ub.ROLE_EDIT_SHELFS

            if "show_random" in to_save and not content.show_random_books():
                content.sidebar_view += ub.SIDEBAR_RANDOM
            elif "show_random" not in to_save and content.show_random_books():
                content.sidebar_view -= ub.SIDEBAR_RANDOM

            if "show_language" in to_save and not content.show_language():
                content.sidebar_view += ub.SIDEBAR_LANGUAGE
            elif "show_language" not in to_save and content.show_language():
                content.sidebar_view -= ub.SIDEBAR_LANGUAGE

            if "show_series" in to_save and not content.show_series():
                content.sidebar_view += ub.SIDEBAR_SERIES
            elif "show_series" not in to_save and content.show_series():
                content.sidebar_view -= ub.SIDEBAR_SERIES

            if "show_category" in to_save and not content.show_category():
                content.sidebar_view += ub.SIDEBAR_CATEGORY
            elif "show_category" not in to_save and content.show_category():
                content.sidebar_view -= ub.SIDEBAR_CATEGORY

            if "show_recent" in to_save and not content.show_recent():
                content.sidebar_view += ub.SIDEBAR_RECENT
            elif "show_recent" not in to_save and content.show_recent():
                content.sidebar_view -= ub.SIDEBAR_RECENT

            if "show_sorted" in to_save and not content.show_sorted():
                content.sidebar_view += ub.SIDEBAR_SORTED
            elif "show_sorted" not in to_save and content.show_sorted():
                content.sidebar_view -= ub.SIDEBAR_SORTED

            if "show_hot" in to_save and not content.show_hot_books():
                content.sidebar_view += ub.SIDEBAR_HOT
            elif "show_hot" not in to_save and content.show_hot_books():
                content.sidebar_view -= ub.SIDEBAR_HOT

            if "show_best_rated" in to_save and not content.show_best_rated_books():
                content.sidebar_view += ub.SIDEBAR_BEST_RATED
            elif "show_best_rated" not in to_save and content.show_best_rated_books():
                content.sidebar_view -= ub.SIDEBAR_BEST_RATED

            if "show_read_and_unread" in to_save and not content.show_read_and_unread():
                content.sidebar_view += ub.SIDEBAR_READ_AND_UNREAD
            elif "show_read_and_unread" not in to_save and content.show_read_and_unread():
                content.sidebar_view -= ub.SIDEBAR_READ_AND_UNREAD

            if "show_author" in to_save and not content.show_author():
                content.sidebar_view += ub.SIDEBAR_AUTHOR
            elif "show_author" not in to_save and content.show_author():
                content.sidebar_view -= ub.SIDEBAR_AUTHOR

            if "show_detail_random" in to_save and not content.show_detail_random():
                content.sidebar_view += ub.DETAIL_RANDOM
            elif "show_detail_random" not in to_save and content.show_detail_random():
                content.sidebar_view -= ub.DETAIL_RANDOM

            content.mature_content = "show_mature_content" in to_save

            if "default_language" in to_save:
                content.default_language = to_save["default_language"]
            if "locale" in to_save and to_save["locale"]:
                content.locale = to_save["locale"]
            if to_save["email"] and to_save["email"] != content.email:
                content.email = to_save["email"]
            if "kindle_mail" in to_save and to_save["kindle_mail"] != content.kindle_mail:
                content.kindle_mail = to_save["kindle_mail"]
        try:
            ub.session.commit()
            flash(_(u"User '%(nick)s' updated", nick=content.nickname), category="success")
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"An unknown error occured."), category="error")
    return render_title_template("user_edit.html", translations=translations, languages=languages, new_user=0,
                                 content=content, downloads=downloads,
                                 title=_(u"Edit User %(nick)s", nick=content.nickname))


@app.route("/admin/book/<int:book_id>", methods=['GET', 'POST'])
@login_required_if_no_ano
@edit_required
def edit_book(book_id):
    # create the function for sorting...
    db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    book = db.session.query(db.Books)\
        .filter(db.Books.id == book_id).filter(common_filters()).first()
    author_names = []

    # Book not found
    if not book:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible"), category="error")
        return redirect(url_for("index"))

    for index in range(0, len(book.languages)):
        try:
            book.languages[index].language_name = LC.parse(book.languages[index].lang_code).get_language_name(
                get_locale())
        except Exception:
            book.languages[index].language_name = _(isoLanguages.get(part3=book.languages[index].lang_code).name)
    for author in book.authors:
        author_names.append(author.name.replace('|', ','))

    # Show form
    if request.method != 'POST':
        return render_title_template('book_edit.html', book=book, authors=author_names, cc=cc,
                                     title=_(u"edit metadata"))

    # Update book
    edited_books_id = set()

    # Check and handle Uploaded file
    if 'btn-upload-format' in request.files and '.' in request.files['btn-upload-format'].filename:
        requested_file = request.files['btn-upload-format']
        file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            flash(_('File extension "%s" is not allowed to be uploaded to this server' % file_ext), category="error")
            return redirect(url_for('index'))

        file_name = book.path.rsplit('/', 1)[-1]
        filepath = config.config_calibre_dir + os.sep + book.path
        filepath = os.path.normpath(filepath)
        saved_filename = filepath + os.sep + file_name + '.' + file_ext

        try:
            requested_file.save(saved_filename)
        except OSError:
            flash(_(u"Failed to store file %s." % saved_filename), category="error")
            return redirect(url_for('index'))

        file_size = os.path.getsize(saved_filename)
        is_format = db.session.query(db.Data).filter(db.Data.book == book_id).filter(db.Data.format == file_ext.upper()).first()
        if is_format:
            # Format entry already exists, no need to update the database
            pass
        else:
            db_format = db.Data(book_id, file_ext.upper(), file_size, file_name)
            db.session.add(db_format)

    to_save = request.form.to_dict()

    if book.title != to_save["book_title"]:
        book.title = to_save["book_title"]
        edited_books_id.add(book.id)

    input_authors = to_save["author_name"].split('&')
    input_authors = list(map(lambda it: it.strip().replace(',', '|'), input_authors))
    # we have all author names now
    if input_authors == ['']:
        input_authors = [_(u'unknown')]  # prevent empty Author
    if book.authors:
        author0_before_edit = book.authors[0].name
    else:
        author0_before_edit = db.Authors(_(u'unknown'), '', 0)
    modify_database_object(input_authors, book.authors, db.Authors, db.session, 'author')
    if book.authors:
        if author0_before_edit != book.authors[0].name:
            edited_books_id.add(book.id)
            book.author_sort = helper.get_sorted_author(input_authors[0])

    error = False
    for b in edited_books_id:
        if config.config_use_google_drive:
            error = helper.update_dir_structure_gdrive(b)
        else:
            error = helper.update_dir_stucture(b, config.config_calibre_dir)
        if error:   # stop on error
            break
    if config.config_use_google_drive:
        updateGdriveCalibreFromLocal()

    if not error:
        if to_save["cover_url"] and save_cover(to_save["cover_url"], book.path):
            book.has_cover = 1

        if book.series_index != to_save["series_index"]:
            book.series_index = to_save["series_index"]

        if len(book.comments):
            book.comments[0].text = to_save["description"]
        else:
            book.comments.append(db.Comments(text=to_save["description"], book=book.id))

        input_tags = to_save["tags"].split(',')
        input_tags = list(map(lambda it: it.strip(), input_tags))
        modify_database_object(input_tags, book.tags, db.Tags, db.session, 'tags')

        input_series = [to_save["series"].strip()]
        input_series = [x for x in input_series if x != '']
        modify_database_object(input_series, book.series, db.Series, db.session, 'series')

        input_languages = to_save["languages"].split(',')
        input_languages = list(map(lambda it: it.strip().lower(), input_languages))

        if to_save["pubdate"]:
            try:
                book.pubdate = datetime.datetime.strptime(to_save["pubdate"], "%Y-%m-%d")
            except ValueError:
                book.pubdate = db.Books.DEFAULT_PUBDATE
        else:
            book.pubdate = db.Books.DEFAULT_PUBDATE

        # retranslate displayed text to language codes
        languages = db.session.query(db.Languages).all()
        input_l = []
        for lang in languages:
            try:
                lang.name = LC.parse(lang.lang_code).get_language_name(get_locale()).lower()
            except Exception:
                lang.name = _(isoLanguages.get(part3=lang.lang_code).name).lower()
            for inp_lang in input_languages:
                if inp_lang == lang.name:
                    input_l.append(lang.lang_code)
        modify_database_object(input_l, book.languages, db.Languages, db.session, 'languages')

        if to_save["rating"].strip():
            old_rating = False
            if len(book.ratings) > 0:
                old_rating = book.ratings[0].rating
            ratingx2 = int(float(to_save["rating"]) * 2)
            if ratingx2 != old_rating:
                is_rating = db.session.query(db.Ratings).filter(db.Ratings.rating == ratingx2).first()
                if is_rating:
                    book.ratings.append(is_rating)
                else:
                    new_rating = db.Ratings(rating=ratingx2)
                    book.ratings.append(new_rating)
                if old_rating:
                    book.ratings.remove(book.ratings[0])
        else:
            if len(book.ratings) > 0:
                book.ratings.remove(book.ratings[0])

        for c in cc:
            cc_string = "custom_column_" + str(c.id)
            if not c.is_multiple:
                if len(getattr(book, cc_string)) > 0:
                    cc_db_value = getattr(book, cc_string)[0].value
                else:
                    cc_db_value = None
                if to_save[cc_string].strip():
                    if c.datatype == 'bool':
                        if to_save[cc_string] == 'None':
                            to_save[cc_string] = None
                        else:
                            to_save[cc_string] = 1 if to_save[cc_string] == 'True' else 0
                        if to_save[cc_string] != cc_db_value:
                            if cc_db_value is not None:
                                if to_save[cc_string] is not None:
                                    setattr(getattr(book, cc_string)[0], 'value', to_save[cc_string])
                                else:
                                    del_cc = getattr(book, cc_string)[0]
                                    getattr(book, cc_string).remove(del_cc)
                                    db.session.delete(del_cc)
                            else:
                                cc_class = db.cc_classes[c.id]
                                new_cc = cc_class(value=to_save[cc_string], book=book_id)
                                db.session.add(new_cc)
                    elif c.datatype == 'int':
                        if to_save[cc_string] == 'None':
                            to_save[cc_string] = None
                        if to_save[cc_string] != cc_db_value:
                            if cc_db_value is not None:
                                if to_save[cc_string] is not None:
                                    setattr(getattr(book, cc_string)[0], 'value', to_save[cc_string])
                                else:
                                    del_cc = getattr(book, cc_string)[0]
                                    getattr(book, cc_string).remove(del_cc)
                                    db.session.delete(del_cc)
                            else:
                                cc_class = db.cc_classes[c.id]
                                new_cc = cc_class(value=to_save[cc_string], book=book_id)
                                db.session.add(new_cc)

                    else:
                        if c.datatype == 'rating':
                            to_save[cc_string] = str(int(float(to_save[cc_string]) * 2))
                        if to_save[cc_string].strip() != cc_db_value:
                            if cc_db_value is not None:
                                # remove old cc_val
                                del_cc = getattr(book, cc_string)[0]
                                getattr(book, cc_string).remove(del_cc)
                                if len(del_cc.books) == 0:
                                    db.session.delete(del_cc)
                            cc_class = db.cc_classes[c.id]
                            new_cc = db.session.query(cc_class).filter(
                                cc_class.value == to_save[cc_string].strip()).first()
                            # if no cc val is found add it
                            if new_cc is None:
                                new_cc = cc_class(value=to_save[cc_string].strip())
                                db.session.add(new_cc)
                                new_cc = db.session.query(cc_class).filter(
                                    cc_class.value == to_save[cc_string].strip()).first()
                            # add cc value to book
                            getattr(book, cc_string).append(new_cc)
                else:
                    if cc_db_value is not None:
                        # remove old cc_val
                        del_cc = getattr(book, cc_string)[0]
                        getattr(book, cc_string).remove(del_cc)
                        if len(del_cc.books) == 0:
                            db.session.delete(del_cc)
            else:
                input_tags = to_save[cc_string].split(',')
                input_tags = list(map(lambda it: it.strip(), input_tags))
                modify_database_object(input_tags, getattr(book, cc_string), db.cc_classes[c.id], db.session, 'custom')
        db.session.commit()
        author_names = []
        for author in book.authors:
            author_names.append(author.name)
        if "detail_view" in to_save:
            return redirect(url_for('show_book', book_id=book.id))
        else:
            return render_title_template('book_edit.html', book=book, authors=author_names, cc=cc,
                                         title=_(u"edit metadata"))
    else:
        db.session.rollback()
        flash( error, category="error")
        return render_title_template('book_edit.html', book=book, authors=author_names, cc=cc,
                                     title=_(u"edit metadata"))


def save_cover(url, book_path):
    img = requests.get(url)
    if img.headers.get('content-type') != 'image/jpeg':
        return false

    if config.config_use_google_drive:
        tmpDir = tempfile.gettempdir()
        f = open(os.path.join(tmpDir, "uploaded_cover.jpg"), "wb")
        f.write(img.content)
        f.close()
        gdriveutils.uploadFileToEbooksFolder(Gdrive.Instance().drive, os.path.join(book_path, 'cover.jpg'), os.path.join(tmpDir, f.name))
        return true

    f = open(os.path.join(config.config_calibre_dir, book_path, "cover.jpg"), "wb")
    f.write(img.content)
    f.close()
    return true


@app.route("/upload", methods=["GET", "POST"])
@login_required_if_no_ano
@upload_required
def upload():
    if not config.config_uploading:
        abort(404)
    # create the function for sorting...
    db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
    db.session.connection().connection.connection.create_function('uuid4', 0, lambda: str(uuid4()))
    if request.method == 'POST' and 'btn-upload' in request.files:
        requested_file = request.files['btn-upload']
        if '.' in requested_file.filename:
            file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                flash(
                    _('File extension "%s" is not allowed to be uploaded to this server' %
                    file_ext),
                    category="error"
                )
                return redirect(url_for('index'))
        else:
            flash(_('File to be uploaded must have an extension'), category="error")
            return redirect(url_for('index'))
        meta = uploader.upload(requested_file)

        title = meta.title
        author = meta.author
        tags = meta.tags
        series = meta.series
        series_index = meta.series_id
        title_dir = helper.get_valid_filename(title)
        author_dir = helper.get_valid_filename(author)
        data_name = title_dir
        filepath = config.config_calibre_dir + os.sep + author_dir + os.sep + title_dir
        saved_filename = filepath + os.sep + data_name + meta.extension.lower()

        if not os.path.exists(filepath):
            try:
                os.makedirs(filepath)
            except OSError:
                flash(_(u"Failed to create path %s (Permission denied)." % filepath), category="error")
                return redirect(url_for('index'))
        try:
            copyfile(meta.file_path, saved_filename)
        except OSError:
            flash(_(u"Failed to store file %s (Permission denied)." % saved_filename), category="error")
            return redirect(url_for('index'))
        try:
            os.unlink(meta.file_path)
        except OSError:
            flash(_(u"Failed to delete file %s (Permission denied)." % meta.file_path), category="warning")

        file_size = os.path.getsize(saved_filename)
        if meta.cover is None:
            has_cover = 0
            basedir = os.path.dirname(__file__)
            copyfile(os.path.join(basedir, "static/generic_cover.jpg"), os.path.join(filepath, "cover.jpg"))
        else:
            has_cover = 1
            move(meta.cover, os.path.join(filepath, "cover.jpg"))

        is_author = db.session.query(db.Authors).filter(db.Authors.name == author).first()
        if is_author:
            db_author = is_author
        else:
            db_author = db.Authors(author, helper.get_sorted_author(author), "")
            db.session.add(db_author)

        db_series = None
        is_series = db.session.query(db.Series).filter(db.Series.name == series).first()
        if is_series:
            db_series = is_series
        elif series != '':
            db_series = db.Series(series, "")
            db.session.add(db_series)

        # add language actually one value in list
        input_language = meta.languages
        db_language = None
        if input_language != "":
            input_language = isoLanguages.get(name=input_language).part3
            hasLanguage = db.session.query(db.Languages).filter(db.Languages.lang_code == input_language).first()
            if hasLanguage:
                db_language = hasLanguage
            else:
                db_language = db.Languages(input_language)
                db.session.add(db_language)
        # combine path and normalize path from windows systems
        path = os.path.join(author_dir, title_dir).replace('\\', '/')
        db_book = db.Books(title, "", db_author.sort, datetime.datetime.now(), datetime.datetime(101, 1, 1),
                           series_index, datetime.datetime.now(), path, has_cover, db_author, [], db_language)
        db_book.authors.append(db_author)
        if db_series:
            db_book.series.append(db_series)
        if db_language is not None:
            db_book.languages.append(db_language)
        db_data = db.Data(db_book, meta.extension.upper()[1:], file_size, data_name)
        db_book.data.append(db_data)

        db.session.add(db_book)
        db.session.flush()  # flush content get db_book.id avalible
        # add comment
        upload_comment = Markup(meta.description).unescape()
        if upload_comment != "":
            db.session.add(db.Comments(upload_comment, db_book.id))
        db.session.commit()

        input_tags = tags.split(',')
        input_tags = list(map(lambda it: it.strip(), input_tags))
        modify_database_object(input_tags, db_book.tags, db.Tags, db.session, 'tags')

        if db_language is not None:  # display Full name instead of iso639.part3
            db_book.languages[0].language_name = _(meta.languages)
        author_names = []
        for author in db_book.authors:
            author_names.append(author.name)
        if config.config_use_google_drive:
            updateGdriveCalibreFromLocal()
        cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
        if current_user.role_edit() or current_user.role_admin():
            return render_title_template('book_edit.html', book=db_book, authors=author_names, cc=cc,
                                         title=_(u"edit metadata"))
        book_in_shelfs = []
        return render_title_template('detail.html', entry=db_book, cc=cc, title=db_book.title,
                                     books_shelfs=book_in_shelfs, )
    else:
        return redirect(url_for("index"))


def start_gevent():
    from gevent.wsgi import WSGIServer
    global gevent_server
    try:
        gevent_server = WSGIServer(('', ub.config.config_port), app)
        gevent_server.serve_forever()
    except SocketError:
        app.logger.info('Unable to listen on \'\', trying on IPv4 only...')
        gevent_server = WSGIServer(('0.0.0.0', ub.config.config_port), app)
        gevent_server.serve_forever()
    except:
        pass
