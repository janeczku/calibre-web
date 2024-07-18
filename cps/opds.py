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

import datetime
import json
from urllib.parse import unquote_plus

from flask import Blueprint, request, render_template, make_response, abort, Response, g
from flask_babel import get_locale
from flask_babel import gettext as _


from sqlalchemy.sql.expression import func, text, or_, and_, true
from sqlalchemy.exc import InvalidRequestError, OperationalError

from . import logger, config, db, calibre_db, ub, isoLanguages, constants
from .usermanagement import requires_basic_auth_if_no_ano, auth
from .helper import get_download_link, get_book_cover
from .pagination import Pagination
from .web import render_read_books


opds = Blueprint('opds', __name__)

log = logger.create()


@opds.route("/opds/")
@opds.route("/opds")
@requires_basic_auth_if_no_ano
def feed_index():
    return render_xml_template('index.xml')


@opds.route("/opds/osd")
@requires_basic_auth_if_no_ano
def feed_osd():
    return render_xml_template('osd.xml', lang='en-EN')


# @opds.route("/opds/search", defaults={'query': ""})
@opds.route("/opds/search/<path:query>")
@requires_basic_auth_if_no_ano
def feed_cc_search(query):
    # Handle strange query from Libera Reader with + instead of spaces
    plus_query = unquote_plus(request.environ['RAW_URI'].split('/opds/search/')[1]).strip()
    return feed_search(plus_query)


@opds.route("/opds/search", methods=["GET"])
@requires_basic_auth_if_no_ano
def feed_normal_search():
    return feed_search(request.args.get("query", "").strip())


@opds.route("/opds/books")
@requires_basic_auth_if_no_ano
def feed_booksindex():
    return render_element_index(db.Books.sort, None, 'opds.feed_letter_books')


@opds.route("/opds/books/letter/<book_id>")
@requires_basic_auth_if_no_ano
def feed_letter_books(book_id):
    off = request.args.get("offset") or 0
    letter = true() if book_id == "00" else func.upper(db.Books.sort).startswith(book_id)
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        letter,
                                                        [db.Books.sort],
                                                        True, config.config_read_column)

    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/new")
@requires_basic_auth_if_no_ano
def feed_new():
    if not auth.current_user().check_visibility(constants.SIDEBAR_RECENT):
        abort(404)
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books, True, [db.Books.timestamp.desc()],
                                                        True, config.config_read_column)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/discover")
@requires_basic_auth_if_no_ano
def feed_discover():
    if not auth.current_user().check_visibility(constants.SIDEBAR_RANDOM):
        abort(404)
    query = calibre_db.generate_linked_query(config.config_read_column, db.Books)
    entries = query.filter(calibre_db.common_filters()).order_by(func.random()).limit(config.config_books_per_page)
    pagination = Pagination(1, config.config_books_per_page, int(config.config_books_per_page))
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/rated")
@requires_basic_auth_if_no_ano
def feed_best_rated():
    if not auth.current_user().check_visibility(constants.SIDEBAR_BEST_RATED):
        abort(404)
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books, db.Books.ratings.any(db.Ratings.rating > 9),
                                                        [db.Books.timestamp.desc()],
                                                        True, config.config_read_column)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/hot")
@requires_basic_auth_if_no_ano
def feed_hot():
    if not auth.current_user().check_visibility(constants.SIDEBAR_HOT):
        abort(404)
    off = request.args.get("offset") or 0
    all_books = ub.session.query(ub.Downloads, func.count(ub.Downloads.book_id)).order_by(
        func.count(ub.Downloads.book_id).desc()).group_by(ub.Downloads.book_id)
    hot_books = all_books.offset(off).limit(config.config_books_per_page)
    entries = list()
    for book in hot_books:
        query = calibre_db.generate_linked_query(config.config_read_column, db.Books)
        download_book = query.filter(calibre_db.common_filters()).filter(
            book.Downloads.book_id == db.Books.id).first()
        if download_book:
            entries.append(download_book)
        else:
            ub.delete_download(book.Downloads.book_id)
    num_books = entries.__len__()
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1),
                            config.config_books_per_page, num_books)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/author")
@requires_basic_auth_if_no_ano
def feed_authorindex():
    if not auth.current_user().check_visibility(constants.SIDEBAR_AUTHOR):
        abort(404)
    return render_element_index(db.Authors.sort, db.books_authors_link, 'opds.feed_letter_author')


@opds.route("/opds/author/letter/<book_id>")
@requires_basic_auth_if_no_ano
def feed_letter_author(book_id):
    if not auth.current_user().check_visibility(constants.SIDEBAR_AUTHOR):
        abort(404)
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
    return render_xml_dataset(db.Authors, book_id)


@opds.route("/opds/publisher")
@requires_basic_auth_if_no_ano
def feed_publisherindex():
    if not auth.current_user().check_visibility(constants.SIDEBAR_PUBLISHER):
        abort(404)
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
    return render_xml_dataset(db.Publishers, book_id)


@opds.route("/opds/category")
@requires_basic_auth_if_no_ano
def feed_categoryindex():
    if not auth.current_user().check_visibility(constants.SIDEBAR_CATEGORY):
        abort(404)
    return render_element_index(db.Tags.name, db.books_tags_link, 'opds.feed_letter_category')


@opds.route("/opds/category/letter/<book_id>")
@requires_basic_auth_if_no_ano
def feed_letter_category(book_id):
    if not auth.current_user().check_visibility(constants.SIDEBAR_CATEGORY):
        abort(404)
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
    return render_xml_dataset(db.Tags, book_id)


@opds.route("/opds/series")
@requires_basic_auth_if_no_ano
def feed_seriesindex():
    if not auth.current_user().check_visibility(constants.SIDEBAR_SERIES):
        abort(404)
    return render_element_index(db.Series.sort, db.books_series_link, 'opds.feed_letter_series')


@opds.route("/opds/series/letter/<book_id>")
@requires_basic_auth_if_no_ano
def feed_letter_series(book_id):
    if not auth.current_user().check_visibility(constants.SIDEBAR_SERIES):
        abort(404)
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
                                                        [db.Books.series_index],
                                                        True, config.config_read_column)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/ratings")
@requires_basic_auth_if_no_ano
def feed_ratingindex():
    if not auth.current_user().check_visibility(constants.SIDEBAR_RATING):
        abort(404)
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
    return render_xml_dataset(db.Ratings, book_id)


@opds.route("/opds/formats")
@requires_basic_auth_if_no_ano
def feed_formatindex():
    if not auth.current_user().check_visibility(constants.SIDEBAR_FORMAT):
        abort(404)
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
                                                        [db.Books.timestamp.desc()],
                                                        True, config.config_read_column)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/language")
@opds.route("/opds/language/")
@requires_basic_auth_if_no_ano
def feed_languagesindex():
    if not auth.current_user().check_visibility(constants.SIDEBAR_LANGUAGE):
        abort(404)
    off = request.args.get("offset") or 0
    if auth.current_user().filter_language() == "all":
        languages = calibre_db.speaking_language()
    else:
        languages = calibre_db.session.query(db.Languages).filter(
            db.Languages.lang_code == auth.current_user().filter_language()).all()
        languages[0].name = isoLanguages.get_language_name(get_locale(), languages[0].lang_code)
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
                                                        [db.Books.timestamp.desc()],
                                                        True, config.config_read_column)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


@opds.route("/opds/shelfindex")
@requires_basic_auth_if_no_ano
def feed_shelfindex():
    if not (auth.current_user().is_authenticated or g.allow_anonymous):
        abort(404)
    off = request.args.get("offset") or 0
    shelf = ub.session.query(ub.Shelf).filter(
        or_(ub.Shelf.is_public == 1, ub.Shelf.user_id == auth.current_user().id)).order_by(ub.Shelf.name).all()
    number = len(shelf)
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            number)
    return render_xml_template('feed.xml', listelements=shelf, folder='opds.feed_shelf', pagination=pagination)


@opds.route("/opds/shelf/<int:book_id>")
@requires_basic_auth_if_no_ano
def feed_shelf(book_id):
    if not (auth.current_user().is_authenticated or g.allow_anonymous):
        abort(404)
    off = request.args.get("offset") or 0
    if auth.current_user().is_anonymous:
        shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1,
                                                  ub.Shelf.id == book_id).first()
    else:
        shelf = ub.session.query(ub.Shelf).filter(or_(and_(ub.Shelf.user_id == int(auth.current_user().id),
                                                           ub.Shelf.id == book_id),
                                                      and_(ub.Shelf.is_public == 1,
                                                           ub.Shelf.id == book_id))).first()
    result = list()
    pagination = list()
    # user is allowed to access shelf
    if shelf:
        result, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1),
                                                           config.config_books_per_page,
                                                           db.Books,
                                                           ub.BookShelf.shelf == shelf.id,
                                                           [ub.BookShelf.order.asc()],
                                                           True, config.config_read_column,
                                                           ub.BookShelf, ub.BookShelf.book_id == db.Books.id)
        # delete shelf entries where book is not existent anymore, can happen if book is deleted outside calibre-web
        wrong_entries = calibre_db.session.query(ub.BookShelf) \
            .join(db.Books, ub.BookShelf.book_id == db.Books.id, isouter=True) \
            .filter(db.Books.id == None).all()
        for entry in wrong_entries:
            log.info('Not existing book {} in {} deleted'.format(entry.book_id, shelf))
            try:
                ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == entry.book_id).delete()
                ub.session.commit()
            except (OperationalError, InvalidRequestError) as e:
                ub.session.rollback()
                log.error_or_exception("Settings Database error: {}".format(e))
    return render_xml_template('feed.xml', entries=result, pagination=pagination)


@opds.route("/opds/download/<book_id>/<book_format>/")
@requires_basic_auth_if_no_ano
def opds_download_link(book_id, book_format):
    if not auth.current_user().role_download():
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


@opds.route("/opds/stats")
@requires_basic_auth_if_no_ano
def get_database_stats():
    stat = dict()
    stat['books'] = calibre_db.session.query(db.Books).count()
    stat['authors'] = calibre_db.session.query(db.Authors).count()
    stat['categories'] = calibre_db.session.query(db.Tags).count()
    stat['series'] = calibre_db.session.query(db.Series).count()
    return Response(json.dumps(stat), mimetype="application/json")


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
    if not (auth.current_user().check_visibility(constants.SIDEBAR_READ_AND_UNREAD) and not auth.current_user().is_anonymous):
        return abort(403)
    off = request.args.get("offset") or 0
    result, pagination = render_read_books(int(off) / (int(config.config_books_per_page)) + 1, True, True)
    return render_xml_template('feed.xml', entries=result, pagination=pagination)


@opds.route("/opds/unreadbooks")
@requires_basic_auth_if_no_ano
def feed_unread_books():
    if not (auth.current_user().check_visibility(constants.SIDEBAR_READ_AND_UNREAD) and not auth.current_user().is_anonymous):
        return abort(403)
    off = request.args.get("offset") or 0
    result, pagination = render_read_books(int(off) / (int(config.config_books_per_page)) + 1, False, True)
    return render_xml_template('feed.xml', entries=result, pagination=pagination)


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


def feed_search(term):
    if term:
        entries, __, ___ = calibre_db.get_search_results(term, config=config)
        entries_count = len(entries) if len(entries) > 0 else 1
        pagination = Pagination(1, entries_count, entries_count)
        return render_xml_template('feed.xml', searchterm=term, entries=entries, pagination=pagination)
    else:
        return render_xml_template('feed.xml', searchterm="")



def render_xml_template(*args, **kwargs):
    # ToDo: return time in current timezone similar to %z
    currtime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    xml = render_template(current_time=currtime, instance=config.config_calibre_web_title, constants=constants.sidebar_settings, *args, **kwargs)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/atom+xml; charset=utf-8"
    return response


def render_xml_dataset(data_table, book_id):
    off = request.args.get("offset") or 0
    entries, __, pagination = calibre_db.fill_indexpage((int(off) / (int(config.config_books_per_page)) + 1), 0,
                                                        db.Books,
                                                        getattr(db.Books, data_table.__tablename__).any(data_table.id == book_id),
                                                        [db.Books.timestamp.desc()],
                                                        True, config.config_read_column)
    return render_xml_template('feed.xml', entries=entries, pagination=pagination)


def render_element_index(database_column, linked_table, folder):
    shift = 0
    off = int(request.args.get("offset") or 0)
    entries = calibre_db.session.query(func.upper(func.substr(database_column, 1, 1)).label('id'), None, None)
    # query = calibre_db.generate_linked_query(config.config_read_column, db.Books)
    if linked_table is not None:
        entries = entries.join(linked_table).join(db.Books)
    entries = entries.filter(calibre_db.common_filters()).group_by(func.upper(func.substr(database_column, 1, 1))).all()
    elements = []
    if off == 0 and entries:
        elements.append({'id': "00", 'name': _("All")})
        shift = 1
    for entry in entries[
                 off + shift - 1:
                 int(off + int(config.config_books_per_page) - shift)]:
        elements.append({'id': entry.id, 'name': entry.id})
    pagination = Pagination((int(off) / (int(config.config_books_per_page)) + 1), config.config_books_per_page,
                            len(entries) + 1)
    return render_xml_template('feed.xml',
                               letterelements=elements,
                               folder=folder,
                               pagination=pagination)
