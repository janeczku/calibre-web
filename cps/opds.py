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

# opds routing functions
from cps import config, mimetypes, app, db
from flask import request, render_template, Response, g, make_response
from pagination import Pagination
from flask import Blueprint
import datetime
import ub
from flask_login import current_user
from functools import wraps
from web import login_required_if_no_ano, fill_indexpage, common_filters, get_search_results, render_read_books
from sqlalchemy.sql.expression import func
import helper
from werkzeug.security import check_password_hash
from werkzeug.datastructures import Headers
try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

opds = Blueprint('opds', __name__)


def requires_basic_auth_if_no_ano(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if config.config_anonbrowse != 1:
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
        return f(*args, **kwargs)

    return decorated


@opds.route("/opds")
@requires_basic_auth_if_no_ano
def feed_index():
    return render_xml_template('index.xml')


@opds.route("/opds/osd")
@requires_basic_auth_if_no_ano
def feed_osd():
    return render_xml_template('osd.xml', lang='en-EN')


@opds.route("/opds/search/<query>")
@requires_basic_auth_if_no_ano
def feed_cc_search(query):
    return feed_search(query.strip())


@opds.route("/opds/search", methods=["GET"])
@requires_basic_auth_if_no_ano
def feed_normal_search():
    return feed_search(request.args.get("query").strip())


@opds.route("/opds/new")
@requires_basic_auth_if_no_ano
def feed_new():
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                                                 db.Books, True, [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/discover")
@requires_basic_auth_if_no_ano
def feed_discover():
    entries = db.session.query(db.Books).filter(common_filters()).order_by(func.random())\
        .limit(config.config_books_per_page)
    pagination = Pagination(1, config.config_books_per_page, int(config.config_books_per_page))
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/rated")
@requires_basic_auth_if_no_ano
def feed_best_rated():
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.ratings.any(db.Ratings.rating > 9), [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/hot")
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


@opds.route("/opds/author")
@requires_basic_auth_if_no_ano
def feed_authorindex():
    off = request.args.get("offset") or 0
    entries = db.session.query(db.Authors).join(db.books_authors_link).join(db.Books).filter(common_filters())\
        .group_by('books_authors_link.author').order_by(db.Authors.sort).limit(config.config_books_per_page).offset(off)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Authors).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='opds.feed_author', pagination=pagination)


@opds.route("/opds/author/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_author(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.authors.any(db.Authors.id == book_id), [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/publisher")
@requires_basic_auth_if_no_ano
def feed_publisherindex():
    off = request.args.get("offset") or 0
    entries = db.session.query(db.Publishers).join(db.books_publishers_link).join(db.Books).filter(common_filters())\
        .group_by('books_publishers_link.publisher').order_by(db.Publishers.sort).limit(config.config_books_per_page).offset(off)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Publishers).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='opds.feed_publisher', pagination=pagination)


@opds.route("/opds/publisher/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_publisher(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                                             db.Books, db.Books.publishers.any(db.Publishers.id == book_id),
                                             [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/category")
@requires_basic_auth_if_no_ano
def feed_categoryindex():
    off = request.args.get("offset") or 0
    entries = db.session.query(db.Tags).join(db.books_tags_link).join(db.Books).filter(common_filters())\
        .group_by('books_tags_link.tag').order_by(db.Tags.name).offset(off).limit(config.config_books_per_page)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Tags).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='opds.feed_category', pagination=pagination)


@opds.route("/opds/category/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_category(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.tags.any(db.Tags.id == book_id), [db.Books.timestamp.desc()])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/series")
@requires_basic_auth_if_no_ano
def feed_seriesindex():
    off = request.args.get("offset") or 0
    entries = db.session.query(db.Series).join(db.books_series_link).join(db.Books).filter(common_filters())\
        .group_by('books_series_link.series').order_by(db.Series.sort).offset(off).all()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(db.session.query(db.Series).all()))
    return render_xml_template('feed.xml', listelements=entries, folder='opds.feed_series', pagination=pagination)


@opds.route("/opds/series/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_series(book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                    db.Books, db.Books.series.any(db.Series.id == book_id), [db.Books.series_index])
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/shelfindex/", defaults={'public': 0})
@opds.route("/opds/shelfindex/<string:public>")
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
    return render_xml_template('feed.xml', listelements=shelf, folder='opds.feed_shelf', pagination=pagination)


@opds.route("/opds/shelf/<int:book_id>")
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


@opds.route("/opds/download/<book_id>/<book_format>/")
@requires_basic_auth_if_no_ano
# @download_required
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

@opds.route("/ajax/book/<string:uuid>")
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


def feed_search(term):
    if term:
        term = term.strip().lower()
        entries = get_search_results( term)
        entriescount = len(entries) if len(entries) > 0 else 1
        pagination = Pagination(1, entriescount, entriescount)
        return render_xml_template('feed.xml', searchterm=term, entries=entries, pagination=pagination)
    else:
        return render_xml_template('feed.xml', searchterm="")

def check_auth(username, password):
    user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == username.lower()).first()
    return bool(user and check_password_hash(user.password, password))


def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def render_xml_template(*args, **kwargs):
    #ToDo: return time in current timezone similar to %z
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
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    return helper.get_book_cover(book.path)

@opds.route("/opds/readbooks/")
@login_required_if_no_ano
def feed_read_books():
    off = request.args.get("offset") or 0
    return render_read_books(int(off) / (int(config.config_books_per_page)) + 1, True, True)


@opds.route("/opds/unreadbooks/")
@login_required_if_no_ano
def feed_unread_books():
    off = request.args.get("offset") or 0
    return render_read_books(int(off) / (int(config.config_books_per_page)) + 1, False, True)
