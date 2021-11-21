# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2021 OzzieIsaacs
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


from flask_login import current_user
from . import ub
import datetime
from sqlalchemy.sql.expression import or_

# Add the current book id to kobo_synced_books table for current user, if entry is already present,
# do nothing (safety precaution)
def add_synced_books(book_id):
    is_present = ub.session.query(ub.KoboSyncedBooks).filter(ub.KoboSyncedBooks.book_id == book_id)\
        .filter(ub.KoboSyncedBooks.user_id == current_user.id).count()
    if not is_present:
        synced_book = ub.KoboSyncedBooks()
        synced_book.user_id = current_user.id
        synced_book.book_id = book_id
        ub.session.add(synced_book)
        ub.session_commit()


# Select all entries of current book in kobo_synced_books table, which are from current user and delete them
def remove_synced_book(book_id):
    ub.session.query(ub.KoboSyncedBooks).filter(ub.KoboSyncedBooks.book_id == book_id) \
        .filter(ub.KoboSyncedBooks.user_id == current_user.id).delete()
    ub.session_commit()


def add_archived_books(book_id):
    archived_book = (ub.session.query(ub.ArchivedBook)
                     .filter(ub.ArchivedBook.book_id == book_id)
                     .filter(ub.ArchivedBook.user_id == current_user.id)
                     .first())
    if not archived_book:
        archived_book = ub.ArchivedBook(user_id=current_user.id, book_id=book_id)
    archived_book.is_archived = True
    archived_book.last_modified = datetime.datetime.utcnow()

    ub.session.merge(archived_book)
    ub.session_commit()


# select all books which are synced by the current user and do not belong to a synced shelf and them to archive
# select all shelves from current user which are synced and do not belong to the "only sync" shelves
def update_on_sync_shelfs(user_id):
    books_to_archive = (ub.session.query(ub.KoboSyncedBooks)
                        .join(ub.BookShelf, ub.KoboSyncedBooks.book_id == ub.BookShelf.book_id, isouter=True)
                        .join(ub.Shelf, ub.Shelf.user_id == user_id, isouter=True)
                        .filter(or_(ub.Shelf.kobo_sync == 0, ub.Shelf.kobo_sync == None))
                        .filter(ub.KoboSyncedBooks.user_id == user_id).all())
    for b in books_to_archive:
        add_archived_books(b.book_id)
        ub.session.query(ub.KoboSyncedBooks) \
            .filter(ub.KoboSyncedBooks.book_id == b.book_id) \
            .filter(ub.KoboSyncedBooks.user_id == user_id).delete()
        ub.session_commit()

    shelves_to_archive = ub.session.query(ub.Shelf).filter(ub.Shelf.user_id == user_id).filter(
        ub.Shelf.kobo_sync == 0).all()
    for a in shelves_to_archive:
        ub.session.add(ub.ShelfArchive(uuid=a.uuid, user_id=user_id))
        ub.session_commit()
