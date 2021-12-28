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

import os
from datetime import datetime
import json
import mimetypes
import chardet  # dependency of requests
import copy

from babel.dates import format_date
from babel import Locale as LC
from flask import Blueprint, jsonify
from flask import request, redirect, send_from_directory, make_response, flash, abort, url_for
from flask import session as flask_session
from flask_babel import gettext as _
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError, InvalidRequestError, OperationalError
from sqlalchemy.sql.expression import text, func, false, not_, and_, or_
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql.functions import coalesce

from .services.worker import WorkerThread

from werkzeug.datastructures import Headers
from werkzeug.security import generate_password_hash, check_password_hash

from . import constants, logger, isoLanguages, services
from . import babel, db, ub, config, get_locale, app
from . import calibre_db, kobo_sync_status
from .gdriveutils import getFileFromEbooksFolder, do_gdrive_download
from .helper import check_valid_domain, render_task_status, check_email, check_username, \
    get_cc_columns, get_book_cover, get_download_link, send_mail, generate_random_password, \
    send_registration_mail, check_send_to_kindle, check_read_formats, tags_filters, reset_password, valid_email
from .pagination import Pagination
from .redirect import redirect_back
from .usermanagement import login_required_if_no_ano
from .kobo_sync_status import remove_synced_book
from .render_template import render_title_template
from .kobo_sync_status import change_archived_books

feature_support = {
    'ldap': bool(services.ldap),
    'goodreads': bool(services.goodreads_support),
    'kobo': bool(services.kobo)
}

try:
    from .oauth_bb import oauth_check, register_user_with_oauth, logout_oauth_user, get_oauth_status
    feature_support['oauth'] = True
except ImportError:
    feature_support['oauth'] = False
    oauth_check = {}

try:
    from functools import wraps
except ImportError:
    pass  # We're not using Python 3

try:
    from natsort import natsorted as sort
except ImportError:
    sort = sorted  # Just use regular sort then, may cause issues with badly named pages in cbz/cbr files


@app.after_request
def add_security_headers(resp):
    resp.headers['Content-Security-Policy'] = "default-src 'self'" + ''.join([' '+host for host in config.config_trustedhosts.strip().split(',')]) + " 'unsafe-inline' 'unsafe-eval'; font-src 'self' data:; img-src 'self' data:"
    if request.endpoint == "editbook.edit_book" or config.config_use_google_drive:
        resp.headers['Content-Security-Policy'] += " *"
    elif request.endpoint == "web.read_book":
        resp.headers['Content-Security-Policy'] += " blob:;style-src-elem 'self' blob: 'unsafe-inline';"
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    resp.headers['Strict-Transport-Security'] = 'max-age=31536000;'
    return resp

web = Blueprint('web', __name__)
log = logger.create()


# ################################### Login logic and rights management ###############################################


def download_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_download():
            return f(*args, **kwargs)
        abort(403)

    return inner


def viewer_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_viewer():
            return f(*args, **kwargs)
        abort(403)

    return inner

# ################################### data provider functions #########################################################


@web.route("/ajax/emailstat")
@login_required
def get_email_status_json():
    tasks = WorkerThread.getInstance().tasks
    return jsonify(render_task_status(tasks))


@web.route("/ajax/bookmark/<int:book_id>/<book_format>", methods=['POST'])
@login_required
def bookmark(book_id, book_format):
    bookmark_key = request.form["bookmark"]
    ub.session.query(ub.Bookmark).filter(and_(ub.Bookmark.user_id == int(current_user.id),
                                              ub.Bookmark.book_id == book_id,
                                              ub.Bookmark.format == book_format)).delete()
    if not bookmark_key:
        ub.session_commit()
        return "", 204

    lbookmark = ub.Bookmark(user_id=current_user.id,
                            book_id=book_id,
                            format=book_format,
                            bookmark_key=bookmark_key)
    ub.session.merge(lbookmark)
    ub.session_commit("Bookmark for user {} in book {} created".format(current_user.id, book_id))
    return "", 201


@web.route("/ajax/toggleread/<int:book_id>", methods=['POST'])
@login_required
def toggle_read(book_id):
    if not config.config_read_column:
        book = ub.session.query(ub.ReadBook).filter(and_(ub.ReadBook.user_id == int(current_user.id),
                                                         ub.ReadBook.book_id == book_id)).first()
        if book:
            if book.read_status == ub.ReadBook.STATUS_FINISHED:
                book.read_status = ub.ReadBook.STATUS_UNREAD
            else:
                book.read_status = ub.ReadBook.STATUS_FINISHED
        else:
            readBook = ub.ReadBook(user_id=current_user.id, book_id = book_id)
            readBook.read_status = ub.ReadBook.STATUS_FINISHED
            book = readBook
        if not book.kobo_reading_state:
            kobo_reading_state = ub.KoboReadingState(user_id=current_user.id, book_id=book_id)
            kobo_reading_state.current_bookmark = ub.KoboBookmark()
            kobo_reading_state.statistics = ub.KoboStatistics()
            book.kobo_reading_state = kobo_reading_state
        ub.session.merge(book)
        ub.session_commit("Book {} readbit toggled".format(book_id))
    else:
        try:
            calibre_db.update_title_sort(config)
            book = calibre_db.get_filtered_book(book_id)
            read_status = getattr(book, 'custom_column_' + str(config.config_read_column))
            if len(read_status):
                read_status[0].value = not read_status[0].value
                calibre_db.session.commit()
            else:
                cc_class = db.cc_classes[config.config_read_column]
                new_cc = cc_class(value=1, book=book_id)
                calibre_db.session.add(new_cc)
                calibre_db.session.commit()
        except (KeyError, AttributeError):
            log.error(u"Custom Column No.%d is not existing in calibre database", config.config_read_column)
            return "Custom Column No.{} is not existing in calibre database".format(config.config_read_column), 400
        except (OperationalError, InvalidRequestError) as e:
            calibre_db.session.rollback()
            log.error(u"Read status could not set: {}".format(e))
            return "Read status could not set: {}".format(e), 400
    return ""

@web.route("/ajax/togglearchived/<int:book_id>", methods=['POST'])
@login_required
def toggle_archived(book_id):
    is_archived = change_archived_books(book_id, message="Book {} archivebit toggled".format(book_id))
    if is_archived:
        remove_synced_book(book_id)
    return ""


@web.route("/ajax/view", methods=["POST"])
@login_required_if_no_ano
def update_view():
    to_save = request.get_json()
    try:
        for element in to_save:
            for param in to_save[element]:
                current_user.set_view_property(element, param, to_save[element][param])
    except Exception as ex:
        log.error("Could not save view_settings: %r %r: %e", request, to_save, ex)
        return "Invalid request", 400
    return "1", 200


'''
@web.route("/ajax/getcomic/<int:book_id>/<book_format>/<int:page>")
@login_required
def get_comic_book(book_id, book_format, page):
    book = calibre_db.get_book(book_id)
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
                            log.error('Unrar binary not found, or unable to decompress file %s', cbr_file)
                            return "", 204
                    else:
                        log.info('Unrar is not supported please install python rarfile extension')
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
                    log.error('unsupported comic format')
                    return "", 204

                b64 = codecs.encode(extract(page), 'base64').decode()
                ext = names[page].rpartition('.')[-1]
                if ext not in ('png', 'gif', 'jpg', 'jpeg', 'webp'):
                    ext = 'png'
                extractedfile="data:image/" + ext + ";base64," + b64
                fileData={"name": names[page], "page":page, "last":len(names)-1, "content": extractedfile}
                return make_response(json.dumps(fileData))
        return "", 204
'''

# ################################### Typeahead ##################################################################


@web.route("/get_authors_json", methods=['GET'])
@login_required_if_no_ano
def get_authors_json():
    return calibre_db.get_typeahead(db.Authors, request.args.get('q'), ('|', ','))


@web.route("/get_publishers_json", methods=['GET'])
@login_required_if_no_ano
def get_publishers_json():
    return calibre_db.get_typeahead(db.Publishers, request.args.get('q'), ('|', ','))


@web.route("/get_tags_json", methods=['GET'])
@login_required_if_no_ano
def get_tags_json():
    return calibre_db.get_typeahead(db.Tags, request.args.get('q'), tag_filter=tags_filters())


@web.route("/get_series_json", methods=['GET'])
@login_required_if_no_ano
def get_series_json():
    return calibre_db.get_typeahead(db.Series, request.args.get('q'))


@web.route("/get_languages_json", methods=['GET'])
@login_required_if_no_ano
def get_languages_json():
    query = (request.args.get('q') or '').lower()
    language_names = isoLanguages.get_language_names(get_locale())
    entries_start = [s for key, s in language_names.items() if s.lower().startswith(query.lower())]
    if len(entries_start) < 5:
        entries = [s for key, s in language_names.items() if query in s.lower()]
        entries_start.extend(entries[0:(5 - len(entries_start))])
        entries_start = list(set(entries_start))
    json_dumps = json.dumps([dict(name=r) for r in entries_start[0:5]])
    return json_dumps


@web.route("/get_matching_tags", methods=['GET'])
@login_required_if_no_ano
def get_matching_tags():
    tag_dict = {'tags': []}
    q = calibre_db.session.query(db.Books).filter(calibre_db.common_filters(True))
    calibre_db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
    author_input = request.args.get('author_name') or ''
    title_input = request.args.get('book_title') or ''
    include_tag_inputs = request.args.getlist('include_tag') or ''
    exclude_tag_inputs = request.args.getlist('exclude_tag') or ''
    q = q.filter(db.Books.authors.any(func.lower(db.Authors.name).ilike("%" + author_input + "%")),
                 func.lower(db.Books.title).ilike("%" + title_input + "%"))
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


def get_sort_function(sort, data):
    order = [db.Books.timestamp.desc()]
    if sort == 'stored':
        sort = current_user.get_view_property(data, 'stored')
    else:
        current_user.set_view_property(data, 'stored', sort)
    if sort == 'pubnew':
        order = [db.Books.pubdate.desc()]
    if sort == 'pubold':
        order = [db.Books.pubdate]
    if sort == 'abc':
        order = [db.Books.sort]
    if sort == 'zyx':
        order = [db.Books.sort.desc()]
    if sort == 'new':
        order = [db.Books.timestamp.desc()]
    if sort == 'old':
        order = [db.Books.timestamp]
    if sort == 'authaz':
        order = [db.Books.author_sort.asc(), db.Series.name, db.Books.series_index]
    if sort == 'authza':
        order = [db.Books.author_sort.desc(), db.Series.name.desc(), db.Books.series_index.desc()]
    if sort == 'seriesasc':
        order = [db.Books.series_index.asc()]
    if sort == 'seriesdesc':
        order = [db.Books.series_index.desc()]
    if sort == 'hotdesc':
        order = [func.count(ub.Downloads.book_id).desc()]
    if sort == 'hotasc':
        order = [func.count(ub.Downloads.book_id).asc()]
    if sort is None:
        sort = "new"
    return order, sort


def render_books_list(data, sort, book_id, page):
    order = get_sort_function(sort, data)
    if data == "rated":
        return render_rated_books(page, book_id, order=order)
    elif data == "discover":
        return render_discover_books(page, book_id)
    elif data == "unread":
        return render_read_books(page, False, order=order)
    elif data == "read":
        return render_read_books(page, True, order=order)
    elif data == "hot":
        return render_hot_books(page, order)
    elif data == "download":
        return render_downloaded_books(page, order, book_id)
    elif data == "author":
        return render_author_books(page, book_id, order)
    elif data == "publisher":
        return render_publisher_books(page, book_id, order)
    elif data == "series":
        return render_series_books(page, book_id, order)
    elif data == "ratings":
        return render_ratings_books(page, book_id, order)
    elif data == "formats":
        return render_formats_books(page, book_id, order)
    elif data == "category":
        return render_category_books(page, book_id, order)
    elif data == "language":
        return render_language_books(page, book_id, order)
    elif data == "archived":
        return render_archived_books(page, order)
    elif data == "search":
        term = (request.args.get('query') or '')
        offset = int(int(config.config_books_per_page) * (page - 1))
        return render_search_results(term, offset, order, config.config_books_per_page)
    elif data == "advsearch":
        term = json.loads(flask_session['query'])
        offset = int(int(config.config_books_per_page) * (page - 1))
        return render_adv_search_results(term, offset, order, config.config_books_per_page)
    else:
        website = data or "newest"
        entries, random, pagination = calibre_db.fill_indexpage(page, 0, db.Books, True, order[0],
                                                                db.books_series_link,
                                                                db.Books.id == db.books_series_link.c.book,
                                                                db.Series)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Books"), page=website, order=order[1])


def render_rated_books(page, book_id, order):
    if current_user.check_visibility(constants.SIDEBAR_BEST_RATED):
        entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                                db.Books,
                                                                db.Books.ratings.any(db.Ratings.rating > 9),
                                                                order[0],
                                                                db.books_series_link,
                                                                db.Books.id == db.books_series_link.c.book,
                                                                db.Series)

        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     id=book_id, title=_(u"Top Rated Books"), page="rated", order=order[1])
    else:
        abort(404)


def render_discover_books(page, book_id):
    if current_user.check_visibility(constants.SIDEBAR_RANDOM):
        entries, __, pagination = calibre_db.fill_indexpage(page, 0, db.Books, True, [func.randomblob(2)])
        pagination = Pagination(1, config.config_books_per_page, config.config_books_per_page)
        return render_title_template('discover.html', entries=entries, pagination=pagination, id=book_id,
                                     title=_(u"Discover (Random Books)"), page="discover")
    else:
        abort(404)

def render_hot_books(page, order):
    if current_user.check_visibility(constants.SIDEBAR_HOT):
        if order[1] not in ['hotasc', 'hotdesc']:
        # Unary expression comparsion only working (for this expression) in sqlalchemy 1.4+
        #if not (order[0][0].compare(func.count(ub.Downloads.book_id).desc()) or
        #        order[0][0].compare(func.count(ub.Downloads.book_id).asc())):
            order = [func.count(ub.Downloads.book_id).desc()], 'hotdesc'
        if current_user.show_detail_random():
            random = calibre_db.session.query(db.Books).filter(calibre_db.common_filters()) \
                .order_by(func.random()).limit(config.config_random_books)
        else:
            random = false()
        off = int(int(config.config_books_per_page) * (page - 1))
        all_books = ub.session.query(ub.Downloads, func.count(ub.Downloads.book_id))\
            .order_by(*order[0]).group_by(ub.Downloads.book_id)
        hot_books = all_books.offset(off).limit(config.config_books_per_page)
        entries = list()
        for book in hot_books:
            downloadBook = calibre_db.session.query(db.Books).filter(calibre_db.common_filters()).filter(
                db.Books.id == book.Downloads.book_id).first()
            if downloadBook:
                entries.append(downloadBook)
            else:
                ub.delete_download(book.Downloads.book_id)
        numBooks = entries.__len__()
        pagination = Pagination(page, config.config_books_per_page, numBooks)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=_(u"Hot Books (Most Downloaded)"), page="hot", order=order[1])
    else:
        abort(404)


def render_downloaded_books(page, order, user_id):
    if current_user.role_admin():
        user_id = int(user_id)
    else:
        user_id = current_user.id
    if current_user.check_visibility(constants.SIDEBAR_DOWNLOAD):
        if current_user.show_detail_random():
            random = calibre_db.session.query(db.Books).filter(calibre_db.common_filters()) \
                .order_by(func.random()).limit(config.config_random_books)
        else:
            random = false()

        entries, __, pagination = calibre_db.fill_indexpage(page,
                                                            0,
                                                            db.Books,
                                                            ub.Downloads.user_id == user_id,
                                                            order[0],
                                                            db.books_series_link,
                                                            db.Books.id == db.books_series_link.c.book,
                                                            db.Series,
                                                            ub.Downloads, db.Books.id == ub.Downloads.book_id)
        for book in entries:
            if not calibre_db.session.query(db.Books).filter(calibre_db.common_filters()) \
                             .filter(db.Books.id == book.id).first():
                ub.delete_download(book.id)
        user = ub.session.query(ub.User).filter(ub.User.id == user_id).first()
        return render_title_template('index.html',
                                     random=random,
                                     entries=entries,
                                     pagination=pagination,
                                     id=user_id,
                                     title=_(u"Downloaded books by %(user)s",user=user.name),
                                     page="download",
                                     order=order[1])
    else:
        abort(404)


def render_author_books(page, author_id, order):
    entries, __, pagination = calibre_db.fill_indexpage(page, 0,
                                                        db.Books,
                                                        db.Books.authors.any(db.Authors.id == author_id),
                                                        [order[0][0], db.Series.name, db.Books.series_index],
                                                        db.books_series_link,
                                                        db.Books.id == db.books_series_link.c.book,
                                                        db.Series)
    if entries is None or not len(entries):
        flash(_(u"Oops! Selected book title is unavailable. File does not exist or is not accessible"),
              category="error")
        return redirect(url_for("web.index"))
    if constants.sqlalchemy_version2:
        author = calibre_db.session.get(db.Authors, author_id)
    else:
        author = calibre_db.session.query(db.Authors).get(author_id)
    author_name = author.name.replace('|', ',')

    author_info = None
    other_books = []
    if services.goodreads_support and config.config_use_goodreads:
        author_info = services.goodreads_support.get_author_info(author_name)
        other_books = services.goodreads_support.get_other_books(author_info, entries)

    return render_title_template('author.html', entries=entries, pagination=pagination, id=author_id,
                                 title=_(u"Author: %(name)s", name=author_name), author=author_info,
                                 other_books=other_books, page="author", order=order[1])


def render_publisher_books(page, book_id, order):
    publisher = calibre_db.session.query(db.Publishers).filter(db.Publishers.id == book_id).first()
    if publisher:
        entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                                db.Books,
                                                                db.Books.publishers.any(db.Publishers.id == book_id),
                                                                [db.Series.name, order[0][0], db.Books.series_index],
                                                                db.books_series_link,
                                                                db.Books.id == db.books_series_link.c.book,
                                                                db.Series)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination, id=book_id,
                                     title=_(u"Publisher: %(name)s", name=publisher.name),
                                     page="publisher",
                                     order=order[1])
    else:
        abort(404)


def render_series_books(page, book_id, order):
    name = calibre_db.session.query(db.Series).filter(db.Series.id == book_id).first()
    if name:
        entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                                db.Books,
                                                                db.Books.series.any(db.Series.id == book_id),
                                                                [order[0][0]])
        return render_title_template('index.html', random=random, pagination=pagination, entries=entries, id=book_id,
                                     title=_(u"Series: %(serie)s", serie=name.name), page="series", order=order[1])
    else:
        abort(404)


def render_ratings_books(page, book_id, order):
    name = calibre_db.session.query(db.Ratings).filter(db.Ratings.id == book_id).first()
    entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                            db.Books,
                                                            db.Books.ratings.any(db.Ratings.id == book_id),
                                                            [order[0][0]])
    if name and name.rating <= 10:
        return render_title_template('index.html', random=random, pagination=pagination, entries=entries, id=book_id,
                                     title=_(u"Rating: %(rating)s stars", rating=int(name.rating / 2)),
                                     page="ratings",
                                     order=order[1])
    else:
        abort(404)


def render_formats_books(page, book_id, order):
    name = calibre_db.session.query(db.Data).filter(db.Data.format == book_id.upper()).first()
    if name:
        entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                                db.Books,
                                                                db.Books.data.any(db.Data.format == book_id.upper()),
                                                                [order[0][0]])
        return render_title_template('index.html', random=random, pagination=pagination, entries=entries, id=book_id,
                                     title=_(u"File format: %(format)s", format=name.format),
                                     page="formats",
                                     order=order[1])
    else:
        abort(404)


def render_category_books(page, book_id, order):
    name = calibre_db.session.query(db.Tags).filter(db.Tags.id == book_id).first()
    if name:
        entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                                db.Books,
                                                                db.Books.tags.any(db.Tags.id == book_id),
                                                                [order[0][0], db.Series.name, db.Books.series_index],
                                                                db.books_series_link,
                                                                db.Books.id == db.books_series_link.c.book,
                                                                db.Series)
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination, id=book_id,
                                     title=_(u"Category: %(name)s", name=name.name), page="category", order=order[1])
    else:
        abort(404)


def render_language_books(page, name, order):
    try:
        lang_name = isoLanguages.get_language_name(get_locale(), name)
    except KeyError:
        abort(404)

    entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                            db.Books,
                                                            db.Books.languages.any(db.Languages.lang_code == name),
                                                            [order[0][0]])
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination, id=name,
                                 title=_(u"Language: %(name)s", name=lang_name), page="language", order=order[1])


def render_read_books(page, are_read, as_xml=False, order=None):
    sort = order[0] if order else []
    if not config.config_read_column:
        if are_read:
            db_filter = and_(ub.ReadBook.user_id == int(current_user.id),
                             ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED)
        else:
            db_filter = coalesce(ub.ReadBook.read_status, 0) != ub.ReadBook.STATUS_FINISHED
        entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                                db.Books,
                                                                db_filter,
                                                                sort,
                                                                db.books_series_link,
                                                                db.Books.id == db.books_series_link.c.book,
                                                                db.Series,
                                                                ub.ReadBook, db.Books.id == ub.ReadBook.book_id)
    else:
        try:
            if are_read:
                db_filter = db.cc_classes[config.config_read_column].value == True
            else:
                db_filter = coalesce(db.cc_classes[config.config_read_column].value, False) != True
            entries, random, pagination = calibre_db.fill_indexpage(page, 0,
                                                                    db.Books,
                                                                    db_filter,
                                                                    sort,
                                                                    db.books_series_link,
                                                                    db.Books.id == db.books_series_link.c.book,
                                                                    db.Series,
                                                                    db.cc_classes[config.config_read_column])
        except (KeyError, AttributeError):
            log.error("Custom Column No.%d is not existing in calibre database", config.config_read_column)
            if not as_xml:
                flash(_("Custom Column No.%(column)d is not existing in calibre database",
                        column=config.config_read_column),
                      category="error")
                return redirect(url_for("web.index"))
            # ToDo: Handle error Case for opds
    if as_xml:
        return entries, pagination
    else:
        if are_read:
            name = _(u'Read Books') + ' (' + str(pagination.total_count) + ')'
            pagename = "read"
        else:
            name = _(u'Unread Books') + ' (' + str(pagination.total_count) + ')'
            pagename = "unread"
        return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                     title=name, page=pagename, order=order[1])


def render_archived_books(page, sort):
    order = sort[0] or []
    archived_books = (
        ub.session.query(ub.ArchivedBook)
        .filter(ub.ArchivedBook.user_id == int(current_user.id))
        .filter(ub.ArchivedBook.is_archived == True)
        .all()
    )
    archived_book_ids = [archived_book.book_id for archived_book in archived_books]

    archived_filter = db.Books.id.in_(archived_book_ids)

    entries, random, pagination = calibre_db.fill_indexpage_with_archived_books(page, 0,
                                                                                db.Books,
                                                                                archived_filter,
                                                                                order,
                                                                                allow_show_archived=True)

    name = _(u'Archived Books') + ' (' + str(len(archived_book_ids)) + ')'
    pagename = "archived"
    return render_title_template('index.html', random=random, entries=entries, pagination=pagination,
                                 title=name, page=pagename, order=sort[1])


def render_prepare_search_form(cc):
    # prepare data for search-form
    tags = calibre_db.session.query(db.Tags)\
        .join(db.books_tags_link)\
        .join(db.Books)\
        .filter(calibre_db.common_filters()) \
        .group_by(text('books_tags_link.tag'))\
        .order_by(db.Tags.name).all()
    series = calibre_db.session.query(db.Series)\
        .join(db.books_series_link)\
        .join(db.Books)\
        .filter(calibre_db.common_filters()) \
        .group_by(text('books_series_link.series'))\
        .order_by(db.Series.name)\
        .filter(calibre_db.common_filters()).all()
    shelves = ub.session.query(ub.Shelf)\
        .filter(or_(ub.Shelf.is_public == 1, ub.Shelf.user_id == int(current_user.id)))\
        .order_by(ub.Shelf.name).all()
    extensions = calibre_db.session.query(db.Data)\
        .join(db.Books)\
        .filter(calibre_db.common_filters()) \
        .group_by(db.Data.format)\
        .order_by(db.Data.format).all()
    if current_user.filter_language() == u"all":
        languages = calibre_db.speaking_language()
    else:
        languages = None
    return render_title_template('search_form.html', tags=tags, languages=languages, extensions=extensions,
                                 series=series,shelves=shelves, title=_(u"Advanced Search"), cc=cc, page="advsearch")


def render_search_results(term, offset=None, order=None, limit=None):
    join = db.books_series_link, db.Books.id == db.books_series_link.c.book, db.Series
    entries, result_count, pagination = calibre_db.get_search_results(term, offset, order, limit, *join)
    return render_title_template('search.html',
                                 searchterm=term,
                                 pagination=pagination,
                                 query=term,
                                 adv_searchterm=term,
                                 entries=entries,
                                 result_count=result_count,
                                 title=_(u"Search"),
                                 page="search",
                                 order=order[1])


# ################################### View Books list ##################################################################


@web.route("/", defaults={'page': 1})
@web.route('/page/<int:page>')
@login_required_if_no_ano
def index(page):
    sort_param = (request.args.get('sort') or 'stored').lower()
    return render_books_list("newest", sort_param, 1, page)


@web.route('/<data>/<sort_param>', defaults={'page': 1, 'book_id': 1})
@web.route('/<data>/<sort_param>/', defaults={'page': 1, 'book_id': 1})
@web.route('/<data>/<sort_param>/<book_id>', defaults={'page': 1})
@web.route('/<data>/<sort_param>/<book_id>/<int:page>')
@login_required_if_no_ano
def books_list(data, sort_param, book_id, page):
    return render_books_list(data, sort_param, book_id, page)


@web.route("/table")
@login_required
def books_table():
    visibility = current_user.view_settings.get('table', {})
    cc = get_cc_columns(filter_config_custom_read=True)
    return render_title_template('book_table.html', title=_(u"Books List"), cc=cc, page="book_table",
                                 visiblility=visibility)

@web.route("/ajax/listbooks")
@login_required
def list_books():
    off = int(request.args.get("offset") or 0)
    limit = int(request.args.get("limit") or config.config_books_per_page)
    search = request.args.get("search")
    sort = request.args.get("sort", "id")
    order = request.args.get("order", "").lower()
    state = None
    join = tuple()

    if sort == "state":
        state = json.loads(request.args.get("state", "[]"))
    elif sort == "tags":
        order = [db.Tags.name.asc()] if order == "asc" else [db.Tags.name.desc()]
        join = db.books_tags_link,db.Books.id == db.books_tags_link.c.book, db.Tags
    elif sort == "series":
        order = [db.Series.name.asc()] if order == "asc" else [db.Series.name.desc()]
        join = db.books_series_link,db.Books.id == db.books_series_link.c.book, db.Series
    elif sort == "publishers":
        order = [db.Publishers.name.asc()] if order == "asc" else [db.Publishers.name.desc()]
        join = db.books_publishers_link,db.Books.id == db.books_publishers_link.c.book, db.Publishers
    elif sort == "authors":
        order = [db.Authors.name.asc(), db.Series.name, db.Books.series_index] if order == "asc" \
            else [db.Authors.name.desc(), db.Series.name.desc(), db.Books.series_index.desc()]
        join = db.books_authors_link, db.Books.id == db.books_authors_link.c.book, db.Authors, \
               db.books_series_link, db.Books.id == db.books_series_link.c.book, db.Series
    elif sort == "languages":
        order = [db.Languages.lang_code.asc()] if order == "asc" else [db.Languages.lang_code.desc()]
        join = db.books_languages_link, db.Books.id == db.books_languages_link.c.book, db.Languages
    elif order and sort in ["sort", "title", "authors_sort", "series_index"]:
        order = [text(sort + " " + order)]
    elif not state:
        order = [db.Books.timestamp.desc()]

    total_count = filtered_count = calibre_db.session.query(db.Books).filter(calibre_db.common_filters(False)).count()

    if state is not None:
        if search:
            books = calibre_db.search_query(search).all()
            filtered_count = len(books)
        else:
            books = calibre_db.session.query(db.Books).filter(calibre_db.common_filters()).all()
        entries = calibre_db.get_checkbox_sorted(books, state, off, limit, order)
    elif search:
        entries, filtered_count, __ = calibre_db.get_search_results(search, off, [order,''], limit, *join)
    else:
        entries, __, __ = calibre_db.fill_indexpage((int(off) / (int(limit)) + 1), limit, db.Books, True, order, *join)

    for entry in entries:
        for index in range(0, len(entry.languages)):
            entry.languages[index].language_name = isoLanguages.get_language_name(get_locale(), entry.languages[
                index].lang_code)
    table_entries = {'totalNotFiltered': total_count, 'total': filtered_count, "rows": entries}
    js_list = json.dumps(table_entries, cls=db.AlchemyEncoder)

    response = make_response(js_list)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

@web.route("/ajax/table_settings", methods=['POST'])
@login_required
def update_table_settings():
    # vals = request.get_json()
    # ToDo: Save table settings
    current_user.view_settings['table'] = json.loads(request.data)
    try:
        try:
            flag_modified(current_user, "view_settings")
        except AttributeError:
            pass
        ub.session.commit()
    except (InvalidRequestError, OperationalError):
        log.error("Invalid request received: %r ", request, )
        return "Invalid request", 400
    return ""


@web.route("/author")
@login_required_if_no_ano
def author_list():
    if current_user.check_visibility(constants.SIDEBAR_AUTHOR):
        if current_user.get_view_property('author', 'dir') == 'desc':
            order = db.Authors.sort.desc()
            order_no = 0
        else:
            order = db.Authors.sort.asc()
            order_no = 1
        entries = calibre_db.session.query(db.Authors, func.count('books_authors_link.book').label('count')) \
            .join(db.books_authors_link).join(db.Books).filter(calibre_db.common_filters()) \
            .group_by(text('books_authors_link.author')).order_by(order).all()
        charlist = calibre_db.session.query(func.upper(func.substr(db.Authors.sort, 1, 1)).label('char')) \
            .join(db.books_authors_link).join(db.Books).filter(calibre_db.common_filters()) \
            .group_by(func.upper(func.substr(db.Authors.sort, 1, 1))).all()
        # If not creating a copy, readonly databases can not display authornames with "|" in it as changing the name
        # starts a change session
        autor_copy = copy.deepcopy(entries)
        for entry in autor_copy:
            entry.Authors.name = entry.Authors.name.replace('|', ',')
        return render_title_template('list.html', entries=autor_copy, folder='web.books_list', charlist=charlist,
                                     title=u"Authors", page="authorlist", data='author', order=order_no)
    else:
        abort(404)

@web.route("/downloadlist")
@login_required_if_no_ano
def download_list():
    if current_user.get_view_property('download', 'dir') == 'desc':
        order = ub.User.name.desc()
        order_no = 0
    else:
        order = ub.User.name.asc()
        order_no = 1
    if current_user.check_visibility(constants.SIDEBAR_DOWNLOAD) and current_user.role_admin():
        entries = ub.session.query(ub.User, func.count(ub.Downloads.book_id).label('count'))\
            .join(ub.Downloads).group_by(ub.Downloads.user_id).order_by(order).all()
        charlist = ub.session.query(func.upper(func.substr(ub.User.name, 1, 1)).label('char')) \
            .filter(ub.User.role.op('&')(constants.ROLE_ANONYMOUS) != constants.ROLE_ANONYMOUS) \
            .group_by(func.upper(func.substr(ub.User.name, 1, 1))).all()
        return render_title_template('list.html', entries=entries, folder='web.books_list', charlist=charlist,
                                     title=_(u"Downloads"), page="downloadlist", data="download", order=order_no)
    else:
        abort(404)


@web.route("/publisher")
@login_required_if_no_ano
def publisher_list():
    if current_user.get_view_property('publisher', 'dir') == 'desc':
        order = db.Publishers.name.desc()
        order_no = 0
    else:
        order = db.Publishers.name.asc()
        order_no = 1
    if current_user.check_visibility(constants.SIDEBAR_PUBLISHER):
        entries = calibre_db.session.query(db.Publishers, func.count('books_publishers_link.book').label('count')) \
            .join(db.books_publishers_link).join(db.Books).filter(calibre_db.common_filters()) \
            .group_by(text('books_publishers_link.publisher')).order_by(order).all()
        charlist = calibre_db.session.query(func.upper(func.substr(db.Publishers.name, 1, 1)).label('char')) \
            .join(db.books_publishers_link).join(db.Books).filter(calibre_db.common_filters()) \
            .group_by(func.upper(func.substr(db.Publishers.name, 1, 1))).all()
        return render_title_template('list.html', entries=entries, folder='web.books_list', charlist=charlist,
                                     title=_(u"Publishers"), page="publisherlist", data="publisher", order=order_no)
    else:
        abort(404)


@web.route("/series")
@login_required_if_no_ano
def series_list():
    if current_user.check_visibility(constants.SIDEBAR_SERIES):
        if current_user.get_view_property('series', 'dir') == 'desc':
            order = db.Series.sort.desc()
            order_no = 0
        else:
            order = db.Series.sort.asc()
            order_no = 1
        if current_user.get_view_property('series', 'series_view') == 'list':
            entries = calibre_db.session.query(db.Series, func.count('books_series_link.book').label('count')) \
                .join(db.books_series_link).join(db.Books).filter(calibre_db.common_filters()) \
                .group_by(text('books_series_link.series')).order_by(order).all()
            charlist = calibre_db.session.query(func.upper(func.substr(db.Series.sort, 1, 1)).label('char')) \
                .join(db.books_series_link).join(db.Books).filter(calibre_db.common_filters()) \
                .group_by(func.upper(func.substr(db.Series.sort, 1, 1))).all()
            return render_title_template('list.html', entries=entries, folder='web.books_list', charlist=charlist,
                                         title=_(u"Series"), page="serieslist", data="series", order=order_no)
        else:
            entries = calibre_db.session.query(db.Books, func.count('books_series_link').label('count'),
                                               func.max(db.Books.series_index), db.Books.id) \
                .join(db.books_series_link).join(db.Series).filter(calibre_db.common_filters())\
                .group_by(text('books_series_link.series')).order_by(order).all()
            charlist = calibre_db.session.query(func.upper(func.substr(db.Series.sort, 1, 1)).label('char')) \
                .join(db.books_series_link).join(db.Books).filter(calibre_db.common_filters()) \
                .group_by(func.upper(func.substr(db.Series.sort, 1, 1))).all()

            return render_title_template('grid.html', entries=entries, folder='web.books_list', charlist=charlist,
                                         title=_(u"Series"), page="serieslist", data="series", bodyClass="grid-view",
                                         order=order_no)
    else:
        abort(404)


@web.route("/ratings")
@login_required_if_no_ano
def ratings_list():
    if current_user.check_visibility(constants.SIDEBAR_RATING):
        if current_user.get_view_property('ratings', 'dir') == 'desc':
            order = db.Ratings.rating.desc()
            order_no = 0
        else:
            order = db.Ratings.rating.asc()
            order_no = 1
        entries = calibre_db.session.query(db.Ratings, func.count('books_ratings_link.book').label('count'),
                                   (db.Ratings.rating / 2).label('name')) \
            .join(db.books_ratings_link).join(db.Books).filter(calibre_db.common_filters()) \
            .group_by(text('books_ratings_link.rating')).order_by(order).all()
        return render_title_template('list.html', entries=entries, folder='web.books_list', charlist=list(),
                                     title=_(u"Ratings list"), page="ratingslist", data="ratings", order=order_no)
    else:
        abort(404)


@web.route("/formats")
@login_required_if_no_ano
def formats_list():
    if current_user.check_visibility(constants.SIDEBAR_FORMAT):
        if current_user.get_view_property('ratings', 'dir') == 'desc':
            order = db.Data.format.desc()
            order_no = 0
        else:
            order = db.Data.format.asc()
            order_no = 1
        entries = calibre_db.session.query(db.Data,
                                           func.count('data.book').label('count'),
                                           db.Data.format.label('format')) \
            .join(db.Books).filter(calibre_db.common_filters()) \
            .group_by(db.Data.format).order_by(order).all()
        return render_title_template('list.html', entries=entries, folder='web.books_list', charlist=list(),
                                     title=_(u"File formats list"), page="formatslist", data="formats", order=order_no)
    else:
        abort(404)


@web.route("/language")
@login_required_if_no_ano
def language_overview():
    if current_user.check_visibility(constants.SIDEBAR_LANGUAGE) and current_user.filter_language() == u"all":
        order_no = 0 if current_user.get_view_property('language', 'dir') == 'desc' else 1
        charlist = list()
        languages = calibre_db.speaking_language(reverse_order=not order_no, with_count=True)
        for lang in languages:
            upper_lang = lang[0].name[0].upper()
            if upper_lang not in charlist:
                charlist.append(upper_lang)
        return render_title_template('languages.html', languages=languages,
                                     charlist=charlist, title=_(u"Languages"), page="langlist",
                                     data="language", order=order_no)
    else:
        abort(404)


@web.route("/category")
@login_required_if_no_ano
def category_list():
    if current_user.check_visibility(constants.SIDEBAR_CATEGORY):
        if current_user.get_view_property('category', 'dir') == 'desc':
            order = db.Tags.name.desc()
            order_no = 0
        else:
            order = db.Tags.name.asc()
            order_no = 1
        entries = calibre_db.session.query(db.Tags, func.count('books_tags_link.book').label('count')) \
            .join(db.books_tags_link).join(db.Books).order_by(order).filter(calibre_db.common_filters()) \
            .group_by(text('books_tags_link.tag')).all()
        charlist = calibre_db.session.query(func.upper(func.substr(db.Tags.name, 1, 1)).label('char')) \
            .join(db.books_tags_link).join(db.Books).filter(calibre_db.common_filters()) \
            .group_by(func.upper(func.substr(db.Tags.name, 1, 1))).all()
        return render_title_template('list.html', entries=entries, folder='web.books_list', charlist=charlist,
                                     title=_(u"Categories"), page="catlist", data="category", order=order_no)
    else:
        abort(404)


# ################################### Task functions ################################################################


@web.route("/tasks")
@login_required
def get_tasks_status():
    # if current user admin, show all email, otherwise only own emails
    tasks = WorkerThread.getInstance().tasks
    answer = render_task_status(tasks)
    return render_title_template('tasks.html', entries=answer, title=_(u"Tasks"), page="tasks")


# method is available without login and not protected by CSRF to make it easy reachable
@app.route("/reconnect", methods=['GET'])
def reconnect():
    calibre_db.reconnect_db(config, ub.app_DB_path)
    return json.dumps({})


# ################################### Search functions ################################################################

@web.route("/search", methods=["GET"])
@login_required_if_no_ano
def search():
    term = request.args.get("query")
    if term:
        return redirect(url_for('web.books_list', data="search", sort_param='stored', query=term.strip()))
    else:
        return render_title_template('search.html',
                                     searchterm="",
                                     result_count=0,
                                     title=_(u"Search"),
                                     page="search")


@web.route("/advsearch", methods=['POST'])
@login_required_if_no_ano
def advanced_search():
    values = dict(request.form)
    params = ['include_tag', 'exclude_tag', 'include_serie', 'exclude_serie', 'include_shelf', 'exclude_shelf',
              'include_language', 'exclude_language', 'include_extension', 'exclude_extension']
    for param in params:
        values[param] = list(request.form.getlist(param))
    flask_session['query'] = json.dumps(values)
    return redirect(url_for('web.books_list', data="advsearch", sort_param='stored', query=""))


def adv_search_custom_columns(cc, term, q):
    for c in cc:
        if c.datatype == "datetime":
            custom_start = term.get('custom_column_' + str(c.id) + '_start')
            custom_end = term.get('custom_column_' + str(c.id) + '_end')
            if custom_start:
                q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                    func.datetime(db.cc_classes[c.id].value) >= func.datetime(custom_start)))
            if custom_end:
                q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                    func.datetime(db.cc_classes[c.id].value) <= func.datetime(custom_end)))
        else:
            custom_query = term.get('custom_column_' + str(c.id))
            if custom_query != '' and custom_query is not None:
                if c.datatype == 'bool':
                    q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                        db.cc_classes[c.id].value == (custom_query == "True")))
                elif c.datatype == 'int' or c.datatype == 'float':
                    q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                        db.cc_classes[c.id].value == custom_query))
                elif c.datatype == 'rating':
                    q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                        db.cc_classes[c.id].value == int(float(custom_query) * 2)))
                else:
                    q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                        func.lower(db.cc_classes[c.id].value).ilike("%" + custom_query + "%")))
    return q


def adv_search_language(q, include_languages_inputs, exclude_languages_inputs):
    if current_user.filter_language() != "all":
        q = q.filter(db.Books.languages.any(db.Languages.lang_code == current_user.filter_language()))
    else:
        for language in include_languages_inputs:
            q = q.filter(db.Books.languages.any(db.Languages.id == language))
        for language in exclude_languages_inputs:
            q = q.filter(not_(db.Books.series.any(db.Languages.id == language)))
    return q


def adv_search_ratings(q, rating_high, rating_low):
    if rating_high:
        rating_high = int(rating_high) * 2
        q = q.filter(db.Books.ratings.any(db.Ratings.rating <= rating_high))
    if rating_low:
        rating_low = int(rating_low) * 2
        q = q.filter(db.Books.ratings.any(db.Ratings.rating >= rating_low))
    return q


def adv_search_read_status(q, read_status):
    if read_status:
        if config.config_read_column:
            try:
                if read_status == "True":
                    q = q.join(db.cc_classes[config.config_read_column], isouter=True) \
                        .filter(db.cc_classes[config.config_read_column].value == True)
                else:
                    q = q.join(db.cc_classes[config.config_read_column], isouter=True) \
                        .filter(coalesce(db.cc_classes[config.config_read_column].value, False) != True)
            except (KeyError, AttributeError):
                log.error(u"Custom Column No.%d is not existing in calibre database", config.config_read_column)
                flash(_("Custom Column No.%(column)d is not existing in calibre database",
                        column=config.config_read_column),
                      category="error")
                return q
        else:
            if read_status == "True":
                q = q.join(ub.ReadBook, db.Books.id == ub.ReadBook.book_id, isouter=True) \
                    .filter(ub.ReadBook.user_id == int(current_user.id),
                            ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED)
            else:
                q = q.join(ub.ReadBook, db.Books.id == ub.ReadBook.book_id, isouter=True) \
                    .filter(ub.ReadBook.user_id == int(current_user.id),
                            coalesce(ub.ReadBook.read_status, 0) != ub.ReadBook.STATUS_FINISHED)
    return q


def adv_search_extension(q, include_extension_inputs, exclude_extension_inputs):
    for extension in include_extension_inputs:
        q = q.filter(db.Books.data.any(db.Data.format == extension))
    for extension in exclude_extension_inputs:
        q = q.filter(not_(db.Books.data.any(db.Data.format == extension)))
    return q


def adv_search_tag(q, include_tag_inputs, exclude_tag_inputs):
    for tag in include_tag_inputs:
        q = q.filter(db.Books.tags.any(db.Tags.id == tag))
    for tag in exclude_tag_inputs:
        q = q.filter(not_(db.Books.tags.any(db.Tags.id == tag)))
    return q


def adv_search_serie(q, include_series_inputs, exclude_series_inputs):
    for serie in include_series_inputs:
        q = q.filter(db.Books.series.any(db.Series.id == serie))
    for serie in exclude_series_inputs:
        q = q.filter(not_(db.Books.series.any(db.Series.id == serie)))
    return q

def adv_search_shelf(q, include_shelf_inputs, exclude_shelf_inputs):
    q = q.outerjoin(ub.BookShelf, db.Books.id == ub.BookShelf.book_id)\
        .filter(or_(ub.BookShelf.shelf == None, ub.BookShelf.shelf.notin_(exclude_shelf_inputs)))
    if len(include_shelf_inputs) > 0:
        q = q.filter(ub.BookShelf.shelf.in_(include_shelf_inputs))
    return q

def extend_search_term(searchterm,
                       author_name,
                       book_title,
                       publisher,
                       pub_start,
                       pub_end,
                       tags,
                       rating_high,
                       rating_low,
                       read_status,
                       ):
    searchterm.extend((author_name.replace('|', ','), book_title, publisher))
    if pub_start:
        try:
            searchterm.extend([_(u"Published after ") +
                               format_date(datetime.strptime(pub_start, "%Y-%m-%d"),
                                           format='medium', locale=get_locale())])
        except ValueError:
            pub_start = u""
    if pub_end:
        try:
            searchterm.extend([_(u"Published before ") +
                               format_date(datetime.strptime(pub_end, "%Y-%m-%d"),
                                           format='medium', locale=get_locale())])
        except ValueError:
            pub_end = u""
    elements = {'tag': db.Tags, 'serie':db.Series, 'shelf':ub.Shelf}
    for key, db_element in elements.items():
        tag_names = calibre_db.session.query(db_element).filter(db_element.id.in_(tags['include_' + key])).all()
        searchterm.extend(tag.name for tag in tag_names)
        tag_names = calibre_db.session.query(db_element).filter(db_element.id.in_(tags['exclude_' + key])).all()
        searchterm.extend(tag.name for tag in tag_names)
    language_names = calibre_db.session.query(db.Languages). \
        filter(db.Languages.id.in_(tags['include_language'])).all()
    if language_names:
        language_names = calibre_db.speaking_language(language_names)
    searchterm.extend(language.name for language in language_names)
    language_names = calibre_db.session.query(db.Languages). \
        filter(db.Languages.id.in_(tags['exclude_language'])).all()
    if language_names:
        language_names = calibre_db.speaking_language(language_names)
    searchterm.extend(language.name for language in language_names)
    if rating_high:
        searchterm.extend([_(u"Rating <= %(rating)s", rating=rating_high)])
    if rating_low:
        searchterm.extend([_(u"Rating >= %(rating)s", rating=rating_low)])
    if read_status:
        searchterm.extend([_(u"Read Status = %(status)s", status=read_status)])
    searchterm.extend(ext for ext in tags['include_extension'])
    searchterm.extend(ext for ext in tags['exclude_extension'])
    # handle custom columns
    searchterm = " + ".join(filter(None, searchterm))
    return searchterm, pub_start, pub_end


def render_adv_search_results(term, offset=None, order=None, limit=None):
    sort = order[0] if order else [db.Books.sort]
    pagination = None

    cc = get_cc_columns(filter_config_custom_read=True)
    calibre_db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
    q = calibre_db.session.query(db.Books).outerjoin(db.books_series_link, db.Books.id == db.books_series_link.c.book)\
        .outerjoin(db.Series)\
        .filter(calibre_db.common_filters(True))

    # parse multiselects to a complete dict
    tags = dict()
    elements = ['tag', 'serie', 'shelf', 'language', 'extension']
    for element in elements:
        tags['include_' + element] = term.get('include_' + element)
        tags['exclude_' + element] = term.get('exclude_' + element)

    author_name = term.get("author_name")
    book_title = term.get("book_title")
    publisher = term.get("publisher")
    pub_start = term.get("publishstart")
    pub_end = term.get("publishend")
    rating_low = term.get("ratinghigh")
    rating_high = term.get("ratinglow")
    description = term.get("comment")
    read_status = term.get("read_status")
    if author_name:
        author_name = author_name.strip().lower().replace(',', '|')
    if book_title:
        book_title = book_title.strip().lower()
    if publisher:
        publisher = publisher.strip().lower()

    searchterm = []
    cc_present = False
    for c in cc:
        if c.datatype == "datetime":
            column_start = term.get('custom_column_' + str(c.id) + '_start')
            column_end = term.get('custom_column_' + str(c.id) + '_end')
            if column_start:
                searchterm.extend([u"{} >= {}".format(c.name,
                                                      format_date(datetime.strptime(column_start, "%Y-%m-%d").date(),
                                                                      format='medium',
                                                                      locale=get_locale())
                                                      )])
                cc_present = True
            if column_end:
                searchterm.extend([u"{} <= {}".format(c.name,
                                                      format_date(datetime.strptime(column_end, "%Y-%m-%d").date(),
                                                                      format='medium',
                                                                      locale=get_locale())
                                                      )])
                cc_present = True
        elif term.get('custom_column_' + str(c.id)):
            searchterm.extend([(u"{}: {}".format(c.name, term.get('custom_column_' + str(c.id))))])
            cc_present = True


    if any(tags.values()) or author_name or book_title or publisher or pub_start or pub_end or rating_low \
       or rating_high or description or cc_present or read_status:
        searchterm, pub_start, pub_end = extend_search_term(searchterm,
                                                            author_name,
                                                            book_title,
                                                            publisher,
                                                            pub_start,
                                                            pub_end,
                                                            tags,
                                                            rating_high,
                                                            rating_low,
                                                            read_status)
        q = q.filter()
        if author_name:
            q = q.filter(db.Books.authors.any(func.lower(db.Authors.name).ilike("%" + author_name + "%")))
        if book_title:
            q = q.filter(func.lower(db.Books.title).ilike("%" + book_title + "%"))
        if pub_start:
            q = q.filter(func.datetime(db.Books.pubdate) > func.datetime(pub_start))
        if pub_end:
            q = q.filter(func.datetime(db.Books.pubdate) < func.datetime(pub_end))
        q = adv_search_read_status(q, read_status)
        if publisher:
            q = q.filter(db.Books.publishers.any(func.lower(db.Publishers.name).ilike("%" + publisher + "%")))
        q = adv_search_tag(q, tags['include_tag'], tags['exclude_tag'])
        q = adv_search_serie(q, tags['include_serie'], tags['exclude_serie'])
        q = adv_search_shelf(q, tags['include_shelf'], tags['exclude_shelf'])
        q = adv_search_extension(q, tags['include_extension'], tags['exclude_extension'])
        q = adv_search_language(q, tags['include_language'], tags['exclude_language'])
        q = adv_search_ratings(q, rating_high, rating_low)

        if description:
            q = q.filter(db.Books.comments.any(func.lower(db.Comments.text).ilike("%" + description + "%")))

        # search custom culumns
        try:
            q = adv_search_custom_columns(cc, term, q)
        except AttributeError as ex:
            log.debug_or_exception(ex)
            flash(_("Error on search for custom columns, please restart Calibre-Web"), category="error")

    q = q.order_by(*sort).all()
    flask_session['query'] = json.dumps(term)
    ub.store_ids(q)
    result_count = len(q)
    if offset is not None and limit is not None:
        offset = int(offset)
        limit_all = offset + int(limit)
        pagination = Pagination((offset / (int(limit)) + 1), limit, result_count)
    else:
        offset = 0
        limit_all = result_count
    return render_title_template('search.html',
                                 adv_searchterm=searchterm,
                                 pagination=pagination,
                                 entries=q[offset:limit_all],
                                 result_count=result_count,
                                 title=_(u"Advanced Search"), page="advsearch",
                                 order=order[1])



@web.route("/advsearch", methods=['GET'])
@login_required_if_no_ano
def advanced_search_form():
    # Build custom columns names
    cc = get_cc_columns(filter_config_custom_read=True)
    return render_prepare_search_form(cc)


# ################################### Download/Send ##################################################################


@web.route("/cover/<int:book_id>")
@login_required_if_no_ano
def get_cover(book_id):
    return get_book_cover(book_id)

@web.route("/robots.txt")
def get_robots():
    return send_from_directory(constants.STATIC_DIR, "robots.txt")

@web.route("/show/<int:book_id>/<book_format>", defaults={'anyname': 'None'})
@web.route("/show/<int:book_id>/<book_format>/<anyname>")
@login_required_if_no_ano
@viewer_required
def serve_book(book_id, book_format, anyname):
    book_format = book_format.split(".")[0]
    book = calibre_db.get_book(book_id)
    data = calibre_db.get_book_format(book_id, book_format.upper())
    if not data:
        return "File not in Database"
    log.info('Serving book: %s', data.name)
    if config.config_use_google_drive:
        try:
            headers = Headers()
            headers["Content-Type"] = mimetypes.types_map.get('.' + book_format, "application/octet-stream")
            df = getFileFromEbooksFolder(book.path, data.name + "." + book_format)
            return do_gdrive_download(df, headers, (book_format.upper() == 'TXT'))
        except AttributeError as ex:
            log.debug_or_exception(ex)
            return "File Not Found"
    else:
        if book_format.upper() == 'TXT':
            try:
                rawdata = open(os.path.join(config.config_calibre_dir, book.path, data.name + "." + book_format),
                               "rb").read()
                result = chardet.detect(rawdata)
                return make_response(
                    rawdata.decode(result['encoding'], 'surrogatepass').encode('utf-8', 'surrogatepass'))
            except FileNotFoundError:
                log.error("File Not Found")
                return "File Not Found"
        return send_from_directory(os.path.join(config.config_calibre_dir, book.path), data.name + "." + book_format)


@web.route("/download/<int:book_id>/<book_format>", defaults={'anyname': 'None'})
@web.route("/download/<int:book_id>/<book_format>/<anyname>")
@login_required_if_no_ano
@download_required
def download_link(book_id, book_format, anyname):
    client = "kobo" if "Kobo" in request.headers.get('User-Agent') else ""
    return get_download_link(book_id, book_format, client)


@web.route('/send/<int:book_id>/<book_format>/<int:convert>', methods=["POST"])
@login_required
@download_required
def send_to_kindle(book_id, book_format, convert):
    if not config.get_mail_server_configured():
        flash(_(u"Please configure the SMTP mail settings first..."), category="error")
    elif current_user.kindle_mail:
        result = send_mail(book_id, book_format, convert, current_user.kindle_mail, config.config_calibre_dir,
                           current_user.name)
        if result is None:
            flash(_(u"Book successfully queued for sending to %(kindlemail)s", kindlemail=current_user.kindle_mail),
                  category="success")
            ub.update_download(book_id, int(current_user.id))
        else:
            flash(_(u"Oops! There was an error sending this book: %(res)s", res=result), category="error")
    else:
        flash(_(u"Please update your profile with a valid Send to Kindle E-mail Address."), category="error")
    if "HTTP_REFERER" in request.environ:
        return redirect(request.environ["HTTP_REFERER"])
    else:
        return redirect(url_for('web.index'))


# ################################### Login Logout ##################################################################


@web.route('/register', methods=['GET', 'POST'])
def register():
    if not config.config_public_reg:
        abort(404)
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('web.index'))
    if not config.get_mail_server_configured():
        flash(_(u"E-Mail server is not configured, please contact your administrator!"), category="error")
        return render_title_template('register.html', title=_("Register"), page="register")

    if request.method == "POST":
        to_save = request.form.to_dict()
        nickname = to_save["email"].strip() if config.config_register_email else to_save.get('name')
        if not nickname or not to_save.get("email"):
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template('register.html', title=_("Register"), page="register")
        try:
            nickname = check_username(nickname)
            email = check_email(to_save["email"])
        except Exception as ex:
            flash(str(ex), category="error")
            return render_title_template('register.html', title=_("Register"), page="register")

        content = ub.User()
        if check_valid_domain(email):
            content.name = nickname
            content.email = email
            password = generate_random_password()
            content.password = generate_password_hash(password)
            content.role = config.config_default_role
            content.sidebar_view = config.config_default_show
            try:
                ub.session.add(content)
                ub.session.commit()
                if feature_support['oauth']:
                    register_user_with_oauth(content)
                send_registration_mail(to_save["email"].strip(), nickname, password)
            except Exception:
                ub.session.rollback()
                flash(_(u"An unknown error occurred. Please try again later."), category="error")
                return render_title_template('register.html', title=_("Register"), page="register")
        else:
            flash(_(u"Your e-mail is not allowed to register"), category="error")
            log.warning('Registering failed for user "%s" e-mail address: %s', nickname, to_save["email"])
            return render_title_template('register.html', title=_("Register"), page="register")
        flash(_(u"Confirmation e-mail was send to your e-mail account."), category="success")
        return redirect(url_for('web.login'))

    if feature_support['oauth']:
        register_user_with_oauth()
    return render_title_template('register.html', config=config, title=_("Register"), page="register")


@web.route('/login', methods=['GET', 'POST'])
def login():
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('web.index'))
    if config.config_login_type == constants.LOGIN_LDAP and not services.ldap:
        log.error(u"Cannot activate LDAP authentication")
        flash(_(u"Cannot activate LDAP authentication"), category="error")
    if request.method == "POST":
        form = request.form.to_dict()
        user = ub.session.query(ub.User).filter(func.lower(ub.User.name) == form['username'].strip().lower()) \
            .first()
        if config.config_login_type == constants.LOGIN_LDAP and services.ldap and user and form['password'] != "":
            login_result, error = services.ldap.bind_user(form['username'], form['password'])
            if login_result:
                login_user(user, remember=bool(form.get('remember_me')))
                ub.store_user_session()
                log.debug(u"You are now logged in as: '%s'", user.name)
                flash(_(u"you are now logged in as: '%(nickname)s'", nickname=user.name),
                      category="success")
                return redirect_back(url_for("web.index"))
            elif login_result is None and user and check_password_hash(str(user.password), form['password']) \
                and user.name != "Guest":
                login_user(user, remember=bool(form.get('remember_me')))
                ub.store_user_session()
                log.info("Local Fallback Login as: '%s'", user.name)
                flash(_(u"Fallback Login as: '%(nickname)s', LDAP Server not reachable, or user not known",
                        nickname=user.name),
                      category="warning")
                return redirect_back(url_for("web.index"))
            elif login_result is None:
                log.info(error)
                flash(_(u"Could not login: %(message)s", message=error), category="error")
            else:
                ip_Address = request.headers.get('X-Forwarded-For', request.remote_addr)
                log.warning('LDAP Login failed for user "%s" IP-address: %s', form['username'], ip_Address)
                flash(_(u"Wrong Username or Password"), category="error")
        else:
            ip_Address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if 'forgot' in form and form['forgot'] == 'forgot':
                if user is not None and user.name != "Guest":
                    ret, __ = reset_password(user.id)
                    if ret == 1:
                        flash(_(u"New Password was send to your email address"), category="info")
                        log.info('Password reset for user "%s" IP-address: %s', form['username'], ip_Address)
                    else:
                        log.error(u"An unknown error occurred. Please try again later")
                        flash(_(u"An unknown error occurred. Please try again later."), category="error")
                else:
                    flash(_(u"Please enter valid username to reset password"), category="error")
                    log.warning('Username missing for password reset IP-address: %s', ip_Address)
            else:
                if user and check_password_hash(str(user.password), form['password']) and user.name != "Guest":
                    login_user(user, remember=bool(form.get('remember_me')))
                    ub.store_user_session()
                    log.debug(u"You are now logged in as: '%s'", user.name)
                    flash(_(u"You are now logged in as: '%(nickname)s'", nickname=user.name), category="success")
                    config.config_is_initial = False
                    return redirect_back(url_for("web.index"))
                else:
                    log.warning('Login failed for user "%s" IP-address: %s', form['username'], ip_Address)
                    flash(_(u"Wrong Username or Password"), category="error")

    next_url = request.args.get('next', default=url_for("web.index"), type=str)
    if url_for("web.logout") == next_url:
        next_url = url_for("web.index")
    return render_title_template('login.html',
                                 title=_(u"Login"),
                                 next_url=next_url,
                                 config=config,
                                 oauth_check=oauth_check,
                                 mail=config.get_mail_server_configured(), page="login")


@web.route('/logout')
@login_required
def logout():
    if current_user is not None and current_user.is_authenticated:
        ub.delete_user_session(current_user.id, flask_session.get('_id',""))
        logout_user()
        if feature_support['oauth'] and (config.config_login_type == 2 or config.config_login_type == 3):
            logout_oauth_user()
    log.debug(u"User logged out")
    return redirect(url_for('web.login'))


# ################################### Users own configuration #########################################################
def change_profile(kobo_support, local_oauth_check, oauth_status, translations, languages):
    to_save = request.form.to_dict()
    current_user.random_books = 0
    if current_user.role_passwd() or current_user.role_admin():
        if to_save.get("password"):
            current_user.password = generate_password_hash(to_save["password"])
    try:
        if to_save.get("kindle_mail", current_user.kindle_mail) != current_user.kindle_mail:
            current_user.kindle_mail = valid_email(to_save["kindle_mail"])
        if to_save.get("email", current_user.email) != current_user.email:
            current_user.email = check_email(to_save["email"])
        if current_user.role_admin():
            if to_save.get("name", current_user.name) != current_user.name:
                # Query User name, if not existing, change
                current_user.name = check_username(to_save["name"])
        current_user.random_books = 1 if to_save.get("show_random") == "on" else 0
        if to_save.get("default_language"):
            current_user.default_language = to_save["default_language"]
        if to_save.get("locale"):
            current_user.locale = to_save["locale"]
        old_state = current_user.kobo_only_shelves_sync
        # 1 -> 0: nothing has to be done
        # 0 -> 1: all synced books have to be added to archived books, + currently synced shelfs which
        # don't have to be synced have to be removed (added to Shelf archive)
        current_user.kobo_only_shelves_sync = int(to_save.get("kobo_only_shelves_sync") == "on") or 0
        if old_state == 0 and current_user.kobo_only_shelves_sync == 1:
            kobo_sync_status.update_on_sync_shelfs(current_user.id)

    except Exception as ex:
        flash(str(ex), category="error")
        return render_title_template("user_edit.html",
                                     content=current_user,
                                     translations=translations,
                                     profile=1,
                                     languages=languages,
                                     title=_(u"%(name)s's profile", name=current_user.name),
                                     page="me",
                                     kobo_support=kobo_support,
                                     registered_oauth=local_oauth_check,
                                     oauth_status=oauth_status)

    val = 0
    for key, __ in to_save.items():
        if key.startswith('show'):
            val += int(key[5:])
    current_user.sidebar_view = val
    if to_save.get("Show_detail_random"):
        current_user.sidebar_view += constants.DETAIL_RANDOM

    try:
        ub.session.commit()
        flash(_(u"Profile updated"), category="success")
        log.debug(u"Profile updated")
    except IntegrityError:
        ub.session.rollback()
        flash(_(u"Found an existing account for this e-mail address"), category="error")
        log.debug(u"Found an existing account for this e-mail address")
    except OperationalError as e:
        ub.session.rollback()
        log.error("Database error: %s", e)
        flash(_(u"Database error: %(error)s.", error=e), category="error")


@web.route("/me", methods=["GET", "POST"])
@login_required
def profile():
    languages = calibre_db.speaking_language()
    translations = babel.list_translations() + [LC('en')]
    kobo_support = feature_support['kobo'] and config.config_kobo_sync
    if feature_support['oauth'] and config.config_login_type == 2:
        oauth_status = get_oauth_status()
        local_oauth_check = oauth_check
    else:
        oauth_status = None
        local_oauth_check = {}

    if request.method == "POST":
        change_profile(kobo_support, local_oauth_check, oauth_status, translations, languages)
    return render_title_template("user_edit.html",
                                 translations=translations,
                                 profile=1,
                                 languages=languages,
                                 content=current_user,
                                 kobo_support=kobo_support,
                                 title=_(u"%(name)s's profile", name=current_user.name),
                                 page="me",
                                 registered_oauth=local_oauth_check,
                                 oauth_status=oauth_status)


# ###################################Show single book ##################################################################


@web.route("/read/<int:book_id>/<book_format>")
@login_required_if_no_ano
@viewer_required
def read_book(book_id, book_format):
    book = calibre_db.get_filtered_book(book_id)
    if not book:
        flash(_(u"Oops! Selected book title is unavailable. File does not exist or is not accessible"), category="error")
        log.debug(u"Oops! Selected book title is unavailable. File does not exist or is not accessible")
        return redirect(url_for("web.index"))

    # check if book has bookmark
    bookmark = None
    if current_user.is_authenticated:
        bookmark = ub.session.query(ub.Bookmark).filter(and_(ub.Bookmark.user_id == int(current_user.id),
                                                             ub.Bookmark.book_id == book_id,
                                                             ub.Bookmark.format == book_format.upper())).first()
    if book_format.lower() == "epub":
        log.debug(u"Start epub reader for %d", book_id)
        return render_title_template('read.html', bookid=book_id, title=book.title, bookmark=bookmark)
    elif book_format.lower() == "pdf":
        log.debug(u"Start pdf reader for %d", book_id)
        return render_title_template('readpdf.html', pdffile=book_id, title=book.title)
    elif book_format.lower() == "txt":
        log.debug(u"Start txt reader for %d", book_id)
        return render_title_template('readtxt.html', txtfile=book_id, title=book.title)
    elif book_format.lower() == "djvu":
        log.debug(u"Start djvu reader for %d", book_id)
        return render_title_template('readdjvu.html', djvufile=book_id, title=book.title)
    else:
        for fileExt in constants.EXTENSIONS_AUDIO:
            if book_format.lower() == fileExt:
                entries = calibre_db.get_filtered_book(book_id)
                log.debug(u"Start mp3 listening for %d", book_id)
                return render_title_template('listenmp3.html', mp3file=book_id, audioformat=book_format.lower(),
                                             entry=entries, bookmark=bookmark)
        for fileExt in ["cbr", "cbt", "cbz"]:
            if book_format.lower() == fileExt:
                all_name = str(book_id)
                title = book.title
                if len(book.series):
                    title = title + " - " + book.series[0].name
                    if book.series_index:
                        title = title + " #" + '{0:.2f}'.format(book.series_index).rstrip('0').rstrip('.')
                log.debug(u"Start comic reader for %d", book_id)
                return render_title_template('readcbr.html', comicfile=all_name, title=title,
                                             extension=fileExt)
        log.debug(u"Oops! Selected book title is unavailable. File does not exist or is not accessible")
        flash(_(u"Oops! Selected book title is unavailable. File does not exist or is not accessible"), category="error")
        return redirect(url_for("web.index"))


@web.route("/book/<int:book_id>")
@login_required_if_no_ano
def show_book(book_id):
    entries = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    if entries:
        for index in range(0, len(entries.languages)):
            entries.languages[index].language_name = isoLanguages.get_language_name(get_locale(), entries.languages[
                index].lang_code)
        cc = get_cc_columns(filter_config_custom_read=True)
        book_in_shelfs = []
        shelfs = ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book_id).all()
        for entry in shelfs:
            book_in_shelfs.append(entry.shelf)

        if not current_user.is_anonymous:
            if not config.config_read_column:
                matching_have_read_book = ub.session.query(ub.ReadBook). \
                    filter(and_(ub.ReadBook.user_id == int(current_user.id), ub.ReadBook.book_id == book_id)).all()
                have_read = len(
                    matching_have_read_book) > 0 and matching_have_read_book[0].read_status == ub.ReadBook.STATUS_FINISHED
            else:
                try:
                    matching_have_read_book = getattr(entries, 'custom_column_' + str(config.config_read_column))
                    have_read = len(matching_have_read_book) > 0 and matching_have_read_book[0].value
                except (KeyError, AttributeError):
                    log.error("Custom Column No.%d is not existing in calibre database", config.config_read_column)
                    have_read = None

            archived_book = ub.session.query(ub.ArchivedBook).\
                filter(and_(ub.ArchivedBook.user_id == int(current_user.id),
                            ub.ArchivedBook.book_id == book_id)).first()
            is_archived = archived_book and archived_book.is_archived

        else:
            have_read = None
            is_archived = None

        entries.tags = sort(entries.tags, key=lambda tag: tag.name)

        entries = calibre_db.order_authors(entries)

        kindle_list = check_send_to_kindle(entries)
        reader_list = check_read_formats(entries)

        audioentries = []
        for media_format in entries.data:
            if media_format.format.lower() in constants.EXTENSIONS_AUDIO:
                audioentries.append(media_format.format.lower())

        return render_title_template('detail.html',
                                     entry=entries,
                                     audioentries=audioentries,
                                     cc=cc,
                                     is_xhr=request.headers.get('X-Requested-With')=='XMLHttpRequest',
                                     title=entries.title,
                                     books_shelfs=book_in_shelfs,
                                     have_read=have_read,
                                     is_archived=is_archived,
                                     kindle_list=kindle_list,
                                     reader_list=reader_list,
                                     page="book")
    else:
        log.debug(u"Oops! Selected book title is unavailable. File does not exist or is not accessible")
        flash(_(u"Oops! Selected book title is unavailable. File does not exist or is not accessible"),
              category="error")
        return redirect(url_for("web.index"))
