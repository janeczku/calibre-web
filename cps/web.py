#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mimetypes
import logging
from logging.handlers import RotatingFileHandler
import sys
import textwrap
mimetypes.add_type('application/xhtml+xml','.xhtml')
from flask import Flask, render_template, session, request, Response, redirect, url_for, send_from_directory, make_response, g, flash, abort
from cps import db, config, ub, helper
import os
import errno
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import false
from sqlalchemy.exc import IntegrityError
from math import ceil
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user, AnonymousUserMixin
from flask.ext.principal import Principal, Identity, AnonymousIdentity, identity_changed
import requests, zipfile
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import base64
from sqlalchemy.sql import *
import json
import datetime
from uuid import uuid4
from shutil import copyfile

class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the 
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
    '''
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
file_handler = RotatingFileHandler(os.path.join(config.LOG_DIR, "calibre-web.log"), maxBytes=10000, backupCount=1)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
app.logger.info('Starting Calibre Web...')
logging.getLogger("book_formats").addHandler(file_handler)
logging.getLogger("book_formats").setLevel(logging.INFO)


Principal(app)

class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.nickname = 'Guest'
        self.role = -1
    def role_admin(self):
        return False
    def role_download(self):
        return False
    def role_upload(self):
        return False
    def role_edit(self):
        return False

lm = LoginManager(app)
lm.init_app(app)
lm.login_view = 'login'
lm.anonymous_user = Anonymous

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

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

#simple pagination for the feed
class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

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

##pagination links in jinja
def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

app.jinja_env.globals['url_for_other_page'] = url_for_other_page

def login_required_if_no_ano(func):
    if config.ANON_BROWSE == 1:
        return func
    return login_required(func)

## custom jinja filters
@app.template_filter('shortentitle')
def shortentitle_filter(s):
    if len(s) > 60:
        s = s.split(':', 1)[0]
        if len(s) > 60:
            s = textwrap.wrap(s, 60, break_long_words=False)[0]+' [...]'
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

@app.before_request
def before_request():
    g.user = current_user
    g.public_shelfes = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1).all()
    g.allow_registration = config.PUBLIC_REG
    g.allow_upload = config.UPLOADING

@app.route("/feed")
@requires_basic_auth_if_no_ano
def feed_index():
    xml = render_template('index.xml')
    response= make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route("/feed/osd")
@requires_basic_auth_if_no_ano
def feed_osd():
    xml = render_template('osd.xml')
    response= make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route("/feed/search", methods=["GET"])
@requires_basic_auth_if_no_ano
def feed_search():
    term = request.args.get("query")
    if term:
        random = db.session.query(db.Books).order_by(func.random()).limit(config.RANDOM_BOOKS)
        entries = db.session.query(db.Books).filter(db.or_(db.Books.tags.any(db.Tags.name.like("%"+term+"%")),db.Books.authors.any(db.Authors.name.like("%"+term+"%")),db.Books.title.like("%"+term+"%"))).all()
        xml = render_template('feed.xml', searchterm=term, entries=entries)
    else:
        xml = render_template('feed.xml', searchterm="")
    response= make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route("/feed/new")
@requires_basic_auth_if_no_ano
def feed_new():
    off = request.args.get("start_index")
    if off:
        entries = db.session.query(db.Books).order_by(db.Books.last_modified.desc()).offset(off).limit(config.NEWEST_BOOKS)
    else:
        entries = db.session.query(db.Books).order_by(db.Books.last_modified.desc()).limit(config.NEWEST_BOOKS)
        off = 0
    xml = render_template('feed.xml', entries=entries, next_url="/feed/new?start_index=%d" % (int(config.NEWEST_BOOKS) + int(off)))
    response= make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/feed/discover")
@requires_basic_auth_if_no_ano
def feed_discover():
    off = request.args.get("start_index")
    if off:
        entries = db.session.query(db.Books).order_by(func.random()).offset(off).limit(config.NEWEST_BOOKS)
    else:
        entries = db.session.query(db.Books).order_by(func.random()).limit(config.NEWEST_BOOKS)
        off = 0
    xml = render_template('feed.xml', entries=entries, next_url="/feed/discover?start_index=%d" % (int(config.NEWEST_BOOKS) + int(off)))
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route("/feed/hot")
@requires_basic_auth_if_no_ano
def feed_hot():
    off = request.args.get("start_index")
    if off:
        entries = db.session.query(db.Books).filter(db.Books.ratings.any(db.Ratings.rating > 9)).offset(off).limit(config.NEWEST_BOOKS)
    else:
        entries = db.session.query(db.Books).filter(db.Books.ratings.any(db.Ratings.rating > 9)).limit(config.NEWEST_BOOKS)
        off = 0

    xml = render_template('feed.xml', entries=entries, next_url="/feed/hot?start_index=%d" % (int(config.NEWEST_BOOKS) + int(off)))
    response= make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route("/feed/download/<int:book_id>/<format>")
@requires_basic_auth_if_no_ano
@download_required
def get_opds_download_link(book_id, format):
    format = format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == format.upper()).first()
    helper.update_download(book_id, int(current_user.id))
    author = helper.get_normalized_author(book.author_sort)
    file_name = book.title
    if len(author) > 0:
        file_name = author+'-'+file_name
    file_name = helper.get_valid_filename(file_name)
    response = make_response(send_from_directory(os.path.join(config.DB_ROOT, book.path), data.name + "." +format))
    response.headers["Content-Disposition"] = "attachment; filename=%s.%s" % (data.name, format)
    return response
    
@app.route("/get_authors_json", methods = ['GET', 'POST'])
@login_required_if_no_ano
def get_authors_json(): 
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.execute("select name from authors where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(r) for r in entries])
        return json_dumps

@app.route("/get_tags_json", methods = ['GET', 'POST'])
@login_required_if_no_ano
def get_tags_json(): 
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.execute("select name from tags where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(r) for r in entries])
        return json_dumps
        
@app.route("/get_series_json", methods = ['GET', 'POST'])
@login_required_if_no_ano
def get_series_json(): 
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.execute("select name from series where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(r) for r in entries])
        return json_dumps
        
@app.route("/get_matching_tags", methods = ['GET', 'POST'])
@login_required_if_no_ano
def get_matching_tags(): 
    tag_dict = {'tags': []}
    if request.method == "GET":
        q = db.session.query(db.Books)
        author_input = request.args.get('author_name')
        title_input = request.args.get('book_title')
        include_tag_inputs = request.args.getlist('include_tag')
        exclude_tag_inputs = request.args.getlist('exclude_tag')
        q = q.filter(db.Books.authors.any(db.Authors.name.like("%" +  author_input + "%")), db.Books.title.like("%"+title_input+"%"))
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
    random = db.session.query(db.Books).order_by(func.random()).limit(config.RANDOM_BOOKS)
    if page == 1:
        entries = db.session.query(db.Books).order_by(db.Books.last_modified.desc()).limit(config.NEWEST_BOOKS)
    else:
        off = int(int(config.NEWEST_BOOKS) * (page - 1))
        entries = db.session.query(db.Books).order_by(db.Books.last_modified.desc()).offset(off).limit(config.NEWEST_BOOKS)
    pagination = Pagination(page, config.NEWEST_BOOKS, len(db.session.query(db.Books).all()))
    return render_template('index.html', random=random, entries=entries, pagination=pagination, title="Latest Books")

@app.route("/hot", defaults={'page': 1})
@app.route('/hot/page/<int:page>')
@login_required_if_no_ano
def hot_books(page):
    random = db.session.query(db.Books).filter(false())
    off = int(int(6) * (page - 1))
    all_books = ub.session.query(ub.Downloads, ub.func.count(ub.Downloads.book_id)).order_by(ub.func.count(ub.Downloads.book_id).desc()).group_by(ub.Downloads.book_id)
    hot_books = all_books.offset(off).limit(config.NEWEST_BOOKS)
    entries = list()
    for book in hot_books:
        entries.append(db.session.query(db.Books).filter(db.Books.id == book.Downloads.book_id).first())
    numBooks = len(all_books.all())
    pages = int(ceil(numBooks / float(config.NEWEST_BOOKS)))
    if pages > 1:
        pagination = Pagination(page, config.NEWEST_BOOKS, len(all_books.all()))
        return render_template('index.html', random=random, entries=entries, pagination=pagination, title="Hot Books (most downloaded)")
    else:
        return render_template('index.html', random=random, entries=entries, title="Hot Books (most downloaded)")

@app.route("/stats")
@login_required
def stats():
    counter = len(db.session.query(db.Books).all())
    return render_template('stats.html', counter=counter, title="Statistics")

@app.route("/discover", defaults={'page': 1})
@app.route('/discover/page/<int:page>')
@login_required_if_no_ano
def discover(page):
    if page == 1:
        entries = db.session.query(db.Books).order_by(func.randomblob(2)).limit(config.NEWEST_BOOKS)
    else:
        off = int(int(config.NEWEST_BOOKS) * (page - 1))
        entries = db.session.query(db.Books).order_by(func.randomblob(2)).offset(off).limit(config.NEWEST_BOOKS)
    pagination = Pagination(page, config.NEWEST_BOOKS, len(db.session.query(db.Books).all()))
    return render_template('discover.html', entries=entries, pagination=pagination, title="Random Books")

@app.route("/book/<int:id>")
@login_required_if_no_ano
def show_book(id):
    entries = db.session.query(db.Books).filter(db.Books.id == id).first()
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    book_in_shelfs = []
    shelfs = ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == id).all()
    for entry in shelfs:
        book_in_shelfs.append(entry.shelf)
    return render_template('detail.html', entry=entries,  cc=cc, title=entries.title, books_shelfs=book_in_shelfs)

@app.route("/category")
@login_required_if_no_ano
def category_list():
    entries = db.session.query(db.Tags).order_by(db.Tags.name).all()
    return render_template('categories.html', entries=entries, title="Category list")

@app.route("/category/<name>")
@login_required_if_no_ano
def category(name):
    random = db.session.query(db.Books).filter(false())
    if name != "all":
        entries = db.session.query(db.Books).filter(db.Books.tags.any(db.Tags.name.like("%" +name + "%" ))).order_by(db.Books.last_modified.desc()).all()
    else:
        entries = db.session.query(db.Books).all()
    return render_template('index.html', random=random, entries=entries, title="Category: %s" % name)

@app.route("/series/<name>")
@login_required_if_no_ano
def series(name):
    random = db.session.query(db.Books).filter(false())
    entries = db.session.query(db.Books).filter(db.Books.series.any(db.Series.name.like("%" +name + "%" ))).order_by(db.Books.series_index).all()
    return render_template('index.html', random=random, entries=entries, title="Series: %s" % name)


@app.route("/admin/")
@login_required
def admin():
    #return "Admin ONLY!"
    abort(403)


@app.route("/search", methods=["GET"])
@login_required_if_no_ano
def search():
    term = request.args.get("query")
    if term:
        random = db.session.query(db.Books).order_by(func.random()).limit(config.RANDOM_BOOKS)
        entries = db.session.query(db.Books).filter(db.or_(db.Books.tags.any(db.Tags.name.like("%"+term+"%")),db.Books.series.any(db.Series.name.like("%"+term+"%")),db.Books.authors.any(db.Authors.name.like("%"+term+"%")),db.Books.title.like("%"+term+"%"))).all()
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
        author_name = request.args.get("author_name")
        book_title = request.args.get("book_title")
        if include_tag_inputs or exclude_tag_inputs or author_name or book_title:
            searchterm = []
            searchterm.extend((author_name, book_title))
            tag_names = db.session.query(db.Tags).filter(db.Tags.id.in_(include_tag_inputs)).all()
            searchterm.extend(tag.name for tag in tag_names)
            searchterm = " + ".join(filter(None, searchterm))
            q = q.filter(db.Books.authors.any(db.Authors.name.like("%" +  author_name + "%")), db.Books.title.like("%"+book_title+"%"))
            random = db.session.query(db.Books).order_by(func.random()).limit(config.RANDOM_BOOKS)
            for tag in include_tag_inputs:
                q = q.filter(db.Books.tags.any(db.Tags.id == tag))
            for tag in exclude_tag_inputs:
                q = q.filter(not_(db.Books.tags.any(db.Tags.id == tag)))
            q = q.all()
            return render_template('search.html', searchterm=searchterm, entries=q)
    tags = db.session.query(db.Tags).order_by(db.Tags.name).all()
    return render_template('search_form.html', tags=tags)

@app.route("/author")
@login_required_if_no_ano
def author_list():
    entries = db.session.query(db.Authors).order_by(db.Authors.sort).all()
    return render_template('authors.html', entries=entries, title="Author list")

@app.route("/author/<name>")
@login_required_if_no_ano
def author(name):
    random = db.session.query(db.Books).filter(false())
    entries = db.session.query(db.Books).filter(db.Books.authors.any(db.Authors.name.like("%" +  name + "%"))).all()
    return render_template('index.html', random=random, entries=entries, title="Author: %s" % name)

@app.route("/cover/<path:cover_path>")
@login_required_if_no_ano
def get_cover(cover_path):
    return send_from_directory(os.path.join(config.DB_ROOT, cover_path), "cover.jpg")

@app.route("/read/<int:book_id>")
@login_required
def read_book(book_id):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    book_dir = os.path.join(config.MAIN_DIR, "cps","static", str(book_id))
    if not os.path.exists(book_dir):
        os.mkdir(book_dir)
        for data in book.data:
            if data.format.lower() == "epub":
                epub_file = os.path.join(config.DB_ROOT, book.path, data.name) + ".epub"
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
                break
    return render_template('read.html', bookid=book_id, title="Read a Book")

@app.route("/download/<int:book_id>/<format>")
@login_required
@download_required
def get_download_link(book_id, format):
    format = format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == format.upper()).first()
    helper.update_download(book_id, int(current_user.id))
    author = helper.get_normalized_author(book.author_sort)
    file_name = book.title
    if len(author) > 0:
        file_name = author+'-'+file_name
    file_name = helper.get_valid_filename(file_name)
    response = make_response(send_from_directory(os.path.join(config.DB_ROOT, book.path), data.name + "." +format))
    response.headers["Content-Disposition"] = \
        "attachment; " \
        "filename={utf_filename}.{suffix};" \
        "filename*=UTF-8''{utf_filename}.{suffix}".format(
        utf_filename=file_name.encode('utf-8'),
        suffix=format
    )
    return response

@app.route('/register', methods = ['GET', 'POST'])
def register():
    error = None
    if not config.PUBLIC_REG:
        abort(404)
    if current_user is not None and current_user.is_authenticated():
        return redirect(url_for('index', _external=True))

    if request.method == "POST":
        to_save = request.form.to_dict()
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash("Please fill out all fields!", category="error")
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
                flash("An unknown error occured. Please try again later.", category="error")
                return render_template('register.html', title="register")
            flash("Your account has been created. Please login.", category="success")
            return redirect(url_for('login', _external=True))
        else:
            flash("This username or email address is already in use.", category="error")
            return render_template('register.html', title="register")

    return render_template('register.html', title="register")

@app.route('/login', methods = ['GET', 'POST'])
def login():
    error = None

    if current_user is not None and current_user.is_authenticated():
        return redirect(url_for('index', _external=True))

    if request.method == "POST":
        form = request.form.to_dict()
        user = ub.session.query(ub.User).filter(ub.User.nickname == form['username']).first()

        if user and check_password_hash(user.password, form['password']):
            login_user(user, remember = True)
            flash("you are now logged in as: '%s'" % user.nickname, category="success")
            return redirect(request.args.get("next") or url_for("index", _external=True))
        else:
            flash("Wrong Username or Password", category="error")

    return render_template('login.html', title="login")

@app.route('/logout')
@login_required
def logout():
    if current_user is not None and current_user.is_authenticated():
        logout_user()
    return redirect(request.args.get("next") or url_for("index", _external=True))


@app.route('/send/<int:book_id>')
@login_required
@download_required
def send_to_kindle(book_id):
    settings = ub.get_mail_settings()
    if settings.get("mail_server", "mail.example.com") == "mail.example.com":
        flash("Please configure the SMTP mail settings first...", category="error")
    elif current_user.kindle_mail:
        result = helper.send_mail(book_id, current_user.kindle_mail)
        if result is None:
            flash("Book successfully send to %s" % current_user.kindle_mail, category="success")
            helper.update_download(book_id, int(current_user.id))
        else:
            flash("There was an error sending this book: %s" % result, category="error")
    else:
        flash("Please configure your kindle email address first...", category="error")
    return redirect(request.environ["HTTP_REFERER"])

@app.route("/shelf/add/<int:shelf_id>/<int:book_id>")
@login_required
def add_to_shelf(shelf_id, book_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if not shelf.is_public and not shelf.user_id == int(current_user.id):
        flash("Sorry you are not allowed to add a book to the the shelf: %s" % shelf.name)
        return redirect(url_for('index', _external=True))

    ins = ub.BookShelf(shelf=shelf.id, book_id=book_id)
    ub.session.add(ins)
    ub.session.commit()

    flash("Book has been added to shelf: %s" % shelf.name, category="success")

    #return redirect(url_for('show_book', id=book_id))
    return redirect(request.environ["HTTP_REFERER"])

@app.route("/shelf/remove/<int:shelf_id>/<int:book_id>")
@login_required
def remove_from_shelf(shelf_id, book_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if not shelf.is_public and not shelf.user_id == int(current_user.id):
        flash("Sorry you are not allowed to remove a book from this shelf: %s" % shelf.name)
        return redirect(url_for('index', _external=True))

    book_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id, ub.BookShelf.book_id == book_id).first()

    #rem = ub.BookShelf(shelf=shelf.id, book_id=book_id)
    ub.session.delete(book_shelf)
    ub.session.commit()

    flash("Book has been removed from shelf: %s" % shelf.name, category="success")

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
        existing_shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.name == shelf.name).first()
        if existing_shelf:
            flash("A shelf with the name '%s' already exists." % to_save["title"], category="error")
        else:
            try:
                ub.session.add(shelf)
                ub.session.commit()
                flash("Shelf %s created" % to_save["title"], category="success")
            except:
                flash("There was an error", category="error")
        return render_template('shelf_edit.html', title="create a shelf")
    else:
        return render_template('shelf_edit.html', title="create a shelf")


@app.route("/shelf/<int:shelf_id>")
@login_required
def show_shelf(shelf_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.or_(ub.and_(ub.Shelf.user_id == int(current_user.id), ub.Shelf.id == shelf_id), ub.and_(ub.Shelf.is_public == 1, ub.Shelf.id == shelf_id))).first()
    result = list()
    if shelf:
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).all()
        for book in books_in_shelf:
            cur_book = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
            result.append(cur_book)

    return render_template('shelf.html', entries=result, title="Shelf: '%s'" % shelf.name)

@app.route("/me", methods = ["GET", "POST"])
@login_required
def profile():
    content = ub.session.query(ub.User).filter(ub.User.id == int(current_user.id)).first()
    downloads = list()
    for book in content.downloads:
        downloads.append(db.session.query(db.Books).filter(db.Books.id == book.book_id).first())
    if request.method == "POST":
        to_save = request.form.to_dict()
        if current_user.role_passwd() or current_user.role_admin():
            if to_save["password"]:
                content.password = generate_password_hash(to_save["password"])
        if to_save["kindle_mail"] and to_save["kindle_mail"] != content.kindle_mail:
            content.kindle_mail = to_save["kindle_mail"]
        if to_save["email"] and to_save["email"] != content.email:
            content.email = to_save["email"]
        try:
            ub.session.commit()
        except IntegrityError:
            ub.session.rollback()
            flash("Found an existing account for this email address.", category="error")
            return render_template("user_edit.html", content=content, downloads=downloads, title="%s's profile" % current_user.nickname)
        flash("Profile updated", category="success")
    return render_template("user_edit.html", profile=1, content=content, downloads=downloads, title="%s's profile" % current_user.nickname)

@app.route("/admin/user")
@login_required
@admin_required
def user_list():
    content = ub.session.query(ub.User).all()
    settings = ub.session.query(ub.Settings).first()
    return render_template("user_list.html", content=content, email=settings, title="User list")

@app.route("/admin/user/new", methods = ["GET", "POST"])
@login_required
@admin_required
def new_user():
    content = ub.User()
    if request.method == "POST":
        to_save = request.form.to_dict()
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash("Please fill out all fields!", category="error")
            return render_template("user_edit.html", new_user=1, content=content, title="Add new user")
        content.password = generate_password_hash(to_save["password"])
        content.nickname = to_save["nickname"]
        content.email = to_save["email"]
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
            flash("User '%s' created" % content.nickname, category="success")
            return redirect(url_for('user_list', _external=True))
        except IntegrityError:
            ub.session.rollback()
            flash("Found an existing account for this email address or nickname.", category="error")
    return render_template("user_edit.html", new_user=1, content=content, title="Add new user")

@app.route("/admin/user/mailsettings", methods = ["GET", "POST"])
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
        if "mail_use_ssl" in to_save:
            content.mail_use_ssl = 1
        else:
            content.mail_use_ssl = 0
        try:
            ub.session.commit()
            flash("Mail settings updated", category="success")
        except (e):
            flash(e, category="error")
    return render_template("email_edit.html", content=content, title="Edit mail settings")

@app.route("/admin/user/<int:user_id>", methods = ["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    content = ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()
    downloads = list()
    for book in content.downloads:
        downloads.append(db.session.query(db.Books).filter(db.Books.id == book.book_id).first())
    if request.method == "POST":
        to_save = request.form.to_dict()
        if "delete" in to_save:
            ub.session.delete(content)
            flash("User '%s' deleted" % content.nickname, category="success")
            return redirect(url_for('user_list', _external=True))
        else:
            if to_save["password"]:
                content.password = generate_password_hash(to_save["password"])
           
            if "admin_role" in to_save and not content.role_admin():
                content.role = content.role + ub.ROLE_ADMIN
            elif not "admin_role" in to_save and content.role_admin():
                content.role = content.role - ub.ROLE_ADMIN
            
            if "download_role" in to_save and not content.role_download():
                content.role = content.role + ub.ROLE_DOWNLOAD
            elif not "download_role" in to_save and content.role_download():
                content.role = content.role - ub.ROLE_DOWNLOAD
            
            if "upload_role" in to_save and not content.role_upload():
                content.role = content.role + ub.ROLE_UPLOAD
            elif not "upload_role" in to_save and content.role_upload():
                content.role = content.role - ub.ROLE_UPLOAD
            
            if "edit_role" in to_save and not content.role_edit():
                content.role = content.role + ub.ROLE_EDIT
            elif not "edit_role" in to_save and content.role_edit():
                content.role = content.role - ub.ROLE_EDIT
            
            if "passwd_role" in to_save and not content.role_passwd():
                content.role = content.role + ub.ROLE_PASSWD
            elif not "passwd_role" in to_save and content.role_passwd():
                content.role = content.role - ub.ROLE_PASSWD
           
            if to_save["email"] and to_save["email"] != content.email:
                content.email = to_save["email"]
            if to_save["kindle_mail"] and to_save["kindle_mail"] != content.kindle_mail:
                content.kindle_mail = to_save["kindle_mail"]
        try:
            ub.session.commit()
            flash("User '%s' updated" % content.nickname, category="success")
        except IntegrityError:
            ub.session.rollback()
            flash("An unknown error occured.", category="error")
    return render_template("user_edit.html", new_user=0, content=content, downloads=downloads, title="Edit User %s" % content.nickname)

@app.route("/admin/book/<int:book_id>", methods=['GET', 'POST'])
@login_required
@edit_required
def edit_book(book_id):
    ## create the function for sorting...
    db.session.connection().connection.connection.create_function("title_sort",1,db.title_sort)
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    author_names = []
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
        # 1. search for authors to remove
        del_authors = []
        for c_author in book.authors:
            found = False
            for inp_author in input_authors:
                if inp_author == c_author.name:
                    found = True
                    break;
            # if the author was not found in the new list, add him to remove list
            if not found:
                del_authors.append(c_author)
        # 2. search for authors that need to be added
        add_authors = []
        for inp_author in input_authors:
            found = False
            for c_author in book.authors:
                if inp_author == c_author.name:
                    found = True
                    break;
            if not found:
                add_authors.append(inp_author)
        # if there are authors to remove, we remove them now
        if len(del_authors) > 0:
            for del_author in del_authors:
                book.authors.remove(del_author)
                authors_books_count = db.session.query(db.Books).filter(db.Books.authors.any(db.Authors.id.is_(del_author.id))).count()
                if authors_books_count == 0:
                    db.session.query(db.Authors).filter(db.Authors.id == del_author.id).delete()
        # if there are authors to add, we add them now!
        if len(add_authors) > 0:
            for add_author in add_authors:
                # check if an author with that name exists
                t_author = db.session.query(db.Authors).filter(db.Authors.name == add_author).first()
                # if no author is found add it
                if t_author == None:
                    new_author = db.Authors(add_author, add_author, "")
                    db.session.add(new_author)
                    t_author = db.session.query(db.Authors).filter(db.Authors.name == add_author).first()
                # add author to book
                book.authors.append(t_author)       
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
        input_tags = [x for x in input_tags if x != '']
        # we have all author names now
        # 1. search for tags to remove
        del_tags = []
        for c_tag in book.tags:
            found = False
            for inp_tag in input_tags:
                if inp_tag == c_tag.name:
                    found = True
                    break;
            # if the tag was not found in the new list, add him to remove list
            if not found:
                del_tags.append(c_tag)
        # 2. search for tags that need to be added
        add_tags = []
        for inp_tag in input_tags:
            found = False
            for c_tag in book.tags:
                if inp_tag == c_tag.name:
                    found = True
                    break;
            if not found:
                add_tags.append(inp_tag)
        # if there are tags to remove, we remove them now
        if len(del_tags) > 0:
            for del_tag in del_tags:
                book.tags.remove(del_tag)
                if len(del_tag.books) == 0:
                    db.session.delete(del_tag)
        # if there are tags to add, we add them now!
        if len(add_tags) > 0:
            for add_tag in add_tags:
                # check if a tag with that name exists
                new_tag = db.session.query(db.Tags).filter(db.Tags.name == add_tag).first()
                # if no tag is found add it
                if new_tag == None:
                    new_tag = db.Tags(add_tag)
                    db.session.add(new_tag)
                    new_tag = db.session.query(db.Tags).filter(db.Tags.name == add_tag).first()
                # add tag to book
                book.tags.append(new_tag)
        
        if to_save["series"].strip():
            is_series = db.session.query(db.Series).filter(db.Series.name.like('%' + to_save["series"].strip() + '%')).first()
            if is_series:
                book.series.append(is_series)
            else:
                new_series = db.Series(name=to_save["series"].strip(), sort=to_save["series"].strip())
                book.series.append(new_series)
        
        if to_save["rating"].strip():
            old_rating = False
            if len(book.ratings) > 0:
                old_rating = book.ratings[0].rating
            ratingx2 = int(float(to_save["rating"]) *2)
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
                    if c.datatype == 'rating':
                        to_save[cc_string] = str(int(float(to_save[cc_string]) *2))
                    if to_save[cc_string].strip() != cc_db_value:
                        if cc_db_value != None:
                            #remove old cc_val
                            del_cc = getattr(book, cc_string)[0]
                            getattr(book, cc_string).remove(del_cc)
                            if len(del_cc.books) == 0:
                                db.session.delete(del_cc)
                        cc_class = db.cc_classes[c.id]
                        new_cc = db.session.query(cc_class).filter(cc_class.value == to_save[cc_string].strip()).first()
                        # if no cc val is found add it
                        if new_cc == None:
                            new_cc = cc_class(value=to_save[cc_string].strip())
                            db.session.add(new_cc)
                            new_cc = db.session.query(cc_class).filter(cc_class.value == to_save[cc_string].strip()).first()
                        # add cc value to book
                        getattr(book, cc_string).append(new_cc)
                else:
                    if cc_db_value != None:
                        #remove old cc_val
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
                            break;
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
                            break;
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
                        new_tag = db.session.query(db.cc_classes[c.id]).filter(db.cc_classes[c.id].value == add_tag).first()
                        # if no tag is found add it
                        if new_tag == None:
                            new_tag = db.cc_classes[c.id](value=add_tag)
                            db.session.add(new_tag)
                            new_tag = db.session.query(db.cc_classes[c.id]).filter(db.cc_classes[c.id].value == add_tag).first()
                        # add tag to book
                        getattr(book, cc_string).append(new_tag)

        db.session.commit()
        author_names = []
        for author in book.authors:
            author_names.append(author.name)
        for b in edited_books_id:
            helper.update_dir_stucture(b)
        if "detail_view" in to_save:
            return redirect(url_for('show_book', id=book.id, _external=True))
        else:
            return render_template('edit_book.html', book=book, authors=author_names, cc=cc)
    else:
        return render_template('edit_book.html', book=book, authors=author_names, cc=cc)

import uploader
from shutil import move

@app.route("/upload", methods = ["GET", "POST"])
@login_required
@upload_required
def upload():
    if not config.UPLOADING:
        abort(404)
    ## create the function for sorting...
    db.session.connection().connection.connection.create_function("title_sort",1,db.title_sort)
    db.session.connection().connection.connection.create_function('uuid4', 0, lambda : str(uuid4()))
    if request.method == 'POST' and 'btn-upload' in request.files:
        file = request.files['btn-upload']
        meta = uploader.upload(file)

        title = meta.title
        author = meta.author

        title_dir = helper.get_valid_filename(title.decode('utf-8'), False)
        author_dir = helper.get_valid_filename(author.decode('utf-8'), False)
        data_name = title_dir
        filepath = config.DB_ROOT + "/" + author_dir + "/" + title_dir
        saved_filename = filepath + "/" + data_name + meta.extension
        if not os.path.exists(filepath):
            try:
                os.makedirs(filepath)
            except OSError:
                flash("Failed to create path %s (Permission denied)." % filepath, category="error")
                return redirect(url_for('index', _external=True))
        try:
            move(meta.file_path, saved_filename)
        except OSError:
            flash("Failed to store file %s (Permission denied)." % saved_filename, category="error")
            return redirect(url_for('index', _external=True))

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
        db_book = db.Books(title, "", "", datetime.datetime.now(), datetime.datetime(101, 01,01), 1, datetime.datetime.now(), path, has_cover, db_author, [])
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
    return render_template('detail.html', entry=db_book,  cc=cc, title=db_book.title, books_shelfs=book_in_shelfs)
