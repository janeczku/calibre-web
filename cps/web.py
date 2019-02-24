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

from cps import mimetypes, global_WorkerThread, searched_ids
from flask import render_template, request, redirect, url_for, send_from_directory, make_response, g, flash, abort
from werkzeug.exceptions import default_exceptions
import helper
import os
from sqlalchemy.exc import IntegrityError
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import gettext as _
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.datastructures import Headers
from babel import Locale as LC
from babel.dates import format_date
from babel.core import UnknownLocaleError
import base64
from sqlalchemy.sql import *
import json
import datetime
from iso639 import languages as isoLanguages
import re
import gdriveutils
from redirect import redirect_back
from cps import lm, babel, ub, config, get_locale, language_table, app, db
from pagination import Pagination
from sqlalchemy.sql.expression import text

feature_support = dict()
try:
    from oauth_bb import oauth_check, register_user_with_oauth, logout_oauth_user, get_oauth_status
    feature_support['oauth'] = True
except ImportError:
    feature_support['oauth'] = False
    oauth_check = {}

try:
    import ldap
    feature_support['ldap'] = True
except ImportError:
    feature_support['ldap'] = False

try:
    from googleapiclient.errors import HttpError
except ImportError:
    pass

try:
    from goodreads.client import GoodreadsClient
    feature_support['goodreads'] = True
except ImportError:
    feature_support['goodreads'] = False

try:
    import Levenshtein
    feature_support['levenshtein'] = True
except ImportError:
    feature_support['levenshtein'] = False

try:
    from functools import reduce, wraps
except ImportError:
    pass  # We're not using Python 3

try:
    import rarfile
    feature_support['rar'] = True
except ImportError:
    feature_support['rar'] = False

try:
    from natsort import natsorted as sort
except ImportError:
    sort = sorted # Just use regular sort then, may cause issues with badly named pages in cbz/cbr files

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

from flask import Blueprint

# Global variables

EXTENSIONS_AUDIO = {'mp3', 'm4a', 'm4b'}

'''EXTENSIONS_READER = set(['txt', 'pdf', 'epub', 'zip', 'cbz', 'tar', 'cbt'] + 
                        (['rar','cbr'] if feature_support['rar'] else []))'''


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



web = Blueprint('web', __name__)


@lm.user_loader
def load_user(user_id):
    try:
        return ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()
    except Exception as e:
        print(e)


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

# checks if domain is in database (including wildcards)
# example SELECT * FROM @TABLE WHERE  'abcdefg' LIKE Name;
# from https://code.luasoftware.com/tutorials/flask/execute-raw-sql-in-flask-sqlalchemy/
def check_valid_domain(domain_text):
    domain_text = domain_text.split('@', 1)[-1].lower()
    sql = "SELECT * FROM registration WHERE :domain LIKE domain;"
    result = ub.session.query(ub.Registration).from_statement(text(sql)).params(domain=domain_text).all()
    return len(result)


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
                            len(db.session.query(database).filter(db_filter).filter(common_filters()).all()))
    entries = db.session.query(database).join(*join, isouter=True).filter(db_filter).filter(common_filters()).\
        order_by(*order).offset(off).limit(config.config_books_per_page).all()
    for book in entries:
        book = order_authors(book)
    return entries, randm, pagination


# read search results from calibre-database and return it (function is used for feed and simple search
def get_search_results(term):
    q = list()
    authorterms = re.split("[, ]+", term)
    for authorterm in authorterms:
        q.append(db.Books.authors.any(db.Authors.name.ilike("%" + authorterm + "%")))
    db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
    db.Books.authors.any(db.Authors.name.ilike("%" + term + "%"))

    return db.session.query(db.Books).filter(common_filters()).filter(
        db.or_(db.Books.tags.any(db.Tags.name.ilike("%" + term + "%")),
               db.Books.series.any(db.Series.name.ilike("%" + term + "%")),
               db.Books.authors.any(and_(*q)),
               db.Books.publishers.any(db.Publishers.name.ilike("%" + term + "%")),
               db.Books.title.ilike("%" + term + "%"))).all()


# Returns the template for rendering and includes the instance name
def render_title_template(*args, **kwargs):
    return render_template(instance=config.config_calibre_web_title, *args, **kwargs)


@web.before_app_request
def before_request():
    g.user = current_user
    g.allow_registration = config.config_public_reg
    g.allow_upload = config.config_uploading
    g.current_theme = config.config_theme
    g.public_shelfes = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1).order_by(ub.Shelf.name).all()
    if not config.db_configured and request.endpoint not in ('admin.basic_configuration', 'login') and '/static/' not in request.path:
        return redirect(url_for('admin.basic_configuration'))


@web.route("/ajax/emailstat")
@login_required
def get_email_status_json():
    tasks = global_WorkerThread.get_taskstatus()
    answer = helper.render_task_status(tasks)
    js = json.dumps(answer, default=helper.json_serial)
    response = make_response(js)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


'''
@web.route("/ajax/getcomic/<int:book_id>/<book_format>/<int:page>")
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
                    if feature_support['rar'] == True:
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


@web.route("/get_authors_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_authors_json():
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.query(db.Authors).filter(db.Authors.name.ilike("%" + query + "%")).all()
        json_dumps = json.dumps([dict(name=r.name.replace('|', ',')) for r in entries])
        return json_dumps


@web.route("/get_publishers_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_publishers_json():
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.query(db.Publishers).filter(db.Publishers.name.ilike("%" + query + "%")).all()
        json_dumps = json.dumps([dict(name=r.name.replace('|', ',')) for r in entries])
        return json_dumps


@web.route("/get_tags_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_tags_json():
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.query(db.Tags).filter(db.Tags.name.ilike("%" + query + "%")).all()
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@web.route("/get_languages_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_languages_json():
    if request.method == "GET":
        query = request.args.get('q').lower()
        # languages = speaking_language()
        languages = language_table[get_locale()]
        entries_start = [s for key, s in languages.items() if s.lower().startswith(query.lower())]
        if len(entries_start) < 5:
            entries = [s for key, s in languages.items() if query in s.lower()]
            entries_start.extend(entries[0:(5-len(entries_start))])
            entries_start = list(set(entries_start))
        json_dumps = json.dumps([dict(name=r) for r in entries_start[0:5]])
        return json_dumps


@web.route("/get_series_json", methods=['GET', 'POST'])
@login_required_if_no_ano
def get_series_json():
    if request.method == "GET":
        query = request.args.get('q')
        entries = db.session.query(db.Series).filter(db.Series.name.ilike("%" + query + "%")).all()
        # entries = db.session.execute("select name from series where name like '%" + query + "%'")
        json_dumps = json.dumps([dict(name=r.name) for r in entries])
        return json_dumps


@web.route("/get_matching_tags", methods=['GET', 'POST'])
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


@web.route("/", defaults={'page': 1})
@web.route('/page/<int:page>')
@login_required_if_no_ano
def index(page):
    entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.timestamp.desc()])
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Recently Added Books"), page="root")


@web.route('/books/newest', defaults={'page': 1})
@web.route('/books/newest/page/<int:page>')
@login_required_if_no_ano
def newest_books(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.pubdate.desc()])
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Newest Books"), page="newest")
    else:
        abort(404)


@web.route('/books/oldest', defaults={'page': 1})
@web.route('/books/oldest/page/<int:page>')
@login_required_if_no_ano
def oldest_books(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.pubdate])
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Oldest Books"), page="oldest")
    else:
        abort(404)


@web.route('/books/a-z', defaults={'page': 1})
@web.route('/books/a-z/page/<int:page>')
@login_required_if_no_ano
def titles_ascending(page):
    if current_user.show_sorted():
        entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.sort])
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Books (A-Z)"), page="a-z")
    else:
        abort(404)


@web.route('/books/z-a', defaults={'page': 1})
@web.route('/books/z-a/page/<int:page>')
@login_required_if_no_ano
def titles_descending(page):
    entries, random, pagination = fill_indexpage(page, db.Books, True, [db.Books.sort.desc()])
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Books (Z-A)"), page="z-a")


@web.route("/hot", defaults={'page': 1})
@web.route('/hot/page/<int:page>')
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


@web.route("/rated", defaults={'page': 1})
@web.route('/rated/page/<int:page>')
@login_required_if_no_ano
def best_rated_books(page):
    if current_user.show_best_rated_books():
        entries, random, pagination = fill_indexpage(page, db.Books, db.Books.ratings.any(db.Ratings.rating > 9),
                                                     [db.Books.timestamp.desc()])
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Best rated books"), page="rated")
    else:
        abort(404)


@web.route("/discover", defaults={'page': 1})
@web.route('/discover/page/<int:page>')
@login_required_if_no_ano
def discover(page):
    if current_user.show_random_books():
        entries, __, pagination = fill_indexpage(page, db.Books, True, [func.randomblob(2)])
        pagination = Pagination(1, config.config_books_per_page, config.config_books_per_page)
        return render_title_template('discover.html', entries=entries, pagination=pagination,
                                     title=_(u"Random Books"), page="discover")
    else:
        abort(404)


@web.route("/author")
@login_required_if_no_ano
def author_list():
    if current_user.show_author():
        entries = db.session.query(db.Authors, func.count('books_authors_link.book').label('count'))\
            .join(db.books_authors_link).join(db.Books).filter(common_filters())\
            .group_by('books_authors_link.author').order_by(db.Authors.sort).all()
        for entry in entries:
            entry.Authors.name = entry.Authors.name.replace('|', ',')
        return render_title_template('list.html', entries=entries, folder='web.author',
                                     title=u"Author list", page="authorlist")
    else:
        abort(404)


@web.route("/author/<int:book_id>", defaults={'page': 1})
@web.route("/author/<int:book_id>/<int:page>")
@login_required_if_no_ano
def author(book_id, page):
    entries, __, pagination = fill_indexpage(page, db.Books, db.Books.authors.any(db.Authors.id == book_id),
                                             [db.Series.name, db.Books.series_index], db.books_series_link, db.Series)
    if entries is None:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("web.index"))

    name = db.session.query(db.Authors).filter(db.Authors.id == book_id).first().name.replace('|', ',')

    author_info = None
    other_books = []
    if feature_support['goodreads'] and config.config_use_goodreads:
        try:
            gc = GoodreadsClient(config.config_goodreads_api_key, config.config_goodreads_api_secret)
            author_info = gc.find_author(author_name=name)
            other_books = get_unique_other_books(entries.all(), author_info.books)
        except Exception:
            # Skip goodreads, if site is down/inaccessible
            app.logger.error('Goodreads website is down/inaccessible')

    return render_title_template('author.html', entries=entries, pagination=pagination,
                                 title=name, author=author_info, other_books=other_books, page="author")


@web.route("/publisher")
@login_required_if_no_ano
def publisher_list():
    if current_user.show_publisher():
        entries = db.session.query(db.Publishers, func.count('books_publishers_link.book').label('count'))\
            .join(db.books_publishers_link).join(db.Books).filter(common_filters())\
            .group_by('books_publishers_link.publisher').order_by(db.Publishers.sort).all()
        return render_title_template('list.html', entries=entries, folder='web.publisher',
                                     title=_(u"Publisher list"), page="publisherlist")
    else:
        abort(404)


@web.route("/publisher/<int:book_id>", defaults={'page': 1})
@web.route('/publisher/<int:book_id>/<int:page>')
@login_required_if_no_ano
def publisher(book_id, page):
    publisher = db.session.query(db.Publishers).filter(db.Publishers.id == book_id).first()
    if publisher:
        entries, random, pagination = fill_indexpage(page, db.Books,
                                                     db.Books.publishers.any(db.Publishers.id == book_id),
                                                     (db.Series.name, db.Books.series_index), db.books_series_link,
                                                     db.Series)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Publisher: %(name)s", name=publisher.name), page="publisher")
    else:
        abort(404)


def get_unique_other_books(library_books, author_books):
    # Get all identifiers (ISBN, Goodreads, etc) and filter author's books by that list so we show fewer duplicates
    # Note: Not all images will be shown, even though they're available on Goodreads.com.
    #       See https://www.goodreads.com/topic/show/18213769-goodreads-book-images
    identifiers = reduce(lambda acc, book: acc + map(lambda identifier: identifier.val, book.identifiers),
                         library_books, [])
    other_books = filter(lambda book: book.isbn not in identifiers and book.gid["#text"] not in identifiers,
                         author_books)

    # Fuzzy match book titles
    if feature_support['levenshtein']:
        library_titles = reduce(lambda acc, book: acc + [book.title], library_books, [])
        other_books = filter(lambda author_book: not filter(
            lambda library_book:
            # Remove items in parentheses before comparing
            Levenshtein.ratio(re.sub(r"\(.*\)", "", author_book.title), library_book) > 0.7,
            library_titles
        ), other_books)

    return other_books


@web.route("/series")
@login_required_if_no_ano
def series_list():
    if current_user.show_series():
        entries = db.session.query(db.Series, func.count('books_series_link.book').label('count'))\
            .join(db.books_series_link).join(db.Books).filter(common_filters())\
            .group_by('books_series_link.series').order_by(db.Series.sort).all()
        return render_title_template('list.html', entries=entries, folder='web.series',
                                     title=_(u"Series list"), page="serieslist")
    else:
        abort(404)


@web.route("/series/<int:book_id>/", defaults={'page': 1})
@web.route("/series/<int:book_id>/<int:page>")
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


@web.route("/language")
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
            'books_languages_link.lang_code').all()
        return render_title_template('languages.html', languages=languages, lang_counter=lang_counter,
                                     title=_(u"Available languages"), page="langlist")
    else:
        abort(404)


@web.route("/language/<name>", defaults={'page': 1})
@web.route('/language/<name>/page/<int:page>')
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


@web.route("/category")
@login_required_if_no_ano
def category_list():
    if current_user.show_category():
        entries = db.session.query(db.Tags, func.count('books_tags_link.book').label('count'))\
            .join(db.books_tags_link).join(db.Books).order_by(db.Tags.name).filter(common_filters())\
            .group_by('books_tags_link.tag').all()
        return render_title_template('list.html', entries=entries, folder='web.category',
                                     title=_(u"Category list"), page="catlist")
    else:
        abort(404)


@web.route("/category/<int:book_id>", defaults={'page': 1})
@web.route('/category/<int:book_id>/<int:page>')
@login_required_if_no_ano
def category(book_id, page):
    name = db.session.query(db.Tags).filter(db.Tags.id == book_id).first()
    if name:
        entries, random, pagination = fill_indexpage(page, db.Books, db.Books.tags.any(db.Tags.id == book_id),
                                                     (db.Series.name, db.Books.series_index),db.books_series_link,
                                                     db.Series)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=_(u"Category: %(name)s", name=name.name), page="category")
    else:
        abort(404)


@web.route("/ajax/toggleread/<int:book_id>", methods=['POST'])
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


@web.route("/book/<int:book_id>")
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
                matching_have_read_book = ub.session.query(ub.ReadBook).\
                    filter(ub.and_(ub.ReadBook.user_id == int(current_user.id), ub.ReadBook.book_id == book_id)).all()
                have_read = len(matching_have_read_book) > 0 and matching_have_read_book[0].is_read
            else:
                try:
                    matching_have_read_book = getattr(entries, 'custom_column_'+str(config.config_read_column))
                    have_read = len(matching_have_read_book) > 0 and matching_have_read_book[0].value
                except KeyError:
                    app.logger.error(
                        u"Custom Column No.%d is not exisiting in calibre database" % config.config_read_column)
                    have_read = None

        else:
            have_read = None

        entries.tags = sort(entries.tags, key=lambda tag: tag.name)

        entries = order_authors(entries)

        kindle_list = helper.check_send_to_kindle(entries)
        reader_list = helper.check_read_formats(entries)

        audioentries = []
        for media_format in entries.data:
            if media_format.format.lower() in EXTENSIONS_AUDIO:
                audioentries.append(media_format.format.lower())

        return render_title_template('detail.html', entry=entries, audioentries=audioentries, cc=cc,
                                     is_xhr=request.is_xhr, title=entries.title, books_shelfs=book_in_shelfs,
                                     have_read=have_read, kindle_list=kindle_list, reader_list=reader_list, page="book")
    else:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("web.index"))


@web.route("/ajax/bookmark/<int:book_id>/<book_format>", methods=['POST'])
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


@web.route("/tasks")
@login_required
def get_tasks_status():
    # if current user admin, show all email, otherwise only own emails
    tasks = global_WorkerThread.get_taskstatus()
    # UIanswer = copy.deepcopy(answer)
    answer = helper.render_task_status(tasks)
    # foreach row format row
    return render_title_template('tasks.html', entries=answer, title=_(u"Tasks"), page="tasks")


@web.route("/search", methods=["GET"])
@login_required_if_no_ano
def search():
    term = request.args.get("query").strip().lower()
    if term:
        entries = get_search_results(term)
        ids = list()
        for element in entries:
            ids.append(element.id)
        searched_ids[current_user.id] = ids
        return render_title_template('search.html', searchterm=term, entries=entries, page="search")
    else:
        return render_title_template('search.html', searchterm="", page="search")


@web.route("/advanced_search", methods=['GET'])
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
    if author_name:
        author_name = author_name.strip().lower().replace(',','|')
    if book_title:
        book_title = book_title.strip().lower()
    if publisher:
        publisher = publisher.strip().lower()

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
        searchterm.extend((author_name.replace('|', ','), book_title, publisher))
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
            q = q.filter(db.Books.authors.any(db.Authors.name.ilike("%" + author_name + "%")))
        if book_title:
            q = q.filter(db.Books.title.ilike("%" + book_title + "%"))
        if pub_start:
            q = q.filter(db.Books.pubdate >= pub_start)
        if pub_end:
            q = q.filter(db.Books.pubdate <= pub_end)
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
        if rating_high:
            rating_high = int(rating_high) * 2
            q = q.filter(db.Books.ratings.any(db.Ratings.rating <= rating_high))
        if rating_low:
            rating_low = int(rating_low) * 2
            q = q.filter(db.Books.ratings.any(db.Ratings.rating >= rating_low))
        if description:
            q = q.filter(db.Books.comments.any(db.Comments.text.ilike("%" + description + "%")))

        # search custom culumns
        for c in cc:
            custom_query = request.args.get('custom_column_' + str(c.id))
            if custom_query:
                if c.datatype == 'bool':
                    getattr(db.Books, 'custom_column_1')
                    q = q.filter(getattr(db.Books, 'custom_column_'+str(c.id)).any(
                        db.cc_classes[c.id].value == (custom_query == "True")))
                elif c.datatype == 'int':
                    q = q.filter(getattr(db.Books, 'custom_column_'+str(c.id)).any(
                        db.cc_classes[c.id].value == custom_query))
                else:
                    q = q.filter(getattr(db.Books, 'custom_column_'+str(c.id)).any(
                        db.cc_classes[c.id].value.ilike("%" + custom_query + "%")))
        q = q.all()
        ids = list()
        for element in q:
            ids.append(element.id)
        searched_ids[current_user.id] = ids
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


@web.route("/cover/<int:book_id>")
@login_required_if_no_ano
def get_cover(book_id):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    return helper.get_book_cover(book.path)


@web.route("/show/<book_id>/<book_format>")
@login_required_if_no_ano
def serve_book(book_id, book_format):
    book_format = book_format.split(".")[0]
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == book_format.upper())\
        .first()
    app.logger.info('Serving book: %s', data.name)
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


@web.route("/unreadbooks/", defaults={'page': 1})
@web.route("/unreadbooks/<int:page>'")
@login_required_if_no_ano
def unread_books(page):
    return render_read_books(page, False)


@web.route("/readbooks/", defaults={'page': 1})
@web.route("/readbooks/<int:page>'")
@login_required_if_no_ano
def read_books(page):
    return render_read_books(page, True)


def render_read_books(page, are_read, as_xml=False):
    if not config.config_read_column:
        readBooks = ub.session.query(ub.ReadBook).filter(ub.ReadBook.user_id == int(current_user.id))\
            .filter(ub.ReadBook.is_read is True).all()
        readBookIds = [x.book_id for x in readBooks]
    else:
        try:
            readBooks = db.session.query(db.cc_classes[config.config_read_column])\
                .filter(db.cc_classes[config.config_read_column].value is True).all()
            readBookIds = [x.book for x in readBooks]
        except KeyError:
            app.logger.error(u"Custom Column No.%d is not existing in calibre database" % config.config_read_column)
            readBookIds = []

    if are_read:
        db_filter = db.Books.id.in_(readBookIds)
    else:
        db_filter = ~db.Books.id.in_(readBookIds)

    entries, random, pagination = fill_indexpage(page, db.Books, db_filter, [db.Books.timestamp.desc()])

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


@web.route("/read/<int:book_id>/<book_format>")
@login_required_if_no_ano
def read_book(book_id, book_format):
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    if not book:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible:"), category="error")
        return redirect(url_for("web.index"))

    # check if book was downloaded before
    bookmark = None
    if current_user.is_authenticated:
        bookmark = ub.session.query(ub.Bookmark).filter(ub.and_(ub.Bookmark.user_id == int(current_user.id),
                                                                ub.Bookmark.book_id == book_id,
                                                                ub.Bookmark.format == book_format.upper())).first()
    if book_format.lower() == "epub":
        return render_title_template('read.html', bookid=book_id, title=_(u"Read a Book"), bookmark=bookmark)
    elif book_format.lower() == "pdf":
        return render_title_template('readpdf.html', pdffile=book_id, title=_(u"Read a Book"))
    elif book_format.lower() == "txt":
        return render_title_template('readtxt.html', txtfile=book_id, title=_(u"Read a Book"))
    elif book_format.lower() == "mp3":
        entries = db.session.query(db.Books).filter(db.Books.id == book_id).filter(common_filters()).first()
        return render_title_template('listenmp3.html', mp3file=book_id, audioformat=book_format.lower(),
                                     title=_(u"Read a Book"), entry=entries, bookmark=bookmark)
    elif book_format.lower() == "m4b":
        entries = db.session.query(db.Books).filter(db.Books.id == book_id).filter(common_filters()).first()
        return render_title_template('listenmp3.html', mp3file=book_id, audioformat=book_format.lower(),
                                     title=_(u"Read a Book"), entry=entries, bookmark=bookmark)
    elif book_format.lower() == "m4a":
        entries = db.session.query(db.Books).filter(db.Books.id == book_id).filter(common_filters()).first()
        return render_title_template('listenmp3.html', mp3file=book_id, audioformat=book_format.lower(),
                                     title=_(u"Read a Book"), entry=entries, bookmark=bookmark)
    else:
        book_dir = os.path.join(config.get_main_dir, "cps", "static", str(book_id))
        if not os.path.exists(book_dir):
            os.mkdir(book_dir)
        for fileext in ["cbr", "cbt", "cbz"]:
            if book_format.lower() == fileext:
                all_name = str(book_id)  # + "/" + book.data[0].name + "." + fileext
                # tmp_file = os.path.join(book_dir, book.data[0].name) + "." + fileext
                # if not os.path.exists(all_name):
                #    cbr_file = os.path.join(config.config_calibre_dir, book.path, book.data[0].name) + "." + fileext
                #    copyfile(cbr_file, tmp_file)
                return render_title_template('readcbr.html', comicfile=all_name, title=_(u"Read a Book"),
                                             extension=fileext)
        '''if feature_support['rar']:
            extensionList = ["cbr","cbt","cbz"]
        else:
            extensionList = ["cbt","cbz"]
        for fileext in extensionList:
            if book_format.lower() == fileext:
                return render_title_template('readcbr.html', comicfile=book_id, 
                extension=fileext, title=_(u"Read a Book"), book=book)
        flash(_(u"Error opening eBook. File does not exist or file is not accessible."), category="error")
        return redirect(url_for("web.index"))'''


@web.route("/download/<int:book_id>/<book_format>")
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


@web.route("/download/<int:book_id>/<book_format>/<anyname>")
@login_required_if_no_ano
@download_required
def get_download_link_ext(book_id, book_format, anyname):
    return get_download_link(book_id, book_format)


@web.route('/register', methods=['GET', 'POST'])
def register():
    if not config.config_public_reg:
        abort(404)
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('web.index'))

    if request.method == "POST":
        to_save = request.form.to_dict()
        if not to_save["nickname"] or not to_save["email"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template('register.html', title=_(u"register"), page="register")

        existing_user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == to_save["nickname"]
                                                         .lower()).first()
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
                    if feature_support['oauth']:
                        register_user_with_oauth(content)
                    helper.send_registration_mail(to_save["email"], to_save["nickname"], password)
                except Exception:
                    ub.session.rollback()
                    flash(_(u"An unknown error occurred. Please try again later."), category="error")
                    return render_title_template('register.html', title=_(u"register"), page="register")
            else:
                flash(_(u"Your e-mail is not allowed to register"), category="error")
                app.logger.info('Registering failed for user "' + to_save['nickname'] + '" e-mail adress: ' +
                                to_save["email"])
                return render_title_template('register.html', title=_(u"register"), page="register")
            flash(_(u"Confirmation e-mail was send to your e-mail account."), category="success")
            return redirect(url_for('web.login'))
        else:
            flash(_(u"This username or e-mail address is already in use."), category="error")
            return render_title_template('register.html', title=_(u"register"), page="register")

    if feature_support['oauth']:
        register_user_with_oauth()
    return render_title_template('register.html', config=config, title=_(u"register"), page="register")


@web.route('/login', methods=['GET', 'POST'])
def login():
    if not config.db_configured:
        return redirect(url_for('admin.basic_configuration'))
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('web.index'))
    if request.method == "POST":
        form = request.form.to_dict()
        user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == form['username'].strip().lower())\
            .first()
        if config.config_login_type == 1 and user:
            try:
                ub.User.try_login(form['username'], form['password'], config.config_ldap_dn,
                                  config.config_ldap_provider_url)
                login_user(user, remember=True)
                flash(_(u"You are now logged in as: '%(nickname)s'", nickname=user.nickname), category="success")
                return redirect_back(url_for("web.index"))
            except ldap.INVALID_CREDENTIALS:
                ipAdress = request.headers.get('X-Forwarded-For', request.remote_addr)
                app.logger.info('LDAP Login failed for user "' + form['username'] + '" IP-adress: ' + ipAdress)
                flash(_(u"Wrong Username or Password"), category="error")
            except ldap.SERVER_DOWN:
                app.logger.info('LDAP Login failed, LDAP Server down')
                flash(_(u"Could not login. LDAP server down, please contact your administrator"), category="error")
        else:
            if user and check_password_hash(user.password, form['password']) and user.nickname is not "Guest":
                login_user(user, remember=True)
                flash(_(u"You are now logged in as: '%(nickname)s'", nickname=user.nickname), category="success")
                return redirect_back(url_for("web.index"))
            else:
                ipAdress = request.headers.get('X-Forwarded-For', request.remote_addr)
                app.logger.info('Login failed for user "' + form['username'] + '" IP-adress: ' + ipAdress)
                flash(_(u"Wrong Username or Password"), category="error")

    # next_url = request.args.get('next')
    # if next_url is None or not is_safe_url(next_url):
    next_url = url_for('web.index')

    return render_title_template('login.html', title=_(u"login"), next_url=next_url, config=config, page="login")


@web.route('/logout')
@login_required
def logout():
    if current_user is not None and current_user.is_authenticated:
        logout_user()
        if feature_support['oauth']:
            logout_oauth_user()
    return redirect(url_for('web.login'))


@web.route('/remote/login')
@remote_login_required
def remote_login():
    auth_token = ub.RemoteAuthToken()
    ub.session.add(auth_token)
    ub.session.commit()

    verify_url = url_for('web.verify_token', token=auth_token.auth_token, _external=true)

    return render_title_template('remote_login.html', title=_(u"login"), token=auth_token.auth_token,
                                 verify_url=verify_url, page="remotelogin")


@web.route('/verify/<token>')
@remote_login_required
@login_required
def verify_token(token):
    auth_token = ub.session.query(ub.RemoteAuthToken).filter(ub.RemoteAuthToken.auth_token == token).first()

    # Token not found
    if auth_token is None:
        flash(_(u"Token not found"), category="error")
        return redirect(url_for('web.index'))

    # Token expired
    if datetime.datetime.now() > auth_token.expiration:
        ub.session.delete(auth_token)
        ub.session.commit()

        flash(_(u"Token has expired"), category="error")
        return redirect(url_for('web.index'))

    # Update token with user information
    auth_token.user_id = current_user.id
    auth_token.verified = True
    ub.session.commit()

    flash(_(u"Success! Please return to your device"), category="success")
    return redirect(url_for('web.index'))


@web.route('/ajax/verify_token', methods=['POST'])
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


@web.route('/send/<int:book_id>/<book_format>/<int:convert>')
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


@web.route("/me", methods=["GET", "POST"])
@login_required
def profile():
    content = ub.session.query(ub.User).filter(ub.User.id == int(current_user.id)).first()
    downloads = list()
    languages = speaking_language()
    translations = babel.list_translations() + [LC('en')]
    if feature_support['oauth']:
        oauth_status = get_oauth_status()
    else:
        oauth_status = None
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
                                         title=_(u"%(name)s's profile", name=current_user.nickname,
                                                 registered_oauth=oauth_check, oauth_status=oauth_status))
        flash(_(u"Profile updated"), category="success")
    return render_title_template("user_edit.html", translations=translations, profile=1, languages=languages,
                                 content=content, downloads=downloads, title=_(u"%(name)s's profile",
                                 name=current_user.nickname), page="me", registered_oauth=oauth_check,
                                 oauth_status=oauth_status)

