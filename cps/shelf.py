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
from datetime import datetime

from flask import Blueprint, request, flash, redirect, url_for
from flask_babel import gettext as _
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import func

from . import logger, ub, searched_ids, db, calibre_db
from .web import render_title_template


shelf = Blueprint('shelf', __name__)
log = logger.create()


def check_shelf_edit_permissions(cur_shelf):
    if not cur_shelf.is_public and not cur_shelf.user_id == int(current_user.id):
        log.error("User %s not allowed to edit shelf %s", current_user, cur_shelf)
        return False
    if cur_shelf.is_public and not current_user.role_edit_shelfs():
        log.info("User %s not allowed to edit public shelves", current_user)
        return False
    return True


def check_shelf_view_permissions(cur_shelf):
    if cur_shelf.is_public:
        return True
    if current_user.is_anonymous or cur_shelf.user_id != current_user.id:
        log.error("User is unauthorized to view non-public shelf: %s", cur_shelf)
        return False
    return True


@shelf.route("/shelf/add/<int:shelf_id>/<int:book_id>")
@login_required
def add_to_shelf(shelf_id, book_id):
    xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if shelf is None:
        log.error("Invalid shelf specified: %s", shelf_id)
        if not xhr:
            flash(_(u"Invalid shelf specified"), category="error")
            return redirect(url_for('web.index'))
        return "Invalid shelf specified", 400

    if not check_shelf_edit_permissions(shelf):
        if not xhr:
            flash(_(u"Sorry you are not allowed to add a book to the the shelf: %(shelfname)s", shelfname=shelf.name),
                  category="error")
            return redirect(url_for('web.index'))
        return "Sorry you are not allowed to add a book to the the shelf: %s" % shelf.name, 403

    book_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id,
                                                          ub.BookShelf.book_id == book_id).first()
    if book_in_shelf:
        log.error("Book %s is already part of %s", book_id, shelf)
        if not xhr:
            flash(_(u"Book is already part of the shelf: %(shelfname)s", shelfname=shelf.name), category="error")
            return redirect(url_for('web.index'))
        return "Book is already part of the shelf: %s" % shelf.name, 400

    maxOrder = ub.session.query(func.max(ub.BookShelf.order)).filter(ub.BookShelf.shelf == shelf_id).first()
    if maxOrder[0] is None:
        maxOrder = 0
    else:
        maxOrder = maxOrder[0]

    shelf.books.append(ub.BookShelf(shelf=shelf.id, book_id=book_id, order=maxOrder + 1))
    shelf.last_modified = datetime.utcnow()
    ub.session.merge(shelf)
    ub.session.commit()
    if not xhr:
        flash(_(u"Book has been added to shelf: %(sname)s", sname=shelf.name), category="success")
        if "HTTP_REFERER" in request.environ:
            return redirect(request.environ["HTTP_REFERER"])
        else:
            return redirect(url_for('web.index'))
    return "", 204


@shelf.route("/shelf/massadd/<int:shelf_id>")
@login_required
def search_to_shelf(shelf_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if shelf is None:
        log.error("Invalid shelf specified: %s", shelf_id)
        flash(_(u"Invalid shelf specified"), category="error")
        return redirect(url_for('web.index'))

    if not check_shelf_edit_permissions(shelf):
        flash(_(u"You are not allowed to add a book to the the shelf: %(name)s", name=shelf.name), category="error")
        return redirect(url_for('web.index'))

    if current_user.id in searched_ids and searched_ids[current_user.id]:
        books_for_shelf = list()
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).all()
        if books_in_shelf:
            book_ids = list()
            for book_id in books_in_shelf:
                book_ids.append(book_id.book_id)
            for searchid in searched_ids[current_user.id]:
                if searchid not in book_ids:
                    books_for_shelf.append(searchid)
        else:
            books_for_shelf = searched_ids[current_user.id]

        if not books_for_shelf:
            log.error("Books are already part of %s", shelf)
            flash(_(u"Books are already part of the shelf: %(name)s", name=shelf.name), category="error")
            return redirect(url_for('web.index'))

        maxOrder = ub.session.query(func.max(ub.BookShelf.order)).filter(ub.BookShelf.shelf == shelf_id).first()
        if maxOrder[0] is None:
            maxOrder = 0
        else:
            maxOrder = maxOrder[0]

        for book in books_for_shelf:
            maxOrder = maxOrder + 1
            shelf.books.append(ub.BookShelf(shelf=shelf.id, book_id=book, order=maxOrder))
        shelf.last_modified = datetime.utcnow()
        ub.session.merge(shelf)
        ub.session.commit()
        flash(_(u"Books have been added to shelf: %(sname)s", sname=shelf.name), category="success")
    else:
        flash(_(u"Could not add books to shelf: %(sname)s", sname=shelf.name), category="error")
    return redirect(url_for('web.index'))


@shelf.route("/shelf/remove/<int:shelf_id>/<int:book_id>")
@login_required
def remove_from_shelf(shelf_id, book_id):
    xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if shelf is None:
        log.error("Invalid shelf specified: %s", shelf_id)
        if not xhr:
            return redirect(url_for('web.index'))
        return "Invalid shelf specified", 400

    # if shelf is public and use is allowed to edit shelfs, or if shelf is private and user is owner
    # allow editing shelfs
    # result   shelf public   user allowed    user owner
    #   false        1             0             x
    #   true         1             1             x
    #   true         0             x             1
    #   false        0             x             0

    if check_shelf_edit_permissions(shelf):
        book_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id,
                                                           ub.BookShelf.book_id == book_id).first()

        if book_shelf is None:
            log.error("Book %s already removed from %s", book_id, shelf)
            if not xhr:
                return redirect(url_for('web.index'))
            return "Book already removed from shelf", 410

        ub.session.delete(book_shelf)
        shelf.last_modified = datetime.utcnow()
        ub.session.commit()

        if not xhr:
            flash(_(u"Book has been removed from shelf: %(sname)s", sname=shelf.name), category="success")
            if "HTTP_REFERER" in request.environ:
                return redirect(request.environ["HTTP_REFERER"])
            else:
                return redirect(url_for('web.index'))
        return "", 204
    else:
        if not xhr:
            flash(_(u"Sorry you are not allowed to remove a book from this shelf: %(sname)s", sname=shelf.name),
                  category="error")
            return redirect(url_for('web.index'))
        return "Sorry you are not allowed to remove a book from this shelf: %s" % shelf.name, 403


@shelf.route("/shelf/create", methods=["GET", "POST"])
@login_required
def create_shelf():
    shelf = ub.Shelf()
    if request.method == "POST":
        to_save = request.form.to_dict()
        if "is_public" in to_save:
            shelf.is_public = 1
        shelf.name = to_save["title"]
        shelf.user_id = int(current_user.id)

        is_shelf_name_unique = False
        if shelf.is_public == 1:
            is_shelf_name_unique = ub.session.query(ub.Shelf) \
                .filter((ub.Shelf.name == to_save["title"]) & (ub.Shelf.is_public == 1)) \
                .first() is None

            if not is_shelf_name_unique:
                flash(_(u"A public shelf with the name '%(title)s' already exists.", title=to_save["title"]),
                      category="error")
        else:
            is_shelf_name_unique = ub.session.query(ub.Shelf) \
                .filter((ub.Shelf.name == to_save["title"]) & (ub.Shelf.is_public == 0) &
                        (ub.Shelf.user_id == int(current_user.id)))\
                                       .first() is None

            if not is_shelf_name_unique:
                flash(_(u"A private shelf with the name '%(title)s' already exists.", title=to_save["title"]),
                      category="error")

        if is_shelf_name_unique:
            try:
                ub.session.add(shelf)
                ub.session.commit()
                flash(_(u"Shelf %(title)s created", title=to_save["title"]), category="success")
                return redirect(url_for('shelf.show_shelf', shelf_id=shelf.id))
            except Exception:
                flash(_(u"There was an error"), category="error")
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"Create a Shelf"), page="shelfcreate")
    else:
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"Create a Shelf"), page="shelfcreate")


@shelf.route("/shelf/edit/<int:shelf_id>", methods=["GET", "POST"])
@login_required
def edit_shelf(shelf_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    if request.method == "POST":
        to_save = request.form.to_dict()

        is_shelf_name_unique = False
        if shelf.is_public == 1:
            is_shelf_name_unique = ub.session.query(ub.Shelf) \
                .filter((ub.Shelf.name == to_save["title"]) & (ub.Shelf.is_public == 1)) \
                .filter(ub.Shelf.id != shelf_id) \
                .first() is None

            if not is_shelf_name_unique:
                flash(_(u"A public shelf with the name '%(title)s' already exists.", title=to_save["title"]),
                      category="error")
        else:
            is_shelf_name_unique = ub.session.query(ub.Shelf) \
                .filter((ub.Shelf.name == to_save["title"]) & (ub.Shelf.is_public == 0) &
                        (ub.Shelf.user_id == int(current_user.id)))\
                                       .filter(ub.Shelf.id != shelf_id)\
                                       .first() is None

            if not is_shelf_name_unique:
                flash(_(u"A private shelf with the name '%(title)s' already exists.", title=to_save["title"]),
                      category="error")

        if is_shelf_name_unique:
            shelf.name = to_save["title"]
            shelf.last_modified = datetime.utcnow()
            if "is_public" in to_save:
                shelf.is_public = 1
            else:
                shelf.is_public = 0
            try:
                ub.session.commit()
                flash(_(u"Shelf %(title)s changed", title=to_save["title"]), category="success")
            except Exception:
                flash(_(u"There was an error"), category="error")
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"Edit a shelf"), page="shelfedit")
    else:
        return render_title_template('shelf_edit.html', shelf=shelf, title=_(u"Edit a shelf"), page="shelfedit")


def delete_shelf_helper(cur_shelf):
    if not cur_shelf or not check_shelf_edit_permissions(cur_shelf):
        return
    shelf_id = cur_shelf.id
    ub.session.delete(cur_shelf)
    ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).delete()
    ub.session.add(ub.ShelfArchive(uuid=cur_shelf.uuid, user_id=cur_shelf.user_id))
    ub.session.commit()
    log.info("successfully deleted %s", cur_shelf)


@shelf.route("/shelf/delete/<int:shelf_id>")
@login_required
def delete_shelf(shelf_id):
    cur_shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    delete_shelf_helper(cur_shelf)
    return redirect(url_for('web.index'))


@shelf.route("/shelf/<int:shelf_id>", defaults={'shelf_type': 1})
@shelf.route("/shelf/<int:shelf_id>/<int:shelf_type>")
def show_shelf(shelf_type, shelf_id):
    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()

    result = list()
    # user is allowed to access shelf
    if shelf and check_shelf_view_permissions(shelf):
        page = "shelf.html" if shelf_type == 1 else 'shelfdown.html'

        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id)\
            .order_by(ub.BookShelf.order.asc()).all()
        for book in books_in_shelf:
            cur_book = calibre_db.get_filtered_book(book.book_id)
            if cur_book:
                result.append(cur_book)
            else:
                cur_book = calibre_db.get_book(book.book_id)
                if not cur_book:
                    log.info('Not existing book %s in %s deleted', book.book_id, shelf)
                    ub.session.query(ub.BookShelf).filter(ub.BookShelf.book_id == book.book_id).delete()
                    ub.session.commit()
        return render_title_template(page, entries=result, title=_(u"Shelf: '%(name)s'", name=shelf.name),
                                     shelf=shelf, page="shelf")
    else:
        flash(_(u"Error opening shelf. Shelf does not exist or is not accessible"), category="error")
        return redirect(url_for("web.index"))


@shelf.route("/shelf/order/<int:shelf_id>", methods=["GET", "POST"])
@login_required
def order_shelf(shelf_id):
    if request.method == "POST":
        to_save = request.form.to_dict()
        books_in_shelf = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id).order_by(
            ub.BookShelf.order.asc()).all()
        counter = 0
        for book in books_in_shelf:
            setattr(book, 'order', to_save[str(book.book_id)])
            counter += 1
            # if order diffrent from before -> shelf.last_modified = datetime.utcnow()
        ub.session.commit()

    shelf = ub.session.query(ub.Shelf).filter(ub.Shelf.id == shelf_id).first()
    result = list()
    if shelf and check_shelf_view_permissions(shelf):
        books_in_shelf2 = ub.session.query(ub.BookShelf).filter(ub.BookShelf.shelf == shelf_id) \
            .order_by(ub.BookShelf.order.asc()).all()
        for book in books_in_shelf2:
            cur_book = calibre_db.get_filtered_book(book.book_id)
            if cur_book:
                result.append({'title': cur_book.title,
                               'id': cur_book.id,
                               'author': cur_book.authors,
                               'series': cur_book.series,
                               'series_index': cur_book.series_index})
            else:
                cur_book = calibre_db.get_book(book.book_id)
                result.append({'title': _('Hidden Book'),
                               'id': cur_book.id,
                               'author': [],
                               'series': []})
    return render_title_template('shelf_order.html', entries=result,
                                 title=_(u"Change order of Shelf: '%(name)s'", name=shelf.name),
                                 shelf=shelf, page="shelforder")
