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

from __future__ import division, print_function, unicode_literals
import os
import datetime
import json
from shutil import move, copyfile
from uuid import uuid4

from flask import Blueprint, request, flash, redirect, url_for, abort, Markup, Response
from flask_babel import gettext as _
from flask_login import current_user, login_required

from . import constants, logger, isoLanguages, gdriveutils, uploader, helper
from . import config, get_locale, db, ub, worker
from .helper import order_authors, common_filters
from .web import login_required_if_no_ano, render_title_template, edit_required, upload_required


editbook = Blueprint('editbook', __name__)
log = logger.create()


# Modifies different Database objects, first check if elements have to be added to database, than check
# if elements have to be deleted, because they are no longer used
def modify_database_object(input_elements, db_book_object, db_object, db_session, db_type):
    # passing input_elements not as a list may lead to undesired results
    if not isinstance(input_elements, list):
        raise TypeError(str(input_elements) + " should be passed as a list")

    input_elements = [x for x in input_elements if x != '']
    # we have all input element (authors, series, tags) names now
    # 1. search for elements to remove
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
                # if inp_element == type_elements:
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
    # if there are elements to remove, we remove them now
    if len(del_elements) > 0:
        for del_element in del_elements:
            db_book_object.remove(del_element)
            if len(del_element.books) == 0:
                db_session.delete(del_element)
    # if there are elements to add, we add them now!
    if len(add_elements) > 0:
        if db_type == 'languages':
            db_filter = db_object.lang_code
        elif db_type == 'custom':
            db_filter = db_object.value
        else:
            db_filter = db_object.name
        for add_element in add_elements:
            # check if a element with that name exists
            db_element = db_session.query(db_object).filter(db_filter == add_element).first()
            # if no element is found add it
            # if new_element is None:
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
                db_session.add(new_element)
                db_book_object.append(new_element)
            else:
                if db_type == 'custom':
                    if db_element.value != add_element:
                        new_element.value = add_element
                        # new_element = db_element
                elif db_type == 'languages':
                    if db_element.lang_code != add_element:
                        db_element.lang_code = add_element
                        # new_element = db_element
                elif db_type == 'series':
                    if db_element.name != add_element:
                        db_element.name = add_element # = add_element # new_element = db_object(add_element, add_element)
                        db_element.sort = add_element
                        # new_element = db_element
                elif db_type == 'author':
                    if db_element.name != add_element:
                        db_element.name = add_element
                        db_element.sort = add_element.replace('|', ',')
                        # new_element = db_element
                elif db_type == 'publisher':
                    if db_element.name != add_element:
                        db_element.name = add_element
                        db_element.sort = None
                        # new_element = db_element
                elif db_element.name != add_element:
                    db_element.name = add_element
                    # new_element = db_element
                # add element to book
                db_book_object.append(db_element)


@editbook.route("/delete/<int:book_id>/", defaults={'book_format': ""})
@editbook.route("/delete/<int:book_id>/<string:book_format>/")
@login_required
def delete_book(book_id, book_format):
    if current_user.role_delete_books():
        book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
        if book:
            helper.delete_book(book, config.config_calibre_dir, book_format=book_format.upper())
            if not book_format:
                # delete book from Shelfs, Downloads, Read list
                ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book_id).delete()
                ub.session.query(ub.ReadBook).filter(ub.ReadBook.book_id == book_id).delete()
                ub.delete_download(book_id)
                ub.session.commit()

                # check if only this book links to:
                # author, language, series, tags, custom columns
                modify_database_object([u''], book.authors, db.Authors, db.session, 'author')
                modify_database_object([u''], book.tags, db.Tags, db.session, 'tags')
                modify_database_object([u''], book.series, db.Series, db.session, 'series')
                modify_database_object([u''], book.languages, db.Languages, db.session, 'languages')
                modify_database_object([u''], book.publishers, db.Publishers, db.session, 'publishers')

                cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
                for c in cc:
                    cc_string = "custom_column_" + str(c.id)
                    if not c.is_multiple:
                        if len(getattr(book, cc_string)) > 0:
                            if c.datatype == 'bool' or c.datatype == 'integer':
                                del_cc = getattr(book, cc_string)[0]
                                getattr(book, cc_string).remove(del_cc)
                                db.session.delete(del_cc)
                            elif c.datatype == 'rating':
                                del_cc = getattr(book, cc_string)[0]
                                getattr(book, cc_string).remove(del_cc)
                                if len(del_cc.books) == 0:
                                    db.session.delete(del_cc)
                            else:
                                del_cc = getattr(book, cc_string)[0]
                                getattr(book, cc_string).remove(del_cc)
                                db.session.delete(del_cc)
                    else:
                        modify_database_object([u''], getattr(book, cc_string), db.cc_classes[c.id],
                                               db.session, 'custom')
                db.session.query(db.Books).filter(db.Books.id == book_id).delete()
            else:
                db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == book_format).delete()
            db.session.commit()
        else:
            # book not found
            log.error('Book with id "%s" could not be deleted: not found', book_id)
    if book_format:
        return redirect(url_for('editbook.edit_book', book_id=book_id))
    else:
        return redirect(url_for('web.index'))


def render_edit_book(book_id):
    db.update_title_sort(config)
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    book = db.session.query(db.Books)\
        .filter(db.Books.id == book_id).filter(common_filters()).first()

    if not book:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible"), category="error")
        return redirect(url_for("web.index"))

    for lang in book.languages:
        lang.language_name = isoLanguages.get_language_name(get_locale(), lang.lang_code)

    book = order_authors(book)

    author_names = []
    for authr in book.authors:
        author_names.append(authr.name.replace('|', ','))

    # Option for showing convertbook button
    valid_source_formats=list()
    if config.config_ebookconverter == 2:
        for file in book.data:
            if file.format.lower() in constants.EXTENSIONS_CONVERT:
                valid_source_formats.append(file.format.lower())

    # Determine what formats don't already exist
    allowed_conversion_formats = constants.EXTENSIONS_CONVERT.copy()
    for file in book.data:
        try:
            allowed_conversion_formats.remove(file.format.lower())
        except Exception:
            log.warning('%s already removed from list.', file.format.lower())

    return render_title_template('book_edit.html', book=book, authors=author_names, cc=cc,
                                 title=_(u"edit metadata"), page="editbook",
                                 conversion_formats=allowed_conversion_formats,
                                 source_formats=valid_source_formats)


def edit_cc_data(book_id, book, to_save):
    cc = db.session.query(db.Custom_Columns).filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    for c in cc:
        cc_string = "custom_column_" + str(c.id)
        if not c.is_multiple:
            if len(getattr(book, cc_string)) > 0:
                cc_db_value = getattr(book, cc_string)[0].value
            else:
                cc_db_value = None
            if to_save[cc_string].strip():
                if c.datatype == 'int' or c.datatype == 'bool':
                    if to_save[cc_string] == 'None':
                        to_save[cc_string] = None
                    elif c.datatype == 'bool':
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
                            db.session.flush()
                            new_cc = db.session.query(cc_class).filter(
                                cc_class.value == to_save[cc_string].strip()).first()
                        # add cc value to book
                        getattr(book, cc_string).append(new_cc)
            else:
                if cc_db_value is not None:
                    # remove old cc_val
                    del_cc = getattr(book, cc_string)[0]
                    getattr(book, cc_string).remove(del_cc)
                    if not del_cc.books or len(del_cc.books) == 0:
                        db.session.delete(del_cc)
        else:
            input_tags = to_save[cc_string].split(',')
            input_tags = list(map(lambda it: it.strip(), input_tags))
            modify_database_object(input_tags, getattr(book, cc_string), db.cc_classes[c.id], db.session,
                                   'custom')
    return cc

def upload_single_file(request, book, book_id):
    # Check and handle Uploaded file
    if 'btn-upload-format' in request.files:
        requested_file = request.files['btn-upload-format']
        # check for empty request
        if requested_file.filename != '':
            if '.' in requested_file.filename:
                file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
                if file_ext not in constants.EXTENSIONS_UPLOAD:
                    flash(_("File extension '%(ext)s' is not allowed to be uploaded to this server", ext=file_ext),
                          category="error")
                    return redirect(url_for('web.show_book', book_id=book.id))
            else:
                flash(_('File to be uploaded must have an extension'), category="error")
                return redirect(url_for('web.show_book', book_id=book.id))

            file_name = book.path.rsplit('/', 1)[-1]
            filepath = os.path.normpath(os.path.join(config.config_calibre_dir, book.path))
            saved_filename = os.path.join(filepath, file_name + '.' + file_ext)

            # check if file path exists, otherwise create it, copy file to calibre path and delete temp file
            if not os.path.exists(filepath):
                try:
                    os.makedirs(filepath)
                except OSError:
                    flash(_(u"Failed to create path %(path)s (Permission denied).", path=filepath), category="error")
                    return redirect(url_for('web.show_book', book_id=book.id))
            try:
                requested_file.save(saved_filename)
            except OSError:
                flash(_(u"Failed to store file %(file)s.", file=saved_filename), category="error")
                return redirect(url_for('web.show_book', book_id=book.id))

            file_size = os.path.getsize(saved_filename)
            is_format = db.session.query(db.Data).filter(db.Data.book == book_id).\
                filter(db.Data.format == file_ext.upper()).first()

            # Format entry already exists, no need to update the database
            if is_format:
                log.warning('Book format %s already existing', file_ext.upper())
            else:
                db_format = db.Data(book_id, file_ext.upper(), file_size, file_name)
                db.session.add(db_format)
                db.session.commit()
                db.update_title_sort(config)

            # Queue uploader info
            uploadText=_(u"File format %(ext)s added to %(book)s", ext=file_ext.upper(), book=book.title)
            worker.add_upload(current_user.nickname,
                "<a href=\"" + url_for('web.show_book', book_id=book.id) + "\">" + uploadText + "</a>")

            return uploader.process(
                saved_filename, *os.path.splitext(requested_file.filename))


def upload_cover(request, book):
    if 'btn-upload-cover' in request.files:
        requested_file = request.files['btn-upload-cover']
        # check for empty request
        if requested_file.filename != '':
            if helper.save_cover(requested_file, book.path) is True:
                return True
            else:
                # ToDo Message not always coorect
                flash(_(u"Cover is not a supported imageformat (jpg/png/webp), can't save"), category="error")
                return False
    return None


@editbook.route("/admin/book/<int:book_id>", methods=['GET', 'POST'])
@login_required_if_no_ano
@edit_required
def edit_book(book_id):
    # Show form
    if request.method != 'POST':
        return render_edit_book(book_id)

    # create the function for sorting...
    db.update_title_sort(config)
    book = db.session.query(db.Books)\
        .filter(db.Books.id == book_id).filter(common_filters()).first()

    # Book not found
    if not book:
        flash(_(u"Error opening eBook. File does not exist or file is not accessible"), category="error")
        return redirect(url_for("web.index"))

    meta = upload_single_file(request, book, book_id)
    if upload_cover(request, book) is True:
        book.has_cover = 1
    try:
        to_save = request.form.to_dict()
        merge_metadata(to_save, meta)
        # Update book
        edited_books_id = None
        #handle book title
        if book.title != to_save["book_title"].rstrip().strip():
            if to_save["book_title"] == '':
                to_save["book_title"] = _(u'Unknown')
            book.title = to_save["book_title"].rstrip().strip()
            edited_books_id = book.id

        # handle author(s)
        input_authors = to_save["author_name"].split('&')
        input_authors = list(map(lambda it: it.strip().replace(',', '|'), input_authors))
        # we have all author names now
        if input_authors == ['']:
            input_authors = [_(u'Unknown')]  # prevent empty Author

        modify_database_object(input_authors, book.authors, db.Authors, db.session, 'author')

        # Search for each author if author is in database, if not, authorname and sorted authorname is generated new
        # everything then is assembled for sorted author field in database
        sort_authors_list = list()
        for inp in input_authors:
            stored_author = db.session.query(db.Authors).filter(db.Authors.name == inp).first()
            if not stored_author:
                stored_author = helper.get_sorted_author(inp)
            else:
                stored_author = stored_author.sort
            sort_authors_list.append(helper.get_sorted_author(stored_author))
        sort_authors = ' & '.join(sort_authors_list)
        if book.author_sort != sort_authors:
            edited_books_id = book.id
            book.author_sort = sort_authors


        if config.config_use_google_drive:
            gdriveutils.updateGdriveCalibreFromLocal()

        error = False
        if edited_books_id:
            error = helper.update_dir_stucture(edited_books_id, config.config_calibre_dir, input_authors[0])

        if not error:
            if to_save["cover_url"]:
                if helper.save_cover_from_url(to_save["cover_url"], book.path) is True:
                    book.has_cover = 1
                else:
                    flash(_(u"Cover is not a jpg file, can't save"), category="error")

            if book.series_index != to_save["series_index"]:
                book.series_index = to_save["series_index"]

            # Handle book comments/description
            if len(book.comments):
                book.comments[0].text = to_save["description"]
            else:
                book.comments.append(db.Comments(text=to_save["description"], book=book.id))

            # Handle book tags
            input_tags = to_save["tags"].split(',')
            input_tags = list(map(lambda it: it.strip(), input_tags))
            modify_database_object(input_tags, book.tags, db.Tags, db.session, 'tags')

            # Handle book series
            input_series = [to_save["series"].strip()]
            input_series = [x for x in input_series if x != '']
            modify_database_object(input_series, book.series, db.Series, db.session, 'series')

            if to_save["pubdate"]:
                try:
                    book.pubdate = datetime.datetime.strptime(to_save["pubdate"], "%Y-%m-%d")
                except ValueError:
                    book.pubdate = db.Books.DEFAULT_PUBDATE
            else:
                book.pubdate = db.Books.DEFAULT_PUBDATE

            if to_save["publisher"]:
                publisher = to_save["publisher"].rstrip().strip()
                if len(book.publishers) == 0 or (len(book.publishers) > 0 and publisher != book.publishers[0].name):
                    modify_database_object([publisher], book.publishers, db.Publishers, db.session, 'publisher')
            elif len(book.publishers):
                modify_database_object([], book.publishers, db.Publishers, db.session, 'publisher')


            # handle book languages
            input_languages = to_save["languages"].split(',')
            unknown_languages = []
            input_l = isoLanguages.get_language_codes(get_locale(), input_languages, unknown_languages)
            for l in unknown_languages:
                log.error('%s is not a valid language', l)
                flash(_(u"%(langname)s is not a valid language", langname=l), category="error")
            modify_database_object(list(input_l), book.languages, db.Languages, db.session, 'languages')

            # handle book ratings
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

            # handle cc data
            edit_cc_data(book_id, book, to_save)

            db.session.commit()
            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()
            if "detail_view" in to_save:
                return redirect(url_for('web.show_book', book_id=book.id))
            else:
                flash(_("Metadata successfully updated"), category="success")
                return render_edit_book(book_id)
        else:
            db.session.rollback()
            flash(error, category="error")
            return render_edit_book(book_id)
    except Exception as e:
        log.exception(e)
        db.session.rollback()
        flash(_("Error editing book, please check logfile for details"), category="error")
        return redirect(url_for('web.show_book', book_id=book.id))


def merge_metadata(to_save, meta):
    if to_save['author_name'] == _(u'Unknown'):
        to_save['author_name'] = ''
    if to_save['book_title'] == _(u'Unknown'):
        to_save['book_title'] = ''
    for s_field, m_field in [
            ('tags', 'tags'), ('author_name', 'author'), ('series', 'series'),
            ('series_index', 'series_id'), ('languages', 'languages'),
            ('book_title', 'title')]:
        to_save[s_field] = to_save[s_field] or getattr(meta, m_field, '')
    to_save["description"] = to_save["description"] or Markup(
        getattr(meta, 'description', '')).unescape()


@editbook.route("/upload", methods=["GET", "POST"])
@login_required_if_no_ano
@upload_required
def upload():
    if not config.config_uploading:
        abort(404)
    if request.method == 'POST' and 'btn-upload' in request.files:
        for requested_file in request.files.getlist("btn-upload"):
            # create the function for sorting...
            db.update_title_sort(config)
            db.session.connection().connection.connection.create_function('uuid4', 0, lambda: str(uuid4()))

            # check if file extension is correct
            if '.' in requested_file.filename:
                file_ext = requested_file.filename.rsplit('.', 1)[-1].lower()
                if file_ext not in constants.EXTENSIONS_UPLOAD:
                    flash(
                        _("File extension '%(ext)s' is not allowed to be uploaded to this server",
                          ext=file_ext), category="error")
                    return Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')
            else:
                flash(_('File to be uploaded must have an extension'), category="error")
                return Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')

            # extract metadata from file
            try:
                meta = uploader.upload(requested_file)
            except (IOError, OSError):
                log.error("File %s could not saved to temp dir", requested_file.filename)
                flash(_(u"File %(filename)s could not saved to temp dir",
                        filename= requested_file.filename), category="error")
                return Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')
            title = meta.title
            authr = meta.author
            tags = meta.tags
            series = meta.series
            series_index = meta.series_id
            title_dir = helper.get_valid_filename(title)
            author_dir = helper.get_valid_filename(authr)
            filepath = os.path.join(config.config_calibre_dir, author_dir, title_dir)
            saved_filename = os.path.join(filepath, title_dir + meta.extension.lower())

            if title != _(u'Unknown') and authr != _(u'Unknown'):
                entry = helper.check_exists_book(authr, title)
                if entry:
                    log.info("Uploaded book probably exists in library")
                    flash(_(u"Uploaded book probably exists in the library, consider to change before upload new: ")
                        + Markup(render_title_template('book_exists_flash.html', entry=entry)), category="warning")

            # check if file path exists, otherwise create it, copy file to calibre path and delete temp file
            if not os.path.exists(filepath):
                try:
                    os.makedirs(filepath)
                except OSError:
                    log.error("Failed to create path %s (Permission denied)", filepath)
                    flash(_(u"Failed to create path %(path)s (Permission denied).", path=filepath), category="error")
                    return Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')
            try:
                copyfile(meta.file_path, saved_filename)
            except OSError:
                log.error("Failed to store file %s (Permission denied)", saved_filename)
                flash(_(u"Failed to store file %(file)s (Permission denied).", file=saved_filename), category="error")
                return Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')
            try:
                os.unlink(meta.file_path)
            except OSError:
                log.error("Failed to delete file %(file)s (Permission denied)", meta.file_path)
                flash(_(u"Failed to delete file %(file)s (Permission denied).", file= meta.file_path),
                      category="warning")

            if meta.cover is None:
                has_cover = 0
                copyfile(os.path.join(constants.STATIC_DIR, 'generic_cover.jpg'),
                         os.path.join(filepath, "cover.jpg"))
            else:
                has_cover = 1
                move(meta.cover, os.path.join(filepath, "cover.jpg"))

            # handle authors
            is_author = db.session.query(db.Authors).filter(db.Authors.name == authr).first()
            if is_author:
                db_author = is_author
            else:
                db_author = db.Authors(authr, helper.get_sorted_author(authr), "")
                db.session.add(db_author)

            # handle series
            db_series = None
            is_series = db.session.query(db.Series).filter(db.Series.name == series).first()
            if is_series:
                db_series = is_series
            elif series != '':
                db_series = db.Series(series, "")
                db.session.add(db_series)

            # add language actually one value in list
            input_language = meta.languages
            db_language = None
            if input_language != "":
                input_language = isoLanguages.get(name=input_language).part3
                hasLanguage = db.session.query(db.Languages).filter(db.Languages.lang_code == input_language).first()
                if hasLanguage:
                    db_language = hasLanguage
                else:
                    db_language = db.Languages(input_language)
                    db.session.add(db_language)

            # combine path and normalize path from windows systems
            path = os.path.join(author_dir, title_dir).replace('\\', '/')
            db_book = db.Books(title, "", db_author.sort, datetime.datetime.now(), datetime.datetime(101, 1, 1),
                            series_index, datetime.datetime.now(), path, has_cover, db_author, [], db_language)
            db_book.authors.append(db_author)
            if db_series:
                db_book.series.append(db_series)
            if db_language is not None:
                db_book.languages.append(db_language)
            file_size = os.path.getsize(saved_filename)
            db_data = db.Data(db_book, meta.extension.upper()[1:], file_size, title_dir)

            # handle tags
            input_tags = tags.split(',')
            input_tags = list(map(lambda it: it.strip(), input_tags))
            if input_tags[0] !="":
                modify_database_object(input_tags, db_book.tags, db.Tags, db.session, 'tags')

            # flush content, get db_book.id available
            db_book.data.append(db_data)
            db.session.add(db_book)
            db.session.flush()

            # add comment
            book_id = db_book.id
            upload_comment = Markup(meta.description).unescape()
            if upload_comment != "":
                db.session.add(db.Comments(upload_comment, book_id))

            # save data to database, reread data
            db.session.commit()
            db.update_title_sort(config)
            book = db.session.query(db.Books).filter(db.Books.id == book_id).filter(common_filters()).first()

            # upload book to gdrive if nesseccary and add "(bookid)" to folder name
            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()
            error = helper.update_dir_stucture(book.id, config.config_calibre_dir)
            db.session.commit()
            if config.config_use_google_drive:
                gdriveutils.updateGdriveCalibreFromLocal()
            if error:
                flash(error, category="error")
            uploadText=_(u"File %(file)s uploaded", file=book.title)
            worker.add_upload(current_user.nickname,
                "<a href=\"" + url_for('web.show_book', book_id=book.id) + "\">" + uploadText + "</a>")

            # create data for displaying display Full language name instead of iso639.part3language
            if db_language is not None:
                book.languages[0].language_name = _(meta.languages)
            author_names = []
            for author in db_book.authors:
                author_names.append(author.name)
            if len(request.files.getlist("btn-upload")) < 2:
                if current_user.role_edit() or current_user.role_admin():
                    resp = {"location": url_for('editbook.edit_book', book_id=db_book.id)}
                    return Response(json.dumps(resp), mimetype='application/json')
                else:
                    resp = {"location": url_for('web.show_book', book_id=db_book.id)}
                    return Response(json.dumps(resp), mimetype='application/json')
        return Response(json.dumps({"location": url_for("web.index")}), mimetype='application/json')


@editbook.route("/admin/book/convert/<int:book_id>", methods=['POST'])
@login_required_if_no_ano
@edit_required
def convert_bookformat(book_id):
    # check to see if we have form fields to work with -  if not send user back
    book_format_from = request.form.get('book_format_from', None)
    book_format_to = request.form.get('book_format_to', None)

    if (book_format_from is None) or (book_format_to is None):
        flash(_(u"Source or destination format for conversion missing"), category="error")
        return redirect(request.environ["HTTP_REFERER"])

    log.info('converting: book id: %s from: %s to: %s', book_id, book_format_from, book_format_to)
    rtn = helper.convert_book_format(book_id, config.config_calibre_dir, book_format_from.upper(),
                                     book_format_to.upper(), current_user.nickname)

    if rtn is None:
        flash(_(u"Book successfully queued for converting to %(book_format)s",
                    book_format=book_format_to),
                    category="success")
    else:
        flash(_(u"There was an error converting this book: %(res)s", res=rtn), category="error")
    return redirect(request.environ["HTTP_REFERER"])
