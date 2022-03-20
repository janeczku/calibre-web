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
from shutil import copyfile
from uuid import uuid4
from markupsafe import escape
from functools import wraps

try:
    from lxml.html.clean import clean_html
except ImportError:
    clean_html = None

from flask import Blueprint, request, flash, redirect, url_for, abort, Markup, Response
from flask_babel import gettext as _
from flask_login import current_user, login_required
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlite3 import OperationalError as sqliteOperationalError
from . import constants, logger, isoLanguages, gdriveutils, uploader, helper, kobo_sync_status
from . import config, get_locale, ub, db
from . import calibre_db
from .services.worker import WorkerThread
from .tasks.upload import TaskUpload
from .render_template import render_title_template
from .usermanagement import login_required_if_no_ano
from .kobo_sync_status import change_archived_books


EditBook = Blueprint('edit-book', __name__)
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


def search_objects_remove(db_book_object, db_type, input_elements):
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
    return add_elements


def remove_objects(db_book_object, db_session, del_elements):
    changed = False
    if len(del_elements) > 0:
        for del_element in del_elements:
            db_book_object.remove(del_element)
            changed = True
            if len(del_element.books) == 0:
                db_session.delete(del_element)
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
        db_element = db_session.query(db_object).filter(db_filter == add_element).first()
        # if no element is found add it
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
            changed = True
            db_session.add(new_element)
            db_book_object.append(new_element)
        else:
            db_element = create_objects_for_addition(db_element, add_element, db_type)
            # add element to book
            changed = True
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
    # we have all input element (authors, series, tags) names now
    # 1. search for elements to remove
    del_elements = search_objects_remove(db_book_object, db_type, input_elements)
    # 2. search for elements that need to be added
    add_elements = search_objects_add(db_book_object, db_type, input_elements)
    # if there are elements to remove, we remove them now
    changed = remove_objects(db_book_object, db_session, del_elements)
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


@EditBook.route("/ajax/delete/<int:book_id>", methods=["POST"])
@login_required
def delete_book_from_details(book_id):
    return Response(delete_book_from_table(book_id, "", True), mimetype='application/json')


@EditBook.route("/delete/<int:book_id>", defaults={'book_format': ""}, methods=["POST"])
@EditBook.route("/delete/<int:book_id>/<string:book_format>", methods=["POST"])
@login_required
def delete_book_ajax(book_id, book_format):
    return delete_book_from_table(book_id, book_format, False)


def delete_whole_book(book_id, book):
    # delete book from Shelfs, Downloads, Read list
    ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book_id).delete()
    ub.session.query(ub.ReadBook).filter(ub.ReadBook.book_id == book_id).delete()
    ub.delete_download(book_id)
    ub.session_commit()

    # check if only this book links to:
    # author, language, series, tags, custom columns
    modify_database_object([u''], book.authors, db.Authors, calibre_db.session, 'author')
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


def render_delete_book_result(book_format, json_response, warning, book_id):
    if book_format:
        if json_response:
            return json.dumps([warning, {"location": url_for("edit-book.show_edit_book", book_id=book_id),
                                         "type": "success",
                                         "format": book_format,
                                         "message": _('Book Format Successfully Deleted')}])
        else:
            flash(_('Book Format Successfully Deleted'), category="success")
            return redirect(url_for('edit-book.show_edit_book', book_id=book_id))
    else:
        if json_response:
            return json.dumps([warning, {"location": url_for('web.index'),
                                         "type": "success",
                                         "format": book_format,
                                         "message": _('Book Successfully Deleted')}])
        else:
            flash(_('Book Successfully Deleted'), category="success")
            return redirect(url_for('web.index'))


def delete_book_from_table(book_id, book_format, json_response):
    warning = {}
    if current_user.role_delete_books():
        book = calibre_db.get_book(book_id)
        if book:
            try:
                result, error = helper.delete_book(book, config.config_calibre_dir, book_format=book_format.upper())
                if not result:
                    if json_response:
                        return json.dumps([{"location": url_for("edit-book.show_edit_book", book_id=book_id),
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
                    return json.dumps([{"location": url_for("edit-book.show_edit_book", book_id=book_id),
                                        "type": "danger",
                                        "format": "",
                                        "message": ex}])
                else:
                    flash(str(ex), category="error")
                    return redirect(url_for('edit-book.show_edit_book', book_id=book_id))

        else:
            # book not found
            log.error('Book with id "%s" could not be deleted: not found', book_id)
        return render_delete_book_result(book_format, json_response, warning, book_id)
    message = _("You are missing permissions to delete books")
    if json_response:
        return json.dumps({"location": url_for("edit-book.show_edit_book", book_id=book_id),
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
        flash(_(u"Oops! Selected book title is unavailable. File does not exist or is not accessible"),
              category="error")
        return redirect(url_for("web.index"))

    for lang in book.languages:
        lang.language_name = isoLanguages.get_language_name(get_locale(), lang.lang_code)

    book.authors = calibre_db.order_authors([book])

    author_names = []
    for authr in book.authors:
        author_names.append(authr.name.replace('|', ','))

    # Option for showing convertbook button
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
                                 title=_(u"edit metadata"), page="editbook",
                                 conversion_formats=allowed_conversion_formats,
                                 config=config,
                                 source_formats=valid_source_formats)


def edit_book_ratings(to_save, book):
    changed = False
    if to_save.get("rating","").strip():
        old_rating = False
        if len(book.ratings) > 0:
            old_rating = book.ratings[0].rating
        rating_x2 = int(float(to_save.get("rating","")) * 2)
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
    input_tags = tags.split(',')
    input_tags = list(map(lambda it: it.strip(), input_tags))
    # Remove duplicates
    input_tags = helper.uniq(input_tags)
    return modify_database_object(input_tags, book.tags, db.Tags, calibre_db.session, 'tags')


def edit_book_series(series, book):
    input_series = [series.strip()]
    input_series = [x for x in input_series if x != '']
    return modify_database_object(input_series, book.series, db.Series, calibre_db.session, 'series')


def edit_book_series_index(series_index, book):
    # Add default series_index to book
    modify_date = False
    series_index = series_index or '1'
    if not series_index.replace('.', '', 1).isdigit():
        flash(_("%(seriesindex)s is not a valid number, skipping", seriesindex=series_index), category="warning")
        return False
    if str(book.series_index) != series_index:
        book.series_index = series_index
        modify_date = True
    return modify_date


# Handle book comments/description
def edit_book_comments(comments, book):
    modify_date = False
    if comments:
        comments = clean_html(comments)
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
    input_languages = languages.split(',')
    unknown_languages = []
    if not upload_mode:
        input_l = isoLanguages.get_language_codes(get_locale(), input_languages, unknown_languages)
    else:
        input_l = isoLanguages.get_valid_language_codes(get_locale(), input_languages, unknown_languages)
    for lang in unknown_languages:
        log.error("'%s' is not a valid language", lang)
        if isinstance(invalid, list):
            invalid.append(lang)
        else:
            raise ValueError(_(u"'%(langname)s' is not a valid language", langname=lang))
    # ToDo: Not working correct
    if upload_mode and len(input_l) == 1:
        # If the language of the file is excluded from the users view, it's not imported, to allow the user to view
        # the book it's language is set to the filter language
        if input_l[0] != current_user.filter_language() and current_user.filter_language() != "all":
            input_l[0] = calibre_db.session.query(db.Languages). \
                filter(db.Languages.lang_code == current_user.filter_language()).first().lang_code
    # Remove duplicates
    input_l = helper.uniq(input_l)
    return modify_database_object(input_l, book.languages, db.Languages, calibre_db.session, 'languages')


def edit_book_publisher(publishers, book):
    changed = False
    if publishers:
        publisher = publishers.rstrip().strip()
        if len(book.publishers) == 0 or (len(book.publishers) > 0 and publisher != book.publishers[0].name):
            changed |= modify_database_object([publisher], book.publishers, db.Publishers, calibre_db.session,
                                              'publisher')
    elif len(book.publishers):
        changed |= modify_database_object([], book.publishers, db.Publishers, calibre_db.session, 'publisher')
    return changed


def edit_cc_data_value(book_id, book, c, to_save, cc_db_value, cc_string):
    changed = False
    if to_save[cc_string] == 'None':
        to_save[cc_string] = None
    elif c.datatype == 'bool':
        to_save[cc_string] = 1 if to_save[cc_string] == 'True' else 0
    elif c.datatype == 'comments':
        to_save[cc_string] = Markup(to_save[cc_string]).unescape()
        if to_save[cc_string]:
            to_save[cc_string] = clean_html(to_save[cc_string])
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
    if to_save[cc_string].strip() != cc_db_value:
        if cc_db_value is not None:
            # remove old cc_val
            del_cc = getattr(book, cc_string)[0]
            getattr(book, cc_string).remove(del_cc)
            if len(del_cc.books) == 0:
                calibre_db.session.delete(del_cc)
                changed = True
        cc_class = db.cc_classes[c.id]
        new_cc = calibre_db.session.query(cc_class).filter(
            cc_class.value == to_save[cc_string].strip()).first()
        # if no cc val is found add it
        if new_cc is None:
            new_cc = cc_class(value=to_save[cc_string].strip())
            calibre_db.session.add(new_cc)
            changed = True
            calibre_db.session.flush()
            new_cc = calibre_db.session.query(cc_class).filter(
                cc_class.value == to_save[cc_string].strip()).first()
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
        if not c.is_multiple:
            if len(getattr(book, cc_string)) > 0:
                cc_db_value = getattr(book, cc_string)[0].value
            else:
                cc_db_value = None
            if to_save[cc_string].strip():
                if c.datatype in ['int', 'bool', 'float', "datetime", "comments"]:
                    changed, to_save = edit_cc_data_value(book_id, book, c, to_save, cc_db_value, cc_string)
                else:
                    changed, to_save = edit_cc_data_string(book, c, to_save, cc_db_value, cc_string)
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
            input_tags = list(map(lambda it: it.strip(), input_tags))
            changed |= modify_database_object(input_tags,
                                              getattr(book, cc_string),
                                              db.cc_classes[c.id],
                                              calibre_db.session,
                                              'custom')
    return changed

# returns None if no file is uploaded
# returns False if an error occours, in all other cases the ebook metadata is returned
def upload_single_file(file_request, book, book_id):
    # Check and handle Uploaded file
    requested_file = file_request.files.get('btn-upload-format', None)
    if requested_file:
        # check for empty request
        if requested_file.filename != '':
            if not current_user.role_upload():
                flash(_(u"User has no rights to upload additional file formats"), category="error")
                return False
            if '.' in requested_file.filename:
                file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
                if file_ext not in constants.EXTENSIONS_UPLOAD and '' not in constants.EXTENSIONS_UPLOAD:
                    flash(_("File extension '%(ext)s' is not allowed to be uploaded to this server", ext=file_ext),
                          category="error")
                    return False
            else:
                flash(_('File to be uploaded must have an extension'), category="error")
                return False

            file_name = book.path.rsplit('/', 1)[-1]
            filepath = os.path.normpath(os.path.join(config.config_calibre_dir, book.path))
            saved_filename = os.path.join(filepath, file_name + '.' + file_ext)

            # check if file path exists, otherwise create it, copy file to calibre path and delete temp file
            if not os.path.exists(filepath):
                try:
                    os.makedirs(filepath)
                except OSError:
                    flash(_(u"Failed to create path %(path)s (Permission denied).", path=filepath), category="error")
                    return False
            try:
                requested_file.save(saved_filename)
            except OSError:
                flash(_(u"Failed to store file %(file)s.", file=saved_filename), category="error")
                return False

            file_size = os.path.getsize(saved_filename)
            is_format = calibre_db.get_book_format(book_id, file_ext.upper())

            # Format entry already exists, no need to update the database
            if is_format:
                log.warning('Book format %s already existing', file_ext.upper())
            else:
                try:
                    db_format = db.Data(book_id, file_ext.upper(), file_size, file_name)
                    calibre_db.session.add(db_format)
                    calibre_db.session.commit()
                    calibre_db.update_title_sort(config)
                except (OperationalError, IntegrityError) as e:
                    calibre_db.session.rollback()
                    log.error_or_exception("Database error: {}".format(e))
                    flash(_(u"Database error: %(error)s.", error=e.orig), category="error")
                    return False # return redirect(url_for('web.show_book', book_id=book.id))

            # Queue uploader info
            link = '<a href="{}">{}</a>'.format(url_for('web.show_book', book_id=book.id), escape(book.title))
            upload_text = _(u"File format %(ext)s added to %(book)s", ext=file_ext.upper(), book=link)
            WorkerThread.add(current_user.name, TaskUpload(upload_text, escape(book.title)))

            return uploader.process(
                saved_filename, *os.path.splitext(requested_file.filename),
                rarExecutable=config.config_rarfile_location)
    return None

def upload_cover(cover_request, book):
    requested_file = cover_request.files.get('btn-upload-cover', None)
    if requested_file:
        # check for empty request
        if requested_file.filename != '':
            if not current_user.role_upload():
                flash(_(u"User has no rights to upload cover"), category="error")
                return False
            ret, message = helper.save_cover(requested_file, book.path)
            if ret is True:
                return True
            else:
                flash(message, category="error")
                return False
    return None


def handle_title_on_edit(book, book_title):
    # handle book title
    book_title = book_title.rstrip().strip()
    if book.title != book_title:
        if book_title == '':
            book_title = _(u'Unknown')
        book.title = book_title
        return True
    return False


def handle_author_on_edit(book, author_name, update_stored=True):
    # handle author(s)
    input_authors, renamed = prepare_authors(author_name)

    change = modify_database_object(input_authors, book.authors, db.Authors, calibre_db.session, 'author')

    # Search for each author if author is in database, if not, author name and sorted author name is generated new
    # everything then is assembled for sorted author field in database
    sort_authors_list = list()
    for inp in input_authors:
        stored_author = calibre_db.session.query(db.Authors).filter(db.Authors.name == inp).first()
        if not stored_author:
            stored_author = helper.get_sorted_author(inp)
        else:
            stored_author = stored_author.sort
        sort_authors_list.append(helper.get_sorted_author(stored_author))
    sort_authors = ' & '.join(sort_authors_list)
    if book.author_sort != sort_authors and update_stored:
        book.author_sort = sort_authors
        change = True
    return input_authors, change, renamed

@EditBook.route("/admin/book/<int:book_id>", methods=['GET'])
@login_required_if_no_ano
@edit_required
def show_edit_book(book_id):
    return render_edit_book(book_id)


@EditBook.route("/admin/book/<int:book_id>", methods=['POST'])
@login_required_if_no_ano
@edit_required
def edit_book(book_id):
    modify_date = False
    edit_error = False

    # create the function for sorting...
    try:
        calibre_db.update_title_sort(config)
    except sqliteOperationalError as e:
        log.error_or_exception(e)
        calibre_db.session.rollback()

    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    # Book not found
    if not book:
        flash(_(u"Oops! Selected book title is unavailable. File does not exist or is not accessible"),
              category="error")
        return redirect(url_for("web.index"))

    to_save = request.form.to_dict()

    try:
        # Update folder of book on local disk
        edited_books_id = None
        title_author_error = None
        # handle book title change
        title_change = handle_title_on_edit(book, to_save["book_title"])
        # handle book author change
        input_authors, author_change, renamed = handle_author_on_edit(book, to_save["author_name"])
        if author_change or title_change:
            edited_books_id = book.id
            modify_date = True
            title_author_error = helper.update_dir_structure(edited_books_id,
                                                             config.config_calibre_dir,
                                                             input_authors[0],
                                                             renamed_author=renamed)
        if title_author_error:
            flash(title_author_error, category="error")
            calibre_db.session.rollback()
            book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)

        # handle upload other formats from local disk
        meta = upload_single_file(request, book, book_id)
        # only merge metadata if file was uploaded and no error occurred (meta equals not false or none)
        if meta:
            merge_metadata(to_save, meta)
        # handle upload covers from local disk
        cover_upload_success = upload_cover(request, book)
        if cover_upload_success:
            book.has_cover = 1
            modify_date = True

        # upload new covers or new file formats to google drive
        if config.config_use_google_drive:
            gdriveutils.updateGdriveCalibreFromLocal()

        if to_save.get("cover_url", None):
            if not current_user.role_upload():
                edit_error = True
                flash(_(u"User has no rights to upload cover"), category="error")
            if to_save["cover_url"].endswith('/static/generic_cover.jpg'):
                book.has_cover = 0
            else:
                result, error = helper.save_cover_from_url(to_save["cover_url"], book.path)
                if result is True:
                    book.has_cover = 1
                    modify_date = True
                else:
                    flash(error, category="error")

        # Add default series_index to book
        modify_date |= edit_book_series_index(to_save["series_index"], book)
        # Handle book comments/description
        modify_date |= edit_book_comments(Markup(to_save['description']).unescape(), book)
        # Handle identifiers
        input_identifiers = identifier_list(to_save, book)
        modification, warning = modify_identifiers(input_identifiers, book.identifiers, calibre_db.session)
        if warning:
            flash(_("Identifiers are not Case Sensitive, Overwriting Old Identifier"), category="warning")
        modify_date |= modification
        # Handle book tags
        modify_date |= edit_book_tags(to_save['tags'], book)
        # Handle book series
        modify_date |= edit_book_series(to_save["series"], book)
        # handle book publisher
        modify_date |= edit_book_publisher(to_save['publisher'], book)
        # handle book languages
        try:
            modify_date |= edit_book_languages(to_save['languages'], book)
        except ValueError as e:
            flash(str(e), category="error")
            edit_error = True
        # handle book ratings
        modify_date |= edit_book_ratings(to_save, book)
        # handle cc data
        modify_date |= edit_all_cc_data(book_id, book, to_save)

        if to_save.get("pubdate", None):
            try:
                book.pubdate = datetime.strptime(to_save["pubdate"], "%Y-%m-%d")
            except ValueError as e:
                book.pubdate = db.Books.DEFAULT_PUBDATE
                flash(str(e), category="error")
                edit_error = True
        else:
            book.pubdate = db.Books.DEFAULT_PUBDATE

        if modify_date:
            book.last_modified = datetime.utcnow()
            kobo_sync_status.remove_synced_book(edited_books_id, all=True)

        calibre_db.session.merge(book)
        calibre_db.session.commit()
        if config.config_use_google_drive:
            gdriveutils.updateGdriveCalibreFromLocal()
        if meta is not False \
            and edit_error is not True \
                and title_author_error is not True \
                and cover_upload_success is not False:
            flash(_("Metadata successfully updated"), category="success")
        if "detail_view" in to_save:
            return redirect(url_for('web.show_book', book_id=book.id))
        else:
            return render_edit_book(book_id)
    except ValueError as e:
        log.error_or_exception("Error: {}".format(e))
        calibre_db.session.rollback()
        flash(str(e), category="error")
        return redirect(url_for('web.show_book', book_id=book.id))
    except (OperationalError, IntegrityError) as e:
        log.error_or_exception("Database error: {}".format(e))
        calibre_db.session.rollback()
        flash(_(u"Database error: %(error)s.", error=e.orig), category="error")
        return redirect(url_for('web.show_book', book_id=book.id))
    except Exception as ex:
        log.error_or_exception(ex)
        calibre_db.session.rollback()
        flash(_("Error editing book: {}".format(ex)), category="error")
        return redirect(url_for('web.show_book', book_id=book.id))


def merge_metadata(to_save, meta):
    if to_save.get('author_name', "") == _(u'Unknown'):
        to_save['author_name'] = ''
    if to_save.get('book_title', "") == _(u'Unknown'):
        to_save['book_title'] = ''
    for s_field, m_field in [
            ('tags', 'tags'), ('author_name', 'author'), ('series', 'series'),
            ('series_index', 'series_id'), ('languages', 'languages'),
            ('book_title', 'title')]:
        to_save[s_field] = to_save[s_field] or getattr(meta, m_field, '')
    to_save["description"] = to_save["description"] or Markup(
        getattr(meta, 'description', '')).unescape()


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
        result.append(db.Identifiers(to_save[val_key], type_value, book.id))
    return result


def prepare_authors(authr):
    # handle authors
    input_authors = authr.split('&')
    # handle_authors(input_authors)
    input_authors = list(map(lambda it: it.strip().replace(',', '|'), input_authors))
    # Remove duplicates in authors list
    input_authors = helper.uniq(input_authors)

    # we have all author names now
    if input_authors == ['']:
        input_authors = [_(u'Unknown')]  # prevent empty Author

    renamed = list()
    for in_aut in input_authors:
        renamed_author = calibre_db.session.query(db.Authors).filter(db.Authors.name == in_aut).first()
        if renamed_author and in_aut != renamed_author.name:
            renamed.append(renamed_author.name)
            all_books = calibre_db.session.query(db.Books) \
                .filter(db.Books.authors.any(db.Authors.name == renamed_author.name)).all()
            sorted_renamed_author = helper.get_sorted_author(renamed_author.name)
            sorted_old_author = helper.get_sorted_author(in_aut)
            for one_book in all_books:
                one_book.author_sort = one_book.author_sort.replace(sorted_renamed_author, sorted_old_author)
    return input_authors, renamed


def prepare_authors_on_upload(title, authr):
    if title != _(u'Unknown') and authr != _(u'Unknown'):
        entry = calibre_db.check_exists_book(authr, title)
        if entry:
            log.info("Uploaded book probably exists in library")
            flash(_(u"Uploaded book probably exists in the library, consider to change before upload new: ")
                  + Markup(render_title_template('book_exists_flash.html', entry=entry)), category="warning")

    input_authors, renamed = prepare_authors(authr)

    sort_authors_list = list()
    db_author = None
    for inp in input_authors:
        stored_author = calibre_db.session.query(db.Authors).filter(db.Authors.name == inp).first()
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
    return sort_authors, input_authors, db_author, renamed


def create_book_on_upload(modify_date, meta):
    title = meta.title
    authr = meta.author
    sort_authors, input_authors, db_author, renamed_authors = prepare_authors_on_upload(title, authr)

    title_dir = helper.get_valid_filename(title, chars=96)
    author_dir = helper.get_valid_filename(db_author.name, chars=96)

    # combine path and normalize path from Windows systems
    path = os.path.join(author_dir, title_dir).replace('\\', '/')

    # Calibre adds books with utc as timezone
    db_book = db.Books(title, "", sort_authors, datetime.utcnow(), datetime(101, 1, 1),
                       '1', datetime.utcnow(), path, meta.cover, db_author, [], "")

    modify_date |= modify_database_object(input_authors, db_book.authors, db.Authors, calibre_db.session,
                                          'author')

    # Add series_index to book
    modify_date |= edit_book_series_index(meta.series_id, db_book)

    # add languages
    invalid = []
    modify_date |= edit_book_languages(meta.languages, db_book, upload_mode=True, invalid=invalid)
    if invalid:
        for lang in invalid:
            flash(_(u"'%(langname)s' is not a valid language", langname=lang), category="warning")

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
    return db_book, input_authors, title_dir, renamed_authors


def file_handling_on_upload(requested_file):
    # check if file extension is correct
    if '.' in requested_file.filename:
        file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
        if file_ext not in constants.EXTENSIONS_UPLOAD and '' not in constants.EXTENSIONS_UPLOAD:
            flash(
                _("File extension '%(ext)s' is not allowed to be uploaded to this server",
                  ext=file_ext), category="error")
            return None, Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')
    else:
        flash(_('File to be uploaded must have an extension'), category="error")
        return None, Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')

    # extract metadata from file
    try:
        meta = uploader.upload(requested_file, config.config_rarfile_location)
    except (IOError, OSError):
        log.error("File %s could not saved to temp dir", requested_file.filename)
        flash(_(u"File %(filename)s could not saved to temp dir",
                filename=requested_file.filename), category="error")
        return None, Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')
    return meta, None


def move_coverfile(meta, db_book):
    # move cover to final directory, including book id
    if meta.cover:
        coverfile = meta.cover
    else:
        coverfile = os.path.join(constants.STATIC_DIR, 'generic_cover.jpg')
    new_coverpath = os.path.join(config.config_calibre_dir, db_book.path)
    try:
        os.makedirs(new_coverpath, exist_ok=True)
        copyfile(coverfile, os.path.join(new_coverpath, "cover.jpg"))
        if meta.cover:
            os.unlink(meta.cover)
    except OSError as e:
        log.error("Failed to move cover file %s: %s", new_coverpath, e)
        flash(_(u"Failed to Move Cover File %(file)s: %(error)s", file=new_coverpath,
                error=e),
              category="error")


@EditBook.route("/upload", methods=["POST"])
@login_required_if_no_ano
@upload_required
def upload():
    if not config.config_uploading:
        abort(404)
    if request.method == 'POST' and 'btn-upload' in request.files:
        for requested_file in request.files.getlist("btn-upload"):
            try:
                modify_date = False
                # create the function for sorting...
                calibre_db.update_title_sort(config)
                calibre_db.session.connection().connection.connection.create_function('uuid4', 0, lambda: str(uuid4()))

                meta, error = file_handling_on_upload(requested_file)
                if error:
                    return error

                db_book, input_authors, title_dir, renamed_authors = create_book_on_upload(modify_date, meta)

                # Comments need book id therefore only possible after flush
                modify_date |= edit_book_comments(Markup(meta.description).unescape(), db_book)

                book_id = db_book.id
                title = db_book.title
                if config.config_use_google_drive:
                    helper.upload_new_file_gdrive(book_id,
                                                  input_authors[0],
                                                  renamed_authors,
                                                  title,
                                                  title_dir,
                                                  meta.file_path,
                                                  meta.extension.lower())
                else:
                    error = helper.update_dir_structure(book_id,
                                                        config.config_calibre_dir,
                                                        input_authors[0],
                                                        meta.file_path,
                                                        title_dir + meta.extension.lower(),
                                                        renamed_author=renamed_authors)

                move_coverfile(meta, db_book)

                # save data to database, reread data
                calibre_db.session.commit()

                if config.config_use_google_drive:
                    gdriveutils.updateGdriveCalibreFromLocal()
                if error:
                    flash(error, category="error")
                link = '<a href="{}">{}</a>'.format(url_for('web.show_book', book_id=book_id), escape(title))
                upload_text = _(u"File %(file)s uploaded", file=link)
                WorkerThread.add(current_user.name, TaskUpload(upload_text, escape(title)))

                if len(request.files.getlist("btn-upload")) < 2:
                    if current_user.role_edit() or current_user.role_admin():
                        resp = {"location": url_for('edit-book.show_edit_book', book_id=book_id)}
                        return Response(json.dumps(resp), mimetype='application/json')
                    else:
                        resp = {"location": url_for('web.show_book', book_id=book_id)}
                        return Response(json.dumps(resp), mimetype='application/json')
            except (OperationalError, IntegrityError) as e:
                calibre_db.session.rollback()
                log.error_or_exception("Database error: {}".format(e))
                flash(_(u"Database error: %(error)s.", error=e.orig), category="error")
        return Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')


@EditBook.route("/admin/book/convert/<int:book_id>", methods=['POST'])
@login_required_if_no_ano
@edit_required
def convert_bookformat(book_id):
    # check to see if we have form fields to work with -  if not send user back
    book_format_from = request.form.get('book_format_from', None)
    book_format_to = request.form.get('book_format_to', None)

    if (book_format_from is None) or (book_format_to is None):
        flash(_(u"Source or destination format for conversion missing"), category="error")
        return redirect(url_for('edit-book.show_edit_book', book_id=book_id))

    log.info('converting: book id: %s from: %s to: %s', book_id, book_format_from, book_format_to)
    rtn = helper.convert_book_format(book_id, config.config_calibre_dir, book_format_from.upper(),
                                     book_format_to.upper(), current_user.name)

    if rtn is None:
        flash(_(u"Book successfully queued for converting to %(book_format)s",
                book_format=book_format_to),
              category="success")
    else:
        flash(_(u"There was an error converting this book: %(res)s", res=rtn), category="error")
    return redirect(url_for('edit-book.show_edit_book', book_id=book_id))


@EditBook.route("/ajax/getcustomenum/<int:c_id>")
@login_required
def table_get_custom_enum(c_id):
    ret = list()
    cc = (calibre_db.session.query(db.CustomColumns)
          .filter(db.CustomColumns.id == c_id)
          .filter(db.CustomColumns.datatype.notin_(db.cc_exceptions)).one_or_none())
    ret.append({'value': "", 'text': ""})
    for idx, en in enumerate(cc.get_display_dict()['enum_values']):
        ret.append({'value': en, 'text': en})
    return json.dumps(ret)


@EditBook.route("/ajax/editbooks/<param>", methods=['POST'])
@login_required_if_no_ano
@edit_required
def edit_list_book(param):
    vals = request.form.to_dict()
    book = calibre_db.get_book(vals['pk'])
    sort_param = ""
    # ret = ""
    try:
        if param == 'series_index':
            edit_book_series_index(vals['value'], book)
            ret = Response(json.dumps({'success': True, 'newValue': book.series_index}), mimetype='application/json')
        elif param == 'tags':
            edit_book_tags(vals['value'], book)
            ret = Response(json.dumps({'success': True, 'newValue': ', '.join([tag.name for tag in book.tags])}),
                           mimetype='application/json')
        elif param == 'series':
            edit_book_series(vals['value'], book)
            ret = Response(json.dumps({'success': True, 'newValue':  ', '.join([serie.name for serie in book.series])}),
                           mimetype='application/json')
        elif param == 'publishers':
            edit_book_publisher(vals['value'], book)
            ret = Response(json.dumps({'success': True,
                                       'newValue': ', '.join([publisher.name for publisher in book.publishers])}),
                           mimetype='application/json')
        elif param == 'languages':
            invalid = list()
            edit_book_languages(vals['value'], book, invalid=invalid)
            if invalid:
                ret = Response(json.dumps({'success': False,
                                           'msg': 'Invalid languages in request: {}'.format(','.join(invalid))}),
                               mimetype='application/json')
            else:
                lang_names = list()
                for lang in book.languages:
                    lang_names.append(isoLanguages.get_language_name(get_locale(), lang.lang_code))
                ret = Response(json.dumps({'success': True, 'newValue':  ', '.join(lang_names)}),
                               mimetype='application/json')
        elif param == 'author_sort':
            book.author_sort = vals['value']
            ret = Response(json.dumps({'success': True, 'newValue':  book.author_sort}),
                           mimetype='application/json')
        elif param == 'title':
            sort_param = book.sort
            if handle_title_on_edit(book, vals.get('value', "")):
                rename_error = helper.update_dir_structure(book.id, config.config_calibre_dir)
                if not rename_error:
                    ret = Response(json.dumps({'success': True, 'newValue':  book.title}),
                                   mimetype='application/json')
                else:
                    ret = Response(json.dumps({'success': False,
                                               'msg': rename_error}),
                                   mimetype='application/json')
        elif param == 'sort':
            book.sort = vals['value']
            ret = Response(json.dumps({'success': True, 'newValue':  book.sort}),
                           mimetype='application/json')
        elif param == 'comments':
            edit_book_comments(vals['value'], book)
            ret = Response(json.dumps({'success': True, 'newValue':  book.comments[0].text}),
                           mimetype='application/json')
        elif param == 'authors':
            input_authors, __, renamed = handle_author_on_edit(book, vals['value'], vals.get('checkA', None) == "true")
            rename_error = helper.update_dir_structure(book.id, config.config_calibre_dir, input_authors[0],
                                                       renamed_author=renamed)
            if not rename_error:
                ret = Response(json.dumps({
                    'success': True,
                    'newValue':  ' & '.join([author.replace('|', ',') for author in input_authors])}),
                    mimetype='application/json')
            else:
                ret = Response(json.dumps({'success': False,
                                           'msg': rename_error}),
                               mimetype='application/json')
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
                ret = Response(json.dumps({'success': True, 'newValue': vals['value']}),
                               mimetype='application/json')
        else:
            return _("Parameter not found"), 400
        book.last_modified = datetime.utcnow()

        calibre_db.session.commit()
        # revert change for sort if automatic fields link is deactivated
        if param == 'title' and vals.get('checkT') == "false":
            book.sort = sort_param
            calibre_db.session.commit()
    except (OperationalError, IntegrityError) as e:
        calibre_db.session.rollback()
        log.error_or_exception("Database error: {}".format(e))
        ret = Response(json.dumps({'success': False,
                                   'msg': 'Database error: {}'.format(e.orig)}),
                       mimetype='application/json')
    return ret


@EditBook.route("/ajax/sort_value/<field>/<int:bookid>")
@login_required
def get_sorted_entry(field, bookid):
    if field in ['title', 'authors', 'sort', 'author_sort']:
        book = calibre_db.get_filtered_book(bookid)
        if book:
            if field == 'title':
                return json.dumps({'sort': book.sort})
            elif field == 'authors':
                return json.dumps({'author_sort': book.author_sort})
            if field == 'sort':
                return json.dumps({'sort': book.title})
            if field == 'author_sort':
                return json.dumps({'author_sort': book.author})
    return ""


@EditBook.route("/ajax/simulatemerge", methods=['POST'])
@login_required
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
            return json.dumps({'to': to_book, 'from': from_book})
    return ""


@EditBook.route("/ajax/mergebooks", methods=['POST'])
@login_required
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
                            filepath_new = os.path.normpath(os.path.join(config.config_calibre_dir,
                                                                         to_book.path,
                                                                         to_name + "." + element.format.lower()))
                            filepath_old = os.path.normpath(os.path.join(config.config_calibre_dir,
                                                                         from_book.path,
                                                                         element.name + "." + element.format.lower()))
                            copyfile(filepath_old, filepath_new)
                            to_book.data.append(db.Data(to_book.id,
                                                        element.format,
                                                        element.uncompressed_size,
                                                        to_name))
                    delete_book_from_table(from_book.id, "", True)
                    return json.dumps({'success': True})
    return ""


@EditBook.route("/ajax/xchange", methods=['POST'])
@login_required
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
            input_authors, author_change, renamed = handle_author_on_edit(book, authors)
            if author_change or title_change:
                edited_books_id = book.id
                modify_date = True

            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()

            if edited_books_id:
                # toDo: Handle error
                edit_error = helper.update_dir_structure(edited_books_id, config.config_calibre_dir, input_authors[0],
                                                         renamed_author=renamed)
            if modify_date:
                book.last_modified = datetime.utcnow()
            try:
                calibre_db.session.commit()
            except (OperationalError, IntegrityError) as e:
                calibre_db.session.rollback()
                log.error_or_exception("Database error: %s", e)
                return json.dumps({'success': False})

            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()
        return json.dumps({'success': True})
    return ""
