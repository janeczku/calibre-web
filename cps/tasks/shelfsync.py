# -*- coding: utf-8 -*-
# vim: ts=4 et

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2020 mmonkey
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime, timezone

from flask_babel import lazy_gettext as N_
from sqlalchemy.exc import InvalidRequestError, OperationalError

from cps import config, logger, db, ub, app
from cps.services.worker import CalibreTask

class TaskSyncShelves(CalibreTask):
    def __init__(self, task_message=N_('Syncing shelves and collections')):
        super(TaskSyncShelves, self).__init__(task_message)
        self.log = logger.create()
        self.cdb = db.CalibreDB(app)

    def run(self, worker_thread):
        self.log.info(f'Running {self.__class__.__name__}')
        try:
            with app.app_context():
                self.sync()
        except Exception as exc:
            self.log.error_or_exception(exc)
        return self._handleSuccess()

    def info(self, *args, **kwargs):
        args = ('SyncShelves: ' + args[0],) + args[1:]
        self.log.info(*args, **kwargs)

    def sync(self):
        # Find which custom column holds collections
        collcc = (
                self.cdb.session.query(db.CustomColumns)
                .filter(db.CustomColumns.label == 'collections')
        ).first()

        # Get the db table object and build the cc field name
        colldb = db.cc_classes[collcc.id]
        collfield = f'custom_column_{collcc.id}'

        # debug
        #self.info(f'shelfsync {collcc.id}')
        #self.info(f'{colldb}, {collfield}')

        # Find calibre books with collections assigned,
        books = (
                self.cdb.session.query(db.Books)
                .order_by(db.Books.id.desc())
        ).all()

        # For each collection, build a list of bookids in that collection
        cContents = {}
        cAllBooks = [book.id for book in books]
        for book in books:
            bookcolls = getattr(book, collfield)
            for coll in bookcolls:
                if coll.value in cContents:
                    cContents[coll.value].append(book.id)
                else:
                    cContents[coll.value] = [book.id]

        # Loop over users, skipping users who have not enabled shelf sync.
        # The rest of the sync activity occurs in this scope.
        for user in ub.session.query(ub.User):
            if user.sync_from_collections != 'on':
                continue

            # Get contents of this user's shelves
            shelves = {}
            sContents = {}

            # There's probably a smarter way to do this with a join,
            # but I don't really know sqlalchemy and right now I just
            # want this to work.
            for shelf in ub.session.query(ub.Shelf).filter(ub.Shelf.user_id == user.id):
                books = (
                        ub.session.query(ub.BookShelf)
                        .filter(ub.BookShelf.shelf == shelf.id)
                        .all()
                )
                # Create a list of bookids in each shelf
                sContents[shelf.name] = [
                    book.book_id
                    for book in books
                ]
                # Update the mapping of shelf names to shelf objects
                shelves[shelf.name] = shelf

            # Loop over collection names.
            # N.B. We intentionally do not loop over shelves that currently
            # are not collections.
            for name in cContents.keys():
                name = str(name)

                # If collection name not in shelves, create new shelf
                if name not in sContents:
                    self.info(f'Creating new shelf {name}')
                    shelf = self.createShelf(name, user)
                    # add to sContents{}
                    sContents[name] = []
                    shelves[name] = shelf

                # Loop over books in collection/shelf, adding/removing as needed
                self.info(f'collection {name}: {len(cContents[name])} {cContents[name]}')
                self.info(f'shelf {name}: {len(sContents[name])} {sContents[name]}')
                ctmp = set(cContents[name])
                stmp = set(sContents[name])
                toAdd = ctmp - stmp
                toRemove = stmp - ctmp

                # adds
                for bookid in toAdd:
                    self.info(f'adding {bookid} from collection to shelf {name}')
                    self.addToShelf(shelves[name], bookid)

                # removes
                for bookid in toRemove:
                    self.info(f'removing {bookid} from shelf {name}')
                    self.removeFromShelf(shelves[name], bookid)

        self.info(f'end shelfsync')

    def createShelf(self, name, user):
        shelf = ub.Shelf()
        shelf.name = name

        # flag it to sync
        shelf.kobo_sync = config.config_kobo_sync

        # make it private to this user
        shelf.is_public = False
        shelf.user_id = int(user.id)

        ub.session.add(shelf)

        try:
            ub.session.commit()
            self.info(f'shelf created: {name}')
            return shelf
        except (OperationalError, InvalidRequestError) as exc:
            ub.session.rollback()
            raise

    def addToShelf(self, shelf, bookid):
        shelf.books.append(ub.BookShelf(shelf=shelf.id, book_id=bookid))
        shelf.last_modified = datetime.now(timezone.utc)
        try:
            ub.session.merge(shelf)
            ub.session.commit()
        except (OperationalError, InvalidRequestError) as e:
            ub.session.rollback()
            log.error_or_exception("Settings Database error: {}".format(e))

    def removeFromShelf(self, shelf, bookid):
        link = (
            ub.session.query(ub.BookShelf)
            .filter(ub.BookShelf.shelf == shelf.id,
                    ub.BookShelf.book_id == bookid)
        ).first()

        if link is None:
            log.error("Book %s already removed from %s", book_id, shelf)
            return

        try:
            ub.session.delete(link)
            shelf.last_modified = datetime.now(timezone.utc)
            ub.session.commit()
        except (OperationalError, InvalidRequestError) as e:
            ub.session.rollback()
            log.error_or_exception("Settings Database error: {}".format(e))

    @property
    def name(self):
        return "Sync shelves and collections"

    @property
    def is_cancellable(self):
        return False
