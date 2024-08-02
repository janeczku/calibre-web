#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2022 OzzieIsaacs
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

import json
from datetime import datetime

from flask import Blueprint, request, redirect, url_for, flash
from flask import session as flask_session
from .cw_login import current_user
from flask_babel import format_date
from flask_babel import gettext as _
from sqlalchemy.sql.expression import func, not_, and_, or_, text, true
from sqlalchemy.sql.functions import coalesce
from sqlalchemy import exists

from . import logger, db, calibre_db, config, ub
from .usermanagement import login_required_if_no_ano
from .render_template import render_title_template
from .pagination import Pagination


search = Blueprint('search', __name__)

log = logger.create()


@search.route("/search", methods=["GET"])
@login_required_if_no_ano
def simple_search():
    term = request.args.get("query")
    if term:
        return redirect(url_for('web.books_list', data="search", sort_param='stored', query=term.strip()))
    else:
        return render_title_template('search.html',
                                     searchterm="",
                                     result_count=0,
                                     title=_("Search"),
                                     page="search")


@search.route("/advsearch", methods=['POST'])
@login_required_if_no_ano
def advanced_search():
    values = dict(request.form)
    params = ['include_tag', 'exclude_tag', 'include_serie', 'exclude_serie', 'include_shelf', 'exclude_shelf',
              'include_language', 'exclude_language', 'include_extension', 'exclude_extension']
    for param in params:
        values[param] = list(request.form.getlist(param))
    flask_session['query'] = json.dumps(values)
    return redirect(url_for('web.books_list', data="advsearch", sort_param='stored', query=""))


@search.route("/advsearch", methods=['GET'])
@login_required_if_no_ano
def advanced_search_form():
    # Build custom columns names
    cc = calibre_db.get_cc_columns(config, filter_config_custom_read=True)
    return render_prepare_search_form(cc)


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
        elif c.datatype in ["int", "float"]:
            custom_low = term.get('custom_column_' + str(c.id) + '_low')
            custom_high = term.get('custom_column_' + str(c.id) + '_high')
            if custom_low:
                q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                    db.cc_classes[c.id].value >= custom_low))
            if custom_high:
                q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                    db.cc_classes[c.id].value <= custom_high))
        else:
            custom_query = term.get('custom_column_' + str(c.id))
            if c.datatype == 'bool':
                if custom_query != "Any":
                    if custom_query == "":
                        q = q.filter(~getattr(db.Books, 'custom_column_' + str(c.id)).
                                     any(db.cc_classes[c.id].value >= 0))
                    else:
                        q = q.filter(getattr(db.Books, 'custom_column_' + str(c.id)).any(
                            db.cc_classes[c.id].value == bool(custom_query == "True")))
            elif custom_query != '' and custom_query is not None:
                if c.datatype == 'rating':
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


def adv_search_read_status(read_status):
    if not config.config_read_column:
        if read_status == "True":
            db_filter = and_(ub.ReadBook.user_id == int(current_user.id),
                             ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED)
        else:
            db_filter = coalesce(ub.ReadBook.read_status, 0) != ub.ReadBook.STATUS_FINISHED
    else:
        try:
            if read_status == "":
                db_filter = coalesce(db.cc_classes[config.config_read_column].value, 2) == 2
            else:
                db_filter = db.cc_classes[config.config_read_column].value == bool(read_status == "True")
        except (KeyError, AttributeError, IndexError):
            log.error("Custom Column No.{} does not exist in calibre database".format(config.config_read_column))
            flash(_("Custom Column No.%(column)d does not exist in calibre database",
                    column=config.config_read_column),
                  category="error")
            return true()
    return db_filter


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
            searchterm.extend([_("Published after ") +
                               format_date(datetime.strptime(pub_start, "%Y-%m-%d"),
                                           format='medium')])
        except ValueError:
            pub_start = ""
    if pub_end:
        try:
            searchterm.extend([_("Published before ") +
                               format_date(datetime.strptime(pub_end, "%Y-%m-%d"),
                                           format='medium')])
        except ValueError:
            pub_end = ""
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
        searchterm.extend([_("Rating <= %(rating)s", rating=rating_high)])
    if rating_low:
        searchterm.extend([_("Rating >= %(rating)s", rating=rating_low)])
    if read_status != "Any":
        searchterm.extend([_("Read Status = '%(status)s'", status=read_status)])
    searchterm.extend(ext for ext in tags['include_extension'])
    searchterm.extend(ext for ext in tags['exclude_extension'])
    # handle custom columns
    searchterm = " + ".join(filter(None, searchterm))
    return searchterm, pub_start, pub_end


def render_adv_search_results(term, offset=None, order=None, limit=None):
    sort = order[0] if order else [db.Books.sort]
    pagination = None

    cc = calibre_db.get_cc_columns(config, filter_config_custom_read=True)
    calibre_db.session.connection().connection.connection.create_function("lower", 1, db.lcase)
    query = calibre_db.generate_linked_query(config.config_read_column, db.Books)
    q = query.outerjoin(db.books_series_link, db.Books.id == db.books_series_link.c.book)\
        .outerjoin(db.Series)\
        .filter(calibre_db.common_filters(True))

    # parse multi selects to a complete dict
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

    search_term = []
    cc_present = False
    for c in cc:
        if c.datatype == "datetime":
            column_start = term.get('custom_column_' + str(c.id) + '_start')
            column_end = term.get('custom_column_' + str(c.id) + '_end')
            if column_start:
                search_term.extend(["{} >= {}".format(c.name,
                                                       format_date(datetime.strptime(column_start, "%Y-%m-%d").date(),
                                                                   format='medium')
                                                       )])
                cc_present = True
            if column_end:
                search_term.extend(["{} <= {}".format(c.name,
                                                      format_date(datetime.strptime(column_end, "%Y-%m-%d").date(),
                                                                   format='medium')
                                                       )])
                cc_present = True
        if c.datatype in ["int", "float"]:
            column_low = term.get('custom_column_' + str(c.id) + '_low')
            column_high = term.get('custom_column_' + str(c.id) + '_high')
            if column_low:
                search_term.extend(["{} >= {}".format(c.name, column_low)])
                cc_present = True
            if column_high:
                search_term.extend(["{} <= {}".format(c.name,column_high)])
                cc_present = True
        elif c.datatype == "bool":
            if term.get('custom_column_' + str(c.id)) != "Any":
                search_term.extend([("{}: {}".format(c.name, term.get('custom_column_' + str(c.id))))])
                cc_present = True
        elif term.get('custom_column_' + str(c.id)):
            search_term.extend([("{}: {}".format(c.name, term.get('custom_column_' + str(c.id))))])
            cc_present = True

    if any(tags.values()) or author_name or book_title or publisher or pub_start or pub_end or rating_low \
       or rating_high or description or cc_present or read_status != "Any":
        search_term, pub_start, pub_end = extend_search_term(search_term,
                                                             author_name,
                                                             book_title,
                                                             publisher,
                                                             pub_start,
                                                             pub_end,
                                                             tags,
                                                             rating_high,
                                                             rating_low,
                                                             read_status)
        if author_name:
            q = q.filter(db.Books.authors.any(func.lower(db.Authors.name).ilike("%" + author_name + "%")))
        if book_title:
            q = q.filter(func.lower(db.Books.title).ilike("%" + book_title + "%"))
        if pub_start:
            q = q.filter(func.datetime(db.Books.pubdate) > func.datetime(pub_start))
        if pub_end:
            q = q.filter(func.datetime(db.Books.pubdate) < func.datetime(pub_end))
        if read_status != "Any":
            q = q.filter(adv_search_read_status(read_status))
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

        # search custom columns
        try:
            q = adv_search_custom_columns(cc, term, q)
        except AttributeError as ex:
            log.debug_or_exception(ex)
            flash(_("Error on search for custom columns, please restart Calibre-Web"), category="error")

    q = q.order_by(*sort).all()
    flask_session['query'] = json.dumps(term)
    ub.store_combo_ids(q)
    result_count = len(q)
    if offset is not None and limit is not None:
        offset = int(offset)
        limit_all = offset + int(limit)
        pagination = Pagination((offset / (int(limit)) + 1), limit, result_count)
    else:
        offset = 0
        limit_all = result_count
    entries = calibre_db.order_authors(q[offset:limit_all], list_return=True, combined=True)
    return render_title_template('search.html',
                                 adv_searchterm=search_term,
                                 pagination=pagination,
                                 entries=entries,
                                 result_count=result_count,
                                 title=_("Advanced Search"), page="advsearch",
                                 order=order[1])


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
    if current_user.filter_language() == "all":
        languages = calibre_db.speaking_language()
    else:
        languages = None
    return render_title_template('search_form.html', tags=tags, languages=languages, extensions=extensions,
                                 series=series,shelves=shelves, title=_("Advanced Search"), cc=cc, page="advsearch")


def render_search_results(term, offset=None, order=None, limit=None):
    if term:
        join = db.books_series_link, db.Books.id == db.books_series_link.c.book, db.Series
        entries, result_count, pagination = calibre_db.get_search_results(term,
                                                                          config,
                                                                          offset,
                                                                          order,
                                                                          limit,
                                                                          *join)
    else:
        entries = list()
        order = [None, None]
        pagination = result_count = None

    return render_title_template('search.html',
                                 searchterm=term,
                                 pagination=pagination,
                                 query=term,
                                 adv_searchterm=term,
                                 entries=entries,
                                 result_count=result_count,
                                 title=_("Search"),
                                 page="search",
                                 order=order[1])


