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


from .cw_login import current_user
from . import ub
from datetime import datetime, timezone
from sqlalchemy.sql.expression import or_, and_, true
# from sqlalchemy import exc


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
def remove_synced_book(book_id, all=False, session=None):
    if not all:
        user = ub.KoboSyncedBooks.user_id == current_user.id
    else:
        user = true()
    if not session:
        ub.session.query(ub.KoboSyncedBooks).filter(ub.KoboSyncedBooks.book_id == book_id).filter(user).delete()
        ub.session_commit()
    else:
        session.query(ub.KoboSyncedBooks).filter(ub.KoboSyncedBooks.book_id == book_id).filter(user).delete()
        ub.session_commit(_session=session)


# If state == none, it will toggle the archive state of the passed book_id. 
# state = true archives it, state = false unarchives it
def change_archived_books(book_id, state=None, message=None):
    archived_book = ub.session.query(ub.ArchivedBook).filter(and_(ub.ArchivedBook.user_id == int(current_user.id),
                                                                  ub.ArchivedBook.book_id == book_id)).first()
    if not archived_book and (state == True or state == None):
        archived_book = ub.ArchivedBook(user_id=current_user.id, book_id=book_id)

    archived_book.is_archived = state if state != None else not archived_book.is_archived
    archived_book.last_modified = datetime.now(timezone.utc)        # toDo. Check utc timestamp

    ub.session.merge(archived_book)
    ub.session_commit(message)
    return archived_book.is_archived


# select all books which are synced by the current user and do not belong to a synced shelf and set them to archive
# select all shelves from current user which are synced and do not belong to the "only sync" shelves
def update_on_sync_shelfs(user_id):
    books_to_archive = (ub.session.query(ub.KoboSyncedBooks)
                        .join(ub.BookShelf, ub.KoboSyncedBooks.book_id == ub.BookShelf.book_id, isouter=True)
                        .join(ub.Shelf, ub.Shelf.user_id == user_id, isouter=True)
                        .filter(or_(ub.Shelf.kobo_sync == 0, ub.Shelf.kobo_sync==None))
                        .filter(ub.KoboSyncedBooks.user_id == user_id).all())
    for b in books_to_archive:
        change_archived_books(b.book_id, True)
        ub.session.query(ub.KoboSyncedBooks) \
            .filter(ub.KoboSyncedBooks.book_id == b.book_id) \
            .filter(ub.KoboSyncedBooks.user_id == user_id).delete()
        ub.session_commit()

    # Search all shelf which are currently not synced
    shelves_to_archive = ub.session.query(ub.Shelf).filter(ub.Shelf.user_id == user_id).filter(
        ub.Shelf.kobo_sync == 0).all()
    for a in shelves_to_archive:
        ub.session.add(ub.ShelfArchive(uuid=a.uuid, user_id=user_id))
        ub.session_commit()
