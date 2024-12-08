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
from datetime import datetime, timezone
import json
from shutil import copyfile

from markupsafe import escape, Markup  # dependency of flask
from functools import wraps

from flask import Blueprint, request, flash, redirect, url_for, abort, jsonify, make_response, Response
from flask_babel import gettext as _
from flask_babel import lazy_gettext as N_
from flask_babel import get_locale
from .cw_login import current_user
from sqlalchemy.exc import OperationalError, IntegrityError, InterfaceError
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.sql.expression import func

from . import constants, logger, isoLanguages, gdriveutils, uploader, helper, kobo_sync_status
from .clean_html import clean_string
from . import config, ub, db, calibre_db
from .services.worker import WorkerThread
from .tasks.upload import TaskUpload
from .render_template import render_title_template
from .kobo_sync_status import change_archived_books
from .redirect import get_redirect_location
from .file_helper import validate_mime_type
from .usermanagement import user_login_required, login_required_if_no_ano
from .string_helper import strip_whitespaces

editbook = Blueprint('edit-book', __name__)
log = logger.create()


def upload_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_upload():
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


@editbook.route("/ajax/delete/<int:book_id>", methods=["POST"])
@user_login_required
def delete_book_from_details(book_id):
    return delete_book_from_table(book_id, "", True) # , mimetype='application/json')


@editbook.route("/delete/<int:book_id>", defaults={'book_format': ""}, methods=["POST"])
@editbook.route("/delete/<int:book_id>/<string:book_format>", methods=["POST"])
@user_login_required
def delete_book_ajax(book_id, book_format):
    return delete_book_from_table(book_id, book_format, False, request.form.to_dict().get('location', ""))


@editbook.route("/admin/book/<int:book_id>", methods=['GET'])
@login_required_if_no_ano
@edit_required
def show_edit_book(book_id):
    return render_edit_book(book_id)


@editbook.route("/admin/book/<int:book_id>", methods=['POST'])
@login_required_if_no_ano
@edit_required
def edit_book(book_id):
    return do_edit_book(book_id)


@editbook.route("/upload", methods=["POST"])
@login_required_if_no_ano
@upload_required
def upload():
    if len(request.files.getlist("btn-upload-format")):
        book_id = request.form.get('book_id', -1)
        return do_edit_book(book_id, request.files.getlist("btn-upload-format"))
    elif len(request.files.getlist("btn-upload")):
        for requested_file in request.files.getlist("btn-upload"):
            try:
                modify_date = False
                # create the function for sorting...
                calibre_db.create_functions(config)
                meta, error = file_handling_on_upload(requested_file)
                if error:
                    return error

                db_book, input_authors, title_dir = create_book_on_upload(modify_date, meta)

                # Comments need book id therefore only possible after flush
                modify_date |= edit_book_comments(Markup(meta.description).unescape(), db_book)

                book_id = db_book.id
                title = db_book.title
                if config.config_use_google_drive:
                    helper.upload_new_file_gdrive(book_id,
                                                  input_authors[0],
                                                  title,
                                                  title_dir,
                                                  meta.file_path,
                                                  meta.extension.lower())
                    for file_format in db_book.data:
                        file_format.name = (helper.get_valid_filename(title, chars=42) + ' - '
                                            + helper.get_valid_filename(input_authors[0], chars=42))
                else:
                    error = helper.update_dir_structure(book_id,
                                                        config.get_book_path(),
                                                        input_authors[0],
                                                        meta.file_path,
                                                        title_dir + meta.extension.lower())
                move_coverfile(meta, db_book)
                if modify_date:
                    calibre_db.set_metadata_dirty(book_id)
                # save data to database, reread data
                calibre_db.session.commit()

                if config.config_use_google_drive:
                    gdriveutils.updateGdriveCalibreFromLocal()
                if error:
                    flash(error, category="error")
                link = '<a href="{}">{}</a>'.format(url_for('web.show_book', book_id=book_id), escape(title))
                upload_text = N_("File %(file)s uploaded", file=link)
                WorkerThread.add(current_user.name, TaskUpload(upload_text, escape(title)))
                helper.add_book_to_thumbnail_cache(book_id)

                if len(request.files.getlist("btn-upload")) < 2:
                    if current_user.role_edit() or current_user.role_admin():
                        resp = {"location": url_for('edit-book.show_edit_book', book_id=book_id)}
                        return make_response(jsonify(resp))
                    else:
                        resp = {"location": url_for('web.show_book', book_id=book_id)}
                        return make_response(jsonify(resp))
            except (OperationalError, IntegrityError, StaleDataError) as e:
                calibre_db.session.rollback()
                log.error_or_exception("Database error: {}".format(e))
                flash(_("Oops! Database Error: %(error)s.", error=e.orig if hasattr(e, "orig") else e),
                      category="error")
        return make_response(jsonify(location=url_for("web.index")))
    abort(404)


@editbook.route("/admin/book/convert/<int:book_id>", methods=['POST'])
@login_required_if_no_ano
@edit_required
def convert_bookformat(book_id):
    # check to see if we have form fields to work with -  if not send user back
    book_format_from = request.form.get('book_format_from', None)
    book_format_to = request.form.get('book_format_to', None)

    if (book_format_from is None) or (book_format_to is None):
        flash(_("Source or destination format for conversion missing"), category="error")
        return redirect(url_for('edit-book.show_edit_book', book_id=book_id))

    log.info('converting: book id: %s from: %s to: %s', book_id, book_format_from, book_format_to)
    rtn = helper.convert_book_format(book_id, config.get_book_path(), book_format_from.upper(),
                                     book_format_to.upper(), current_user.name)

    if rtn is None:
        flash(_("Book successfully queued for converting to %(book_format)s",
                book_format=book_format_to),
              category="success")
    else:
        flash(_("There was an error converting this book: %(res)s", res=rtn), category="error")
    return redirect(url_for('edit-book.show_edit_book', book_id=book_id))


@editbook.route("/ajax/getcustomenum/<int:c_id>")
@user_login_required
def table_get_custom_enum(c_id):
    ret = list()
    cc = (calibre_db.session.query(db.CustomColumns)
          .filter(db.CustomColumns.id == c_id)
          .filter(db.CustomColumns.datatype.notin_(db.cc_exceptions)).one_or_none())
    ret.append({'value': "", 'text': ""})
    for idx, en in enumerate(cc.get_display_dict()['enum_values']):
        ret.append({'value': en, 'text': en})
    return make_response(jsonify(ret))


@editbook.route("/ajax/editbooks/<param>", methods=['POST'])
@login_required_if_no_ano
@edit_required
def edit_list_book(param):
    vals = request.form.to_dict()
    return edit_book_param(param, vals)

@editbook.route("/ajax/editselectedbooks", methods=['POST'])
@login_required_if_no_ano
@edit_required
def edit_selected_books():
    d = request.get_json()
    selections = d.get('selections')
    title = d.get('title')
    title_sort = d.get('title_sort')
    author_sort = d.get('author_sort')
    authors = d.get('authors')
    categories = d.get('categories')
    series = d.get('series')
    languages = d.get('languages')
    publishers = d.get('publishers')
    comments = d.get('comments')
    checkA = d.get('checkA')

    if len(selections) != 0:
        for book_id in selections:
            vals = {
                "pk": book_id,
                "value": None,
                "checkA": checkA,
            }
            if title:
                vals['value'] = title
                edit_book_param('title', vals)
            if title_sort:
                vals['value'] = title_sort
                edit_book_param('sort', vals)
            if author_sort:
                vals['value'] = author_sort
                edit_book_param('author_sort', vals)
            if authors:
                vals['value'] = authors
                edit_book_param('authors', vals)
            if categories:
                vals['value'] = categories
                edit_book_param('tags', vals)
            if series:
                vals['value'] = series
                edit_book_param('series', vals)
            if languages:
                vals['value'] = languages
                edit_book_param('languages', vals)
            if publishers:
                vals['value'] = publishers
                edit_book_param('publishers', vals)
            if comments:
                vals['value'] = comments
                edit_book_param('comments', vals)
        return json.dumps({'success': True})
    return ""

# Separated from /editbooks so that /editselectedbooks can also use this
#
# param: the property of the book to be changed
# vals - JSON Object:
#   { 
#       'pk': "the book id",
#       'value': "changes value of param to what's passed here"
#       'checkA': "Optional. Used to check if autosort author is enabled. Assumed as true if not passed"
#       'checkT': "Optional. Used to check if autotitle author is enabled. Assumed as true if not passed"
#   }
#
@login_required_if_no_ano
@edit_required
def edit_book_param(param, vals):
    book = calibre_db.get_book(vals['pk'])
    calibre_db.create_functions(config)
    sort_param = ""
    ret = ""
    try:
        if param == 'series_index':
            edit_book_series_index(vals['value'], book)
            ret = make_response(jsonify(success=True, newValue=book.series_index))
        elif param == 'tags':
            edit_book_tags(vals['value'], book)
            ret = make_response(jsonify(success=True, newValue=', '.join([tag.name for tag in book.tags])))
        elif param == 'series':
            edit_book_series(vals['value'], book)
            ret = make_response(jsonify(success=True, newValue=', '.join([serie.name for serie in book.series])))
        elif param == 'publishers':
            edit_book_publisher(vals['value'], book)
            ret = make_response(jsonify(success=True,
                                       newValue=', '.join([publisher.name for publisher in book.publishers])))
        elif param == 'languages':
            invalid = list()
            edit_book_languages(vals['value'], book, invalid=invalid)
            if invalid:
                ret = make_response(jsonify(success=False,
                                           msg='Invalid languages in request: {}'.format(','.join(invalid))))
            else:
                lang_names = list()
                for lang in book.languages:
                    lang_names.append(isoLanguages.get_language_name(get_locale(), lang.lang_code))
                ret = make_response(jsonify(success=True, newValue=', '.join(lang_names)))
        elif param == 'author_sort':
            book.author_sort = vals['value']
            ret = make_response(jsonify(success=True, newValue=book.author_sort))
        elif param == 'title':
            sort_param = book.sort
            if handle_title_on_edit(book, vals.get('value', "")):
                rename_error = helper.update_dir_structure(book.id, config.get_book_path())
                if not rename_error:
                    ret = make_response(jsonify(success=True, newValue=book.title))
                else:
                    ret = make_response(jsonify(success=False, msg=rename_error))
        elif param == 'sort':
            book.sort = vals['value']
            ret = make_response(jsonify(success=True,newValue=book.sort))
        elif param == 'comments':
            edit_book_comments(vals['value'], book)
            ret = make_response(jsonify(success=True, newValue=book.comments[0].text))
        elif param == 'authors':
            input_authors, __ = handle_author_on_edit(book, vals['value'], vals.get('checkA', None) == "true")
            rename_error = helper.update_dir_structure(book.id, config.get_book_path(), input_authors[0])
            if not rename_error:
                ret = make_response(jsonify(
                    success=True,
                    newValue=' & '.join([author.replace('|', ',') for author in input_authors])))
            else:
                ret = make_response(jsonify(success=False, msg=rename_error))
        elif param == 'is_archived':
            is_archived = change_archived_books(book.id, vals['value'] == "True",
                                                message="Book {} archive bit set to: {}".format(book.id, vals['value']))
            if is_archived:
                kobo_sync_status.remove_synced_book(book.id)
            return ""
        elif param == 'read_status':
            ret = helper.edit_book_read_status(book.id, vals['value'] == "True")
            if ret:
                return ret, 400
        elif param.startswith("custom_column_"):
            new_val = dict()
            new_val[param] = vals['value']
            edit_single_cc_data(book.id, book, param[14:], new_val)
            # ToDo: Very hacky find better solution
            if vals['value'] in ["True", "False"]:
                ret = ""
            else:
                ret = make_response(jsonify(success=True, newValue=vals['value']))
        else:
            return _("Parameter not found"), 400
        book.last_modified = datetime.now(timezone.utc)

        calibre_db.session.commit()
        # revert change for sort if automatic fields link is deactivated
        if param == 'title' and vals.get('checkT') == "false":
            book.sort = sort_param
            calibre_db.session.commit()
    except (OperationalError, IntegrityError, StaleDataError) as e:
        calibre_db.session.rollback()
        log.error_or_exception("Database error: {}".format(e))
        ret = make_response(jsonify(success=False,
                                   msg='Database error: {}'.format(e.orig if hasattr(e, "orig") else e)))
    return ret


@editbook.route("/ajax/sort_value/<field>/<int:bookid>")
@user_login_required
def get_sorted_entry(field, bookid):
    if field in ['title', 'authors', 'sort', 'author_sort']:
        book = calibre_db.get_filtered_book(bookid)
        if book:
            if field == 'title':
                return make_response(jsonify(sort=book.sort))
            elif field == 'authors':
                return make_response(jsonify(author_sort=book.author_sort))
            if field == 'sort':
                return make_response(jsonify(sort=book.title))
            if field == 'author_sort':
                return make_response(jsonify(authors=" & ".join([a.name for a in calibre_db.order_authors([book])])))
    return ""

@editbook.route("/ajax/simulatemerge", methods=['POST'])
@user_login_required
@edit_required
def simulate_merge_list_book():
    vals = request.get_json().get('Merge_books')
    if vals:
        to_book = calibre_db.get_book(vals[0]).title
        vals.pop(0)
        if to_book:
            from_book = []
            for book_id in vals:
                from_book.append(calibre_db.get_book(book_id).title)
            return make_response(jsonify({'to': to_book, 'from': from_book}))
    return ""

@editbook.route("/ajax/displayselectedbooks", methods=['POST'])
@user_login_required
@edit_required
def display_selected_books():
    vals = request.get_json().get('selections')
    books = []
    if vals:
        for book_id in vals:
            books.append(calibre_db.get_book(book_id).title)
        return json.dumps({'books': books})
    return ""

@editbook.route("/ajax/archiveselectedbooks", methods=['POST'])
@login_required_if_no_ano
@edit_required
def archive_selected_books():
    vals = request.get_json().get('selections')
    state = request.get_json().get('archive')
    if vals:
        for book_id in vals:
            is_archived = change_archived_books(book_id, state,
                                                message="Book {} archive bit set to: {}".format(book_id, state))
            if is_archived:
                kobo_sync_status.remove_synced_book(book_id)
        return json.dumps({'success': True})
    return ""

@editbook.route("/ajax/deleteselectedbooks", methods=['POST'])
@user_login_required
@edit_required
def delete_selected_books():
    vals = request.get_json().get('selections')
    if vals:
        for book_id in vals:
            delete_book_from_table(book_id, "", True)
        return json.dumps({'success': True})
    return ""

@editbook.route("/ajax/readselectedbooks", methods=['POST'])
@user_login_required
@edit_required
def read_selected_books():
    vals = request.get_json().get('selections')
    markAsRead = request.get_json().get('markAsRead')
    if vals:
        try:
            for book_id in vals:
                ret = helper.edit_book_read_status(book_id, markAsRead)

        except (OperationalError, IntegrityError, StaleDataError) as e:
            calibre_db.session.rollback()
            log.error_or_exception("Database error: {}".format(e))
            ret = Response(json.dumps({'success': False,
                    'msg': 'Database error: {}'.format(e.orig if hasattr(e, "orig") else e)}),
                    mimetype='application/json')

        return json.dumps({'success': True})
    return ""

@editbook.route("/ajax/mergebooks", methods=['POST'])
@user_login_required
@edit_required
def merge_list_book():
    vals = request.get_json().get('Merge_books')
    to_file = list()
    if vals:
        # load all formats from target book
        to_book = calibre_db.get_book(vals[0])
        vals.pop(0)
        if to_book:
            for file in to_book.data:
                to_file.append(file.format)
            to_name = helper.get_valid_filename(to_book.title,
                                                chars=96) + ' - ' + helper.get_valid_filename(to_book.authors[0].name,
                                                                                              chars=96)
            for book_id in vals:
                from_book = calibre_db.get_book(book_id)
                if from_book:
                    for element in from_book.data:
                        if element.format not in to_file:
                            # create new data entry with: book_id, book_format, uncompressed_size, name
                            filepath_new = os.path.normpath(os.path.join(config.get_book_path(),
                                                                         to_book.path,
                                                                         to_name + "." + element.format.lower()))
                            filepath_old = os.path.normpath(os.path.join(config.get_book_path(),
                                                                         from_book.path,
                                                                         element.name + "." + element.format.lower()))
                            copyfile(filepath_old, filepath_new)
                            to_book.data.append(db.Data(to_book.id,
                                                        element.format,
                                                        element.uncompressed_size,
                                                        to_name))
                    delete_book_from_table(from_book.id, "", True)
                    return make_response(jsonify(success=True))
    return ""


@editbook.route("/ajax/xchange", methods=['POST'])
@user_login_required
@edit_required
def table_xchange_author_title():
    vals = request.get_json().get('xchange')
    edited_books_id = False
    if vals:
        for val in vals:
            modify_date = False
            book = calibre_db.get_book(val)
            authors = book.title
            book.authors = calibre_db.order_authors([book])
            author_names = []
            for authr in book.authors:
                author_names.append(authr.name.replace('|', ','))

            title_change = handle_title_on_edit(book, " ".join(author_names))
            input_authors, author_change = handle_author_on_edit(book, authors)
            if author_change or title_change:
                edited_books_id = book.id
                modify_date = True

            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()

            if edited_books_id:
                # toDo: Handle error
                edit_error = helper.update_dir_structure(edited_books_id, config.get_book_path(), input_authors[0])
            if modify_date:
                book.last_modified = datetime.now(timezone.utc)
                calibre_db.set_metadata_dirty(book.id)
            try:
                calibre_db.session.commit()
            except (OperationalError, IntegrityError, StaleDataError) as e:
                calibre_db.session.rollback()
                log.error_or_exception("Database error: {}".format(e))
                return make_response(jsonify(success=False))

            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()
        return make_response(jsonify(success=True))
    return ""


def do_edit_book(book_id, upload_formats=None):
    modify_date = False
    edit_error = False

    # create the function for sorting...
    calibre_db.create_functions(config)

    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    # Book not found
    if not book:
        flash(_("Oops! Selected book is unavailable. File does not exist or is not accessible"),
              category="error")
        return redirect(url_for("web.index"))

    to_save = request.form.to_dict()

    try:
        # Update folder of book on local disk
        edited_books_id = None
        title_author_error = None
        # upload_mode = False
        # handle book title change
        if "title" in to_save:
            title_change = handle_title_on_edit(book, to_save["title"])
        # handle book author change
        if not upload_formats:
            input_authors, author_change = handle_author_on_edit(book, to_save["authors"])
            if author_change or title_change:
                edited_books_id = book.id
                modify_date = True
                title_author_error = helper.update_dir_structure(edited_books_id,
                                                                 config.get_book_path(),
                                                                 input_authors[0])
            if title_author_error:
                flash(title_author_error, category="error")
                calibre_db.session.rollback()
                book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)

            # handle book ratings
            modify_date |= edit_book_ratings(to_save, book)
        else:
            # handle upload other formats from local disk
            to_save, edit_error = upload_book_formats(upload_formats, book, book_id, book.has_cover)
        # handle upload covers from local disk
        cover_upload_success = upload_cover(request, book)
        if cover_upload_success or to_save.get("format_cover"):
            book.has_cover = 1
            modify_date = True

        # upload new covers or new file formats to google drive
        if config.config_use_google_drive:
            gdriveutils.updateGdriveCalibreFromLocal()

        if to_save.get("cover_url",):
            if not current_user.role_upload():
                edit_error = True
                flash(_("User has no rights to upload cover"), category="error")
            if to_save["cover_url"].endswith('/static/generic_cover.jpg'):
                book.has_cover = 0
            else:
                result, error = helper.save_cover_from_url(to_save["cover_url"].strip(), book.path)
                if result is True:
                    book.has_cover = 1
                    modify_date = True
                    helper.replace_cover_thumbnail_cache(book.id)
                else:
                    edit_error = True
                    flash(error, category="error")

        # Add default series_index to book
        modify_date |= edit_book_series_index(to_save.get("series_index"), book)
        # Handle book comments/description
        modify_date |= edit_book_comments(Markup(to_save.get('comments')).unescape(), book)
        # Handle identifiers
        input_identifiers = identifier_list(to_save, book)
        modification, warning = modify_identifiers(input_identifiers, book.identifiers, calibre_db.session)
        if warning:
            flash(_("Identifiers are not Case Sensitive, Overwriting Old Identifier"), category="warning")
        modify_date |= modification
        # Handle book tags
        modify_date |= edit_book_tags(to_save.get('tags'), book)
        # Handle book series
        modify_date |= edit_book_series(to_save.get("series"), book)
        # handle book publisher
        modify_date |= edit_book_publisher(to_save.get('publisher'), book)
        # handle book languages
        try:
            invalid = []
            modify_date |= edit_book_languages(to_save.get('languages'), book, upload_mode=upload_formats,
                                               invalid=invalid)
            if invalid:
                for lang in invalid:
                    flash(_("'%(langname)s' is not a valid language", langname=lang), category="warning")
        except ValueError as e:
            flash(str(e), category="error")
            edit_error = True
        # handle cc data
        modify_date |= edit_all_cc_data(book_id, book, to_save)

        if to_save.get("pubdate") is not None:
            if to_save.get("pubdate"):
                try:
                    book.pubdate = datetime.strptime(to_save["pubdate"], "%Y-%m-%d")
                except ValueError as e:
                    book.pubdate = db.Books.DEFAULT_PUBDATE
                    flash(str(e), category="error")
                    edit_error = True
            else:
                book.pubdate = db.Books.DEFAULT_PUBDATE

        if modify_date:
            book.last_modified = datetime.now(timezone.utc)
            kobo_sync_status.remove_synced_book(edited_books_id, all=True)
            calibre_db.set_metadata_dirty(book.id)

        calibre_db.session.merge(book)
        calibre_db.session.commit()
        if config.config_use_google_drive:
            gdriveutils.updateGdriveCalibreFromLocal()
        if edit_error is not True and title_author_error is not True and cover_upload_success is not False:
            flash(_("Metadata successfully updated"), category="success")

        if upload_formats:
            resp = {"location": url_for('edit-book.show_edit_book', book_id=book_id)}
            return make_response(jsonify(resp))

        if "detail_view" in to_save:
            return redirect(url_for('web.show_book', book_id=book.id))
        else:
            return render_edit_book(book_id)
    except ValueError as e:
        log.error_or_exception("Error: {}".format(e))
        calibre_db.session.rollback()
        flash(str(e), category="error")
        return redirect(url_for('web.show_book', book_id=book.id))
    except (OperationalError, IntegrityError, StaleDataError, InterfaceError) as e:
        log.error_or_exception("Database error: {}".format(e))
        calibre_db.session.rollback()
        flash(_("Oops! Database Error: %(error)s.", error=e.orig if hasattr(e, "orig") else e), category="error")
        return redirect(url_for('web.show_book', book_id=book.id))
    except Exception as ex:
        log.error_or_exception(ex)
        calibre_db.session.rollback()
        flash(_("Error editing book: {}".format(ex)), category="error")
        return redirect(url_for('web.show_book', book_id=book.id))


def merge_metadata(book, meta, to_save):
    if meta.cover:
        to_save['cover_format'] = meta.cover
    for s_field, m_field in [
            ('tags', 'tags'), ('authors', 'author'), ('series', 'series'),
            ('series_index', 'series_id'), ('languages', 'languages'),
            ('title', 'title'), ('comments', 'description')]:
        try:
            val = None if len(getattr(book, s_field)) else getattr(meta, m_field, '')
        except TypeError:
            val = None if len(str(getattr(book, s_field))) else getattr(meta, m_field, '')
        if val:
            to_save[s_field] = val


def identifier_list(to_save, book):
    """Generate a list of Identifiers from form information"""
    id_type_prefix = 'identifier-type-'
    id_val_prefix = 'identifier-val-'
    result = []
    for type_key, type_value in to_save.items():
        if not type_key.startswith(id_type_prefix):
            continue
        val_key = id_val_prefix + type_key[len(id_type_prefix):]
        if val_key not in to_save.keys():
            continue
        if to_save[val_key].startswith("data:"):
            to_save[val_key], __, __ = str.partition(to_save[val_key], ",")
        result.append(db.Identifiers(to_save[val_key], type_value, book.id))
    return result


def prepare_authors(authr, calibre_path, gdrive=False):
    if gdrive:
        calibre_path = ""
    # handle authors
    input_authors = authr.split('&')
    # handle_authors(input_authors)
    input_authors = list(map(lambda it: it.strip().replace(',', '|'), input_authors))
    # Remove duplicates in authors list
    input_authors = helper.uniq(input_authors)

    # we have all author names now
    if input_authors == ['']:
        input_authors = [_('Unknown')]  # prevent empty Author

    for in_aut in input_authors:
        renamed_author = calibre_db.session.query(db.Authors).filter(func.lower(db.Authors.name).ilike(in_aut)).first()
        if renamed_author and in_aut != renamed_author.name:
            old_author_name = renamed_author.name
            # rename author in Database
            create_objects_for_addition(renamed_author, in_aut,"author")
            # rename all Books with this author as first author:
            # rename all book author_sort strings with the new author name
            all_books = calibre_db.session.query(db.Books) \
                .filter(db.Books.authors.any(db.Authors.name == renamed_author.name)).all()
            for one_book in all_books:
                # ToDo: check
                sorted_old_author = helper.get_sorted_author(old_author_name)
                sorted_renamed_author = helper.get_sorted_author(in_aut)
                # change author sort path
                try:
                    author_index = one_book.author_sort.index(sorted_old_author)
                    one_book.author_sort = one_book.author_sort.replace(sorted_old_author, sorted_renamed_author)
                except ValueError:
                    log.error("Sorted author {} not found in database".format(sorted_old_author))
                    author_index = -1
                # change book path if changed author is first author -> match on first position
                if author_index == 0:
                    one_titledir = one_book.path.split('/')[1]
                    one_old_authordir = one_book.path.split('/')[0]
                    # rename author path only once per renamed author -> search all books with author name in book.path
                    # das muss einmal geschehen aber pro Buch geprüft werden ansonsten habe ich das Problem das vlt. 2 gleiche Ordner bis auf Groß/Kleinschreibung vorhanden sind im Umzug
                    new_author_dir = helper.rename_author_path(in_aut, one_old_authordir, renamed_author.name, calibre_path, gdrive)
                    one_book.path = os.path.join(new_author_dir, one_titledir).replace('\\', '/')
                    # rename all books in book data with the new author name and move corresponding files to new locations
                    # old_path = os.path.join(calibre_path, new_author_dir, one_titledir)
                    new_path = os.path.join(calibre_path, new_author_dir, one_titledir)
                    all_new_name = helper.get_valid_filename(one_book.title, chars=42) + ' - ' \
                                   + helper.get_valid_filename(renamed_author.name, chars=42)
                    # change location in database to new author/title path
                    helper.rename_all_files_on_change(one_book, new_path, new_path, all_new_name, gdrive)

    return input_authors


def prepare_authors_on_upload(title, authr):
    if title != _('Unknown') and authr != _('Unknown'):
        entry = calibre_db.check_exists_book(authr, title)
        if entry:
            log.info("Uploaded book probably exists in library")
            flash(_("Uploaded book probably exists in the library, consider to change before upload new: ")
                  + Markup(render_title_template('book_exists_flash.html', entry=entry)), category="warning")

    input_authors = prepare_authors(authr, config.get_book_path(), config.config_use_google_drive)

    sort_authors_list = list()
    db_author = None
    for inp in input_authors:
        # stored_author = calibre_db.session.query(db.Authors).filter(db.Authors.name == inp).first()
        stored_author = calibre_db.session.query(db.Authors).filter(func.lower(db.Authors.name).ilike(inp)).first()
        if not stored_author:
            if not db_author:
                db_author = db.Authors(inp, helper.get_sorted_author(inp), "")
                calibre_db.session.add(db_author)
                calibre_db.session.commit()
            sort_author = helper.get_sorted_author(inp)
        else:
            if not db_author:
                db_author = stored_author
            sort_author = stored_author.sort
        sort_authors_list.append(sort_author)
    sort_authors = ' & '.join(sort_authors_list)
    return sort_authors, input_authors, db_author


def create_book_on_upload(modify_date, meta):
    title = meta.title
    authr = meta.author
    sort_authors, input_authors, db_author = prepare_authors_on_upload(title, authr)

    title_dir = helper.get_valid_filename(title, chars=96)
    author_dir = helper.get_valid_filename(db_author.name, chars=96)

    # combine path and normalize path from Windows systems
    path = os.path.join(author_dir, title_dir).replace('\\', '/')

    try:
        pubdate = datetime.strptime(meta.pubdate[:10], "%Y-%m-%d")
    except ValueError:
        pubdate = datetime(101, 1, 1)

    # Calibre adds books with utc as timezone
    db_book = db.Books(title, "", sort_authors, datetime.now(timezone.utc), pubdate,
                       '1', datetime.now(timezone.utc), path, meta.cover, db_author, [], "")

    modify_date |= modify_database_object(input_authors, db_book.authors, db.Authors, calibre_db.session,
                                          'author')

    # Add series_index to book
    modify_date |= edit_book_series_index(meta.series_id, db_book)

    # add languages
    invalid = []
    modify_date |= edit_book_languages(meta.languages, db_book, upload_mode=True, invalid=invalid)
    if invalid:
        for lang in invalid:
            flash(_("'%(langname)s' is not a valid language", langname=lang), category="warning")

    # handle tags
    modify_date |= edit_book_tags(meta.tags, db_book)

    # handle publisher
    modify_date |= edit_book_publisher(meta.publisher, db_book)

    # handle series
    modify_date |= edit_book_series(meta.series, db_book)

    # Add file to book
    file_size = os.path.getsize(meta.file_path)
    db_data = db.Data(db_book, meta.extension.upper()[1:], file_size, title_dir)
    db_book.data.append(db_data)
    calibre_db.session.add(db_book)

    # flush content, get db_book.id available
    calibre_db.session.flush()

    # Handle identifiers now that db_book.id is available
    identifier_list = []
    for type_key, type_value in meta.identifiers:
        identifier_list.append(db.Identifiers(type_value, type_key, db_book.id))
    modification, warning = modify_identifiers(identifier_list, db_book.identifiers, calibre_db.session)
    if warning:
        flash(_("Identifiers are not Case Sensitive, Overwriting Old Identifier"), category="warning")
    modify_date |= modification

    return db_book, input_authors, title_dir


def file_handling_on_upload(requested_file):
    # check if file extension is correct
    allowed_extensions = config.config_upload_formats.split(',')
    if requested_file:
        if config.config_check_extensions and allowed_extensions != ['']:
            if not validate_mime_type(requested_file, allowed_extensions):
                flash(_("File type isn't allowed to be uploaded to this server"), category="error")
                return None, make_response(jsonify(location=url_for("web.index")))
    if '.' in requested_file.filename:
        file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
        if file_ext not in allowed_extensions and '' not in allowed_extensions:
            flash(
                _("File extension '%(ext)s' is not allowed to be uploaded to this server",
                  ext=file_ext), category="error")
            return None, make_response(jsonify(location=url_for("web.index")))
    else:
        flash(_('File to be uploaded must have an extension'), category="error")
        return None, make_response(jsonify(location=url_for("web.index")))

    # extract metadata from file
    try:
        meta = uploader.upload(requested_file, config.config_rarfile_location)
    except (IOError, OSError):
        log.error("File %s could not saved to temp dir", requested_file.filename)
        flash(_("File %(filename)s could not saved to temp dir",
                filename=requested_file.filename), category="error")
        return None, make_response(jsonify(location=url_for("web.index")))
    return meta, None


def move_coverfile(meta, db_book):
    # move cover to final directory, including book id
    if meta.cover:
        cover_file = meta.cover
    else:
        cover_file = os.path.join(constants.STATIC_DIR, 'generic_cover.jpg')
    new_cover_path = os.path.join(config.get_book_path(), db_book.path)
    try:
        os.makedirs(new_cover_path, exist_ok=True)
        copyfile(cover_file, os.path.join(new_cover_path, "cover.jpg"))
        if meta.cover:
            os.unlink(meta.cover)
    except OSError as e:
        log.error("Failed to move cover file %s: %s", new_cover_path, e)
        flash(_("Failed to Move Cover File %(file)s: %(error)s", file=new_cover_path,
                error=e),
              category="error")


def delete_whole_book(book_id, book):
    # delete book from shelves, Downloads, Read list
    ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book_id).delete()
    ub.session.query(ub.ReadBook).filter(ub.ReadBook.book_id == book_id).delete()
    ub.delete_download(book_id)
    ub.session_commit()

    # check if only this book links to:
    # author, language, series, tags, custom columns
    modify_database_object([''], book.authors, db.Authors, calibre_db.session, 'author')
    modify_database_object([u''], book.tags, db.Tags, calibre_db.session, 'tags')
    modify_database_object([u''], book.series, db.Series, calibre_db.session, 'series')
    modify_database_object([u''], book.languages, db.Languages, calibre_db.session, 'languages')
    modify_database_object([u''], book.publishers, db.Publishers, calibre_db.session, 'publishers')

    cc = calibre_db.session.query(db.CustomColumns). \
        filter(db.CustomColumns.datatype.notin_(db.cc_exceptions)).all()
    for c in cc:
        cc_string = "custom_column_" + str(c.id)
        if not c.is_multiple:
            if len(getattr(book, cc_string)) > 0:
                if c.datatype == 'bool' or c.datatype == 'integer' or c.datatype == 'float':
                    del_cc = getattr(book, cc_string)[0]
                    getattr(book, cc_string).remove(del_cc)
                    log.debug('remove ' + str(c.id))
                    calibre_db.session.delete(del_cc)
                    calibre_db.session.commit()
                elif c.datatype == 'rating':
                    del_cc = getattr(book, cc_string)[0]
                    getattr(book, cc_string).remove(del_cc)
                    if len(del_cc.books) == 0:
                        log.debug('remove ' + str(c.id))
                        calibre_db.session.delete(del_cc)
                        calibre_db.session.commit()
                else:
                    del_cc = getattr(book, cc_string)[0]
                    getattr(book, cc_string).remove(del_cc)
                    log.debug('remove ' + str(c.id))
                    calibre_db.session.delete(del_cc)
                    calibre_db.session.commit()
        else:
            modify_database_object([u''], getattr(book, cc_string), db.cc_classes[c.id],
                                   calibre_db.session, 'custom')
    calibre_db.session.query(db.Books).filter(db.Books.id == book_id).delete()


def render_delete_book_result(book_format, json_response, warning, book_id, location=""):
    if book_format:
        if json_response:
            return jsonify([warning, {"location": url_for("edit-book.show_edit_book", book_id=book_id),
                                         "type": "success",
                                         "format": book_format,
                                         "message": _('Book Format Successfully Deleted')}])
        else:
            flash(_('Book Format Successfully Deleted'), category="success")
            return redirect(url_for('edit-book.show_edit_book', book_id=book_id))
    else:
        if json_response:
            return jsonify([warning, {"location": get_redirect_location(location, "web.index"),
                                         "type": "success",
                                         "format": book_format,
                                         "message": _('Book Successfully Deleted')}])
        else:
            flash(_('Book Successfully Deleted'), category="success")
            return redirect(get_redirect_location(location, "web.index"))


def delete_book_from_table(book_id, book_format, json_response, location=""):
    warning = {}
    if current_user.role_delete_books():
        book = calibre_db.get_book(book_id)
        if book:
            try:
                result, error = helper.delete_book(book, config.get_book_path(), book_format=book_format.upper())
                if not result:
                    if json_response:
                        return jsonify([{"location": url_for("edit-book.show_edit_book", book_id=book_id),
                                            "type": "danger",
                                            "format": "",
                                            "message": error}])
                    else:
                        flash(error, category="error")
                        return redirect(url_for('edit-book.show_edit_book', book_id=book_id))
                if error:
                    if json_response:
                        warning = {"location": url_for("edit-book.show_edit_book", book_id=book_id),
                                   "type": "warning",
                                   "format": "",
                                   "message": error}
                    else:
                        flash(error, category="warning")
                if not book_format:
                    delete_whole_book(book_id, book)
                else:
                    calibre_db.session.query(db.Data).filter(db.Data.book == book.id).\
                        filter(db.Data.format == book_format).delete()
                    if book_format.upper() in ['KEPUB', 'EPUB', 'EPUB3']:
                        kobo_sync_status.remove_synced_book(book.id, True)
                calibre_db.session.commit()
            except Exception as ex:
                log.error_or_exception(ex)
                calibre_db.session.rollback()
                if json_response:
                    return jsonify([{"location": url_for("edit-book.show_edit_book", book_id=book_id),
                                        "type": "danger",
                                        "format": "",
                                        "message": ex}])
                else:
                    flash(str(ex), category="error")
                    return redirect(url_for('edit-book.show_edit_book', book_id=book_id))

        else:
            # book not found
            log.error('Book with id "%s" could not be deleted: not found', book_id)
        return render_delete_book_result(book_format, json_response, warning, book_id, location)
    message = _("You are missing permissions to delete books")
    if json_response:
        return jsonify({"location": url_for("edit-book.show_edit_book", book_id=book_id),
                           "type": "danger",
                           "format": "",
                           "message": message})
    else:
        flash(message, category="error")
        return redirect(url_for('edit-book.show_edit_book', book_id=book_id))


def render_edit_book(book_id):
    cc = calibre_db.session.query(db.CustomColumns).filter(db.CustomColumns.datatype.notin_(db.cc_exceptions)).all()
    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    if not book:
        flash(_("Oops! Selected book is unavailable. File does not exist or is not accessible"),
              category="error")
        return redirect(url_for("web.index"))

    for lang in book.languages:
        lang.language_name = isoLanguages.get_language_name(get_locale(), lang.lang_code)

    book.authors = calibre_db.order_authors([book])

    author_names = []
    for authr in book.authors:
        author_names.append(authr.name.replace('|', ','))

    # Option for showing convert_book button
    valid_source_formats = list()
    allowed_conversion_formats = list()
    kepub_possible = None
    if config.config_converterpath:
        for file in book.data:
            if file.format.lower() in constants.EXTENSIONS_CONVERT_FROM:
                valid_source_formats.append(file.format.lower())
    if config.config_kepubifypath and 'epub' in [file.format.lower() for file in book.data]:
        kepub_possible = True
        if not config.config_converterpath:
            valid_source_formats.append('epub')

    # Determine what formats don't already exist
    if config.config_converterpath:
        allowed_conversion_formats = constants.EXTENSIONS_CONVERT_TO[:]
        for file in book.data:
            if file.format.lower() in allowed_conversion_formats:
                allowed_conversion_formats.remove(file.format.lower())
    if kepub_possible:
        allowed_conversion_formats.append('kepub')
    return render_title_template('book_edit.html', book=book, authors=author_names, cc=cc,
                                 title=_("edit metadata"), page="editbook",
                                 conversion_formats=allowed_conversion_formats,
                                 config=config,
                                 source_formats=valid_source_formats)


def edit_book_ratings(to_save, book):
    changed = False
    if strip_whitespaces(to_save.get("rating", "")):
        old_rating = False
        if len(book.ratings) > 0:
            old_rating = book.ratings[0].rating
        rating_x2 = int(float(to_save.get("rating", "")) * 2)
        if rating_x2 != old_rating:
            changed = True
            is_rating = calibre_db.session.query(db.Ratings).filter(db.Ratings.rating == rating_x2).first()
            if is_rating:
                book.ratings.append(is_rating)
            else:
                new_rating = db.Ratings(rating=rating_x2)
                book.ratings.append(new_rating)
            if old_rating:
                book.ratings.remove(book.ratings[0])
    else:
        if len(book.ratings) > 0:
            book.ratings.remove(book.ratings[0])
            changed = True
    return changed


def edit_book_tags(tags, book):
    if tags is not None:
        input_tags = tags.split(',')
        input_tags = list(map(lambda it: strip_whitespaces(it), input_tags))
        # Remove duplicates
        input_tags = helper.uniq(input_tags)
        return modify_database_object(input_tags, book.tags, db.Tags, calibre_db.session, 'tags')
    return False

def edit_book_series(series, book):
    if series is not None:
        input_series = [strip_whitespaces(series)]
        input_series = [x for x in input_series if x != '']
        return modify_database_object(input_series, book.series, db.Series, calibre_db.session, 'series')
    return False


def edit_book_series_index(series_index, book):
    if series_index:
        # Add default series_index to book
        modify_date = False
        series_index = series_index or '1'
        if not series_index.replace('.', '', 1).isdigit():
            flash(_("Seriesindex: %(seriesindex)s is not a valid number, skipping", seriesindex=series_index), category="warning")
            return False
        if str(book.series_index) != series_index:
            book.series_index = series_index
            modify_date = True
        return modify_date
    return False


# Handle book comments/description
def edit_book_comments(comments, book):
    if comments is not None:
        modify_date = False
        if comments:
            comments = clean_string(comments, book.id)
        if len(book.comments):
            if book.comments[0].text != comments:
                book.comments[0].text = comments
                modify_date = True
        else:
            if comments:
                book.comments.append(db.Comments(comment=comments, book=book.id))
                modify_date = True
        return modify_date


def edit_book_languages(languages, book, upload_mode=False, invalid=None):
    if languages is not None:
        input_languages = languages.split(',')
        unknown_languages = []
        if not upload_mode:
            input_l = isoLanguages.get_language_code_from_name(get_locale(), input_languages, unknown_languages)
        else:
            input_l = isoLanguages.get_valid_language_codes_from_code(get_locale(), input_languages, unknown_languages)
        for lang in unknown_languages:
            log.error("'%s' is not a valid language", lang)
            if isinstance(invalid, list):
                invalid.append(lang)
            else:
                raise ValueError(_("'%(langname)s' is not a valid language", langname=lang))
        # ToDo: Not working correct
        if upload_mode and len(input_l) == 1:
            # If the language of the file is excluded from the users view, it's not imported, to allow the user to view
            # the book it's language is set to the filter language
            if input_l[0] != current_user.filter_language() and current_user.filter_language() != "all":
                input_l[0] = calibre_db.session.query(db.Languages). \
                    filter(db.Languages.lang_code == current_user.filter_language()).first().lang_code
        # Remove duplicates from normalized langcodes
        input_l = helper.uniq(input_l)
        return modify_database_object(input_l, book.languages, db.Languages, calibre_db.session, 'languages')
    return False


def edit_book_publisher(publishers, book):
    if publishers is not None:
        changed = False
        if publishers:
            publisher = strip_whitespaces(publishers)
            if len(book.publishers) == 0 or (len(book.publishers) > 0 and publisher != book.publishers[0].name):
                changed |= modify_database_object([publisher], book.publishers, db.Publishers, calibre_db.session,
                                                  'publisher')
        elif len(book.publishers):
            changed |= modify_database_object([], book.publishers, db.Publishers, calibre_db.session, 'publisher')
        return changed
    return False

def edit_cc_data_value(book_id, book, c, to_save, cc_db_value, cc_string):
    changed = False
    if to_save[cc_string] == 'None':
        to_save[cc_string] = None
    elif c.datatype == 'bool':
        to_save[cc_string] = 1 if to_save[cc_string] == 'True' else 0
    elif c.datatype == 'comments':
        to_save[cc_string] = Markup(to_save[cc_string]).unescape()
        if to_save[cc_string]:
            to_save[cc_string] = clean_string(to_save[cc_string], book_id)
    elif c.datatype == 'datetime':
        try:
            to_save[cc_string] = datetime.strptime(to_save[cc_string], "%Y-%m-%d")
        except ValueError:
            to_save[cc_string] = db.Books.DEFAULT_PUBDATE

    if to_save[cc_string] != cc_db_value:
        if cc_db_value is not None:
            if to_save[cc_string] is not None:
                setattr(getattr(book, cc_string)[0], 'value', to_save[cc_string])
                changed = True
            else:
                del_cc = getattr(book, cc_string)[0]
                getattr(book, cc_string).remove(del_cc)
                calibre_db.session.delete(del_cc)
                changed = True
        else:
            cc_class = db.cc_classes[c.id]
            new_cc = cc_class(value=to_save[cc_string], book=book_id)
            calibre_db.session.add(new_cc)
            changed = True
    return changed, to_save


def edit_cc_data_string(book, c, to_save, cc_db_value, cc_string):
    changed = False
    if c.datatype == 'rating':
        to_save[cc_string] = str(int(float(to_save[cc_string]) * 2))
    if strip_whitespaces(to_save[cc_string]) != cc_db_value:
        if cc_db_value is not None:
            # remove old cc_val
            del_cc = getattr(book, cc_string)[0]
            getattr(book, cc_string).remove(del_cc)
            if len(del_cc.books) == 0:
                calibre_db.session.delete(del_cc)
                changed = True
        cc_class = db.cc_classes[c.id]
        new_cc = calibre_db.session.query(cc_class).filter(
            cc_class.value == strip_whitespaces(to_save[cc_string])).first()
        # if no cc val is found add it
        if new_cc is None:
            new_cc = cc_class(value=strip_whitespaces(to_save[cc_string]))
            calibre_db.session.add(new_cc)
            changed = True
            calibre_db.session.flush()
            new_cc = calibre_db.session.query(cc_class).filter(
                cc_class.value == strip_whitespaces(to_save[cc_string])).first()
        # add cc value to book
        getattr(book, cc_string).append(new_cc)
    return changed, to_save


def edit_single_cc_data(book_id, book, column_id, to_save):
    cc = (calibre_db.session.query(db.CustomColumns)
          .filter(db.CustomColumns.datatype.notin_(db.cc_exceptions))
          .filter(db.CustomColumns.id == column_id)
          .all())
    return edit_cc_data(book_id, book, to_save, cc)


def edit_all_cc_data(book_id, book, to_save):
    cc = calibre_db.session.query(db.CustomColumns).filter(db.CustomColumns.datatype.notin_(db.cc_exceptions)).all()
    return edit_cc_data(book_id, book, to_save, cc)


def edit_cc_data(book_id, book, to_save, cc):
    changed = False
    for c in cc:
        cc_string = "custom_column_" + str(c.id)
        if to_save.get(cc_string) is not None:
            if not c.is_multiple:
                if len(getattr(book, cc_string)) > 0:
                    cc_db_value = getattr(book, cc_string)[0].value
                else:
                    cc_db_value = None
                if strip_whitespaces(to_save[cc_string]):
                    if c.datatype in ['int', 'bool', 'float', "datetime", "comments"]:
                        change, to_save = edit_cc_data_value(book_id, book, c, to_save, cc_db_value, cc_string)
                    else:
                        change, to_save = edit_cc_data_string(book, c, to_save, cc_db_value, cc_string)
                    changed |= change
                else:
                    if cc_db_value is not None:
                        # remove old cc_val
                        del_cc = getattr(book, cc_string)[0]
                        getattr(book, cc_string).remove(del_cc)
                        if not del_cc.books or len(del_cc.books) == 0:
                            calibre_db.session.delete(del_cc)
                            changed = True
            else:
                input_tags = to_save[cc_string].split(',')
                input_tags = list(map(lambda it: strip_whitespaces(it), input_tags))
                changed |= modify_database_object(input_tags,
                                                  getattr(book, cc_string),
                                                  db.cc_classes[c.id],
                                                  calibre_db.session,
                                                  'custom')
    return changed


# returns False if an error occurs or no book is uploaded, in all other cases the ebook metadata to change is returned
def upload_book_formats(requested_files, book, book_id, no_cover=True):
    # Check and handle Uploaded file
    to_save = dict()
    error = False
    allowed_extensions = config.config_upload_formats.split(',')
    for requested_file in requested_files:
        current_filename = requested_file.filename
        if config.config_check_extensions and allowed_extensions != ['']:
            if not validate_mime_type(requested_file, allowed_extensions):
                flash(_("File type isn't allowed to be uploaded to this server"), category="error")
                error = True
                continue
        if current_filename != '':
            if not current_user.role_upload():
                flash(_("User has no rights to upload additional file formats"), category="error")
                error = True
                continue
            if '.' in current_filename:
                file_ext = current_filename.rsplit('.', 1)[-1].lower()
                if file_ext not in allowed_extensions and '' not in allowed_extensions:
                    flash(_("File extension '%(ext)s' is not allowed to be uploaded to this server", ext=file_ext),
                          category="error")
                    error = True
                    continue
            else:
                flash(_('File to be uploaded must have an extension'), category="error")
                error = True
                continue

            file_name = book.path.rsplit('/', 1)[-1]
            filepath = os.path.normpath(os.path.join(config.get_book_path(), book.path))
            saved_filename = os.path.join(filepath, file_name + '.' + file_ext)

            # check if file path exists, otherwise create it, copy file to calibre path and delete temp file
            if not os.path.exists(filepath):
                try:
                    os.makedirs(filepath)
                except OSError:
                    flash(_("Failed to create path %(path)s (Permission denied).", path=filepath),
                          category="error")
                    error = True
                    continue
            try:
                requested_file.save(saved_filename)
            except OSError:
                flash(_("Failed to store file %(file)s.", file=saved_filename), category="error")
                error = True
                continue

            file_size = os.path.getsize(saved_filename)

            # Format entry already exists, no need to update the database
            if calibre_db.get_book_format(book_id, file_ext.upper()):
                log.warning('Book format %s already existing', file_ext.upper())
            else:
                try:
                    db_format = db.Data(book_id, file_ext.upper(), file_size, file_name)
                    calibre_db.session.add(db_format)
                    calibre_db.session.commit()
                    calibre_db.create_functions(config)
                except (OperationalError, IntegrityError, StaleDataError) as e:
                    calibre_db.session.rollback()
                    log.error_or_exception("Database error: {}".format(e))
                    flash(_("Oops! Database Error: %(error)s.", error=e.orig if hasattr(e, "orig") else e),
                          category="error")
                    error = True
                    continue

            # Queue uploader info
            link = '<a href="{}">{}</a>'.format(url_for('web.show_book', book_id=book.id), escape(book.title))
            upload_text = N_("File format %(ext)s added to %(book)s", ext=file_ext.upper(), book=link)
            WorkerThread.add(current_user.name, TaskUpload(upload_text, escape(book.title)))
            meta = uploader.process(
                saved_filename,
                *os.path.splitext(current_filename),
                rar_executable=config.config_rarfile_location,
                no_cover=no_cover)
            merge_metadata(book, meta, to_save)
    #if to_save.get('languages'):
    #    langs = []
    #    for lang_code in to_save['languages'].split(','):
    #        langs.append(isoLanguages.get_language_name(get_locale(), lang_code))
    #    to_save['languages'] = ",".join(langs)
    return to_save, error


def upload_cover(cover_request, book):
    requested_file = cover_request.files.get('btn-upload-cover', None)
    if requested_file:
        # check for empty request
        if requested_file.filename != '':
            if not current_user.role_upload():
                flash(_("User has no rights to upload cover"), category="error")
                return False
            ret, message = helper.save_cover(requested_file, book.path)
            if ret is True:
                helper.replace_cover_thumbnail_cache(book.id)
                return True
            else:
                flash(message, category="error")
                return False
    return None


def handle_title_on_edit(book, book_title):
    # handle book title
    book_title = strip_whitespaces(book_title)
    if book.title != book_title:
        if book_title == '':
            book_title = _(u'Unknown')
        book.title = book_title
        return True
    return False


def handle_author_on_edit(book, author_name, update_stored=True):
    change = False
    input_authors = prepare_authors(author_name, config.get_book_path(), config.config_use_google_drive)

    # Search for each author if author is in database, if not, author name and sorted author name is generated new
    # everything then is assembled for sorted author field in database
    sort_authors_list = list()
    for inp in input_authors:
        stored_author = calibre_db.session.query(db.Authors).filter(db.Authors.name == inp).first()
        if not stored_author:
            stored_author = helper.get_sorted_author(inp.replace('|', ','))
        else:
            stored_author = stored_author.sort
        sort_authors_list.append(helper.get_sorted_author(stored_author))
    sort_authors = ' & '.join(sort_authors_list)
    if book.author_sort != sort_authors and update_stored:
        book.author_sort = sort_authors
        change = True

    change |= modify_database_object(input_authors, book.authors, db.Authors, calibre_db.session, 'author')

    return input_authors, change


def search_objects_remove(db_book_object, db_type, input_elements):
    del_elements = []
    for c_elements in db_book_object:
        found = False
        if db_type == 'custom':
            type_elements = c_elements.value
        else:
            type_elements = c_elements
        for inp_element in input_elements:
            if type_elements == inp_element:
                found = True
                break
        # if the element was not found in the new list, add it to remove list
        if not found:
            del_elements.append(c_elements)
    return del_elements


def search_objects_add(db_book_object, db_type, input_elements):
    add_elements = []
    for inp_element in input_elements:
        found = False
        for c_elements in db_book_object:
            if db_type == 'custom':
                type_elements = c_elements.value
            else:
                type_elements = c_elements
            if type_elements == inp_element:
                found = True
                break
        if not found:
            add_elements.append(inp_element)
    return add_elements


def remove_objects(db_book_object, db_session, del_elements):
    changed = False
    if len(del_elements) > 0:
        for del_element in del_elements:
            db_book_object.remove(del_element)
            changed = True
            if len(del_element.books) == 0:
                db_session.delete(del_element)
                db_session.flush()
    return changed


def add_objects(db_book_object, db_object, db_session, db_type, add_elements):
    changed = False
    if db_type == 'languages':
        db_filter = db_object.lang_code
    elif db_type == 'custom':
        db_filter = db_object.value
    else:
        db_filter = db_object.name
    for add_element in add_elements:
        # check if an element with that name exists
        changed = True
        db_element = db_session.query(db_object).filter((func.lower(db_filter).ilike(add_element))).all()
        # if no element is found add it
        if not db_element:
            if db_type == 'author':
                new_element = db_object(add_element, helper.get_sorted_author(add_element.replace('|', ',')))
            elif db_type == 'series':
                new_element = db_object(add_element, add_element)
            elif db_type == 'custom':
                new_element = db_object(value=add_element)
            elif db_type == 'publisher':
                new_element = db_object(add_element, None)
            else:  # db_type should be tag or language
                new_element = db_object(add_element)
            db_session.add(new_element)
            db_book_object.append(new_element)
        else:
            if len(db_element) == 1:
                db_element = create_objects_for_addition(db_element[0], add_element, db_type)
            else:
                db_el = db_session.query(db_object).filter(db_filter == add_element).first()
                db_element = db_element[0] if not db_el else db_el
            # add element to book
            db_book_object.append(db_element)

    return changed


def create_objects_for_addition(db_element, add_element, db_type):
    if db_type == 'custom':
        if db_element.value != add_element:
            db_element.value = add_element
    elif db_type == 'languages':
        if db_element.lang_code != add_element:
            db_element.lang_code = add_element
    elif db_type == 'series':
        if db_element.name != add_element:
            db_element.name = add_element
            db_element.sort = add_element
    elif db_type == 'author':
        if db_element.name != add_element:
            db_element.name = add_element
            db_element.sort = helper.get_sorted_author(add_element.replace('|', ','))
    elif db_type == 'publisher':
        if db_element.name != add_element:
            db_element.name = add_element
            db_element.sort = None
    elif db_element.name != add_element:
        db_element.name = add_element
    return db_element


# Modifies different Database objects, first check if elements have to be deleted,
# because they are no longer used, than check if elements have to be added to database
def modify_database_object(input_elements, db_book_object, db_object, db_session, db_type):
    # passing input_elements not as a list may lead to undesired results
    if not isinstance(input_elements, list):
        raise TypeError(str(input_elements) + " should be passed as a list")
    input_elements = [x for x in input_elements if x != '']

    changed = False
    # If elements are renamed (upper lower case), rename it
    for rec_a, rec_b in zip(db_book_object, input_elements):
        if db_type == "custom":
            if rec_a.value.casefold() == rec_b.casefold() and rec_a.value != rec_b:
                create_objects_for_addition(rec_a, rec_b, db_type)
        else:
            if rec_a.get().casefold() == rec_b.casefold() and rec_a.get() != rec_b:
                create_objects_for_addition(rec_a, rec_b, db_type)
        # we have all input element (authors, series, tags) names now
    # 1. search for elements to remove
    del_elements = search_objects_remove(db_book_object, db_type, input_elements)
    # 2. search for elements that need to be added
    add_elements = search_objects_add(db_book_object, db_type, input_elements)

    # if there are elements to remove, we remove them now
    changed |= remove_objects(db_book_object, db_session, del_elements)
    # if there are elements to add, we add them now!
    if len(add_elements) > 0:
        changed |= add_objects(db_book_object, db_object, db_session, db_type, add_elements)
    return changed


def modify_identifiers(input_identifiers, db_identifiers, db_session):
    """Modify Identifiers to match input information.
       input_identifiers is a list of read-to-persist Identifiers objects.
       db_identifiers is a list of already persisted list of Identifiers objects."""
    changed = False
    error = False
    input_dict = dict([(identifier.type.lower(), identifier) for identifier in input_identifiers])
    if len(input_identifiers) != len(input_dict):
        error = True
    db_dict = dict([(identifier.type.lower(), identifier) for identifier in db_identifiers])
    # delete db identifiers not present in input or modify them with input val
    for identifier_type, identifier in db_dict.items():
        if identifier_type not in input_dict.keys():
            db_session.delete(identifier)
            changed = True
        else:
            input_identifier = input_dict[identifier_type]
            identifier.type = input_identifier.type
            identifier.val = input_identifier.val
    # add input identifiers not present in db
    for identifier_type, identifier in input_dict.items():
        if identifier_type not in db_dict.keys():
            db_session.add(identifier)
            changed = True
    return changed, error
