#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mimetypes
import logging
from logging.handlers import RotatingFileHandler
import textwrap
from flask import Flask, render_template, session, request, Response, redirect, url_for, send_from_directory, \
    make_response, g, flash, abort
import db, config, ub, helper
import os
import errno
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import false
from sqlalchemy.exc import IntegrityError
from math import ceil
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_principal import Principal, Identity, AnonymousIdentity, identity_changed
from flask_babel import Babel
from flask_babel import gettext as _
import requests, zipfile
from werkzeug.security import generate_password_hash, check_password_hash
from babel import Locale as LC
from babel import negotiate_locale
from functools import wraps
import base64
from sqlalchemy.sql import *
import json
import urllib
import datetime
from iso639 import languages as isoLanguages
from uuid import uuid4
import os.path
import sys
import subprocess
import shutil
import re
from shutil import move

try:
    from wand.image import Image

    use_generic_pdf_cover = False
except ImportError, e:
    use_generic_pdf_cover = True

from shutil import copyfile
from cgi import escape

mimetypes.init()
mimetypes.add_type('application/xhtml+xml', '.xhtml')
mimetypes.add_type('application/epub+zip', '.epub')
mimetypes.add_type('application/x-mobipocket-ebook', '.mobi')
mimetypes.add_type('application/x-mobipocket-ebook', '.prc')
mimetypes.add_type('application/vnd.amazon.ebook', '.azw')
mimetypes.add_type('application/x-cbr', '.cbr')
mimetypes.add_type('application/x-cbz', '.cbz')
mimetypes.add_type('application/x-cbt', '.cbt')
mimetypes.add_type('image/vnd.djvu', '.djvu')


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

    def __init__(self, app):
        self.app = app

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


app = (Flask(__name__))
app.wsgi_app = ReverseProxied(app.wsgi_app)

formatter = logging.Formatter(
    "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
file_handler = RotatingFileHandler(os.path.join(config.LOG_DIR, "calibre-web.log"), maxBytes=50000, backupCount=1)
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
if config.DEVELOPMENT:
    app.logger.setLevel(logging.DEBUG)
else:
    app.logger.setLevel(logging.INFO)

app.logger.info('Starting Calibre Web...')
logging.getLogger("book_formats").addHandler(file_handler)
logging.getLogger("book_formats").setLevel(logging.INFO)

Principal(app)

babel = Babel(app)

import uploader

global global_queue
global_queue = None


lm = LoginManager(app)
lm.init_app(app)
lm.login_view = 'login'
lm.anonymous_user = ub.Anonymous

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'


@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    if user is not None and hasattr(user, "locale"):
        return user.locale
    translations=[item.language for item in babel.list_translations()]+ ['en']
    preferred = [x.replace('-', '_') for x in request.accept_languages.values()]
    return negotiate_locale(preferred, translations)


@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone


@lm.user_loader
def load_user(id):
    return ub.session.query(ub.User).filter(ub.User.id == int(id)).first()


@lm.header_loader
def load_user_from_header(header_val):
    if header_val.startswith('Basic '):
        header_val = header_val.replace('Basic ', '', 1)
    try:
        header_val = base64.b64decode(header_val)
        basic_username = header_val.split(':')[0]
        basic_password = header_val.split(':')[1]
    except TypeError:
        pass
    user = ub.session.query(ub.User).filter(ub.User.nickname == basic_username).first()
    if user and check_password_hash(user.password, basic_password):
        return user
    return


def check_auth(username, password):
    user = ub.session.query(ub.User).filter(ub.User.nickname == username).first()
    if user and check_password_hash(user.password, password):
        return True
    else:
        return False


def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_basic_auth_if_no_ano(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if config.ANON_BROWSE != 1:
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
        return int((self.page-2) * self.per_page)

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
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
                    (num > self.page - left_current - 1 and \
                                 num < self.page + right_current) or \
                            num > self.pages - right_edge:
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
    if config.ANON_BROWSE == 1:
        return func
    return login_required(func)


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
        s = mimetypes.types_map['.'+val]
    except:
        s= 'application/octet-stream'
    return s


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


# Fill indexpage with all requested data from database
def fill_indexpage(page, database, db_filter, order):
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if current_user.show_random_books():
        random = db.session.query(db.Books).filter(filter).order_by(func.random()).limit(config.RANDOM_BOOKS)
    else:
        random = false
    off = int(int(config.NEWEST_BOOKS) * (page - 1))
    pagination = Pagination(page, config.NEWEST_BOOKS,
                            len(db.session.query(database).filter(db_filter).filter(filter).all()))
    entries = db.session.query(database).filter(db_filter).filter(filter).order_by(order).offset(off).limit(
        config.NEWEST_BOOKS)
    return entries, random, pagination


def modify_database_object(input_elements, db_book_object, db_object, db_session, type):
    input_elements = [x for x in input_elements if x != '']
    # we have all input element (authors, series, tags) names now
    # 1. search for elements to remove
    del_elements = []
    for c_elements in db_book_object:
        found = False
        for inp_element in input_elements:
            if inp_element == c_elements.name:
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
            if inp_element == c_elements.name:
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
        if type == 'languages':
            db_filter = db_object.lang_code
        else:
            db_filter = db_object.name
        for add_element in add_elements:
            # check if a element with that name exists
            new_element = db_session.query(db_object).filter(db_filter == add_element).first()
            # if no element is found add it
            if new_element is None:
                if type == 'author':
                    new_element = db_object(add_element, add_element, "")
                else:
                    if type == 'series':
                        new_element = db_object(add_element, add_element)
                    else:  # type should be tag, or languages
                        new_element = db_object(add_element)
                db_session.add(new_element)
                new_element = db.session.query(db_object).filter(db_filter == add_element).first()
            # add element to book
            db_book_object.append(new_element)


@app.before_request
def before_request():
    g.user = current_user
    g.public_shelfes = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1).all()
    g.allow_registration = config.PUBLIC_REG
    g.allow_upload = config.UPLOADING


@app.route("/opds")
@requires_basic_auth_if_no_ano
def feed_index():
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    xml = render_template('index.xml')
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/osd")
@requires_basic_auth_if_no_ano
def feed_osd():
    xml = render_template('osd.xml')
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
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
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if term:
        entries = db.session.query(db.Books).filter(db.or_(db.Books.tags.any(db.Tags.name.like("%" + term + "%")),
                                                           db.Books.authors.any(db.Authors.name.like("%" + term + "%")),
                                                           db.Books.title.like("%" + term + "%"))).filter(filter).all()
        entriescount = len(entries) if len(entries) > 0 else 1
        pagination = Pagination( 1,entriescount,entriescount)
        xml = render_template('feed.xml', searchterm=term, entries=entries, pagination=pagination)
    else:
        xml = render_template('feed.xml', searchterm="")
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/new")
@requires_basic_auth_if_no_ano
def feed_new():
    off = request.args.get("offset")
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if not off:
        off = 0
    entries = db.session.query(db.Books).filter(filter).order_by(db.Books.timestamp.desc()).offset(off).limit(
        config.NEWEST_BOOKS)
    pagination = Pagination((int(off)/(int(config.NEWEST_BOOKS))+1), config.NEWEST_BOOKS,
                            len(db.session.query(db.Books).filter(filter).all()))
    xml = render_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/discover")
@requires_basic_auth_if_no_ano
def feed_discover():
    # off = request.args.get("start_index")
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    # if not off:
    # off = 0
    entries = db.session.query(db.Books).filter(filter).order_by(func.random()).limit(config.NEWEST_BOOKS)
    pagination = Pagination(1, config.NEWEST_BOOKS,int(config.NEWEST_BOOKS))
    xml = render_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/hot")
@requires_basic_auth_if_no_ano
def feed_hot():
    off = request.args.get("offset")
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if not off:
        off = 0
    entries = db.session.query(db.Books).filter(filter).filter(db.Books.ratings.any(db.Ratings.rating > 9)).offset(
        off).limit(config.NEWEST_BOOKS)
    pagination = Pagination((int(off)/(int(config.NEWEST_BOOKS))+1), config.NEWEST_BOOKS,
                            len(db.session.query(db.Books).filter(filter).filter(db.Books.ratings.any(db.Ratings.rating > 9)).all()))
    xml = render_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/author")
@requires_basic_auth_if_no_ano
def feed_authorindex():
    off = request.args.get("offset")
    # ToDo: Language filter not working
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if not off:
        off = 0
    authors = db.session.query(db.Authors).order_by(db.Authors.sort).offset(off).limit(config.NEWEST_BOOKS)
    pagination = Pagination((int(off)/(int(config.NEWEST_BOOKS))+1), config.NEWEST_BOOKS,
                            len(db.session.query(db.Authors).all()))
    xml = render_template('feed.xml', authors=authors, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/author/<int:id>")
@requires_basic_auth_if_no_ano
def feed_author(id):
    off = request.args.get("offset")
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if not off:
        off = 0
    entries = db.session.query(db.Books).filter(db.Books.authors.any(db.Authors.id == id )).filter(
        filter).offset(off).limit(config.NEWEST_BOOKS)
    pagination = Pagination((int(off)/(int(config.NEWEST_BOOKS))+1), config.NEWEST_BOOKS,
                            len(db.session.query(db.Books).filter(db.Books.authors.any(db.Authors.id == id )).filter(filter).all()))
    xml = render_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/category")
@requires_basic_auth_if_no_ano
def feed_categoryindex():
    off = request.args.get("offset")
    if not off:
        off = 0
    entries = db.session.query(db.Tags).order_by(db.Tags.name).offset(off).limit(config.NEWEST_BOOKS)
    pagination = Pagination((int(off)/(int(config.NEWEST_BOOKS))+1), config.NEWEST_BOOKS,
                            len(db.session.query(db.Tags).all()))
    xml = render_template('feed.xml', categorys=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/category/<int:id>")
@requires_basic_auth_if_no_ano
def feed_category(id):
    off = request.args.get("offset")
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if not off:
        off = 0
    entries = db.session.query(db.Books).filter(db.Books.tags.any(db.Tags.id==id)).order_by(
        db.Books.timestamp.desc()).filter(filter).offset(off).limit(config.NEWEST_BOOKS)
    pagination = Pagination((int(off)/(int(config.NEWEST_BOOKS))+1), config.NEWEST_BOOKS,
                            len(db.session.query(db.Books).filter(db.Books.tags.any(db.Tags.id==id)).filter(filter).all()))
    xml = render_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/series")
@requires_basic_auth_if_no_ano
def feed_seriesindex():
    off = request.args.get("offset")
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if not off:
        off = 0
    entries = db.session.query(db.Series).order_by(db.Series.name).offset(off).limit(config.NEWEST_BOOKS)
    pagination = Pagination((int(off)/(int(config.NEWEST_BOOKS))+1), config.NEWEST_BOOKS,
                            len(db.session.query(db.Series).all()))
    xml = render_template('feed.xml', series=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/series/<int:id>")
@requires_basic_auth_if_no_ano
def feed_series(id):
    off = request.args.get("offset")
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if not off:
        off = 0
    entries = db.session.query(db.Books).filter(db.Books.series.any(db.Series.id == id)).order_by(
        db.Books.timestamp.desc()).filter(filter).offset(off).limit(config.NEWEST_BOOKS)
    pagination = Pagination((int(off)/(int(config.NEWEST_BOOKS))+1), config.NEWEST_BOOKS,
                            len(db.session.query(db.Books).filter(db.Books.series.any(db.Series.id == id)).filter(filter).all()))
    xml = render_template('feed.xml', entries=entries, pagination=pagination)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/opds/download/<book_id>/<format>/")
@requires_basic_auth_if_no_ano
@download_required
def get_opds_download_link(book_id, format):
    format = format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == format.upper()).first()
    if current_user.is_authenticated:
        helper.update_download(book_id, int(current_user.id))
    author = helper.get_normalized_author(book.author_sort)
    file_name = book.title
    if len(author) > 0:
        file_name = author + '-' + file_name
    file_name = helper.get_valid_filename(file_name)
    response = make_response(send_from_directory(os.path.join(config.DB_ROOT, book.path), data.name + "." + format))
    response.headers["Content-Disposition"] = "attachment; filename=\"%s.%s\"" % (data.name, format)
    return response

@app.route("/ajax/book/<string:uuid>")
@requires_basic_auth_if_no_ano
def get_metadata_calibre_companion(uuid):
    entry = db.session.query(db.Books).filter(db.Books.uuid.like("%"+uuid+"%")).first()
    if entry is not None :
        js = render_template('json.txt',entry=entry)
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
        entries = db.session.execute("select name from authors where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(r) for r in entries])
        return json_dumps


@app.route("/get_tags_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_tags_json():
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.execute("select name from tags where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(r) for r in entries])
        return json_dumps


@app.route("/get_languages_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_languages_json():
    if request.method == "GET":
        query = request.args.get('q').lower()
        # entries = db.session.execute("select lang_code from languages where lang_code like '%" + query + "%'")
        languages = db.session.query(db.Languages).all()
        for lang in languages:
            try:
                cur_l = LC.parse(lang.lang_code)
                lang.name = cur_l.get_language_name(get_locale())
            except:
                lang.name = _(isoLanguages.get(part3=lang.lang_code).name)

        entries = [s for s in languages if query in s.name.lower()]
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@app.route("/get_series_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_series_json():
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.execute("select name from series where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(r) for r in entries])
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
        q = q.filter(db.Books.authors.any(db.Authors.name.like("%" + author_input + "%")),
                     db.Books.title.like("%" + title_input + "%"))
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
    return render_template('index.html', random=random, entries=entries, pagination=pagination,
                           title=_(u"Latest Books"))


@app.route("/hot", defaults={'page': 1})
@app.route('/hot/page/<int:page>')
@login_required_if_no_ano
def hot_books(page):
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if current_user.show_random_books():
        random = db.session.query(db.Books).filter(filter).order_by(func.random()).limit(config.RANDOM_BOOKS)
    else:
        random = false
    off = int(int(config.NEWEST_BOOKS) * (page - 1))
    all_books = ub.session.query(ub.Downloads, ub.func.count(ub.Downloads.book_id)).order_by(
        ub.func.count(ub.Downloads.book_id).desc()).group_by(ub.Downloads.book_id)
    hot_books = all_books.offset(off).limit(config.NEWEST_BOOKS)
    entries = list()
    for book in hot_books:
        entries.append(db.session.query(db.Books).filter(filter).filter(db.Books.id == book.Downloads.book_id).first())
    numBooks = entries.__len__()
    pagination = Pagination(page, config.NEWEST_BOOKS, numBooks)
    return render_template('index.html', random=random, entries=entries, pagination=pagination,
                           title=_(u"Hot Books (most downloaded)"))


@app.route("/discover", defaults={'page': 1})
@app.route('/discover/page/<int:page>')
@login_required_if_no_ano
def discover(page):
    entries, random, pagination = fill_indexpage(page, db.Books, func.randomblob(2), db.Books.timestamp.desc())
    return render_template('discover.html', entries=entries, pagination=pagination, title=_(u"Random Books"))


@app.route("/author")
@login_required_if_no_ano
def author_list():
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    entries = db.session.query(db.Authors, func.count('books_authors_link.book').label('count')).join(
        db.books_authors_link).join(db.Books).filter(
        filter).group_by('books_authors_link.author').order_by(db.Authors.sort).all()
    return render_template('list.html', entries=entries, folder='author', title=_(u"Author list"))


@app.route("/author/<name>")
@login_required_if_no_ano
def author(name):
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    if current_user.show_random_books():
        random = db.session.query(db.Books).filter(filter).order_by(func.random()).limit(config.RANDOM_BOOKS)
    else:
        random = false

    entries = db.session.query(db.Books).filter(db.Books.authors.any(db.Authors.name.like("%" + name + "%"))).filter(
        filter).all()
    return render_template('index.html', random=random, entries=entries, title=_(u"Author: %(nam)s", nam=name))


@app.route("/series")
@login_required_if_no_ano
def series_list():
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    entries = db.session.query(db.Series, func.count('books_series_link.book').label('count')).join(
        db.books_series_link).join(db.Books).filter(
        filter).group_by('books_series_link.series').order_by(db.Series.sort).all()
    return render_template('list.html', entries=entries, folder='series', title=_(u"Series list"))


@app.route("/series/<name>/", defaults={'page': 1})
@app.route("/series/<name>/<int:page>'")
@login_required_if_no_ano
def series(name, page):
    entries, random, pagination = fill_indexpage(page, db.Books, db.Books.series.any(db.Series.name == name),
                                                 db.Books.series_index)
    if entries:
        return render_template('index.html', random=random, pagination=pagination, entries=entries,
                               title=_(u"Series: %(serie)s", serie=name))
    else:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))


@app.route("/language")
@login_required_if_no_ano
def language_overview():
    if current_user.filter_language() == u"all":
        languages = db.session.query(db.Languages).all()
        for lang in languages:
            try:
                cur_l = LC.parse(lang.lang_code)
                lang.name = cur_l.get_language_name(get_locale())
            except:
                lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    else:
        try:
            langfound = 1
            cur_l = LC.parse(current_user.filter_language())
        except:
            langfound = 0
        languages = db.session.query(db.Languages).filter(
            db.Languages.lang_code == current_user.filter_language()).all()
        if langfound:
            languages[0].name = cur_l.get_language_name(get_locale())
        else:
            languages[0].name = _(isoLanguages.get(part3=languages[0].lang_code).name)
    lang_counter = db.session.query(db.books_languages_link,
                                    func.count('books_languages_link.book').label('bookcount')).group_by(
        'books_languages_link.lang_code').all()
    return render_template('languages.html', languages=languages, lang_counter=lang_counter,
                           title=_(u"Available languages"))


@app.route("/language/<name>", defaults={'page': 1})
@app.route('/language/<name>/page/<int:page>')
@login_required_if_no_ano
def language(name, page):
    entries, random, pagination = fill_indexpage(page, db.Books, db.Books.languages.any(db.Languages.lang_code == name),
                                                 db.Books.timestamp.desc())
    try:
        cur_l = LC.parse(name)
        name = cur_l.get_language_name(get_locale())
    except:
        name = _(isoLanguages.get(part3=name).name)
    return render_template('index.html', random=random, entries=entries, pagination=pagination,
                           title=_(u"Language: %(name)s", name=name))


@app.route("/category")
@login_required_if_no_ano
def category_list():
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    entries = db.session.query(db.Tags, func.count('books_tags_link.book').label('count')).join(
        db.books_tags_link).join(db.Books).filter(
        filter).group_by('books_tags_link.tag').all()
    return render_template('list.html', entries=entries, folder='category', title=_(u"Category list"))


@app.route("/category/<name>", defaults={'page': 1})
@app.route('/category/<name>/<int:page>')
@login_required_if_no_ano
def category(name, page):
    entries, random, pagination = fill_indexpage(page, db.Books, db.Books.tags.any(db.Tags.name == name),
                                                 db.Books.timestamp.desc())
    return render_template('index.html', random=random, entries=entries, pagination=pagination,
                           title=_(u"Category: %(name)s", name=name))


@app.route("/book/<int:id>")
@login_required_if_no_ano
def show_book(id):
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    entries = db.session.query(db.Books).filter(db.Books.id == id).filter(filter).first()
    if entries:
        for index in range(0, len(entries.languages)):
            try:
                entries.languages[index].language_name = LC.parse(entries.languages[index].lang_code).get_language_name(
                    get_locale())
            except:
                entries.languages[index].language_name = _(
                    isoLanguages.get(part3=entries.languages[index].lang_code).name)
        cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
        book_in_shelfs = []
        shelfs = ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == id).all()
        for entry in shelfs:
            book_in_shelfs.append(entry.shelf)

        return render_template('detail.html', entry=entries, cc=cc, title=entries.title, books_shelfs=book_in_shelfs)
    else:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin_forbidden():
    return "Admin ONLY!"
    abort(403)


@app.route("/stats")
@login_required
def stats():
    counter = len(db.session.query(db.Books).all())
    authors = len(db.session.query(db.Authors).all())
    Versions=uploader.book_formats.get_versions()
    if sys.platform == "win32":
        kindlegen = os.path.join(config.MAIN_DIR, "vendor", u"kindlegen.exe")
    else:
        kindlegen = os.path.join(config.MAIN_DIR, "vendor", u"kindlegen")
    kindlegen_version=_('not installed')
    if os.path.exists(kindlegen):
        p = subprocess.Popen(kindlegen, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        check = p.wait()
        for lines in p.stdout.readlines():
            if re.search('Amazon kindlegen\(', lines):
                Versions['KindlegenVersion'] = lines
    Versions['PythonVersion']=sys.version
    return render_template('stats.html', bookcounter=counter, authorcounter=authors, Versions=Versions, title=_(u"Statistics"))


@app.route("/shutdown")
@login_required
def shutdown():
    # logout_user()
    # add restart command to queue
    global_queue.put("something")
    flash(_(u"Server restarts"), category="info")
    return redirect(url_for("index"))


@app.route("/search", methods=["GET"])
@login_required_if_no_ano
def search():
    term = request.args.get("query").strip()
    if term:
        if current_user.filter_language() != "all":
            filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
        else:
            filter = True
        entries = db.session.query(db.Books).filter(db.or_(db.Books.tags.any(db.Tags.name.like("%" + term + "%")),
                                                           db.Books.series.any(db.Series.name.like("%" + term + "%")),
                                                           db.Books.authors.any(db.Authors.name.like("%" + term + "%")),
                                                           db.Books.title.like("%" + term + "%"))).filter(filter).all()
        return render_template('search.html', searchterm=term, entries=entries)
    else:
        return render_template('search.html', searchterm="")


@app.route("/advanced_search", methods=["GET"])
@login_required_if_no_ano
def advanced_search():
    if request.method == 'GET':
        q = db.session.query(db.Books)
        include_tag_inputs = request.args.getlist('include_tag')
        exclude_tag_inputs = request.args.getlist('exclude_tag')
        include_series_inputs = request.args.getlist('include_serie')
        exclude_series_inputs = request.args.getlist('exclude_serie')
        include_languages_inputs = request.args.getlist('include_language')
        exclude_languages_inputs = request.args.getlist('exclude_language')

        author_name = request.args.get("author_name")
        book_title = request.args.get("book_title")
        if author_name: author_name = author_name.strip()
        if book_title: book_title = book_title.strip()
        if include_tag_inputs or exclude_tag_inputs or include_series_inputs or exclude_series_inputs or \
                include_languages_inputs or exclude_languages_inputs or author_name or book_title:
            searchterm = []
            searchterm.extend((author_name, book_title))
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
                except:
                    lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
            searchterm.extend(language.name for language in language_names)
            searchterm = " + ".join(filter(None, searchterm))
            q = q.filter(db.Books.authors.any(db.Authors.name.like("%" + author_name + "%")),
                         db.Books.title.like("%" + book_title + "%"))
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
            return render_template('search.html', searchterm=searchterm, entries=q)
    tags = db.session.query(db.Tags).order_by(db.Tags.name).all()
    series = db.session.query(db.Series).order_by(db.Series.name).all()
    if current_user.filter_language() == u"all":
        languages = db.session.query(db.Languages).all()
        for lang in languages:
            try:
                cur_l = LC.parse(lang.lang_code)
                lang.name = cur_l.get_language_name(get_locale())
            except:
                lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    else:
        languages=None
    return render_template('search_form.html', tags=tags, languages=languages, series=series)


@app.route("/cover/<path:cover_path>")
@login_required_if_no_ano
def get_cover(cover_path):
    return send_from_directory(os.path.join(config.DB_ROOT, cover_path), "cover.jpg")

@app.route("/opds/thumb_240_240/<path:book_id>")
@app.route("/opds/cover_240_240/<path:book_id>")
@app.route("/opds/cover_90_90/<path:book_id>")
@app.route("/opds/cover/<path:book_id>")
@requires_basic_auth_if_no_ano
def feed_get_cover(book_id):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    return send_from_directory(os.path.join(config.DB_ROOT, book.path), "cover.jpg")


@app.route("/read/<int:book_id>/<format>")
@login_required
def read_book(book_id, format):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    if book:
        book_dir = os.path.join(config.MAIN_DIR, "cps", "static", str(book_id))
        if not os.path.exists(book_dir):
            os.mkdir(book_dir)
        if format.lower() == "epub":
            # check if mimetype file is exists
            mime_file = str(book_id) + "/mimetype"
            if not os.path.exists(mime_file):
                epub_file = os.path.join(config.DB_ROOT, book.path, book.data[0].name) + ".epub"
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
                            if exception.errno == errno.EEXIST:
                                pass
                            else:
                                raise
                    if fileName:
                        fd = open(os.path.join(newDir, fileName), "wb")
                        fd.write(zfile.read(name))
                        fd.close()
                zfile.close()
            return render_template('read.html', bookid=book_id, title=_(u"Read a Book"))
        elif format.lower() == "pdf":
            all_name = str(book_id) + "/" + urllib.quote(book.data[0].name) + ".pdf"
            tmp_file = os.path.join(book_dir, urllib.quote(book.data[0].name)) + ".pdf"
            if not os.path.exists(tmp_file):
                pdf_file = os.path.join(config.DB_ROOT, book.path, book.data[0].name) + ".pdf"
                copyfile(pdf_file, tmp_file)
            return render_template('readpdf.html', pdffile=all_name, title=_(u"Read a Book"))
        elif format.lower() == "txt":
            all_name = str(book_id) + "/" + urllib.quote(book.data[0].name) + ".txt"
            tmp_file = os.path.join(book_dir, urllib.quote(book.data[0].name)) + ".txt"
            if not os.path.exists(all_name):
                txt_file = os.path.join(config.DB_ROOT, book.path, book.data[0].name) + ".txt"
                copyfile(txt_file, tmp_file)
            return render_template('readtxt.html', txtfile=all_name, title=_(u"Read a Book"))
        elif format.lower() == "cbr":
            all_name = str(book_id) + "/" + urllib.quote(book.data[0].name) + ".cbr"
            tmp_file = os.path.join(book_dir, urllib.quote(book.data[0].name)) + ".cbr"
            if not os.path.exists(all_name):
                cbr_file = os.path.join(config.DB_ROOT, book.path, book.data[0].name) + ".cbr"
                copyfile(cbr_file, tmp_file)
            return render_template('readcbr.html', comicfile=all_name, title=_(u"Read a Book"))

    else:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))


@app.route("/download/<int:book_id>/<format>")
@login_required_if_no_ano
@download_required
def get_download_link(book_id, format):
    format = format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == format.upper()).first()
    if data:
        if current_user.is_authenticated:         # collect downloaded books only for registered user and not for anonymous user
            helper.update_download(book_id, int(current_user.id))
        author = helper.get_normalized_author(book.author_sort)
        file_name = book.title
        if len(author) > 0:
            file_name = author + '-' + file_name
        file_name = helper.get_valid_filename(file_name)
        response = make_response(send_from_directory(os.path.join(config.DB_ROOT, book.path), data.name + "." + format))
        try:
            response.headers["Content-Type"]=mimetypes.types_map['.'+format]
        except:
            pass
        response.headers["Content-Disposition"] = \
            "attachment; " \
            "filename={utf_filename}.{suffix};" \
            "filename*=UTF-8''{utf_filename}.{suffix}".format(
                utf_filename=file_name.encode('utf-8'),
                suffix=format
            )
        return response
    else:
        abort(404)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if not config.PUBLIC_REG:
        abort(404)
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == "POST":
        to_save = request.form.to_dict()
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_template('register.html', title="register")

        existing_user = ub.session.query(ub.User).filter(ub.User.nickname == to_save["nickname"]).first()
        existing_email = ub.session.query(ub.User).filter(ub.User.email == to_save["email"]).first()
        if not existing_user and not existing_email:
            content = ub.User()
            content.password = generate_password_hash(to_save["password"])
            content.nickname = to_save["nickname"]
            content.email = to_save["email"]
            content.role = 0
            try:
                ub.session.add(content)
                ub.session.commit()
            except:
                ub.session.rollback()
                flash(_(u"An unknown error occured. Please try again later."), category="error")
                return render_template('register.html', title="register")
            flash("Your account has been created. Please login.", category="success")
            return redirect(url_for('login'))
        else:
            flash(_(u"This username or email address is already in use."), category="error")
            return render_template('register.html', title="register")

    return render_template('register.html', title=_(u"register"))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == "POST":
        form = request.form.to_dict()
        user = ub.session.query(ub.User).filter(ub.User.nickname == form['username'].strip()).first()

        if user and check_password_hash(user.password, form['password']):
            login_user(user, remember=True)
            flash(_(u"you are now logged in as: '%(nickname)s'", nickname=user.nickname), category="success")
            # test=
            return redirect(url_for("index"))
        else:
            flash(_(u"Wrong Username or Password"), category="error")

    return render_template('login.html', title=_(u"login"))


@app.route('/logout')
@login_required
def logout():
    if current_user is not None and current_user.is_authenticated:
        logout_user()
    return redirect(url_for('login'))


@app.route('/send/<int:book_id>')
@login_required
@download_required
def send_to_kindle(book_id):
    settings = ub.get_mail_settings()
    if settings.get("mail_server", "mail.example.com") == "mail.example.com":
        flash(_(u"Please configure the SMTP mail settings first..."), category="error")
    elif current_user.kindle_mail:
        result = helper.send_mail(book_id, current_user.kindle_mail)
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
    if not shelf.is_public and not shelf.user_id == int(current_user.id):
        flash("Sorry you are not allowed to add a book to the the shelf: %s" % shelf.name)
        return redirect(url_for('index'))
    maxO = ub.session.query(func.max(ub.BookShelf.order)).filter(ub.BookShelf.shelf == shelf_id).first()
    if maxO[0] is None:
        maxOrder = 0
    else:
        maxOrder = maxO[0]
    ins = ub.BookShelf(shelf=shelf.id, book_id=book_id, order=maxOrder+1)
    ub.session.add(ins)
    ub.session.commit()

    flash(_(u"Book has been added to shelf: %(sname)s", sname=shelf.name), category="success")

    # return redirect(url_for('show_book', id=book_id))
    return redirect(request.environ["HTTP_REFERER"])


@app.route("/shelf/remove/<int:shelf_id>/<int:book_id>")
@login_required
def remove_from_shelf(shelf_id, book_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if not shelf.is_public and not shelf.user_id == int(current_user.id):
        flash("Sorry you are not allowed to remove a book from this shelf: %s" % shelf.name)
        return redirect(url_for('index'))

    book_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id,
                                                       ub.BookShelf.book_id == book_id).first()

    # rem = ub.BookShelf(shelf=shelf.id, book_id=book_id)
    ub.session.delete(book_shelf)
    ub.session.commit()

    flash(_(u"Book has been removed from shelf: %(sname)s", sname=shelf.name), category="success")

    return redirect(request.environ["HTTP_REFERER"])


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
        existing_shelf = ub.session.query(ub.Shelf).filter(or_((ub.Shelf.name == to_save["title"])&( ub.Shelf.is_public == 1),
                    (ub.Shelf.name == to_save["title"])& (ub.Shelf.user_id == int(current_user.id)))).first()
        if existing_shelf:
            flash(_(u"A shelf with the name '%(title)s' already exists.", title=to_save["title"]), category="error")
        else:
            try:
                ub.session.add(shelf)
                ub.session.commit()
                flash(_(u"Shelf %(title)s created", title=to_save["title"]), category="success")
            except:
                flash(_(u"There was an error"), category="error")
        return render_template('shelf_edit.html', shelf=shelf, title=_(u"create a shelf"))
    else:
        return render_template('shelf_edit.html', shelf=shelf, title=_(u"create a shelf"))

@app.route("/shelf/edit/<int:shelf_id>", methods=["GET", "POST"])
@login_required
def edit_shelf(shelf_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if request.method == "POST":
        to_save = request.form.to_dict()
        existing_shelf = ub.session.query(ub.Shelf).filter(or_((ub.Shelf.name == to_save["title"])&( ub.Shelf.is_public == 1),
                    (ub.Shelf.name == to_save["title"])& (ub.Shelf.user_id == int(current_user.id)))).filter(ub.Shelf.id!=shelf_id).first()
        if existing_shelf:
            flash(_(u"A shelf with the name '%(title)s' already exists.",title=to_save["title"]), category="error")
        else:
            shelf.name = to_save["title"]
            if "is_public" in to_save:
                shelf.is_public = 1
            else:
                shelf.is_public = 0
            try:
                ub.session.commit()
                flash(_(u"Shelf %(title)s changed",title=to_save["title"]), category="success")
            except:
                flash(_(u"There was an error"), category="error")
        return render_template('shelf_edit.html', shelf=shelf, title=_(u"Edit a shelf"))
    else:
        return render_template('shelf_edit.html', shelf=shelf, title=_(u"Edit a shelf"))



@app.route("/shelf/delete/<int:shelf_id>")
@login_required
def delete_shelf(shelf_id):
    cur_shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    deleted = 0
    if current_user.role == ub.ROLE_ADMIN:
        deleted = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).delete()

    else:
        deleted = ub.session.query(ub.Shelf).filter(ub.or_(ub.and_(ub.Shelf.user_id == int(current_user.id),
                                                                   ub.Shelf.id == shelf_id),
                                                           ub.and_(ub.Shelf.is_public == 1,
                                                                   ub.Shelf.id == shelf_id))).delete()

    if deleted:
        ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).delete()
        ub.session.commit()
        flash(_("successfully deleted shelf %(name)s", name=cur_shelf.name, category="success"))
    return redirect(url_for('index'))


@app.route("/shelf/<int:shelf_id>")
@login_required_if_no_ano
def show_shelf(shelf_id):
    if current_user.is_anonymous():
        shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1, ub.Shelf.id == shelf_id).first()
    else:
        shelf = ub.session.query(ub.Shelf).filter(ub.or_(ub.and_(ub.Shelf.user_id == int(current_user.id),
                                                                 ub.Shelf.id == shelf_id),
                                                         ub.and_(ub.Shelf.is_public == 1,
                                                                 ub.Shelf.id == shelf_id))).first()
    result = list()
    if shelf:
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).order_by(ub.BookShelf.order.asc()).all()
        for book in books_in_shelf:
            cur_book = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
            result.append(cur_book)

    return render_template('shelf.html', entries=result, title=_(u"Shelf: '%(name)s'", name=shelf.name), shelf=shelf)


@app.route("/shelf/order/<int:shelf_id>", methods=["GET", "POST"])
@login_required
def order_shelf(shelf_id):
    if request.method == "POST":
        to_save = request.form.to_dict()
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).order_by(
            ub.BookShelf.order.asc()).all()
        counter=0
        for book in books_in_shelf:
            setattr(book, 'order', to_save[str(book.book_id)])
            counter+=1
        ub.session.commit()
    if current_user.is_anonymous():
        shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1, ub.Shelf.id == shelf_id).first()
    else:
        shelf = ub.session.query(ub.Shelf).filter(ub.or_(ub.and_(ub.Shelf.user_id == int(current_user.id),
                                                                 ub.Shelf.id == shelf_id),
                                                         ub.and_(ub.Shelf.is_public == 1,
                                                                 ub.Shelf.id == shelf_id))).first()
    result = list()
    if shelf:
        books_in_shelf2 = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).order_by(ub.BookShelf.order.asc()).all()
        for book in books_in_shelf2:
            cur_book = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
            result.append(cur_book)
    return render_template('shelf_order.html', entries=result, title=_(u"Change order of Shelf: '%(name)s'", name=shelf.name), shelf=shelf)


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
        except:
            lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    translations = babel.list_translations() + [LC('en')]
    for book in content.downloads:
        downloadBook=db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
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
        content.random_books = 0
        content.language_books = 0
        content.series_books = 0
        content.category_books = 0
        content.hot_books = 0
        if "show_random" in to_save and to_save["show_random"] == "on":
            content.random_books = 1
        if "show_language" in to_save and to_save["show_language"] == "on":
            content.language_books = 1
        if "show_series" in to_save and to_save["show_series"] == "on":
            content.series_books = 1
        if "show_category" in to_save and to_save["show_category"] == "on":
            content.category_books = 1
        if "show_hot" in to_save and to_save["show_hot"] == "on":
            content.hot_books = 1
        if "default_language" in to_save:
            content.default_language = to_save["default_language"]
        try:
            ub.session.commit()
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"Found an existing account for this email address."), category="error")
            return render_template("user_edit.html", content=content, downloads=downloads,
                                   title=_(u"%(name)s's profile", name=current_user.nickname))
        flash(_(u"Profile updated"), category="success")
    return render_template("user_edit.html", translations=translations, profile=1, languages=languages, content=content,
                           downloads=downloads, title=_(u"%(name)s's profile", name=current_user.nickname))


@app.route("/admin/view")
@login_required
@admin_required
def admin():
    content = ub.session.query(ub.User).all()
    settings = ub.session.query(ub.Settings).first()
    return render_template("admin.html", content=content, email=settings, config=config, title=_(u"Admin page"))

@app.route("/admin/config")
@login_required
@admin_required
def configuration():
    content = ub.session.query(ub.User).all()
    settings = ub.session.query(ub.Settings).first()
    return render_template("admin.html", content=content, email=settings, config=config, title=_(u"Admin page"))


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
        except:
            lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    translations = [LC('en')] + babel.list_translations()
    if request.method == "POST":
        to_save = request.form.to_dict()
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_template("user_edit.html", new_user=1, content=content, title=_(u"Add new user"))
        content.password = generate_password_hash(to_save["password"])
        content.nickname = to_save["nickname"]
        content.email = to_save["email"]
        content.default_language = to_save["default_language"]
        content.locale = to_save["locale"]
        content.random_books = 0
        content.language_books = 0
        content.series_books = 0
        content.category_books = 0
        content.hot_books = 0
        if "show_language" in to_save:
            content.language_books = to_save["show_language"]
        if "show_series" in to_save:
            content.series_books = to_save["show_series"]
        if "show_category" in to_save:
            content.category_books = to_save["show_category"]
        if "show_hot" in to_save:
            content.hot_books = to_save["show_hot"]
        content.role = 0
        if "admin_role" in to_save:
            content.role = content.role + ub.ROLE_ADMIN
        if "download_role" in to_save:
            content.role = content.role + ub.ROLE_DOWNLOAD
        if "upload_role" in to_save:
            content.role = content.role + ub.ROLE_UPLOAD
        if "edit_role" in to_save:
            content.role = content.role + ub.ROLE_EDIT
        if "passwd_role" in to_save:
            content.role = content.role + ub.ROLE_PASSWD
        try:
            ub.session.add(content)
            ub.session.commit()
            flash(_("User '%(user)s' created", user=content.nickname), category="success")
            return redirect(url_for('admin'))
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"Found an existing account for this email address or nickname."), category="error")
    return render_template("user_edit.html", new_user=1, content=content, translations=translations,
                           languages=languages, title="Add new user")


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
            result=helper.send_test_mail(current_user.kindle_mail)
            if result is None:
                flash(_(u"Test E-Mail successfully send to %(kindlemail)s", kindlemail=current_user.kindle_mail),
                      category="success")
            else:
                flash(_(u"There was an error sending the Test E-Mail: %(res)s", res=result), category="error")
    return render_template("email_edit.html", content=content, title=_("Edit mail settings"))


@app.route("/admin/user/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    content = ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()
    downloads = list()
    languages = db.session.query(db.Languages).all()
    for lang in languages:
        try:
            cur_l = LC.parse(lang.lang_code)
            lang.name = cur_l.get_language_name(get_locale())
        except:
            lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
    translations = babel.list_translations() + [LC('en')]
    for book in content.downloads:
        downloadBook=db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
        if downloadBook:
            downloads.append(db.session.query(db.Books).filter(db.Books.id == book.book_id).first())
        else:
            ub.session.query(ub.Downloads).filter(book.book_id == ub.Downloads.book_id).delete()
            ub.session.commit()
    if request.method == "POST":
        to_save = request.form.to_dict()
        if "delete" in to_save:
            ub.session.delete(content)
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

            if "passwd_role" in to_save and not content.role_passwd():
                content.role = content.role + ub.ROLE_PASSWD
            elif "passwd_role" not in to_save and content.role_passwd():
                content.role = content.role - ub.ROLE_PASSWD
            content.random_books = 0
            content.language_books = 0
            content.series_books = 0
            content.category_books = 0
            content.hot_books = 0
            if "show_random" in to_save and to_save["show_random"] == "on":
                content.random_books = 1
            if "show_language" in to_save and to_save["show_language"] == "on":
                content.language_books = 1
            if "show_series" in to_save and to_save["show_series"] == "on":
                content.series_books = 1
            if "show_category" in to_save and to_save["show_category"] == "on":
                content.category_books = 1
            if "show_hot" in to_save and to_save["show_hot"] == "on":
                content.hot_books = 1
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
    return render_template("user_edit.html", translations=translations, languages=languages, new_user=0,
                           content=content, downloads=downloads, title=_(u"Edit User %(nick)s", nick=content.nickname))


@app.route("/admin/book/<int:book_id>", methods=['GET', 'POST'])
@login_required_if_no_ano
@edit_required
def edit_book(book_id):
    # create the function for sorting...
    db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    if current_user.filter_language() != "all":
        filter = db.Books.languages.any(db.Languages.lang_code == current_user.filter_language())
    else:
        filter = True
    book = db.session.query(db.Books).filter(db.Books.id == book_id).filter(filter).first()
    author_names = []
    if book:
        for index in range(0, len(book.languages)):
            try:
                book.languages[index].language_name = LC.parse(book.languages[index].lang_code).get_language_name(
                    get_locale())
            except:
                book.languages[index].language_name = _(isoLanguages.get(part3=book.languages[index].lang_code).name)
        for author in book.authors:
            author_names.append(author.name)
        if request.method == 'POST':
            edited_books_id = set()
            to_save = request.form.to_dict()
            if book.title != to_save["book_title"]:
                book.title = to_save["book_title"]
                edited_books_id.add(book.id)
            input_authors = to_save["author_name"].split('&')
            input_authors = map(lambda it: it.strip(), input_authors)
            # we have all author names now
            author0_before_edit = book.authors[0].name
            modify_database_object(input_authors, book.authors, db.Authors, db.session, 'author')
            if author0_before_edit != book.authors[0].name:
                edited_books_id.add(book.id)

            if to_save["cover_url"] and os.path.splitext(to_save["cover_url"])[1].lower() == ".jpg":
                img = requests.get(to_save["cover_url"])
                f = open(os.path.join(config.DB_ROOT, book.path, "cover.jpg"), "wb")
                f.write(img.content)
                f.close()

            if book.series_index != to_save["series_index"]:
                book.series_index = to_save["series_index"]

            if len(book.comments):
                book.comments[0].text = to_save["description"]
            else:
                book.comments.append(db.Comments(text=to_save["description"], book=book.id))

            input_tags = to_save["tags"].split(',')
            input_tags = map(lambda it: it.strip(), input_tags)
            modify_database_object(input_tags, book.tags, db.Tags, db.session, 'tags')

            input_series = [to_save["series"].strip()]
            input_series = [x for x in input_series if x != '']
            modify_database_object(input_series, book.series, db.Series, db.session, 'series')

            input_languages = to_save["languages"].split(',')
            input_languages = map(lambda it: it.strip().lower(), input_languages)

            # retranslate displayed text to language codes
            languages = db.session.query(db.Languages).all()
            input_l = []
            for lang in languages:
                try:
                    lang.name = LC.parse(lang.lang_code).get_language_name(get_locale()).lower()
                except:
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
                    input_tags = map(lambda it: it.strip(), input_tags)
                    input_tags = [x for x in input_tags if x != '']
                    # we have all author names now
                    # 1. search for tags to remove
                    del_tags = []
                    for c_tag in getattr(book, cc_string):
                        found = False
                        for inp_tag in input_tags:
                            if inp_tag == c_tag.value:
                                found = True
                                break
                        # if the tag was not found in the new list, add him to remove list
                        if not found:
                            del_tags.append(c_tag)
                    # 2. search for tags that need to be added
                    add_tags = []
                    for inp_tag in input_tags:
                        found = False
                        for c_tag in getattr(book, cc_string):
                            if inp_tag == c_tag.value:
                                found = True
                                break
                        if not found:
                            add_tags.append(inp_tag)
                    # if there are tags to remove, we remove them now
                    if len(del_tags) > 0:
                        for del_tag in del_tags:
                            getattr(book, cc_string).remove(del_tag)
                            if len(del_tag.books) == 0:
                                db.session.delete(del_tag)
                    # if there are tags to add, we add them now!
                    if len(add_tags) > 0:
                        for add_tag in add_tags:
                            # check if a tag with that name exists
                            new_tag = db.session.query(db.cc_classes[c.id]).filter(
                                db.cc_classes[c.id].value == add_tag).first()
                            # if no tag is found add it
                            if new_tag is None:
                                new_tag = db.cc_classes[c.id](value=add_tag)
                                db.session.add(new_tag)
                                new_tag = db.session.query(db.cc_classes[c.id]).filter(
                                    db.cc_classes[c.id].value == add_tag).first()
                            # add tag to book
                            getattr(book, cc_string).append(new_tag)

            db.session.commit()
            author_names = []
            for author in book.authors:
                author_names.append(author.name)
            for b in edited_books_id:
                helper.update_dir_stucture(b)
            if "detail_view" in to_save:
                return redirect(url_for('show_book', id=book.id))
            else:
                return render_template('edit_book.html', book=book, authors=author_names, cc=cc)
        else:
            return render_template('edit_book.html', book=book, authors=author_names, cc=cc)
    else:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("index"))


@app.route("/upload", methods=["GET", "POST"])
@login_required_if_no_ano
@upload_required
def upload():
    if not config.UPLOADING:
        abort(404)
    # create the function for sorting...
    db.session.connection().connection.connection.create_function("title_sort", 1, db.title_sort)
    db.session.connection().connection.connection.create_function('uuid4', 0, lambda: str(uuid4()))
    if request.method == 'POST' and 'btn-upload' in request.files:
        file = request.files['btn-upload']
        meta = uploader.upload(file)

        title = meta.title.encode('utf-8')
        author = meta.author.encode('utf-8')

        title_dir = helper.get_valid_filename(title.decode('utf-8'), False)
        author_dir = helper.get_valid_filename(author.decode('utf-8'), False)
        data_name = title_dir
        filepath = config.DB_ROOT + os.sep + author_dir + os.sep + title_dir
        saved_filename = filepath + os.sep + data_name + meta.extension

        if not os.path.exists(filepath):
            try:
                os.makedirs(filepath)
            except OSError:
                flash(_(u"Failed to create path %s (Permission denied)." % filepath), category="error")
                return redirect(url_for('index'))
        try:
            copyfile(meta.file_path, saved_filename)
        except OSError, e:
            flash(_(u"Failed to store file %s (Permission denied)." % saved_filename), category="error")
            return redirect(url_for('index'))
        try:
            os.unlink(meta.file_path)
        except OSError, e:
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
            db_author = db.Authors(author, "", "")
            db.session.add(db_author)
        path = os.path.join(author_dir, title_dir)
        db_book = db.Books(title, "", "", datetime.datetime.now(), datetime.datetime(101, 01, 01), 1,
                           datetime.datetime.now(), path, has_cover, db_author, [])
        db_book.authors.append(db_author)
        db_data = db.Data(db_book, meta.extension.upper()[1:], file_size, data_name)
        db_book.data.append(db_data)

        db.session.add(db_book)
        db.session.commit()
        author_names = []
        for author in db_book.authors:
            author_names.append(author.name)
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    if current_user.role_edit() or current_user.role_admin():
        return render_template('edit_book.html', book=db_book, authors=author_names, cc=cc)
    book_in_shelfs = []
    return render_template('detail.html', entry=db_book, cc=cc, title=db_book.title, books_shelfs=book_in_shelfs)
