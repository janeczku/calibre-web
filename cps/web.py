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
import logging
from logging.handlers import RotatingFileHandler
from flask import (Flask, render_template, request, Response, redirect,
                   url_for, send_from_directory, make_response, g, flash,
                   abort, Markup)
from flask import __version__ as flaskVersion
from werkzeug import __version__ as werkzeugVersion
from werkzeug.exceptions import default_exceptions

from jinja2 import __version__  as jinja2Version
import cache_buster
import ub
from ub import config
import helper
import os
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
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.datastructures import Headers
from babel import Locale as LC
from babel import negotiate_locale
from babel import __version__ as babelVersion
from babel.dates import format_date, format_datetime
from babel.core import UnknownLocaleError
from functools import wraps
import base64
from sqlalchemy.sql import *
import json
import datetime
import isoLanguages
from pytz import __version__ as pytzVersion
from uuid import uuid4
import os.path
import sys
import re
import db
from shutil import move, copyfile
import gdriveutils
import converter
import tempfile
from redirect import redirect_back
import time
import server
from reverseproxy import ReverseProxied
from updater import updater_thread
import hashlib
import unidecode

try:
    from googleapiclient.errors import HttpError
except ImportError:
    pass

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

try:
    import rarfile
    rar_support=True
except ImportError:
    rar_support=False

try:
    from natsort import natsorted as sort
except ImportError:
    sort=sorted # Just use regular sort then
                #   may cause issues with badly named pages in cbz/cbr files
try:
    import cPickle
except ImportError:
    import pickle as cPickle

try:
    from urllib.parse import quote
    from imp import reload
except ImportError:
    from urllib import quote

try:
    from flask_login import __version__ as flask_loginVersion
except ImportError:
    from flask_login.__about__ import __version__ as flask_loginVersion


# Global variables
current_milli_time = lambda: int(round(time.time() * 1000))
gdrive_watch_callback_token = 'target=calibreweb-watch_files'
# ToDo: Somehow caused by circular import under python3 refactor
py3_gevent_link = None
py3_restart_Typ = False
EXTENSIONS_UPLOAD = {'txt', 'pdf', 'epub', 'mobi', 'azw', 'azw3', 'cbr', 'cbz', 'cbt', 'djvu', 'prc', 'doc', 'docx',
                      'fb2', 'html', 'rtf', 'odt'}
EXTENSIONS_CONVERT = {'pdf', 'epub', 'mobi', 'azw3', 'docx', 'rtf', 'fb2', 'lit', 'lrf', 'txt', 'htmlz'}


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

# custom error page
def error_http(error):
    return render_template('http_error.html',
                            error_code=error.code,
                            error_name=error.name,
                            instance=config.config_calibre_web_title
                            ), error.code

# http error handling
for ex in default_exceptions:
    # new routine for all client errors, server errors stay
    if ex < 500:
        app.register_error_handler(ex, error_http)

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
babel = Babel(app)

import uploader

lm = LoginManager(app)
lm.init_app(app)
lm.login_view = 'login'
lm.anonymous_user = ub.Anonymous
app.secret_key = os.getenv('SECRET_KEY', 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT')
db.setup_db()

try:
    with open(os.path.join(config.get_main_dir, 'cps/translations/iso639.pickle'), 'rb') as f:
        language_table = cPickle.load(f)
except cPickle.UnpicklingError as error:
    app.logger.error("Can't read file cps/translations/iso639.pickle: %s", error)
    print("Can't read file cps/translations/iso639.pickle: %s" % error)
    helper.global_WorkerThread.stop()
    sys.exit(1)

def is_gdrive_ready():
    return os.path.exists(os.path.join(config.get_main_dir, 'settings.yaml')) and \
           os.path.exists(os.path.join(config.get_main_dir, 'gdrive_credentials'))



@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
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


@lm.user_loader
def load_user(user_id):
    return ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()


@lm.header_loader
def load_user_from_header(header_val):
    if header_val.startswith('Basic '):
        header_val = header_val.replace('Basic ', '', 1)
    basic_username = basic_password = ''
    try:
        header_val = base64.b64decode(header_val).decode('utf-8')
        basic_username = header_val.split(':')[0]
        basic_password = header_val.split(':')[1]
    except TypeError:
        pass
    user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == basic_username.lower()).first()
    if user and check_password_hash(user.password, basic_password):
        return user
    return


def check_auth(username, password):
    if sys.version_info.major == 3:
        username=username.encode('windows-1252')
    user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == username.decode('utf-8').lower()).first()
    return bool(user and check_password_hash(user.password, password))


def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


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

    # right_edge: last right_edges count of all pages are shown as number, means, if 10 pages are paginated -> 9,10 shwn
    # left_edge: first left_edges count of all pages are shown as number                                    -> 1,2 shwn
    # left_current: left_current count below current page are shown as number, means if current page 5      -> 3,4 shwn
    # left_current: right_current count above current page are shown as number, means if current page 5     -> 6,7 shwn
    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=4, right_edge=2):
        last = 0
        left_current = self.page - left_current - 1
        right_current = self.page + right_current + 1
        right_edge = self.pages - right_edge
        for num in range(1, (self.pages + 1)):
            if num <= left_edge or (left_current < num < right_current) or num > right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


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
            response = make_response(json.dumps(data, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return response, 403
        abort(403)

    return inner


# custom jinja filters

# pagination links in jinja
@app.template_filter('url_for_other_page')
def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


# shortentitles to at longest nchar, shorten longer words if necessary
@app.template_filter('shortentitle')
def shortentitle_filter(s, nchar=20):
    text = s.split()
    res = ""  # result
    suml = 0  # overall length
    for line in text:
        if suml >= 60:
            res += '...'
            break
        # if word longer than 20 chars truncate line and append '...', otherwise add whole word to result
        # string, and summarize total length to stop at chars given by nchar
        if len(line) > nchar:
            res += line[:(nchar-3)] + '[..] '
            suml += nchar+3
        else:
            res += line + ' '
            suml += len(line) + 1
    return res.strip()


@app.template_filter('mimetype')
def mimetype_filter(val):
    try:
        s = mimetypes.types_map['.' + val]
    except Exception:
        s = 'application/octet-stream'
    return s


@app.template_filter('formatdate')
def formatdate_filter(val):
    try:
        conformed_timestamp = re.sub(r"[:]|([-](?!((\d{2}[:]\d{2})|(\d{4}))$))", '', val)
        formatdate = datetime.datetime.strptime(conformed_timestamp[:15], "%Y%m%d %H%M%S")
        return format_date(formatdate, format='medium', locale=get_locale())
    except AttributeError as e:
        app.logger.error('Babel error: %s, Current user locale: %s, Current User: %s' % (e, current_user.locale, current_user.nickname))
        return formatdate



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


'''@app.template_filter('canread')
def canread(ext):
    if isinstance(ext, db.Data):
        ext = ext.format
    return ext.lower() in EXTENSIONS_READER'''


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
        if current_user.role_download():
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


# Language and content filters for displaying in the UI
def common_filters():
    if current_user.filter_language() != "all":
        lang_filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        lang_filter = true()
    content_rating_filter = false() if current_user.mature_content else \
        db.Books.tags.any(db.Tags.name.in_(config.mature_content_tags()))
    return and_(lang_filter, ~content_rating_filter)


# Creates for all stored languages a translated speaking name in the array for the UI
def speaking_language(languages=None):
    if not languages:
        languages = db.session.query(db.Languages).all()
    for lang in languages:
        try:
            cur_l = LC.parse(lang.lang_code)
            lang.name = cur_l.get_language_name(get_locale())
        except UnknownLocaleError:
            lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    return languages

# Orders all Authors in the list according to authors sort
def order_authors(entry):
    sort_authors = entry.author_sort.split('&')
    authors_ordered = list()
    error = False
    for auth in sort_authors:
        # ToDo: How to handle not found authorname
        result = db.session.query(db.Authors).filter(db.Authors.sort == auth.lstrip().strip()).first()
        if not result:
            error = True
            break
        authors_ordered.append(result)
    if not error:
        entry.authors = authors_ordered
    return entry

# Fill indexpage with all requested data from database
def fill_indexpage(page, database, db_filter, order, *join):
    if current_user.show_detail_random():
        randm = db.session.query(db.Books).filter(common_filters())\
            .order_by(func.random()).limit(config.config_random_books)
    else:
        randm = false()
    off = int(int(config.config_books_per_page) * (page - 1))
    pagination = Pagination(page, config.config_books_per_page,
                            len(db.session.query(database)
                            .filter(db_filter).filter(common_filters()).all()))
    entries = db.session.query(database).join(*join,isouter=True).filter(db_filter)\
            .filter(common_filters()).order_by(*order).offset(off).limit(config.config_books_per_page).all()
    for book in entries:
        book = order_authors(book)
    return entries, randm, pagination


# Modifies different Database objects, first check if elements have to be added to database, than check
# if elements have to be deleted, because they are no longer used
def modify_database_object(input_elements, db_book_object, db_object, db_session, db_type):
    # passing input_elements not as a list may lead to undesired results
    if not isinstance(input_elements, list):
        raise TypeError(str(input_elements) + " should be passed as a list")

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
            if inp_element.lower() == type_elements.lower():
                # if inp_element == type_elements:
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
            db_element = db_session.query(db_object).filter(db_filter == add_element).first()
            # if no element is found add it
            # if new_element is None:
            if db_type == 'author':
                new_element = db_object(add_element, helper.get_sorted_author(add_element.replace('|', ',')), "")
            elif db_type == 'series':
                new_element = db_object(add_element, add_element)
            elif db_type == 'custom':
                new_element = db_object(value=add_element)
            elif db_type == 'publisher':
                new_element = db_object(add_element, None)
            else:  # db_type should be tag or language
                new_element = db_object(add_element)
            if db_element is None:
                db_session.add(new_element)
                db_book_object.append(new_element)
            else:
                if db_type == 'custom':
                    if db_element.value != add_element:
                        new_element.value = add_element
                        # new_element = db_element
                elif db_type == 'languages':
                    if db_element.lang_code != add_element:
                        db_element.lang_code = add_element
                        # new_element = db_element
                elif db_type == 'series':
                    if db_element.name != add_element:
                        db_element.name = add_element # = add_element # new_element = db_object(add_element, add_element)
                        db_element.sort = add_element
                        # new_element = db_element
                elif db_type == 'author':
                    if db_element.name != add_element:
                        db_element.name = add_element
                        db_element.sort = add_element.replace('|', ',')
                        # new_element = db_element
                elif db_type == 'publisher':
                    if db_element.name != add_element:
                        db_element.name = add_element
                        db_element.sort = None
                        # new_element = db_element
                elif db_element.name != add_element:
                    db_element.name = add_element
                    # new_element = db_element
                # add element to book
                db_book_object.append(db_element)


# read search results from calibre-database and return it (function is used for feed and simple search
def get_search_results(term):
    db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
    q = list()
    authorterms = re.split("[, ]+", term)
    for authorterm in authorterms:
        q.append(db.Books.authors.any(db.func.lower(db.Authors.name).ilike("%" + authorterm + "%")))

    db.Books.authors.any(db.func.lower(db.Authors.name).ilike("%" + term + "%"))

    return db.session.query(db.Books).filter(common_filters()).filter(
        db.or_(db.Books.tags.any(db.func.lower(db.Tags.name).ilike("%" + term + "%")),
               db.Books.series.any(db.func.lower(db.Series.name).ilike("%" + term + "%")),
               db.Books.authors.any(and_(*q)),
               db.Books.publishers.any(db.func.lower(db.Publishers.name).ilike("%" + term + "%")),
               db.func.lower(db.Books.title).ilike("%" + term + "%")
               )).all()


def feed_search(term):
    if term:
        term = term.strip().lower()
        entries = get_search_results( term)
        entriescount = len(entries) if len(entries) > 0 else 1
        pagination = Pagination(1, entriescount, entriescount)
        return render_xml_template('feed.xml', searchterm=term, entries=entries, pagination=pagination)
    else:
        return render_xml_template('feed.xml', searchterm="")


def render_xml_template(*args, **kwargs):
    #ToDo: return time in current timezone similar to %z
    currtime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    xml = render_template(current_time=currtime, instance=config.config_calibre_web_title, *args, **kwargs)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


# Returns the template for redering and includes the instance name
def render_title_template(*args, **kwargs):
    return render_template(instance=config.config_calibre_web_title, accept=EXTENSIONS_UPLOAD, *args, **kwargs)


@app.before_request
def before_request():
    g.user = current_user
    g.allow_registration = config.config_public_reg
    g.allow_upload = config.config_uploading
    g.current_theme = config.config_theme
    g.config_authors_max = config.config_authors_max
    g.public_shelfes = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1).order_by(ub.Shelf.name).all()
    if not config.db_configured and request.endpoint not in ('basic_configuration', 'login') and '/static/' not in request.path:
        return redirect(url_for('basic_configuration'))


# Routing functions

@app.route("/opds/")
@app.route("/opds")
@requires_basic_auth_if_no_ano
def feed_index():
    return render_xml_template('index.xml')


@app.route("/opds/osd")
@requires_basic_auth_if_no_ano
def feed_osd():
    return render_xml_template('osd.xml', lang='en-EN')


@app.route("/opds/search/", defaults={'query': ""})
@app.route("/opds/search/<query>")
@requires_basic_auth_if_no_ano
def feed_cc_search(query):
    return feed_search(query.strip())


@app.route("/opds/search", methods=["GET"])
@requires_basic_auth_if_no_ano
def feed_normal_search():
    return feed_search(request.args.get("query").strip())


@app.route("/opds/new")
@requires_basic_auth_if_no_ano
def feed_new():
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                                                 db.Books, True, [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@app.route("/opds/discover")
@requires_basic_auth_if_no_ano
def feed_discover():
    entries = db.session.query(db.Books).filter(common_filters()).order_by(func.random())\
        .limit(config.config_books_per_page)
    pagination = Pagination(1, config.config_books_per_page, int(config.config_books_per_page))
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@app.route("/opds/rated")
@requires_basic_auth_if_no_ano
def feed_best_rated():
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.ratings.any(db.Ratings.rating > 9), [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@app.route("/opds/hot")
@requires_basic_auth_if_no_ano
def feed_hot():
    off = request.args.get("offset") or 0
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
            ub.delete_download(book.Downloads.book_id)
            # ub.session.query(ub.Downloads).filter(book.Downloads.book_id == ub.Downloads.book_id).delete()
            # ub.session.commit()
    numBooks = entries.__len__()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1),
                            config.config_books_per_page, numBooks)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@app.route("/opds/author")
@requires_basic_auth_if_no_ano
def feed_authorindex():
    off = request.args.get("offset") or 0
    entries = db.session.query(db.Authors).join(db.books_authors_link).join(db.Books).filter(common_filters())\
        .group_by(text('books_authors_link.author')).order_by(db.Authors.sort).limit(config.config_books_per_page).offset(off)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Authors).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='feed_author', pagination=pagination)


@app.route("/opds/author/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_author(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.authors.any(db.Authors.id == book_id), [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@app.route("/opds/publisher")
@requires_basic_auth_if_no_ano
def feed_publisherindex():
    off = request.args.get("offset") or 0
    entries = db.session.query(db.Publishers).join(db.books_publishers_link).join(db.Books).filter(common_filters())\
        .group_by(text('books_publishers_link.publisher')).order_by(db.Publishers.sort).limit(config.config_books_per_page).offset(off)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Publishers).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='feed_publisher', pagination=pagination)


@app.route("/opds/publisher/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_publisher(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                                             db.Books, db.Books.publishers.any(db.Publishers.id == book_id),
                                             [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@app.route("/opds/category")
@requires_basic_auth_if_no_ano
def feed_categoryindex():
    off = request.args.get("offset") or 0
    entries = db.session.query(db.Tags).join(db.books_tags_link).join(db.Books).filter(common_filters())\
        .group_by(text('books_tags_link.tag')).order_by(db.Tags.name).offset(off).limit(config.config_books_per_page)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Tags).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='feed_category', pagination=pagination)


@app.route("/opds/category/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_category(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.tags.any(db.Tags.id == book_id), [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@app.route("/opds/series")
@requires_basic_auth_if_no_ano
def feed_seriesindex():
    off = request.args.get("offset") or 0
    entries = db.session.query(db.Series).join(db.books_series_link).join(db.Books).filter(common_filters())\
        .group_by(text('books_series_link.series')).order_by(db.Series.sort).offset(off).all()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Series).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='feed_series', pagination=pagination)


@app.route("/opds/series/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_series(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.series.any(db.Series.id == book_id), [db.Books.series_index])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@app.route("/opds/shelfindex/", defaults={'public': 0})
@app.route("/opds/shelfindex/<string:public>")
@requires_basic_auth_if_no_ano
def feed_shelfindex(public):
    off = request.args.get("offset") or 0
    if public is not 0:
        shelf = g.public_shelfes
        number = len(shelf)
    else:
        shelf = g.user.shelf
        number = shelf.count()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            number)
    return render_xml_template('feed.xml', listelements=shelf, folder='feed_shelf', pagination=pagination)


@app.route("/opds/shelf/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_shelf(book_id):
    off = request.args.get("offset") or 0
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
        return render_xml_template('feed.xml', entries=result, pagination=pagination)


@app.route("/opds/download/<book_id>/<book_format>/")
@requires_basic_auth_if_no_ano
@download_required
def get_opds_download_link(book_id, book_format):
    book_format = book_format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == book_format.upper()).first()
    app.logger.info(data.name)
    if current_user.is_authenticated:
        ub.update_download(book_id, int(current_user.id))
    file_name = book.title
    if len(book.authors) > 0:
        file_name = book.authors[0].name + '_' + file_name
    file_name = helper.get_valid_filename(file_name)
    headers = Headers()
    headers["Content-Disposition"] = "attachment; filename*=UTF-8''%s.%s" % (quote(file_name.encode('utf8')),
                                                                             book_format)
    try:
        headers["Content-Type"] = mimetypes.types_map['.' + book_format]
    except KeyError:
        headers["Content-Type"] = "application/octet-stream"
    return helper.do_download_file(book, book_format, data, headers)


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

@app.route("/ajax/emailstat")
@login_required
def get_email_status_json():
    tasks=helper.global_WorkerThread.get_taskstatus()
    answer = helper.render_task_status(tasks)
    js=json.dumps(answer, default=helper.json_serial)
    response = make_response(js)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


# checks if domain is in database (including wildcards)
# example SELECT * FROM @TABLE WHERE  'abcdefg' LIKE Name;
# from https://code.luasoftware.com/tutorials/flask/execute-raw-sql-in-flask-sqlalchemy/
def check_valid_domain(domain_text):
    domain_text = domain_text.split('@',1)[-1].lower()
    sql = "SELECT * FROM registration WHERE :domain LIKE domain;"
    result = ub.session.query(ub.Registration).from_statement(text(sql)).params(domain=domain_text).all()
    return len(result)


@app.route("/ajax/editdomain", methods=['POST'])
@login_required
@admin_required
def edit_domain():
    ''' POST /post
        name:  'username',  //name of field (column in db)
        pk:    1            //primary key (record id)
        value: 'superuser!' //new value'''
    vals = request.form.to_dict()
    answer = ub.session.query(ub.Registration).filter(ub.Registration.id == vals['pk']).first()
    # domain_name = request.args.get('domain')
    answer.domain = vals['value'].replace('*','%').replace('?','_').lower()
    ub.session.commit()
    return ""


@app.route("/ajax/adddomain", methods=['POST'])
@login_required
@admin_required
def add_domain():
    domain_name = request.form.to_dict()['domainname'].replace('*','%').replace('?','_').lower()
    check = ub.session.query(ub.Registration).filter(ub.Registration.domain == domain_name).first()
    if not check:
        new_domain = ub.Registration(domain=domain_name)
        ub.session.add(new_domain)
        ub.session.commit()
    return ""


@app.route("/ajax/deletedomain", methods=['POST'])
@login_required
@admin_required
def delete_domain():
    domain_id = request.form.to_dict()['domainid'].replace('*','%').replace('?','_').lower()
    ub.session.query(ub.Registration).filter(ub.Registration.id == domain_id).delete()
    ub.session.commit()
    # If last domain was deleted, add all domains by default
    if not ub.session.query(ub.Registration).count():
        new_domain = ub.Registration(domain="%.%")
        ub.session.add(new_domain)
        ub.session.commit()
    return ""


@app.route("/ajax/domainlist")
@login_required
@admin_required
def list_domain():
    answer = ub.session.query(ub.Registration).all()
    json_dumps = json.dumps([{"domain":r.domain.replace('%','*').replace('_','?'),"id":r.id} for r in answer])
    js=json.dumps(json_dumps.replace('"', "'")).lstrip('"').strip('"')
    response = make_response(js.replace("'",'"'))
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


'''
@app.route("/ajax/getcomic/<int:book_id>/<book_format>/<int:page>")
@login_required
def get_comic_book(book_id, book_format, page):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    if not book:
        return "", 204
    else:
        for bookformat in book.data:
            if bookformat.format.lower() == book_format.lower():
                cbr_file = os.path.join(config.config_calibre_dir, book.path, bookformat.name) + "." + book_format
                if book_format in ("cbr", "rar"):
                    if rar_support == True:
                        rarfile.UNRAR_TOOL = config.config_rarfile_location
                        try:
                            rf = rarfile.RarFile(cbr_file)
                            names = sort(rf.namelist())
                            extract = lambda page: rf.read(names[page])
                        except:
                            # rarfile not valid
                            app.logger.error('Unrar binary not found, or unable to decompress file ' + cbr_file)
                            return "", 204
                    else:
                        app.logger.info('Unrar is not supported please install python rarfile extension')
                        # no support means return nothing
                        return "", 204
                elif book_format in ("cbz", "zip"):
                    zf = zipfile.ZipFile(cbr_file)
                    names=sort(zf.namelist())
                    extract = lambda page: zf.read(names[page])
                elif book_format in ("cbt", "tar"):
                    tf = tarfile.TarFile(cbr_file)
                    names=sort(tf.getnames())
                    extract = lambda page: tf.extractfile(names[page]).read()
                else:
                    app.logger.error('unsupported comic format')
                    return "", 204

                if sys.version_info.major >= 3:
                    b64 = codecs.encode(extract(page), 'base64').decode()
                else:
                    b64 = extract(page).encode('base64')
                ext = names[page].rpartition('.')[-1]
                if ext not in ('png', 'gif', 'jpg', 'jpeg'):
                    ext = 'png'
                extractedfile="data:image/" + ext + ";base64," + b64
                fileData={"name": names[page], "page":page, "last":len(names)-1, "content": extractedfile}
                return make_response(json.dumps(fileData))
        return "", 204
'''


@app.route("/get_authors_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_authors_json():
    if request.method == "GET":
        query = request.args.get('q')
        db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
        entries = db.session.query(db.Authors).filter(db.func.lower(db.Authors.name).ilike("%" + query + "%")).all()
        json_dumps = json.dumps([dict(name=r.name.replace('|',',')) for r in entries])
        return json_dumps


@app.route("/get_publishers_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_publishers_json():
    if request.method == "GET":
        query = request.args.get('q')
        db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
        entries = db.session.query(db.Publishers).filter(db.func.lower(db.Publishers.name).ilike("%" + query + "%")).all()
        json_dumps = json.dumps([dict(name=r.name.replace('|',',')) for r in entries])
        return json_dumps


@app.route("/get_tags_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_tags_json():
    if request.method == "GET":
        query = request.args.get('q')
        db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
        entries = db.session.query(db.Tags).filter(db.func.lower(db.Tags.name).ilike("%" + query + "%")).all()
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@app.route("/get_languages_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_languages_json():
    if request.method == "GET":
        query = request.args.get('q').lower()
        # languages = speaking_language()
        languages = language_table[get_locale()]
        entries_start = [s for key, s in languages.items() if s.lower().startswith(query.lower())]
        if len(entries_start) < 5:
            entries = [s for key,s in languages.items() if query in s.lower()]
            entries_start.extend(entries[0:(5-len(entries_start))])
            entries_start = list(set(entries_start))
        json_dumps = json.dumps([dict(name=r) for r in entries_start[0:5]])
        return json_dumps


@app.route("/get_series_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_series_json():
    if request.method == "GET":
        query = request.args.get('q')
        db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
        entries = db.session.query(db.Series).filter(db.func.lower(db.Series.name).ilike("%" + query + "%")).all()
        # entries = db.session.execute("select name from series where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@app.route("/get_matching_tags", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_matching_tags():
    tag_dict = {'tags': []}
    if request.method == "GET":
        q = db.session.query(db.Books)
        db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
        author_input = request.args.get('author_name')
        title_input = request.args.get('book_title')
        include_tag_inputs = request.args.getlist('include_tag')
        exclude_tag_inputs = request.args.getlist('exclude_tag')
        q = q.filter(db.Books.authors.any(db.func.lower(db.Authors.name).ilike("%" + author_input + "%")),
                     db.func.lower(db.Books.title).ilike("%" + title_input + "%"))
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


@app.route("/get_update_status", methods=['GET'])
@login_required_if_no_ano
def get_update_status():
    return updater_thread.get_available_updates(request.method)


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
                "4": _(u'Replacing files'),
                "5": _(u'Database connections are closed'),
                "6": _(u'Stopping server'),
                "7": _(u'Update finished, please press okay and reload page'),
                "8": _(u'Update failed:') + u' ' + _(u'HTTP Error'),
                "9": _(u'Update failed:') + u' ' + _(u'Connection error'),
                "10": _(u'Update failed:') + u' ' + _(u'Timeout while establishing connection'),
                "11": _(u'Update failed:') + u' ' + _(u'General error')
            }
            status['text'] = text
            # helper.updater_thread = helper.Updater()
            updater_thread.status = 0
            updater_thread.start()
            status['status'] = updater_thread.get_update_status()
    elif request.method == "GET":
        try:
            status['status'] = updater_thread.get_update_status()
            if status['status']  == -1:
                status['status'] = 7
        except AttributeError:
            # thread is not active, occours after restart on update
            status['status'] = 7
        except Exception:
            status['status'] = 11
    return json.dumps(status)


@app.route("/", defaults={'page': 1})
@app.route('/page/<int:page>')
@login_required_if_no_ano
def index(page):
    entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.timestamp.desc()])
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Recently Added Books"), page="root", config_authors_max=config.config_authors_max)


@app.route('/books/newest', defaults={'page': 1})
@app.route('/books/newest/page/<int:page>')
@login_required_if_no_ano
def newest_books(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.pubdate.desc()])
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Newest Books"), page="newest")
    else:
        abort(404)


@app.route('/books/oldest', defaults={'page': 1})
@app.route('/books/oldest/page/<int:page>')
@login_required_if_no_ano
def oldest_books(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.pubdate])
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Oldest Books"), page="oldest")
    else:
        abort(404)


@app.route('/books/a-z', defaults={'page': 1})
@app.route('/books/a-z/page/<int:page>')
@login_required_if_no_ano
def titles_ascending(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.sort])
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Books (A-Z)"), page="a-z")
    else:
        abort(404)


@app.route('/books/z-a', defaults={'page': 1})
@app.route('/books/z-a/page/<int:page>')
@login_required_if_no_ano
def titles_descending(page):
    entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.sort.desc()])
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Books (Z-A)"), page="z-a")


@app.route("/hot", defaults={'page': 1})
@app.route('/hot/page/<int:page>')
@login_required_if_no_ano
def hot_books(page):
    if current_user.show_hot_books():
        if current_user.show_detail_random():
            random = db.session.query(db.Books).filter(common_filters())\
                .order_by(func.random()).limit(config.config_random_books)
        else:
            random = false()
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
                ub.delete_download(book.Downloads.book_id)
                # ub.session.query(ub.Downloads).filter(book.Downloads.book_id == ub.Downloads.book_id).delete()
                # ub.session.commit()
        numBooks = entries.__len__()
        pagination = Pagination(page, config.config_books_per_page, numBooks)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Hot Books (most downloaded)"), page="hot")
    else:
       abort(404)


@app.route("/rated", defaults={'page': 1})
@app.route('/rated/page/<int:page>')
@login_required_if_no_ano
def best_rated_books(page):
    if current_user.show_best_rated_books():
        entries, random, pagination = fill_indexpage(page, db.Books, db.Books.ratings.any(db.Ratings.rating > 9),
                                                     [db.Books.timestamp.desc()])
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Best rated books"), page="rated")
    else:
        abort(404)


@app.route("/discover", defaults={'page': 1})
@app.route('/discover/page/<int:page>')
@login_required_if_no_ano
def discover(page):
    if current_user.show_random_books():
        entries, __, pagination = fill_indexpage(page, db.Books, True, [func.randomblob(2)])
        pagination = Pagination(1, config.config_books_per_page, config.config_books_per_page)
        return render_title_template('discover.html', entries=entries, pagination=pagination,
                                     title=_(u"Random Books"), page="discover")
    else:
        abort(404)


@app.route("/author")
@login_required_if_no_ano
def author_list():
    if current_user.show_author():
        entries = db.session.query(db.Authors, func.count('books_authors_link.book').label('count'))\
            .join(db.books_authors_link).join(db.Books).filter(common_filters())\
            .group_by(text('books_authors_link.author')).order_by(db.Authors.sort).all()
        for entry in entries:
            entry.Authors.name = entry.Authors.name.replace('|', ',')
        return render_title_template('list.html', entries=entries, folder='author',
                                     title=u"Author list", page="authorlist")
    else:
        abort(404)


@app.route("/author/<int:book_id>", defaults={'page': 1})
@app.route("/author/<int:book_id>/<int:page>")
@login_required_if_no_ano
def author(book_id, page):
    entries, __, pagination = fill_indexpage(page, db.Books, db.Books.authors.any(db.Authors.id == book_id),
                                            [db.Series.name, db.Books.series_index],db.books_series_link, db.Series)
    if entries is None:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))

    name = (db.session.query(db.Authors).filter(db.Authors.id == book_id).first().name).replace('|', ',')

    author_info = None
    other_books = []
    if goodreads_support and config.config_use_goodreads:
        try:
            gc = GoodreadsClient(config.config_goodreads_api_key, config.config_goodreads_api_secret)
            author_info = gc.find_author(author_name=name)
            other_books = get_unique_other_books(entries.all(), author_info.books)
        except Exception:
            # Skip goodreads, if site is down/inaccessible
            app.logger.error('Goodreads website is down/inaccessible')

    return render_title_template('author.html', entries=entries, pagination=pagination,
                                 title=name, author=author_info, other_books=other_books, page="author",
                                 config_authors_max=config.config_authors_max)


@app.route("/publisher")
@login_required_if_no_ano
def publisher_list():
    if current_user.show_publisher():
        entries = db.session.query(db.Publishers, func.count('books_publishers_link.book').label('count'))\
            .join(db.books_publishers_link).join(db.Books).filter(common_filters())\
            .group_by(text('books_publishers_link.publisher')).order_by(db.Publishers.sort).all()
        return render_title_template('list.html', entries=entries, folder='publisher',
                                     title=_(u"Publisher list"), page="publisherlist")
    else:
        abort(404)


@app.route("/publisher/<int:book_id>", defaults={'page': 1})
@app.route('/publisher/<int:book_id>/<int:page>')
@login_required_if_no_ano
def publisher(book_id, page):
    publisher = db.session.query(db.Publishers).filter(db.Publishers.id == book_id).first()
    if publisher:
        entries, random, pagination = fill_indexpage(page, db.Books,
                                            db.Books.publishers.any(db.Publishers.id == book_id),
                                            (db.Series.name, db.Books.series_index), db.books_series_link, db.Series)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Publisher: %(name)s", name=publisher.name), page="publisher")
    else:
        abort(404)


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
            .group_by(text('books_series_link.series')).order_by(db.Series.sort).all()
        return render_title_template('list.html', entries=entries, folder='series',
                                     title=_(u"Series list"), page="serieslist")
    else:
        abort(404)


@app.route("/series/<int:book_id>/", defaults={'page': 1})
@app.route("/series/<int:book_id>/<int:page>")
@login_required_if_no_ano
def series(book_id, page):
    name = db.session.query(db.Series).filter(db.Series.id == book_id).first()
    if name:
        entries, random, pagination = fill_indexpage(page, db.Books, db.Books.series.any(db.Series.id == book_id),
                                                 [db.Books.series_index])
        return render_title_template('index.html', random=random, pagination=pagination, entries=entries,
                                     title=_(u"Series: %(serie)s", serie=name.name), page="series")
    else:
        abort(404)


@app.route("/language")
@login_required_if_no_ano
def language_overview():
    if current_user.show_language():
        if current_user.filter_language() == u"all":
            languages = speaking_language()
        else:
            try:
                cur_l = LC.parse(current_user.filter_language())
            except UnknownLocaleError:
                cur_l = None
            languages = db.session.query(db.Languages).filter(
                db.Languages.lang_code == current_user.filter_language()).all()
            if cur_l:
                languages[0].name = cur_l.get_language_name(get_locale())
            else:
                languages[0].name = _(isoLanguages.get(part3=languages[0].lang_code).name)
        lang_counter = db.session.query(db.books_languages_link,
                                        func.count('books_languages_link.book').label('bookcount')).group_by(
            text('books_languages_link.lang_code')).all()
        return render_title_template('languages.html', languages=languages, lang_counter=lang_counter,
                                     title=_(u"Available languages"), page="langlist")
    else:
        abort(404)


@app.route("/language/<name>", defaults={'page': 1})
@app.route('/language/<name>/page/<int:page>')
@login_required_if_no_ano
def language(name, page):
    try:
        cur_l = LC.parse(name)
        lang_name = cur_l.get_language_name(get_locale())
    except UnknownLocaleError:
        try:
            lang_name = _(isoLanguages.get(part3=name).name)
        except KeyError:
            abort(404)
    entries, random, pagination = fill_indexpage(page, db.Books, db.Books.languages.any(db.Languages.lang_code == name),
                                                 [db.Books.timestamp.desc()])
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Language: %(name)s", name=lang_name), page="language")


@app.route("/category")
@login_required_if_no_ano
def category_list():
    if current_user.show_category():
        entries = db.session.query(db.Tags, func.count('books_tags_link.book').label('count'))\
            .join(db.books_tags_link).join(db.Books).order_by(db.Tags.name).filter(common_filters())\
            .group_by(text('books_tags_link.tag')).all()
        return render_title_template('list.html', entries=entries, folder='category',
                                     title=_(u"Category list"), page="catlist")
    else:
        abort(404)


@app.route("/category/<int:book_id>", defaults={'page': 1})
@app.route('/category/<int:book_id>/<int:page>')
@login_required_if_no_ano
def category(book_id, page):
    name = db.session.query(db.Tags).filter(db.Tags.id == book_id).first()
    if name:
        entries, random, pagination = fill_indexpage(page, db.Books, db.Books.tags.any(db.Tags.id == book_id),
                                        (db.Series.name, db.Books.series_index),db.books_series_link,db.Series)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Category: %(name)s", name=name.name), page="category")
    else:
        abort(404)


@app.route("/ajax/toggleread/<int:book_id>", methods=['POST'])
@login_required
def toggle_read(book_id):
    if not config.config_read_column:
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
    else:
        try:
            db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
            book = db.session.query(db.Books).filter(db.Books.id == book_id).filter(common_filters()).first()
            read_status = getattr(book, 'custom_column_' + str(config.config_read_column))
            if len(read_status):
                read_status[0].value = not read_status[0].value
                db.session.commit()
            else:
                cc_class = db.cc_classes[config.config_read_column]
                new_cc = cc_class(value=1, book=book_id)
                db.session.add(new_cc)
                db.session.commit()
        except KeyError:
            app.logger.error(
                    u"Custom Column No.%d is not exisiting in calibre database" % config.config_read_column)
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
            except UnknownLocaleError:
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
            if not config.config_read_column:
                matching_have_read_book = ub.session.query(ub.ReadBook)\
                    .filter(ub.and_(ub.ReadBook.user_id == int(current_user.id),
                    ub.ReadBook.book_id == book_id)).all()
                have_read = len(matching_have_read_book) > 0 and matching_have_read_book[0].is_read
            else:
                try:
                    matching_have_read_book = getattr(entries,'custom_column_'+str(config.config_read_column))
                    have_read = len(matching_have_read_book) > 0 and matching_have_read_book[0].value
                except KeyError:
                    app.logger.error(
                        u"Custom Column No.%d is not exisiting in calibre database" % config.config_read_column)
                    have_read = None

        else:
            have_read = None

        entries.tags = sort(entries.tags, key = lambda tag: tag.name)

        entries = order_authors(entries)

        kindle_list = helper.check_send_to_kindle(entries)
        reader_list = helper.check_read_formats(entries)

        return render_title_template('detail.html', entry=entries, cc=cc, is_xhr=request.is_xhr,
                                     title=entries.title, books_shelfs=book_in_shelfs,
                                     have_read=have_read, kindle_list=kindle_list, reader_list=reader_list, page="book")
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

    lbookmark = ub.Bookmark(user_id=current_user.id,
                           book_id=book_id,
                           format=book_format,
                           bookmark_key=bookmark_key)
    ub.session.merge(lbookmark)
    ub.session.commit()
    return "", 201


@app.route("/tasks")
@login_required
def get_tasks_status():
    # if current user admin, show all email, otherwise only own emails
    tasks=helper.global_WorkerThread.get_taskstatus()
    answer = helper.render_task_status(tasks)
    return render_title_template('tasks.html', entries=answer, title=_(u"Tasks"), page="tasks")


@app.route("/admin")
@login_required
def admin_forbidden():
    abort(403)


@app.route("/stats")
@login_required
def stats():
    counter = db.session.query(db.Books).count()
    authors = db.session.query(db.Authors).count()
    categorys = db.session.query(db.Tags).count()
    series = db.session.query(db.Series).count()
    versions = uploader.book_formats.get_versions()
    versions['Babel'] = 'v' + babelVersion
    versions['Sqlalchemy'] = 'v' + sqlalchemyVersion
    versions['Werkzeug'] = 'v' + werkzeugVersion
    versions['Jinja2'] = 'v' + jinja2Version
    versions['Flask'] = 'v' + flaskVersion
    versions['Flask Login'] = 'v' + flask_loginVersion
    versions['Flask Principal'] = 'v' + flask_principalVersion
    versions['Iso 639'] = 'v' + isoLanguages.__version__
    versions['pytz'] = 'v' + pytzVersion

    versions['Requests'] = 'v' + requests.__version__
    versions['pySqlite'] = 'v' + db.engine.dialect.dbapi.version
    versions['Sqlite'] = 'v' + db.engine.dialect.dbapi.sqlite_version
    versions.update(converter.versioncheck())
    versions.update(server.Server.getNameVersion())
    versions['Python'] = sys.version
    return render_title_template('stats.html', bookcounter=counter, authorcounter=authors, versions=versions,
                                 categorycounter=categorys, seriecounter=series, title=_(u"Statistics"), page="stat")


@app.route("/delete/<int:book_id>/", defaults={'book_format': ""})
@app.route("/delete/<int:book_id>/<string:book_format>/")
@login_required
def delete_book(book_id, book_format):
    if current_user.role_delete_books():
        book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
        if book:
            helper.delete_book(book, config.config_calibre_dir, book_format=book_format.upper())
            if not book_format:
                # delete book from Shelfs, Downloads, Read list
                ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book_id).delete()
                ub.session.query(ub.ReadBook).filter(ub.ReadBook.book_id == book_id).delete()
                ub.delete_download(book_id)
                ub.session.commit()

                # check if only this book links to:
                # author, language, series, tags, custom columns
                modify_database_object([u''], book.authors, db.Authors, db.session, 'author')
                modify_database_object([u''], book.tags, db.Tags, db.session, 'tags')
                modify_database_object([u''], book.series, db.Series, db.session, 'series')
                modify_database_object([u''], book.languages, db.Languages, db.session, 'languages')
                modify_database_object([u''], book.publishers, db.Publishers, db.session, 'publishers')

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
                        modify_database_object([u''], getattr(book, cc_string), db.cc_classes[c.id],
                                               db.session, 'custom')
                db.session.query(db.Books).filter(db.Books.id == book_id).delete()
            else:
                db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == book_format).delete()
            db.session.commit()
        else:
            # book not found
            app.logger.info('Book with id "'+str(book_id)+'" could not be deleted')
    if book_format:
        return redirect(url_for('edit_book', book_id=book_id))
    else:
        return redirect(url_for('index'))



@app.route("/gdrive/authenticate")
@login_required
@admin_required
def authenticate_google_drive():
    try:
        authUrl = gdriveutils.Gauth.Instance().auth.GetAuthUrl()
    except gdriveutils.InvalidConfigError:
        flash(_(u'Google Drive setup not completed, try to deactivate and activate Google Drive again'),
              category="error")
        return redirect(url_for('index'))
    return redirect(authUrl)


@app.route("/gdrive/callback")
def google_drive_callback():
    auth_code = request.args.get('code')
    if not auth_code:
        abort(403)
    try:
        credentials = gdriveutils.Gauth.Instance().auth.flow.step2_exchange(auth_code)
        with open(os.path.join(config.get_main_dir,'gdrive_credentials'), 'w') as f:
            f.write(credentials.to_json())
    except ValueError as error:
        app.logger.error(error)
    return redirect(url_for('configuration'))


@app.route("/gdrive/watch/subscribe")
@login_required
@admin_required
def watch_gdrive():
    if not config.config_google_drive_watch_changes_response:
        with open(os.path.join(config.get_main_dir,'client_secrets.json'), 'r') as settings:
            filedata = json.load(settings)
        if filedata['web']['redirect_uris'][0].endswith('/'):
            filedata['web']['redirect_uris'][0] = filedata['web']['redirect_uris'][0][:-((len('/gdrive/callback')+1))]
        else:
            filedata['web']['redirect_uris'][0] = filedata['web']['redirect_uris'][0][:-(len('/gdrive/callback'))]
        address = '%s/gdrive/watch/callback' % filedata['web']['redirect_uris'][0]
        notification_id = str(uuid4())
        try:
            result = gdriveutils.watchChange(gdriveutils.Gdrive.Instance().drive, notification_id,
                               'web_hook', address, gdrive_watch_callback_token, current_milli_time() + 604800*1000)
            settings = ub.session.query(ub.Settings).first()
            settings.config_google_drive_watch_changes_response = json.dumps(result)
            ub.session.merge(settings)
            ub.session.commit()
            settings = ub.session.query(ub.Settings).first()
            config.loadSettings()
        except HttpError as e:
            reason=json.loads(e.content)['error']['errors'][0]
            if reason['reason'] == u'push.webhookUrlUnauthorized':
                flash(_(u'Callback domain is not verified, please follow steps to verify domain in google developer console'), category="error")
            else:
                flash(reason['message'], category="error")

    return redirect(url_for('configuration'))


@app.route("/gdrive/watch/revoke")
@login_required
@admin_required
def revoke_watch_gdrive():
    last_watch_response = config.config_google_drive_watch_changes_response
    if last_watch_response:
        try:
            gdriveutils.stopChannel(gdriveutils.Gdrive.Instance().drive, last_watch_response['id'],
                                    last_watch_response['resourceId'])
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
    app.logger.debug(request.headers)
    if request.headers.get('X-Goog-Channel-Token') == gdrive_watch_callback_token \
            and request.headers.get('X-Goog-Resource-State') == 'change' \
            and request.data:

        data = request.data

        def updateMetaData():
            app.logger.info('Change received from gdrive')
            app.logger.debug(data)
            try:
                j = json.loads(data)
                app.logger.info('Getting change details')
                response = gdriveutils.getChangeById(gdriveutils.Gdrive.Instance().drive, j['id'])
                app.logger.debug(response)
                if response:
                    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
                    if not response['deleted'] and response['file']['title'] == 'metadata.db' and response['file']['md5Checksum'] != hashlib.md5(dbpath):
                        tmpDir = tempfile.gettempdir()
                        app.logger.info('Database file updated')
                        copyfile(dbpath, os.path.join(tmpDir, "metadata.db_" + str(current_milli_time())))
                        app.logger.info('Backing up existing and downloading updated metadata.db')
                        gdriveutils.downloadFile(None, "metadata.db", os.path.join(tmpDir, "tmp_metadata.db"))
                        app.logger.info('Setting up new DB')
                        # prevent error on windows, as os.rename does on exisiting files
                        move(os.path.join(tmpDir, "tmp_metadata.db"), dbpath)
                        db.setup_db()
            except Exception as e:
                app.logger.info(e.message)
                app.logger.exception(e)
        updateMetaData()
    return ''


@app.route("/shutdown")
@login_required
@admin_required
def shutdown():
    task = int(request.args.get("parameter").strip())
    if task == 1 or task == 0:  # valid commandos received
        # close all database connections
        db.session.close()
        db.engine.dispose()
        ub.session.close()
        ub.engine.dispose()

        showtext = {}
        if task == 0:
            showtext['text'] = _(u'Server restarted, please reload page')
            server.Server.setRestartTyp(True)
        else:
            showtext['text'] = _(u'Performing shutdown of server, please close window')
            server.Server.setRestartTyp(False)
        # stop gevent/tornado server
        server.Server.stopServer()
        return json.dumps(showtext)
    else:
        if task == 2:
            db.session.close()
            db.engine.dispose()
            db.setup_db()
            return json.dumps({})
        abort(404)


@app.route("/search", methods=["GET"])
@login_required_if_no_ano
def search():
    term = request.args.get("query").strip().lower()
    if term:
        entries = get_search_results(term)
        ids = list()
        for element in entries:
            ids.append(element.id)
        ub.searched_ids[current_user.id] = ids
        return render_title_template('search.html', searchterm=term, entries=entries, page="search")
    else:
        return render_title_template('search.html', searchterm="", page="search")


@app.route("/advanced_search", methods=['GET'])
@login_required_if_no_ano
def advanced_search():
    # Build custom columns names
    tmpcc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    if config.config_columns_to_ignore:
        cc = []
        for col in tmpcc:
            r = re.compile(config.config_columns_to_ignore)
            if r.match(col.label):
                cc.append(col)
    else:
        cc = tmpcc

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
    pub_start = request.args.get("Publishstart")
    pub_end = request.args.get("Publishend")
    rating_low = request.args.get("ratinghigh")
    rating_high = request.args.get("ratinglow")
    description = request.args.get("comment")
    if author_name: author_name = author_name.strip().lower().replace(',','|')
    if book_title: book_title = book_title.strip().lower()
    if publisher: publisher = publisher.strip().lower()

    searchterm = []
    cc_present = False
    for c in cc:
        if request.args.get('custom_column_' + str(c.id)):
            searchterm.extend([(u"%s: %s" % (c.name, request.args.get('custom_column_' + str(c.id))))])
            cc_present = True

    if include_tag_inputs or exclude_tag_inputs or include_series_inputs or exclude_series_inputs or \
            include_languages_inputs or exclude_languages_inputs or author_name or book_title or \
            publisher or pub_start or pub_end or rating_low or rating_high or description or cc_present:
        searchterm = []
        searchterm.extend((author_name.replace('|',','), book_title, publisher))
        if pub_start:
            try:
                searchterm.extend([_(u"Published after ") +
                               format_date(datetime.datetime.strptime(pub_start,"%Y-%m-%d"),
                                           format='medium', locale=get_locale())])
            except ValueError:
                pub_start = u""
        if pub_end:
            try:
                searchterm.extend([_(u"Published before ") +
                               format_date(datetime.datetime.strptime(pub_end,"%Y-%m-%d"),
                                           format='medium', locale=get_locale())])
            except ValueError:
                pub_start = u""
        tag_names = db.session.query(db.Tags).filter(db.Tags.id.in_(include_tag_inputs)).all()
        searchterm.extend(tag.name for tag in tag_names)
        serie_names = db.session.query(db.Series).filter(db.Series.id.in_(include_series_inputs)).all()
        searchterm.extend(serie.name for serie in serie_names)
        language_names = db.session.query(db.Languages).filter(db.Languages.id.in_(include_languages_inputs)).all()
        if language_names:
            language_names = speaking_language(language_names)
        searchterm.extend(language.name for language in language_names)
        if rating_high:
            searchterm.extend([_(u"Rating <= %(rating)s", rating=rating_high)])
        if rating_low:
            searchterm.extend([_(u"Rating >= %(rating)s", rating=rating_low)])
        # handle custom columns
        for c in cc:
            if request.args.get('custom_column_' + str(c.id)):
                searchterm.extend([(u"%s: %s" % (c.name, request.args.get('custom_column_' + str(c.id))))])
        searchterm = " + ".join(filter(None, searchterm))
        q = q.filter()
        if author_name:
            q = q.filter(db.Books.authors.any(db.func.lower(db.Authors.name).ilike("%" + author_name + "%")))
        if book_title:
            q = q.filter(db.func.lower(db.Books.title).ilike("%" + book_title + "%"))
        if pub_start:
            q = q.filter(db.Books.pubdate >= pub_start)
        if pub_end:
            q = q.filter(db.Books.pubdate <= pub_end)
        if publisher:
            q = q.filter(db.Books.publishers.any(db.func.lower(db.Publishers.name).ilike("%" + publisher + "%")))
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
        if rating_high:
            rating_high = int(rating_high) * 2
            q = q.filter(db.Books.ratings.any(db.Ratings.rating <= rating_high))
        if rating_low:
            rating_low = int(rating_low) *2
            q = q.filter(db.Books.ratings.any(db.Ratings.rating >= rating_low))
        if description:
            q = q.filter(db.Books.comments.any(db.func.lower(db.Comments.text).ilike("%" + description + "%")))

        # search custom culumns
        for c in cc:
            custom_query = request.args.get('custom_column_' + str(c.id))
            if custom_query:
                if c.datatype == 'bool':
                    q = q.filter(getattr(db.Books, 'custom_column_'+str(c.id)).any(
                        db.cc_classes[c.id].value == (custom_query== "True") ))
                elif c.datatype == 'int':
                    q = q.filter(getattr(db.Books, 'custom_column_'+str(c.id)).any(
                        db.cc_classes[c.id].value == custom_query ))
                else:
                    q = q.filter(getattr(db.Books, 'custom_column_'+str(c.id)).any(
                        db.func.lower(db.cc_classes[c.id].value).ilike("%" + custom_query + "%")))
        q = q.all()
        ids = list()
        for element in q:
            ids.append(element.id)
        ub.searched_ids[current_user.id] = ids
        return render_title_template('search.html', searchterm=searchterm,
                                     entries=q, title=_(u"search"), page="search")
    # prepare data for search-form
    tags = db.session.query(db.Tags).order_by(db.Tags.name).all()
    series = db.session.query(db.Series).order_by(db.Series.name).all()
    if current_user.filter_language() == u"all":
        languages = speaking_language()
    else:
        languages = None
    return render_title_template('search_form.html', tags=tags, languages=languages,
                                 series=series, title=_(u"search"), cc=cc, page="advsearch")


@app.route("/cover/<int:book_id>")
@login_required_if_no_ano
def get_cover(book_id):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    return helper.get_book_cover(book.path)


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
        df = gdriveutils.getFileFromEbooksFolder(book.path, data.name + "." + book_format)
        return gdriveutils.do_gdrive_download(df, headers)
    else:
        return send_from_directory(os.path.join(config.config_calibre_dir, book.path), data.name + "." + book_format)


@app.route("/opds/thumb_240_240/<book_id>")
@app.route("/opds/cover_240_240/<book_id>")
@app.route("/opds/cover_90_90/<book_id>")
@app.route("/opds/cover/<book_id>")
@requires_basic_auth_if_no_ano
def feed_get_cover(book_id):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    if book:
        return helper.get_book_cover(book.path)
    else:
        abort(404)


def render_read_books(page, are_read, as_xml=False):
    if not config.config_read_column:
        readBooks = ub.session.query(ub.ReadBook).filter(ub.ReadBook.user_id == int(current_user.id))\
            .filter(ub.ReadBook.is_read == True).all()
        readBookIds = [x.book_id for x in readBooks]
    else:
        try:
            readBooks = db.session.query(db.cc_classes[config.config_read_column])\
                .filter(db.cc_classes[config.config_read_column].value==True).all()
            readBookIds = [x.book for x in readBooks]
        except KeyError:
            app.logger.error(u"Custom Column No.%d is not existing in calibre database" % config.config_read_column)
            readBookIds = []

    if are_read:
        db_filter = db.Books.id.in_(readBookIds)
    else:
        db_filter = ~db.Books.id.in_(readBookIds)

    entries, random, pagination = fill_indexpage(page, db.Books,
            db_filter, [db.Books.timestamp.desc()])

    if as_xml:
        xml = render_title_template('feed.xml', entries=entries, pagination=pagination)
        response = make_response(xml)
        response.headers["Content-Type"] = "application/xml; charset=utf-8"
        return response
    else:
        if are_read:
            name = _(u'Read Books') + ' (' + str(len(readBookIds)) + ')'
        else:
            total_books = db.session.query(func.count(db.Books.id)).scalar()
            name = _(u'Unread Books') + ' (' + str(total_books - len(readBookIds)) + ')'
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                title=_(name, name=name), page="read")


@app.route("/opds/readbooks/")
@requires_basic_auth_if_no_ano
def feed_read_books():
    off = request.args.get("offset") or 0
    return render_read_books(int(off) / (int(config.config_books_per_page)) + 1, True, True)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), "favicon.ico")

@app.route("/readbooks/", defaults={'page': 1})
@app.route("/readbooks/<int:page>")
@login_required_if_no_ano
def read_books(page):
    return render_read_books(page, True)


@app.route("/opds/unreadbooks/")
@requires_basic_auth_if_no_ano
def feed_unread_books():
    off = request.args.get("offset") or 0
    return render_read_books(int(off) / (int(config.config_books_per_page)) + 1, False, True)


@app.route("/unreadbooks/", defaults={'page': 1})
@app.route("/unreadbooks/<int:page>")
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

    # check if book has bookmark
    lbookmark = None
    if current_user.is_authenticated:
        lbookmark = ub.session.query(ub.Bookmark).filter(ub.and_(ub.Bookmark.user_id == int(current_user.id),
                                                            ub.Bookmark.book_id == book_id,
                                                            ub.Bookmark.format == book_format.upper())).first()
    if book_format.lower() == "epub":
        return render_title_template('read.html', bookid=book_id, title=_(u"Read a Book"), bookmark=lbookmark)
    elif book_format.lower() == "pdf":
        return render_title_template('readpdf.html', pdffile=book_id, title=_(u"Read a Book"))
    elif book_format.lower() == "txt":
        return render_title_template('readtxt.html', txtfile=book_id, title=_(u"Read a Book"))
    else:
        book_dir = os.path.join(config.get_main_dir, "cps", "static", str(book_id))
        if not os.path.exists(book_dir):
            os.mkdir(book_dir)
        for fileext in ["cbr", "cbt", "cbz"]:
            if book_format.lower() == fileext:
                all_name = str(book_id) # + "/" + book.data[0].name + "." + fileext
                #tmp_file = os.path.join(book_dir, book.data[0].name) + "." + fileext
                #if not os.path.exists(all_name):
                #    cbr_file = os.path.join(config.config_calibre_dir, book.path, book.data[0].name) + "." + fileext
                #    copyfile(cbr_file, tmp_file)
                return render_title_template('readcbr.html', comicfile=all_name, title=_(u"Read a Book"),
                                             extension=fileext)
        '''if rar_support == True:
            extensionList = ["cbr","cbt","cbz"]
        else:
            extensionList = ["cbt","cbz"]
        for fileext in extensionList:
            if book_format.lower() == fileext:
                return render_title_template('readcbr.html', comicfile=book_id, 
                extension=fileext, title=_(u"Read a Book"), book=book)
        flash(_(u"Error opening eBook. File does not exist or file is not accessible."), category="error")
        return redirect(url_for("index"))'''
        flash(_(u"Error opening eBook. Fileformat is not supported."), category="error")
        return redirect(url_for("index"))



@app.route("/download/<int:book_id>/<book_format>")
@login_required_if_no_ano
@download_required
def get_download_link(book_id, book_format):
    book_format = book_format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id)\
        .filter(db.Data.format == book_format.upper()).first()
    if data:
        # collect downloaded books only for registered user and not for anonymous user
        if current_user.is_authenticated:
            ub.update_download(book_id, int(current_user.id))
        file_name = book.title
        if len(book.authors) > 0:
            file_name = book.authors[0].name + '_' + file_name
        file_name = helper.get_valid_filename(file_name)
        headers = Headers()
        try:
            headers["Content-Type"] = mimetypes.types_map['.' + book_format]
        except KeyError:
            headers["Content-Type"] = "application/octet-stream"
        headers["Content-Disposition"] = "attachment; filename*=UTF-8''%s.%s" % (quote(file_name.encode('utf-8')),
                                                                                 book_format)
        return helper.do_download_file(book, book_format, data, headers)
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
        if not to_save["nickname"] or not to_save["email"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template('register.html', title=_(u"register"), page="register")

        existing_user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == to_save["nickname"].lower()).first()
        existing_email = ub.session.query(ub.User).filter(ub.User.email == to_save["email"].lower()).first()
        if not existing_user and not existing_email:
            content = ub.User()
            # content.password = generate_password_hash(to_save["password"])
            if check_valid_domain(to_save["email"]):
                content.nickname = to_save["nickname"]
                content.email = to_save["email"]
                password = helper.generate_random_password()
                content.password = generate_password_hash(password)
                content.role = config.config_default_role
                content.sidebar_view = config.config_default_show
                content.mature_content = bool(config.config_default_show & ub.MATURE_CONTENT)
                try:
                    ub.session.add(content)
                    ub.session.commit()
                    helper.send_registration_mail(to_save["email"],to_save["nickname"], password)
                except Exception:
                    ub.session.rollback()
                    flash(_(u"An unknown error occurred. Please try again later."), category="error")
                    return render_title_template('register.html', title=_(u"register"), page="register")
            else:
                flash(_(u"Your e-mail is not allowed to register"), category="error")
                app.logger.info('Registering failed for user "' + to_save['nickname'] + '" e-mail adress: ' + to_save["email"])
                return render_title_template('register.html', title=_(u"register"), page="register")
            flash(_(u"Confirmation e-mail was send to your e-mail account."), category="success")
            return redirect(url_for('login'))
        else:
            flash(_(u"This username or e-mail address is already in use."), category="error")
            return render_title_template('register.html', title=_(u"register"), page="register")

    return render_title_template('register.html', title=_(u"register"), page="register")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not config.db_configured:
        return redirect(url_for('basic_configuration'))
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        form = request.form.to_dict()
        user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == form['username'].strip().lower()).first()
        if user and check_password_hash(user.password, form['password']) and user.nickname is not "Guest":
            login_user(user, remember=True)
            flash(_(u"you are now logged in as: '%(nickname)s'", nickname=user.nickname), category="success")
            return redirect_back(url_for("index"))
        else:
            ipAdress = request.headers.get('X-Forwarded-For', request.remote_addr)
            app.logger.info('Login failed for user "' + form['username'] + '" IP-adress: ' + ipAdress)
            flash(_(u"Wrong Username or Password"), category="error")

    # next_url = request.args.get('next')
    # if next_url is None or not is_safe_url(next_url):
    next_url = url_for('index')

    return render_title_template('login.html', title=_(u"login"), next_url=next_url,
                                 remote_login=config.config_remote_login, page="login")


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
                                 verify_url=verify_url, page="remotelogin")


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

    response = make_response(json.dumps(data, ensure_ascii=False))
    response.headers["Content-Type"] = "application/json; charset=utf-8"

    return response


@app.route('/send/<int:book_id>/<book_format>/<int:convert>')
@login_required
@download_required
def send_to_kindle(book_id, book_format, convert):
    settings = ub.get_mail_settings()
    if settings.get("mail_server", "mail.example.com") == "mail.example.com":
        flash(_(u"Please configure the SMTP mail settings first..."), category="error")
    elif current_user.kindle_mail:
        result = helper.send_mail(book_id, book_format, convert, current_user.kindle_mail, config.config_calibre_dir,
                                  current_user.nickname)
        if result is None:
            flash(_(u"Book successfully queued for sending to %(kindlemail)s", kindlemail=current_user.kindle_mail),
                  category="success")
            ub.update_download(book_id, int(current_user.id))
        else:
            flash(_(u"There was an error sending this book: %(res)s", res=result), category="error")
    else:
        flash(_(u"Please configure your kindle e-mail address first..."), category="error")
    return redirect(request.environ["HTTP_REFERER"])


@app.route("/shelf/add/<int:shelf_id>/<int:book_id>")
@login_required
def add_to_shelf(shelf_id, book_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if shelf is None:
        app.logger.info("Invalid shelf specified")
        if not request.is_xhr:
            flash(_(u"Invalid shelf specified"), category="error")
            return redirect(url_for('index'))
        return "Invalid shelf specified", 400

    if not shelf.is_public and not shelf.user_id == int(current_user.id):
        app.logger.info("Sorry you are not allowed to add a book to the the shelf: %s" % shelf.name)
        if not request.is_xhr:
            flash(_(u"Sorry you are not allowed to add a book to the the shelf: %(shelfname)s", shelfname=shelf.name),
                  category="error")
            return redirect(url_for('index'))
        return "Sorry you are not allowed to add a book to the the shelf: %s" % shelf.name, 403

    if shelf.is_public and not current_user.role_edit_shelfs():
        app.logger.info("User is not allowed to edit public shelves")
        if not request.is_xhr:
            flash(_(u"You are not allowed to edit public shelves"), category="error")
            return redirect(url_for('index'))
        return "User is not allowed to edit public shelves", 403

    book_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id,
                                          ub.BookShelf.book_id == book_id).first()
    if book_in_shelf:
        app.logger.info("Book is already part of the shelf: %s" % shelf.name)
        if not request.is_xhr:
            flash(_(u"Book is already part of the shelf: %(shelfname)s", shelfname=shelf.name), category="error")
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
        if "HTTP_REFERER" in request.environ:
            return redirect(request.environ["HTTP_REFERER"])
        else:
            return redirect(url_for('index'))
    return "", 204


@app.route("/shelf/massadd/<int:shelf_id>")
@login_required
def search_to_shelf(shelf_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if shelf is None:
        app.logger.info("Invalid shelf specified")
        flash(_(u"Invalid shelf specified"), category="error")
        return redirect(url_for('index'))

    if not shelf.is_public and not shelf.user_id == int(current_user.id):
        app.logger.info("You are not allowed to add a book to the the shelf: %s" % shelf.name)
        flash(_(u"You are not allowed to add a book to the the shelf: %(name)s", name=shelf.name), category="error")
        return redirect(url_for('index'))

    if shelf.is_public and not current_user.role_edit_shelfs():
        app.logger.info("User is not allowed to edit public shelves")
        flash(_(u"User is not allowed to edit public shelves"), category="error")
        return redirect(url_for('index'))

    if current_user.id in ub.searched_ids and ub.searched_ids[current_user.id]:
        books_for_shelf = list()
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).all()
        if books_in_shelf:
            book_ids = list()
            for book_id in books_in_shelf:
                book_ids.append(book_id.book_id)
            for id in ub.searched_ids[current_user.id]:
                if id not in book_ids:
                    books_for_shelf.append(id)
        else:
            books_for_shelf = ub.searched_ids[current_user.id]

        if not books_for_shelf:
            app.logger.info("Books are already part of the shelf: %s" % shelf.name)
            flash(_(u"Books are already part of the shelf: %(name)s", name=shelf.name), category="error")
            return redirect(url_for('index'))

        maxOrder = ub.session.query(func.max(ub.BookShelf.order)).filter(ub.BookShelf.shelf == shelf_id).first()
        if maxOrder[0] is None:
            maxOrder = 0
        else:
            maxOrder = maxOrder[0]

        for book in books_for_shelf:
            maxOrder = maxOrder + 1
            ins = ub.BookShelf(shelf=shelf.id, book_id=book, order=maxOrder)
            ub.session.add(ins)
        ub.session.commit()
        flash(_(u"Books have been added to shelf: %(sname)s", sname=shelf.name), category="success")
    else:
        flash(_(u"Could not add books to shelf: %(sname)s", sname=shelf.name), category="error")
    return redirect(url_for('index'))


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
            flash(_(u"Sorry you are not allowed to remove a book from this shelf: %(sname)s", sname=shelf.name),
                  category="error")
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
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"create a shelf"), page="shelfcreate")
    else:
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"create a shelf"), page="shelfcreate")


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
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"Edit a shelf"), page="shelfedit")
    else:
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"Edit a shelf"), page="shelfedit")


@app.route("/shelf/delete/<int:shelf_id>")
@login_required
def delete_shelf(shelf_id):
    cur_shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    deleted = None
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
            if cur_book:
                result.append(cur_book)
            else:
                app.logger.info('Not existing book %s in shelf %s deleted' % (book.book_id, shelf.id))
                ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book.book_id).delete()
                ub.session.commit()
        return render_title_template('shelf.html', entries=result, title=_(u"Shelf: '%(name)s'", name=shelf.name),
                                 shelf=shelf, page="shelf")
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
                                 title=_(u"Change order of Shelf: '%(name)s'", name=shelf.name),
                                 shelf=shelf, page="shelforder")


@app.route("/me", methods=["GET", "POST"])
@login_required
def profile():
    content = ub.session.query(ub.User).filter(ub.User.id == int(current_user.id)).first()
    downloads = list()
    languages = speaking_language()
    translations = babel.list_translations() + [LC('en')]
    for book in content.downloads:
        downloadBook = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
        if downloadBook:
            downloads.append(db.session.query(db.Books).filter(db.Books.id == book.book_id).first())
        else:
            ub.delete_download(book.book_id)
            # ub.session.query(ub.Downloads).filter(book.book_id == ub.Downloads.book_id).delete()
            # ub.session.commit()
    if request.method == "POST":
        to_save = request.form.to_dict()
        content.random_books = 0
        if current_user.role_passwd() or current_user.role_admin():
            if "password" in to_save and to_save["password"]:
                content.password = generate_password_hash(to_save["password"])
        if "kindle_mail" in to_save and to_save["kindle_mail"] != content.kindle_mail:
            content.kindle_mail = to_save["kindle_mail"]
        if to_save["email"] and to_save["email"] != content.email:
            if config.config_public_reg and not check_valid_domain(to_save["email"]):
                flash(_(u"E-mail is not from valid domain"), category="error")
                return render_title_template("user_edit.html", content=content, downloads=downloads,
                                     title=_(u"%(name)s's profile", name=current_user.nickname))
            content.email = to_save["email"]
        if "show_random" in to_save and to_save["show_random"] == "on":
            content.random_books = 1
        if "default_language" in to_save:
            content.default_language = to_save["default_language"]
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
        if "show_publisher" in to_save:
            content.sidebar_view += ub.SIDEBAR_PUBLISHER
        if "show_read_and_unread" in to_save:
            content.sidebar_view += ub.SIDEBAR_READ_AND_UNREAD
        if "show_detail_random" in to_save:
            content.sidebar_view += ub.DETAIL_RANDOM

        content.mature_content = "show_mature_content" in to_save

        try:
            ub.session.commit()
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"Found an existing account for this e-mail address."), category="error")
            return render_title_template("user_edit.html", content=content, downloads=downloads,
                                         title=_(u"%(name)s's profile", name=current_user.nickname))
        flash(_(u"Profile updated"), category="success")
    return render_title_template("user_edit.html", translations=translations, profile=1, languages=languages,
                                content=content, downloads=downloads, title=_(u"%(name)s's profile",
                                name=current_user.nickname), page="me")


@app.route("/admin/view")
@login_required
@admin_required
def admin():
    version = updater_thread.get_current_version_info()
    if version is False:
        commit = _(u'Unknown')
    else:
        if 'datetime' in version:
            commit = version['datetime']

            tz = datetime.timedelta(seconds=time.timezone if (time.localtime().tm_isdst == 0) else time.altzone)
            form_date = datetime.datetime.strptime(commit[:19], "%Y-%m-%dT%H:%M:%S")
            if len(commit) > 19:    # check if string has timezone
                if commit[19] == '+':
                    form_date -= datetime.timedelta(hours=int(commit[20:22]), minutes=int(commit[23:]))
                elif commit[19] == '-':
                    form_date += datetime.timedelta(hours=int(commit[20:22]), minutes=int(commit[23:]))
            commit = format_datetime(form_date - tz, format='short', locale=get_locale())
        else:
            commit = version['version']

    content = ub.session.query(ub.User).all()
    settings = ub.session.query(ub.Settings).first()
    return render_title_template("admin.html", content=content, email=settings, config=config, commit=commit,
                                 title=_(u"Admin page"), page="admin")


@app.route("/admin/config", methods=["GET", "POST"])
@login_required
@admin_required
def configuration():
    return configuration_helper(0)


@app.route("/admin/viewconfig", methods=["GET", "POST"])
@login_required
@admin_required
def view_configuration():
    reboot_required = False
    if request.method == "POST":
        to_save = request.form.to_dict()
        content = ub.session.query(ub.Settings).first()
        if "config_calibre_web_title" in to_save:
            content.config_calibre_web_title = to_save["config_calibre_web_title"]
        if "config_columns_to_ignore" in to_save:
            content.config_columns_to_ignore = to_save["config_columns_to_ignore"]
        if "config_read_column" in to_save:
            content.config_read_column = int(to_save["config_read_column"])
        if "config_theme" in to_save:
            content.config_theme = int(to_save["config_theme"])
        if "config_title_regex" in to_save:
            if content.config_title_regex != to_save["config_title_regex"]:
                content.config_title_regex = to_save["config_title_regex"]
                reboot_required = True
        if "config_random_books" in to_save:
            content.config_random_books = int(to_save["config_random_books"])
        if "config_books_per_page" in to_save:
            content.config_books_per_page = int(to_save["config_books_per_page"])
        # maximum authors to show before we display a 'show more' link
        if "config_authors_max" in to_save:
            content.config_authors_max = int(to_save["config_authors_max"])
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
        if "edit_shelf_role" in to_save:
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
        if "show_publisher" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_PUBLISHER
        if "show_best_rated" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_BEST_RATED
        if "show_read_and_unread" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_READ_AND_UNREAD
        if "show_recent" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_RECENT
        if "show_sorted" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_SORTED
        if "show_mature_content" in to_save:
            content.config_default_show = content.config_default_show + ub.MATURE_CONTENT
        ub.session.commit()
        flash(_(u"Calibre-Web configuration updated"), category="success")
        config.loadSettings()
        before_request()
        if reboot_required:
            # db.engine.dispose() # ToDo verify correct
            # ub.session.close()
            # ub.engine.dispose()
            # stop Server
            server.Server.setRestartTyp(True)
            server.Server.stopServer()
            app.logger.info('Reboot required, restarting')
    readColumn = db.session.query(db.Custom_Columns)\
            .filter(db.and_(db.Custom_Columns.datatype == 'bool',db.Custom_Columns.mark_for_delete == 0)).all()
    return render_title_template("config_view_edit.html", content=config, readColumns=readColumn,
                                 title=_(u"UI Configuration"), page="uiconfig")



@app.route("/config", methods=["GET", "POST"])
@unconfigured
def basic_configuration():
    logout_user()
    return configuration_helper(1)


def configuration_helper(origin):
    reboot_required = False
    gdriveError=None
    db_change = False
    success = False
    filedata = None
    if gdriveutils.gdrive_support == False:
        gdriveError = _('Import of optional Google Drive requirements missing')
    else:
        if not os.path.isfile(os.path.join(config.get_main_dir,'client_secrets.json')):
            gdriveError = _('client_secrets.json is missing or not readable')
        else:
            with open(os.path.join(config.get_main_dir,'client_secrets.json'), 'r') as settings:
                filedata=json.load(settings)
            if not 'web' in filedata:
                gdriveError = _('client_secrets.json is not configured for web application')
    if request.method == "POST":
        to_save = request.form.to_dict()
        content = ub.session.query(ub.Settings).first()  # type: ub.Settings
        if "config_calibre_dir" in to_save:
            if content.config_calibre_dir != to_save["config_calibre_dir"]:
                content.config_calibre_dir = to_save["config_calibre_dir"]
                db_change = True
        # Google drive setup
        if not os.path.isfile(os.path.join(config.get_main_dir, 'settings.yaml')):
            content.config_use_google_drive = False
        if "config_use_google_drive" in to_save and not content.config_use_google_drive and not gdriveError:
            if filedata:
                if filedata['web']['redirect_uris'][0].endswith('/'):
                    filedata['web']['redirect_uris'][0] = filedata['web']['redirect_uris'][0][:-1]
                with open(os.path.join(config.get_main_dir,'settings.yaml'), 'w') as f:
                    yaml = "client_config_backend: settings\nclient_config_file: %(client_file)s\n" \
                           "client_config:\n" \
                           "  client_id: %(client_id)s\n  client_secret: %(client_secret)s\n" \
                           "  redirect_uri: %(redirect_uri)s\n\nsave_credentials: True\n" \
                           "save_credentials_backend: file\nsave_credentials_file: %(credential)s\n\n" \
                           "get_refresh_token: True\n\noauth_scope:\n" \
                           "  - https://www.googleapis.com/auth/drive\n"
                    f.write(yaml % {'client_file': os.path.join(config.get_main_dir,'client_secrets.json'),
                                    'client_id': filedata['web']['client_id'],
                                   'client_secret': filedata['web']['client_secret'],
                                   'redirect_uri': filedata['web']['redirect_uris'][0],
                                    'credential': os.path.join(config.get_main_dir,'gdrive_credentials')})
            else:
                flash(_(u'client_secrets.json is not configured for web application'), category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                             goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                             page="config")
        # always show google drive settings, but in case of error deny support
        if "config_use_google_drive" in to_save and not gdriveError:
            content.config_use_google_drive = "config_use_google_drive" in to_save
        else:
            content.config_use_google_drive = 0
        if "config_google_drive_folder" in to_save:
            if content.config_google_drive_folder != to_save["config_google_drive_folder"]:
                content.config_google_drive_folder = to_save["config_google_drive_folder"]
                gdriveutils.deleteDatabaseOnChange()

        if "config_port" in to_save:
            if content.config_port != int(to_save["config_port"]):
                content.config_port = int(to_save["config_port"])
                reboot_required = True
        if "config_keyfile" in to_save:
            if content.config_keyfile != to_save["config_keyfile"]:
                if os.path.isfile(to_save["config_keyfile"]) or to_save["config_keyfile"] is u"":
                    content.config_keyfile = to_save["config_keyfile"]
                    reboot_required = True
                else:
                    ub.session.commit()
                    flash(_(u'Keyfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", content=config, origin=origin,
                                                 gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                                 goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                                 page="config")
        if "config_certfile" in to_save:
            if content.config_certfile != to_save["config_certfile"]:
                if os.path.isfile(to_save["config_certfile"]) or to_save["config_certfile"] is u"":
                    content.config_certfile = to_save["config_certfile"]
                    reboot_required = True
                else:
                    ub.session.commit()
                    flash(_(u'Certfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", content=config, origin=origin,
                                                 gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                                 goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                                 page="config")
        content.config_uploading = 0
        content.config_anonbrowse = 0
        content.config_public_reg = 0
        if "config_uploading" in to_save and to_save["config_uploading"] == "on":
            content.config_uploading = 1
        if "config_anonbrowse" in to_save and to_save["config_anonbrowse"] == "on":
            content.config_anonbrowse = 1
        if "config_public_reg" in to_save and to_save["config_public_reg"] == "on":
            content.config_public_reg = 1

        if "config_converterpath" in to_save:
            content.config_converterpath = to_save["config_converterpath"].strip()
        if "config_calibre" in to_save:
            content.config_calibre = to_save["config_calibre"].strip()
        if "config_ebookconverter" in to_save:
            content.config_ebookconverter = int(to_save["config_ebookconverter"])

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
        if "config_updater" in to_save:
            content.config_updatechannel = int(to_save["config_updater"])
        if "config_log_level" in to_save:
            content.config_log_level = int(to_save["config_log_level"])
        if content.config_logfile != to_save["config_logfile"]:
            # check valid path, only path or file
            if os.path.dirname(to_save["config_logfile"]):
                if os.path.exists(os.path.dirname(to_save["config_logfile"])) and \
                        os.path.basename(to_save["config_logfile"]) and not os.path.isdir(to_save["config_logfile"]):
                    content.config_logfile = to_save["config_logfile"]
                else:
                    ub.session.commit()
                    flash(_(u'Logfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", content=config, origin=origin,
                                                 gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                                 goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                                 page="config")
            else:
                content.config_logfile = to_save["config_logfile"]
            reboot_required = True

        # Rarfile Content configuration
        if "config_rarfile_location" in to_save and to_save['config_rarfile_location'] is not u"":
            check = helper.check_unrar(to_save["config_rarfile_location"].strip())
            if not check[0] :
                content.config_rarfile_location = to_save["config_rarfile_location"].strip()
            else:
                flash(check[1], category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdriveutils.gdrive_support, goodreads=goodreads_support,
                                             rarfile_support=rar_support, title=_(u"Basic Configuration"))
        try:
            if content.config_use_google_drive and is_gdrive_ready() and not \
                    os.path.exists(os.path.join(content.config_calibre_dir, "metadata.db")):
                gdriveutils.downloadFile(None, "metadata.db", config.config_calibre_dir + "/metadata.db")
            if db_change:
                if config.db_configured:
                    db.session.close()
                    db.engine.dispose()
            ub.session.commit()
            flash(_(u"Calibre-Web configuration updated"), category="success")
            config.loadSettings()
            app.logger.setLevel(config.config_log_level)
            logging.getLogger("book_formats").setLevel(config.config_log_level)
        except Exception as e:
            flash(e, category="error")
            return render_title_template("config_edit.html", content=config, origin=origin,
                                         gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                         goodreads=goodreads_support, rarfile_support=rar_support,
                                         title=_(u"Basic Configuration"), page="config")
        if db_change:
            reload(db)
            if not db.setup_db():
                flash(_(u'DB location is not valid, please enter correct path'), category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdriveutils.gdrive_support,gdriveError=gdriveError,
                                             goodreads=goodreads_support, rarfile_support=rar_support,
                                             title=_(u"Basic Configuration"), page="config")
        if reboot_required:
            # stop Server
            server.Server.setRestartTyp(True)
            server.Server.stopServer()
            app.logger.info('Reboot required, restarting')
        if origin:
            success = True
    if is_gdrive_ready() and gdriveutils.gdrive_support == True: # and config.config_use_google_drive == True:
        gdrivefolders=gdriveutils.listRootFolders()
    else:
        gdrivefolders=list()
    return render_title_template("config_edit.html", origin=origin, success=success, content=config,
                                 show_authenticate_google_drive=not is_gdrive_ready(),
                                 gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                 gdrivefolders=gdrivefolders, rarfile_support=rar_support,
                                 goodreads=goodreads_support, title=_(u"Basic Configuration"), page="config")


@app.route("/admin/user/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_user():
    content = ub.User()
    languages = speaking_language()
    translations = [LC('en')] + babel.list_translations()
    if request.method == "POST":
        to_save = request.form.to_dict()
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
        if "show_publisher" in to_save:
            content.sidebar_view += ub.SIDEBAR_PUBLISHER
        if "show_detail_random" in to_save:
            content.sidebar_view += ub.DETAIL_RANDOM
        if "show_sorted" in to_save:
            content.sidebar_view += ub.SIDEBAR_SORTED
        if "show_recent" in to_save:
            content.sidebar_view += ub.SIDEBAR_RECENT

        content.role = 0
        if "admin_role" in to_save:
            content.role = content.role + ub.ROLE_ADMIN
        if "download_role" in to_save:
            content.role = content.role + ub.ROLE_DOWNLOAD
        if "upload_role" in to_save:
            content.role = content.role + ub.ROLE_UPLOAD
        if "edit_role" in to_save:
            content.role = content.role + ub.ROLE_EDIT
        if "delete_role" in to_save:
            content.role = content.role + ub.ROLE_DELETE_BOOKS
        if "passwd_role" in to_save:
            content.role = content.role + ub.ROLE_PASSWD
        if "edit_shelf_role" in to_save:
            content.role = content.role + ub.ROLE_EDIT_SHELFS
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         title=_(u"Add new user"))
        content.password = generate_password_hash(to_save["password"])
        content.nickname = to_save["nickname"]
        if config.config_public_reg and not check_valid_domain(to_save["email"]):
            flash(_(u"E-mail is not from valid domain"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         title=_(u"Add new user"))
        else:
            content.email = to_save["email"]
        try:
            ub.session.add(content)
            ub.session.commit()
            flash(_(u"User '%(user)s' created", user=content.nickname), category="success")
            return redirect(url_for('admin'))
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"Found an existing account for this e-mail address or nickname."), category="error")
    else:
        content.role = config.config_default_role
        content.sidebar_view = config.config_default_show
        content.mature_content = bool(config.config_default_show & ub.MATURE_CONTENT)
    return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                 languages=languages, title=_(u"Add new user"), page="newuser")


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
        except Exception as e:
            flash(e, category="error")
        if "test" in to_save and to_save["test"]:
            if current_user.kindle_mail:
                result = helper.send_test_mail(current_user.kindle_mail, current_user.nickname)
                if result is None:
                    flash(_(u"Test e-mail successfully send to %(kindlemail)s", kindlemail=current_user.kindle_mail),
                          category="success")
                else:
                    flash(_(u"There was an error sending the Test e-mail: %(res)s", res=result), category="error")
            else:
                flash(_(u"Please configure your kindle e-mail address first..."), category="error")
        else:
            flash(_(u"E-mail server settings updated"), category="success")
    return render_title_template("email_edit.html", content=content, title=_(u"Edit e-mail server settings"),
                                 page="mailset")


@app.route("/admin/user/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    content = ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()  # type: ub.User
    downloads = list()
    languages = speaking_language()
    translations = babel.list_translations() + [LC('en')]
    for book in content.downloads:
        downloadbook = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
        if downloadbook:
            downloads.append(downloadbook)
        else:
            ub.delete_download(book.book_id)
            # ub.session.query(ub.Downloads).filter(book.book_id == ub.Downloads.book_id).delete()
            # ub.session.commit()
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

            if "show_publisher" in to_save and not content.show_publisher():
                content.sidebar_view += ub.SIDEBAR_PUBLISHER
            elif "show_publisher" not in to_save and content.show_publisher():
                content.sidebar_view -= ub.SIDEBAR_PUBLISHER

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
                                content=content, downloads=downloads, title=_(u"Edit User %(nick)s",
                                nick=content.nickname), page="edituser")


@app.route("/admin/resetpassword/<int:user_id>")
@login_required
@admin_required
def reset_password(user_id):
    if not config.config_public_reg:
        abort(404)
    if current_user is not None and current_user.is_authenticated:
        existing_user = ub.session.query(ub.User).filter(ub.User.id == user_id).first()
        password = helper.generate_random_password()
        existing_user.password = generate_password_hash(password)
        try:
            ub.session.commit()
            helper.send_registration_mail(existing_user.email, existing_user.nickname, password, True)
            flash(_(u"Password for user %(user)s reset", user=existing_user.nickname), category="success")
        except Exception:
            ub.session.rollback()
            flash(_(u"An unknown error occurred. Please try again later."), category="error")
    return redirect(url_for('admin'))


def render_edit_book(book_id):
    db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    book = db.session.query(db.Books)\
        .filter(db.Books.id == book_id).filter(common_filters()).first()

    if not book:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible"), category="error")
        return redirect(url_for("index"))

    for indx in range(0, len(book.languages)):
        book.languages[indx].language_name = language_table[get_locale()][book.languages[indx].lang_code]

    book = order_authors(book)

    author_names = []
    for authr in book.authors:
        author_names.append(authr.name.replace('|', ','))

    # Option for showing convertbook button
    valid_source_formats=list()
    if config.config_ebookconverter == 2:
        for file in book.data:
            if file.format.lower() in EXTENSIONS_CONVERT:
                valid_source_formats.append(file.format.lower())

    # Determine what formats don't already exist
    allowed_conversion_formats = EXTENSIONS_CONVERT.copy()
    for file in book.data:
        try:
            allowed_conversion_formats.remove(file.format.lower())
        except Exception:
            app.logger.warning(file.format.lower() + ' already removed from list.')

    return render_title_template('book_edit.html', book=book, authors=author_names, cc=cc,
                                 title=_(u"edit metadata"), page="editbook",
                                 conversion_formats=allowed_conversion_formats,
                                 source_formats=valid_source_formats)


def edit_cc_data(book_id, book, to_save):
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
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
                            db.session.flush()
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
            modify_database_object(input_tags, getattr(book, cc_string), db.cc_classes[c.id], db.session,
                                   'custom')
    return cc

def upload_single_file(request, book, book_id):
    # Check and handle Uploaded file
    if 'btn-upload-format' in request.files:
        requested_file = request.files['btn-upload-format']
        # check for empty request
        if requested_file.filename != '':
            if '.' in requested_file.filename:
                file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
                if file_ext not in EXTENSIONS_UPLOAD:
                    flash(_("File extension '%(ext)s' is not allowed to be uploaded to this server", ext=file_ext),
                          category="error")
                    return redirect(url_for('show_book', book_id=book.id))
            else:
                flash(_('File to be uploaded must have an extension'), category="error")
                return redirect(url_for('show_book', book_id=book.id))

            file_name = book.path.rsplit('/', 1)[-1]
            filepath = os.path.normpath(os.path.join(config.config_calibre_dir, book.path))
            saved_filename = os.path.join(filepath, file_name + '.' + file_ext)

            # check if file path exists, otherwise create it, copy file to calibre path and delete temp file
            if not os.path.exists(filepath):
                try:
                    os.makedirs(filepath)
                except OSError:
                    flash(_(u"Failed to create path %(path)s (Permission denied).", path=filepath), category="error")
                    return redirect(url_for('show_book', book_id=book.id))
            try:
                requested_file.save(saved_filename)
            except OSError:
                flash(_(u"Failed to store file %(file)s.", file=saved_filename), category="error")
                return redirect(url_for('show_book', book_id=book.id))

            file_size = os.path.getsize(saved_filename)
            is_format = db.session.query(db.Data).filter(db.Data.book == book_id).\
                filter(db.Data.format == file_ext.upper()).first()

            # Format entry already exists, no need to update the database
            if is_format:
                app.logger.info('Book format already existing')
            else:
                db_format = db.Data(book_id, file_ext.upper(), file_size, file_name)
                db.session.add(db_format)
                db.session.commit()
                db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)

            # Queue uploader info
            uploadText=_(u"File format %(ext)s added to %(book)s", ext=file_ext.upper(), book=book.title)
            helper.global_WorkerThread.add_upload(current_user.nickname,
                "<a href=\"" + url_for('show_book', book_id=book.id) + "\">" + uploadText + "</a>")


def upload_cover(request, book):
    if 'btn-upload-cover' in request.files:
        requested_file = request.files['btn-upload-cover']
        # check for empty request
        if requested_file.filename != '':
            if helper.save_cover(requested_file, book.path) is True:
                return True
            else:
                # ToDo Message not always coorect
                flash(_(u"Cover is not a supported imageformat (jpg/png/webp), can't save"), category="error")
                return False
    return None

@app.route("/admin/book/<int:book_id>", methods=['GET', 'POST'])
@login_required_if_no_ano
@edit_required
def edit_book(book_id):
    # Show form
    if request.method != 'POST':
        return render_edit_book(book_id)

    # create the function for sorting...
    db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
    book = db.session.query(db.Books)\
        .filter(db.Books.id == book_id).filter(common_filters()).first()

    # Book not found
    if not book:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible"), category="error")
        return redirect(url_for("index"))

    upload_single_file(request, book, book_id)
    if upload_cover(request, book) is True:
        book.has_cover = 1
    try:
        to_save = request.form.to_dict()
        # Update book
        edited_books_id = None
        #handle book title
        if book.title != to_save["book_title"].rstrip().strip():
            if to_save["book_title"] == '':
                to_save["book_title"] = _(u'unknown')
            book.title = to_save["book_title"].rstrip().strip()
            edited_books_id = book.id

        # handle author(s)
        input_authors = to_save["author_name"].split('&')
        input_authors = list(map(lambda it: it.strip().replace(',', '|'), input_authors))
        # we have all author names now
        if input_authors == ['']:
            input_authors = [_(u'unknown')]  # prevent empty Author

        modify_database_object(input_authors, book.authors, db.Authors, db.session, 'author')

        # Search for each author if author is in database, if not, authorname and sorted authorname is generated new
        # everything then is assembled for sorted author field in database
        sort_authors_list = list()
        for inp in input_authors:
            stored_author = db.session.query(db.Authors).filter(db.Authors.name == inp).first()
            if not stored_author:
                stored_author = helper.get_sorted_author(inp)
            else:
                stored_author = stored_author.sort
            sort_authors_list.append(helper.get_sorted_author(stored_author))
        sort_authors = ' & '.join(sort_authors_list)
        if book.author_sort != sort_authors:
            edited_books_id = book.id
            book.author_sort = sort_authors


        if config.config_use_google_drive:
            gdriveutils.updateGdriveCalibreFromLocal()

        error = False
        if edited_books_id:
            error = helper.update_dir_stucture(edited_books_id, config.config_calibre_dir, input_authors[0])

        if not error:
            if to_save["cover_url"]:
                if helper.save_cover_from_url(to_save["cover_url"], book.path) is True:
                    book.has_cover = 1
                else:
                    flash(_(u"Cover is not a supported imageformat (jpg/png/webp), can't save"), category="error")

            if book.series_index != to_save["series_index"]:
                book.series_index = to_save["series_index"]

            # Handle book comments/description
            if len(book.comments):
                book.comments[0].text = to_save["description"]
            else:
                book.comments.append(db.Comments(text=to_save["description"], book=book.id))

            # Handle book tags
            input_tags = to_save["tags"].split(',')
            input_tags = list(map(lambda it: it.strip(), input_tags))
            modify_database_object(input_tags, book.tags, db.Tags, db.session, 'tags')

            # Handle book series
            input_series = [to_save["series"].strip()]
            input_series = [x for x in input_series if x != '']
            modify_database_object(input_series, book.series, db.Series, db.session, 'series')

            if to_save["pubdate"]:
                try:
                    book.pubdate = datetime.datetime.strptime(to_save["pubdate"], "%Y-%m-%d")
                except ValueError:
                    book.pubdate = db.Books.DEFAULT_PUBDATE
            else:
                book.pubdate = db.Books.DEFAULT_PUBDATE

            if to_save["publisher"]:
                publisher = to_save["publisher"].rstrip().strip()
                if len(book.publishers) == 0 or (len(book.publishers) > 0 and publisher != book.publishers[0].name):
                    modify_database_object([publisher], book.publishers, db.Publishers, db.session, 'publisher')
            elif len(book.publishers):
                modify_database_object([], book.publishers, db.Publishers, db.session, 'publisher')


            # handle book languages
            input_languages = to_save["languages"].split(',')
            input_languages = [x.strip().lower() for x in input_languages if x != '']
            input_l = []
            invers_lang_table = [x.lower() for x in language_table[get_locale()].values()]
            for lang in input_languages:
                try:
                    res = list(language_table[get_locale()].keys())[invers_lang_table.index(lang)]
                    input_l.append(res)
                except ValueError:
                    app.logger.error('%s is not a valid language' % lang)
                    flash(_(u"%(langname)s is not a valid language", langname=lang), category="error")
            modify_database_object(input_l, book.languages, db.Languages, db.session, 'languages')

            # handle book ratings
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

            # handle cc data
            edit_cc_data(book_id, book, to_save)

            db.session.commit()
            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()
            if "detail_view" in to_save:
                return redirect(url_for('show_book', book_id=book.id))
            else:
                flash(_("Metadata successfully updated"), category="success")
                return render_edit_book(book_id)
        else:
            db.session.rollback()
            flash(error, category="error")
            return render_edit_book(book_id)
    except Exception as e:
        app.logger.exception(e)
        db.session.rollback()
        flash(_("Error editing book, please check logfile for details"), category="error")
        return redirect(url_for('show_book', book_id=book.id))


@app.route("/upload", methods=["GET", "POST"])
@login_required_if_no_ano
@upload_required
def upload():
    if not config.config_uploading:
        abort(404)
    if request.method == 'POST' and 'btn-upload' in request.files:
        for requested_file in request.files.getlist("btn-upload"):
            # create the function for sorting...
            db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
            db.session.connection().connection.connection.create_function('uuid4', 0, lambda: str(uuid4()))

            # check if file extension is correct
            if '.' in requested_file.filename:
                file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
                if file_ext not in EXTENSIONS_UPLOAD:
                    return Response(_("File extension '%(ext)s' is not allowed to be uploaded to this server",
                          ext=file_ext)), 422
            else:
                return Response(_('File to be uploaded must have an extension')), 422

            # extract metadata from file
            meta = uploader.upload(requested_file)
            title = meta.title
            authr = meta.author
            tags = meta.tags
            series = meta.series
            series_index = meta.series_id
            title_dir = helper.get_valid_filename(title)
            author_dir = helper.get_valid_filename(authr)
            filepath = os.path.join(config.config_calibre_dir, author_dir, title_dir)
            saved_filename = os.path.join(filepath, title_dir + meta.extension.lower())

            # check if file path exists, otherwise create it, copy file to calibre path and delete temp file
            if not os.path.exists(filepath):
                try:
                    os.makedirs(filepath)
                except OSError:
                    return Response(_(u"Failed to create path %(path)s (Permission denied).", path=filepath)), 422
            try:
                copyfile(meta.file_path, saved_filename)
            except OSError:
                return Response(_(u"Failed to store file %(file)s (Permission denied).", file=saved_filename)), 422

            try:
                os.unlink(meta.file_path)
            except OSError:
                return Response(_(u"Failed to delete file %(file)s (Permission denied).", file= meta.file_path)), 422

            if meta.cover is None:
                has_cover = 0
                copyfile(os.path.join(config.get_main_dir, "cps/static/generic_cover.jpg"),
                         os.path.join(filepath, "cover.jpg"))
            else:
                has_cover = 1
                move(meta.cover, os.path.join(filepath, "cover.jpg"))

            # handle authors
            is_author = db.session.query(db.Authors).filter(db.Authors.name == authr).first()
            if is_author:
                db_author = is_author
            else:
                db_author = db.Authors(authr, helper.get_sorted_author(authr), "")
                db.session.add(db_author)

            # handle series
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
            file_size = os.path.getsize(saved_filename)
            db_data = db.Data(db_book, meta.extension.upper()[1:], file_size, title_dir)

            # handle tags
            input_tags = tags.split(',')
            input_tags = list(map(lambda it: it.strip(), input_tags))
            if input_tags[0] !="":
                modify_database_object(input_tags, db_book.tags, db.Tags, db.session, 'tags')

            # flush content, get db_book.id available
            db_book.data.append(db_data)
            db.session.add(db_book)
            db.session.flush()

            # add comment
            book_id = db_book.id
            upload_comment = Markup(meta.description).unescape()
            if upload_comment != "":
                db.session.add(db.Comments(upload_comment, book_id))

            # save data to database, reread data
            db.session.commit()
            db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
            book = db.session.query(db.Books).filter(db.Books.id == book_id).filter(common_filters()).first()

            # upload book to gdrive if nesseccary and add "(bookid)" to folder name
            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()
            error = helper.update_dir_stucture(book.id, config.config_calibre_dir)
            db.session.commit()
            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()
            if error:
                flash(error, category="error")
            uploadText=_(u"File %(title)s", title=book.title)
            helper.global_WorkerThread.add_upload(current_user.nickname,
                "<a href=\"" + url_for('show_book', book_id=book.id) + "\">" + uploadText + "</a>")

            # create data for displaying display Full language name instead of iso639.part3language
            if db_language is not None:
                book.languages[0].language_name = _(meta.languages)
            author_names = []
            for author in db_book.authors:
                author_names.append(author.name)
            if len(request.files.getlist("btn-upload")) < 2:
                if current_user.role_edit() or current_user.role_admin():
                    resp = {"location": url_for('edit_book', book_id=db_book.id)}
                    return Response(json.dumps(resp), mimetype='application/json')
                else:
                    resp = {"location": url_for('show_book', book_id=db_book.id)}
                    return Response(json.dumps(resp), mimetype='application/json')
    return Response(json.dumps({"location": url_for("index")}), mimetype='application/json')


@app.route("/admin/book/convert/<int:book_id>", methods=['POST'])
@login_required_if_no_ano
@edit_required
def convert_bookformat(book_id):
    # check to see if we have form fields to work with -  if not send user back
    book_format_from = request.form.get('book_format_from', None)
    book_format_to = request.form.get('book_format_to', None)

    if (book_format_from is None) or (book_format_to is None):
        flash(_(u"Source or destination format for conversion missing"), category="error")
        return redirect(request.environ["HTTP_REFERER"])

    app.logger.debug('converting: book id: ' + str(book_id) +
                     ' from: ' + request.form['book_format_from'] +
                     ' to: ' + request.form['book_format_to'])
    rtn = helper.convert_book_format(book_id, config.config_calibre_dir, book_format_from.upper(),
                                     book_format_to.upper(), current_user.nickname)

    if rtn is None:
        flash(_(u"Book successfully queued for converting to %(book_format)s",
                    book_format=book_format_to),
                    category="success")
    else:
        flash(_(u"There was an error converting this book: %(res)s", res=rtn), category="error")
    return redirect(request.environ["HTTP_REFERER"])
