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

import sys
import datetime
from functools import wraps

from flask import Blueprint, request, render_template, Response, g, make_response, abort
from flask_login import current_user
from sqlalchemy.sql.expression import func, text, or_, and_, true
from werkzeug.security import check_password_hash

from . import constants, logger, config, db, calibre_db, ub, services, get_locale, isoLanguages
from .helper import get_download_link, get_book_cover
from .pagination import Pagination
from .web import render_read_books
from .usermanagement import load_user_from_request
from flask_babel import gettext as _
from babel import Locale as LC
from babel.core import UnknownLocaleError

opds = Blueprint('opds', __name__)

log = logger.create()


def requires_basic_auth_if_no_ano(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if config.config_anonbrowse != 1:
            if not auth or auth.type != 'basic' or not check_auth(auth.username, auth.password):
                return authenticate()
        return f(*args, **kwargs)
    if config.config_login_type == constants.LOGIN_LDAP and services.ldap and config.config_anonbrowse != 1:
        return services.ldap.basic_auth_required(f)
    return decorated


class FeedObject:
    def __init__(self, rating_id, rating_name):
        self.rating_id = rating_id
        self.rating_name = rating_name

    @property
    def id(self):
        return self.rating_id

    @property
    def name(self):
        return self.rating_name


@opds.route("/opds/")
@opds.route("/opds")
@requires_basic_auth_if_no_ano
def feed_index():
    return render_xml_template('index.xml')


@opds.route("/opds/osd")
@requires_basic_auth_if_no_ano
def feed_osd():
    return render_xml_template('osd.xml', lang='en-EN')


@opds.route("/opds/search", defaults={'query': ""})
@opds.route("/opds/search/<query>")
@requires_basic_auth_if_no_ano
def feed_cc_search(query):
    return feed_search(query.strip())


@opds.route("/opds/search", methods=["GET"])
@requires_basic_auth_if_no_ano
def feed_normal_search():
    return feed_search(request.args.get("query", "").strip())


@opds.route("/opds/books")
@requires_basic_auth_if_no_ano
def feed_booksindex():
    shift = 0
    off = int(request.args.get("offset") or 0)
    entries = calibre_db.session.query(func.upper(func.substr(db.Books.sort, 1, 1)).label('id'))\
        .filter(calibre_db.common_filters()).group_by(func.upper(func.substr(db.Books.sort, 1, 1))).all()

    elements = []
    if off == 0:
        elements.append({'id': "00", 'name':_("All")})
        shift = 1
    for entry in entries[
                 off + shift - 1:
                 int(off + int(config.config_books_per_page) - shift)]:
        elements.append({'id': entry.id, 'name': entry.id})

    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(entries) + 1)
    return render_xml_template('feed.xml',
                               letterelements=elements,
                               folder='opds.feed_letter_books',
                               pagination=pagination)


@opds.route("/opds/books/letter/<book_id>")
@requires_basic_auth_if_no_ano
def feed_letter_books(book_id):
    off = request.args.get("offset") or 0
    letter = true() if book_id == "00" else func.upper(db.Books.sort).startswith(book_id)
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        letter,
                                                        [db.Books.sort])

    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/new")
@requires_basic_auth_if_no_ano
def feed_new():
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books, True, [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/discover")
@requires_basic_auth_if_no_ano
def feed_discover():
    entries = calibre_db.session.query(db.Books).filter(calibre_db.common_filters()).order_by(func.random())\
        .limit(config.config_books_per_page)
    pagination = Pagination(1, config.config_books_per_page, int(config.config_books_per_page))
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/rated")
@requires_basic_auth_if_no_ano
def feed_best_rated():
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books, db.Books.ratings.any(db.Ratings.rating > 9),
                                                        [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/hot")
@requires_basic_auth_if_no_ano
def feed_hot():
    off = request.args.get("offset") or 0
    all_books = ub.session.query(ub.Downloads, func.count(ub.Downloads.book_id)).order_by(
        func.count(ub.Downloads.book_id).desc()).group_by(ub.Downloads.book_id)
    hot_books = all_books.offset(off).limit(config.config_books_per_page)
    entries = list()
    for book in hot_books:
        downloadBook = calibre_db.get_book(book.Downloads.book_id)
        if downloadBook:
            entries.append(
                calibre_db.get_filtered_book(book.Downloads.book_id)
            )
        else:
            ub.delete_download(book.Downloads.book_id)
    numBooks = entries.__len__()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1),
                            config.config_books_per_page, numBooks)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/author")
@requires_basic_auth_if_no_ano
def feed_authorindex():
    shift = 0
    off = int(request.args.get("offset") or 0)
    entries = calibre_db.session.query(func.upper(func.substr(db.Authors.sort, 1, 1)).label('id'))\
        .join(db.books_authors_link).join(db.Books).filter(calibre_db.common_filters())\
        .group_by(func.upper(func.substr(db.Authors.sort, 1, 1))).all()

    elements = []
    if off == 0:
        elements.append({'id': "00", 'name':_("All")})
        shift = 1
    for entry in entries[
                 off + shift - 1:
                 int(off + int(config.config_books_per_page) - shift)]:
        elements.append({'id': entry.id, 'name': entry.id})

    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(entries) + 1)
    return render_xml_template('feed.xml',
                               letterelements=elements,
                               folder='opds.feed_letter_author',
                               pagination=pagination)


@opds.route("/opds/author/letter/<book_id>")
@requires_basic_auth_if_no_ano
def feed_letter_author(book_id):
    off = request.args.get("offset") or 0
    letter = true() if book_id == "00" else func.upper(db.Authors.sort).startswith(book_id)
    entries = calibre_db.session.query(db.Authors).join(db.books_authors_link).join(db.Books)\
        .filter(calibre_db.common_filters()).filter(letter)\
        .group_by(text('books_authors_link.author'))\
        .order_by(db.Authors.sort)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            entries.count())
    entries = entries.limit(config.config_books_per_page).offset(off).all()
    return render_xml_template('feed.xml', listelements=entries, folder='opds.feed_author', pagination=pagination)


@opds.route("/opds/author/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_author(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        db.Books.authors.any(db.Authors.id == book_id),
                                                        [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/publisher")
@requires_basic_auth_if_no_ano
def feed_publisherindex():
    off = request.args.get("offset") or 0
    entries = calibre_db.session.query(db.Publishers)\
        .join(db.books_publishers_link)\
        .join(db.Books).filter(calibre_db.common_filters())\
        .group_by(text('books_publishers_link.publisher'))\
        .order_by(db.Publishers.sort)\
        .limit(config.config_books_per_page).offset(off)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(calibre_db.session.query(db.Publishers).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='opds.feed_publisher', pagination=pagination)


@opds.route("/opds/publisher/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_publisher(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        db.Books.publishers.any(db.Publishers.id == book_id),
                                                        [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/category")
@requires_basic_auth_if_no_ano
def feed_categoryindex():
    shift = 0
    off = int(request.args.get("offset") or 0)
    entries = calibre_db.session.query(func.upper(func.substr(db.Tags.name, 1, 1)).label('id'))\
        .join(db.books_tags_link).join(db.Books).filter(calibre_db.common_filters())\
        .group_by(func.upper(func.substr(db.Tags.name, 1, 1))).all()
    elements = []
    if off == 0:
        elements.append({'id': "00", 'name':_("All")})
        shift = 1
    for entry in entries[
                 off + shift - 1:
                 int(off + int(config.config_books_per_page) - shift)]:
        elements.append({'id': entry.id, 'name': entry.id})

    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(entries) + 1)
    return render_xml_template('feed.xml',
                               letterelements=elements,
                               folder='opds.feed_letter_category',
                               pagination=pagination)

@opds.route("/opds/category/letter/<book_id>")
@requires_basic_auth_if_no_ano
def feed_letter_category(book_id):
    off = request.args.get("offset") or 0
    letter = true() if book_id == "00" else func.upper(db.Tags.name).startswith(book_id)
    entries = calibre_db.session.query(db.Tags)\
        .join(db.books_tags_link)\
        .join(db.Books)\
        .filter(calibre_db.common_filters()).filter(letter)\
        .group_by(text('books_tags_link.tag'))\
        .order_by(db.Tags.name)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            entries.count())
    entries = entries.offset(off).limit(config.config_books_per_page).all()
    return render_xml_template('feed.xml', listelements=entries, folder='opds.feed_category', pagination=pagination)


@opds.route("/opds/category/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_category(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        db.Books.tags.any(db.Tags.id == book_id),
                                                        [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/series")
@requires_basic_auth_if_no_ano
def feed_seriesindex():
    shift = 0
    off = int(request.args.get("offset") or 0)
    entries = calibre_db.session.query(func.upper(func.substr(db.Series.sort, 1, 1)).label('id'))\
        .join(db.books_series_link).join(db.Books).filter(calibre_db.common_filters())\
        .group_by(func.upper(func.substr(db.Series.sort, 1, 1))).all()
    elements = []
    if off == 0:
        elements.append({'id': "00", 'name':_("All")})
        shift = 1
    for entry in entries[
                 off + shift - 1:
                 int(off + int(config.config_books_per_page) - shift)]:
        elements.append({'id': entry.id, 'name': entry.id})
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(entries) + 1)
    return render_xml_template('feed.xml',
                               letterelements=elements,
                               folder='opds.feed_letter_series',
                               pagination=pagination)

@opds.route("/opds/series/letter/<book_id>")
@requires_basic_auth_if_no_ano
def feed_letter_series(book_id):
    off = request.args.get("offset") or 0
    letter = true() if book_id == "00" else func.upper(db.Series.sort).startswith(book_id)
    entries = calibre_db.session.query(db.Series)\
        .join(db.books_series_link)\
        .join(db.Books)\
        .filter(calibre_db.common_filters()).filter(letter)\
        .group_by(text('books_series_link.series'))\
        .order_by(db.Series.sort)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            entries.count())
    entries = entries.offset(off).limit(config.config_books_per_page).all()
    return render_xml_template('feed.xml', listelements=entries, folder='opds.feed_series', pagination=pagination)


@opds.route("/opds/series/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_series(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        db.Books.series.any(db.Series.id == book_id),
                                                        [db.Books.series_index])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/ratings")
@requires_basic_auth_if_no_ano
def feed_ratingindex():
    off = request.args.get("offset") or 0
    entries = calibre_db.session.query(db.Ratings, func.count('books_ratings_link.book').label('count'),
                               (db.Ratings.rating / 2).label('name')) \
        .join(db.books_ratings_link)\
        .join(db.Books)\
        .filter(calibre_db.common_filters()) \
        .group_by(text('books_ratings_link.rating'))\
        .order_by(db.Ratings.rating).all()

    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(entries))
    element = list()
    for entry in entries:
        element.append(FeedObject(entry[0].id, _("{} Stars").format(entry.name)))
    return render_xml_template('feed.xml', listelements=element, folder='opds.feed_ratings', pagination=pagination)


@opds.route("/opds/ratings/<book_id>")
@requires_basic_auth_if_no_ano
def feed_ratings(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        db.Books.ratings.any(db.Ratings.id == book_id),
                                                        [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/formats")
@requires_basic_auth_if_no_ano
def feed_formatindex():
    off = request.args.get("offset") or 0
    entries = calibre_db.session.query(db.Data).join(db.Books)\
        .filter(calibre_db.common_filters()) \
        .group_by(db.Data.format)\
        .order_by(db.Data.format).all()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(entries))

    element = list()
    for entry in entries:
        element.append(FeedObject(entry.format, entry.format))
    return render_xml_template('feed.xml', listelements=element, folder='opds.feed_format', pagination=pagination)


@opds.route("/opds/formats/<book_id>")
@requires_basic_auth_if_no_ano
def feed_format(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        db.Books.data.any(db.Data.format == book_id.upper()),
                                                        [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/language")
@opds.route("/opds/language/")
@requires_basic_auth_if_no_ano
def feed_languagesindex():
    off = request.args.get("offset") or 0
    if current_user.filter_language() == u"all":
        languages = calibre_db.speaking_language()
    else:
        #try:
        #    cur_l = LC.parse(current_user.filter_language())
        #except UnknownLocaleError:
        #    cur_l = None
        languages = calibre_db.session.query(db.Languages).filter(
            db.Languages.lang_code == current_user.filter_language()).all()
        languages[0].name = isoLanguages.get_language_name(get_locale(), languages[0].lang_code)
        #if cur_l:
        #    languages[0].name = cur_l.get_language_name(get_locale())
        #else:
        #    languages[0].name = _(isoLanguages.get(part3=languages[0].lang_code).name)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(languages))
    return render_xml_template('feed.xml', listelements=languages, folder='opds.feed_languages', pagination=pagination)


@opds.route("/opds/language/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_languages(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        db.Books.languages.any(db.Languages.id == book_id),
                                                        [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/shelfindex")
@requires_basic_auth_if_no_ano
def feed_shelfindex():
    off = request.args.get("offset") or 0
    shelf = g.shelves_access
    number = len(shelf)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            number)
    return render_xml_template('feed.xml', listelements=shelf, folder='opds.feed_shelf', pagination=pagination)


@opds.route("/opds/shelf/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_shelf(book_id):
    off = request.args.get("offset") or 0
    if current_user.is_anonymous:
        shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1,
                                                  ub.Shelf.id == book_id).first()
    else:
        shelf = ub.session.query(ub.Shelf).filter(or_(and_(ub.Shelf.user_id == int(current_user.id),
                                                           ub.Shelf.id == book_id),
                                                      and_(ub.Shelf.is_public == 1,
                                                           ub.Shelf.id == book_id))).first()
    result = list()
    # user is allowed to access shelf
    if shelf:
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == book_id).order_by(
            ub.BookShelf.order.asc()).all()
        for book in books_in_shelf:
            cur_book = calibre_db.get_book(book.book_id)
            result.append(cur_book)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(result))
    return render_xml_template('feed.xml', entries=result, pagination=pagination)


@opds.route("/opds/download/<book_id>/<book_format>/")
@requires_basic_auth_if_no_ano
def opds_download_link(book_id, book_format):
    # I gave up with this: With enabled ldap login, the user doesn't get logged in, therefore it's always guest
    # workaround, loading the user from the request and checking it's download rights here
    # in case of anonymous browsing user is None
    user = load_user_from_request(request) or current_user
    if not user.role_download():
        return abort(403)
    if "Kobo" in request.headers.get('User-Agent'):
        client = "kobo"
    else:
        client = ""
    return get_download_link(book_id, book_format.lower(), client)


@opds.route("/ajax/book/<string:uuid>/<library>")
@opds.route("/ajax/book/<string:uuid>", defaults={'library': ""})
@requires_basic_auth_if_no_ano
def get_metadata_calibre_companion(uuid, library):
    entry = calibre_db.session.query(db.Books).filter(db.Books.uuid.like("%" + uuid + "%")).first()
    if entry is not None:
        js = render_template('json.txt', entry=entry)
        response = make_response(js)
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response
    else:
        return ""


def feed_search(term):
    if term:
        entries, __, ___ = calibre_db.get_search_results(term)
        entriescount = len(entries) if len(entries) > 0 else 1
        pagination = Pagination(1, entriescount, entriescount)
        return render_xml_template('feed.xml', searchterm=term, entries=entries, pagination=pagination)
    else:
        return render_xml_template('feed.xml', searchterm="")


def check_auth(username, password):
    try:
        username = username.encode('windows-1252')
    except UnicodeEncodeError:
        username = username.encode('utf-8')
    user = ub.session.query(ub.User).filter(func.lower(ub.User.name) ==
                                            username.decode('utf-8').lower()).first()
    if bool(user and check_password_hash(str(user.password), password)):
        return True
    else:
        ip_Address = request.headers.get('X-Forwarded-For', request.remote_addr)
        log.warning('OPDS Login failed for user "%s" IP-address: %s', username.decode('utf-8'), ip_Address)
        return False


def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def render_xml_template(*args, **kwargs):
    # ToDo: return time in current timezone similar to %z
    currtime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    xml = render_template(current_time=currtime, instance=config.config_calibre_web_title, *args, **kwargs)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


@opds.route("/opds/thumb_240_240/<book_id>")
@opds.route("/opds/cover_240_240/<book_id>")
@opds.route("/opds/cover_90_90/<book_id>")
@opds.route("/opds/cover/<book_id>")
@requires_basic_auth_if_no_ano
def feed_get_cover(book_id):
    return get_book_cover(book_id)


@opds.route("/opds/readbooks")
@requires_basic_auth_if_no_ano
def feed_read_books():
    off = request.args.get("offset") or 0
    result, pagination = render_read_books(int(off) / (int(config.config_books_per_page)) + 1, True, True)
    return render_xml_template('feed.xml', entries=result, pagination=pagination)


@opds.route("/opds/unreadbooks")
@requires_basic_auth_if_no_ano
def feed_unread_books():
    off = request.args.get("offset") or 0
    result, pagination = render_read_books(int(off) / (int(config.config_books_per_page)) + 1, False, True)
    return render_xml_template('feed.xml', entries=result, pagination=pagination)
