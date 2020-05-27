# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019 mutschler, cervinko, ok11, jkrehm, nanu-c, Wineliva,
#                            pjeby, elelay, idalin, Ozzieisaacs
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
import sys
import os
import re
import ast
import json
from datetime import datetime
import threading

from sqlalchemy import create_engine
from sqlalchemy import Table, Column, ForeignKey, CheckConstraint
from sqlalchemy import String, Integer, Boolean, TIMESTAMP, Float
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from flask_login import current_user
from sqlalchemy.sql.expression import and_, true, false, text, func, or_
from babel import Locale as LC
from babel.core import UnknownLocaleError
from flask_babel import gettext as _

from . import logger, ub, isoLanguages
from .pagination import Pagination

try:
    import unidecode
    use_unidecode = True
except ImportError:
    use_unidecode = False


cc_exceptions = ['datetime', 'comments', 'composite', 'series']
cc_classes = {}

Base = declarative_base()

books_authors_link = Table('books_authors_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('author', Integer, ForeignKey('authors.id'), primary_key=True)
    )

books_tags_link = Table('books_tags_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('tag', Integer, ForeignKey('tags.id'), primary_key=True)
    )

books_series_link = Table('books_series_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('series', Integer, ForeignKey('series.id'), primary_key=True)
    )

books_ratings_link = Table('books_ratings_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('rating', Integer, ForeignKey('ratings.id'), primary_key=True)
    )

books_languages_link = Table('books_languages_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('lang_code', Integer, ForeignKey('languages.id'), primary_key=True)
    )

books_publishers_link = Table('books_publishers_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('publisher', Integer, ForeignKey('publishers.id'), primary_key=True)
    )


class Identifiers(Base):
    __tablename__ = 'identifiers'

    id = Column(Integer, primary_key=True)
    type = Column(String(collation='NOCASE'), nullable=False, default="isbn")
    val = Column(String(collation='NOCASE'), nullable=False)
    book = Column(Integer, ForeignKey('books.id'), nullable=False)

    def __init__(self, val, id_type, book):
        self.val = val
        self.type = id_type
        self.book = book

    def formatType(self):
        if self.type == "amazon":
            return u"Amazon"
        elif self.type == "isbn":
            return u"ISBN"
        elif self.type == "doi":
            return u"DOI"
        elif self.type == "goodreads":
            return u"Goodreads"
        elif self.type == "google":
            return u"Google Books"
        elif self.type == "kobo":
            return u"Kobo"
        if self.type == "lubimyczytac":
            return u"Lubimyczytac"
        else:
            return self.type

    def __repr__(self):
        if self.type == "amazon" or self.type == "asin":
            return u"https://amzn.com/{0}".format(self.val)
        elif self.type == "isbn":
            return u"https://www.worldcat.org/isbn/{0}".format(self.val)
        elif self.type == "doi":
            return u"https://dx.doi.org/{0}".format(self.val)
        elif self.type == "goodreads":
            return u"https://www.goodreads.com/book/show/{0}".format(self.val)
        elif self.type == "douban":
            return u"https://book.douban.com/subject/{0}".format(self.val)
        elif self.type == "google":
            return u"https://books.google.com/books?id={0}".format(self.val)
        elif self.type == "kobo":
            return u"https://www.kobo.com/ebook/{0}".format(self.val)
        elif self.type == "lubimyczytac":
            return u" https://lubimyczytac.pl/ksiazka/{0}".format(self.val)
        elif self.type == "url":
            return u"{0}".format(self.val)
        else:
            return u""


class Comments(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    text = Column(String(collation='NOCASE'), nullable=False)
    book = Column(Integer, ForeignKey('books.id'), nullable=False)

    def __init__(self, text, book):
        self.text = text
        self.book = book

    def __repr__(self):
        return u"<Comments({0})>".format(self.text)


class Tags(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(collation='NOCASE'), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return u"<Tags('{0})>".format(self.name)


class Authors(Base):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'), unique=True, nullable=False)
    sort = Column(String(collation='NOCASE'))
    link = Column(String, nullable=False, default="")

    def __init__(self, name, sort, link):
        self.name = name
        self.sort = sort
        self.link = link

    def __repr__(self):
        return u"<Authors('{0},{1}{2}')>".format(self.name, self.sort, self.link)


class Series(Base):
    __tablename__ = 'series'

    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'), unique=True, nullable=False)
    sort = Column(String(collation='NOCASE'))

    def __init__(self, name, sort):
        self.name = name
        self.sort = sort

    def __repr__(self):
        return u"<Series('{0},{1}')>".format(self.name, self.sort)


class Ratings(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True)
    rating = Column(Integer, CheckConstraint('rating>-1 AND rating<11'), unique=True)

    def __init__(self, rating):
        self.rating = rating

    def __repr__(self):
        return u"<Ratings('{0}')>".format(self.rating)


class Languages(Base):
    __tablename__ = 'languages'

    id = Column(Integer, primary_key=True)
    lang_code = Column(String(collation='NOCASE'), nullable=False, unique=True)

    def __init__(self, lang_code):
        self.lang_code = lang_code

    def __repr__(self):
        return u"<Languages('{0}')>".format(self.lang_code)


class Publishers(Base):
    __tablename__ = 'publishers'

    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'), nullable=False, unique=True)
    sort = Column(String(collation='NOCASE'))

    def __init__(self, name, sort):
        self.name = name
        self.sort = sort

    def __repr__(self):
        return u"<Publishers('{0},{1}')>".format(self.name, self.sort)


class Data(Base):
    __tablename__ = 'data'
    __table_args__ = {'schema':'calibre'}

    id = Column(Integer, primary_key=True)
    book = Column(Integer, ForeignKey('books.id'), nullable=False)
    format = Column(String(collation='NOCASE'), nullable=False)
    uncompressed_size = Column(Integer, nullable=False)
    name = Column(String, nullable=False)

    def __init__(self, book, book_format, uncompressed_size, name):
        self.book = book
        self.format = book_format
        self.uncompressed_size = uncompressed_size
        self.name = name

    def __repr__(self):
        return u"<Data('{0},{1}{2}{3}')>".format(self.book, self.format, self.uncompressed_size, self.name)


class Books(Base):
    __tablename__ = 'books'

    DEFAULT_PUBDATE = "0101-01-01 00:00:00+00:00"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(collation='NOCASE'), nullable=False, default='Unknown')
    sort = Column(String(collation='NOCASE'))
    author_sort = Column(String(collation='NOCASE'))
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    pubdate = Column(String) # , default=datetime.utcnow)
    series_index = Column(String, nullable=False, default="1.0")
    last_modified = Column(TIMESTAMP, default=datetime.utcnow)
    path = Column(String, default="", nullable=False)
    has_cover = Column(Integer, default=0)
    uuid = Column(String)
    isbn = Column(String(collation='NOCASE'), default="")
    # Iccn = Column(String(collation='NOCASE'), default="")
    flags = Column(Integer, nullable=False, default=1)

    authors = relationship('Authors', secondary=books_authors_link, backref='books')
    tags = relationship('Tags', secondary=books_tags_link, backref='books',order_by="Tags.name")
    comments = relationship('Comments', backref='books')
    data = relationship('Data', backref='books')
    series = relationship('Series', secondary=books_series_link, backref='books')
    ratings = relationship('Ratings', secondary=books_ratings_link, backref='books')
    languages = relationship('Languages', secondary=books_languages_link, backref='books')
    publishers = relationship('Publishers', secondary=books_publishers_link, backref='books')
    identifiers = relationship('Identifiers', backref='books')

    def __init__(self, title, sort, author_sort, timestamp, pubdate, series_index, last_modified, path, has_cover,
                 authors, tags, languages=None):
        self.title = title
        self.sort = sort
        self.author_sort = author_sort
        self.timestamp = timestamp
        self.pubdate = pubdate
        self.series_index = series_index
        self.last_modified = last_modified
        self.path = path
        self.has_cover = has_cover

    def __repr__(self):
        return u"<Books('{0},{1}{2}{3}{4}{5}{6}{7}{8}')>".format(self.title, self.sort, self.author_sort,
                                                                 self.timestamp, self.pubdate, self.series_index,
                                                                 self.last_modified, self.path, self.has_cover)

    @property
    def atom_timestamp(self):
        return (self.timestamp.strftime('%Y-%m-%dT%H:%M:%S+00:00') or '')

class Custom_Columns(Base):
    __tablename__ = 'custom_columns'

    id = Column(Integer, primary_key=True)
    label = Column(String)
    name = Column(String)
    datatype = Column(String)
    mark_for_delete = Column(Boolean)
    editable = Column(Boolean)
    display = Column(String)
    is_multiple = Column(Boolean)
    normalized = Column(Boolean)

    def get_display_dict(self):
        display_dict = ast.literal_eval(self.display)
        if sys.version_info < (3, 0):
            display_dict['enum_values'] = [x.decode('unicode_escape') for x in display_dict['enum_values']]
        return display_dict


class CalibreDB(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.engine = None
        self.session = None
        self.queue = None
        self.log = None
        self.config = None

    def add_queue(self,queue):
        self.queue = queue
        self.log = logger.create()

    def run(self):
        while True:
            i = self.queue.get()
            if i == 'dummy':
                self.queue.task_done()
                break
            if i['task'] == 'add_format':
                cur_book = self.session.query(Books).filter(Books.id == i['id']).first()
                cur_book.data.append(i['format'])
                try:
                    # db.session.merge(cur_book)
                    self.session.commit()
                except OperationalError as e:
                    self.session.rollback()
                    self.log.error("Database error: %s", e)
                    # self._handleError(_(u"Database error: %(error)s.", error=e))
                    # return
            self.queue.task_done()


    def stop(self):
        self.queue.put('dummy')

    def setup_db(self, config, app_db_path):
        self.config = config
        self.dispose()
        # global engine

        if not config.config_calibre_dir:
            config.invalidate()
            return False

        dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
        if not os.path.exists(dbpath):
            config.invalidate()
            return False

        try:
            #engine = create_engine('sqlite:///{0}'.format(dbpath),
            self.engine = create_engine('sqlite://',
                                   echo=False,
                                   isolation_level="SERIALIZABLE",
                                   connect_args={'check_same_thread': False})
            self.engine.execute("attach database '{}' as calibre;".format(dbpath))
            self.engine.execute("attach database '{}' as app_settings;".format(app_db_path))

            conn = self.engine.connect()
            # conn.text_factory = lambda b: b.decode(errors = 'ignore') possible fix for #1302
        except Exception as e:
            config.invalidate(e)
            return False

        config.db_configured = True
        self.update_title_sort(config, conn.connection)

        if not cc_classes:
            cc = conn.execute("SELECT id, datatype FROM custom_columns")

            cc_ids = []
            books_custom_column_links = {}
            for row in cc:
                if row.datatype not in cc_exceptions:
                    books_custom_column_links[row.id] = Table('books_custom_column_' + str(row.id) + '_link', Base.metadata,
                                                              Column('book', Integer, ForeignKey('books.id'),
                                                                     primary_key=True),
                                                              Column('value', Integer,
                                                                     ForeignKey('custom_column_' + str(row.id) + '.id'),
                                                                     primary_key=True)
                                                              )
                    cc_ids.append([row.id, row.datatype])
                    if row.datatype == 'bool':
                        ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                                  'id': Column(Integer, primary_key=True),
                                  'book': Column(Integer, ForeignKey('books.id')),
                                  'value': Column(Boolean)}
                    elif row.datatype == 'int':
                        ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                                  'id': Column(Integer, primary_key=True),
                                  'book': Column(Integer, ForeignKey('books.id')),
                                  'value': Column(Integer)}
                    elif row.datatype == 'float':
                        ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                                  'id': Column(Integer, primary_key=True),
                                  'book': Column(Integer, ForeignKey('books.id')),
                                  'value': Column(Float)}
                    else:
                        ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                                  'id': Column(Integer, primary_key=True),
                                  'value': Column(String)}
                    cc_classes[row.id] = type(str('Custom_Column_' + str(row.id)), (Base,), ccdict)

            for cc_id in cc_ids:
                if (cc_id[1] == 'bool') or (cc_id[1] == 'int') or (cc_id[1] == 'float'):
                    setattr(Books,
                            'custom_column_' + str(cc_id[0]),
                            relationship(cc_classes[cc_id[0]],
                                         primaryjoin=(
                                         Books.id == cc_classes[cc_id[0]].book),
                                         backref='books'))
                else:
                    setattr(Books,
                            'custom_column_' + str(cc_id[0]),
                            relationship(cc_classes[cc_id[0]],
                                         secondary=books_custom_column_links[cc_id[0]],
                                         backref='books'))

        Session = scoped_session(sessionmaker(autocommit=False,
                                              autoflush=False,
                                              bind=self.engine))
        self.session = Session()
        return True

    def get_book(self, book_id):
        return self.session.query(Books).filter(Books.id == book_id).first()

    def get_filtered_book(self, book_id, allow_show_archived=False):
        return self.session.query(Books).filter(Books.id == book_id).\
            filter(self.common_filters(allow_show_archived)).first()

    def get_book_by_uuid(self, book_uuid):
        return self.session.query(Books).filter(Books.uuid == book_uuid).first()

    def get_book_format(self, book_id, format):
        return self.session.query(Data).filter(Data.book == book_id).filter(Data.format == format).first()

    # Language and content filters for displaying in the UI
    def common_filters(self, allow_show_archived=False):
        if not allow_show_archived:
            archived_books = (
                ub.session.query(ub.ArchivedBook)
                    .filter(ub.ArchivedBook.user_id == int(current_user.id))
                    .filter(ub.ArchivedBook.is_archived == True)
                    .all()
            )
            archived_book_ids = [archived_book.book_id for archived_book in archived_books]
            archived_filter = Books.id.notin_(archived_book_ids)
        else:
            archived_filter = true()

        if current_user.filter_language() != "all":
            lang_filter = Books.languages.any(Languages.lang_code == current_user.filter_language())
        else:
            lang_filter = true()
        negtags_list = current_user.list_denied_tags()
        postags_list = current_user.list_allowed_tags()
        neg_content_tags_filter = false() if negtags_list == [''] else Books.tags.any(Tags.name.in_(negtags_list))
        pos_content_tags_filter = true() if postags_list == [''] else Books.tags.any(Tags.name.in_(postags_list))
        if self.config.config_restricted_column:
            pos_cc_list = current_user.allowed_column_value.split(',')
            pos_content_cc_filter = true() if pos_cc_list == [''] else \
                getattr(Books, 'custom_column_' + str(self.config.config_restricted_column)). \
                    any(cc_classes[self.config.config_restricted_column].value.in_(pos_cc_list))
            neg_cc_list = current_user.denied_column_value.split(',')
            neg_content_cc_filter = false() if neg_cc_list == [''] else \
                getattr(Books, 'custom_column_' + str(self.config.config_restricted_column)). \
                    any(cc_classes[self.config.config_restricted_column].value.in_(neg_cc_list))
        else:
            pos_content_cc_filter = true()
            neg_content_cc_filter = false()
        return and_(lang_filter, pos_content_tags_filter, ~neg_content_tags_filter,
                    pos_content_cc_filter, ~neg_content_cc_filter, archived_filter)

    # Fill indexpage with all requested data from database
    def fill_indexpage(self, page, database, db_filter, order, *join):
        return self.fill_indexpage_with_archived_books(page, database, db_filter, order, False, *join)

    def fill_indexpage_with_archived_books(self, page, database, db_filter, order, allow_show_archived, *join):
        if current_user.show_detail_random():
            randm = self.session.query(Books) \
                .filter(self.common_filters(allow_show_archived)) \
                .order_by(func.random()) \
                .limit(self.config.config_random_books)
        else:
            randm = false()
        off = int(int(self.config.config_books_per_page) * (page - 1))
        query = self.session.query(database) \
            .join(*join, isouter=True) \
            .filter(db_filter) \
            .filter(self.common_filters(allow_show_archived))
        pagination = Pagination(page, self.config.config_books_per_page,
                                len(query.all()))
        entries = query.order_by(*order).offset(off).limit(self.config.config_books_per_page).all()
        for book in entries:
            book = self.order_authors(book)
        return entries, randm, pagination

    # Orders all Authors in the list according to authors sort
    def order_authors(self, entry):
        sort_authors = entry.author_sort.split('&')
        authors_ordered = list()
        error = False
        for auth in sort_authors:
            # ToDo: How to handle not found authorname
            result = self.session.query(Authors).filter(Authors.sort == auth.lstrip().strip()).first()
            if not result:
                error = True
                break
            authors_ordered.append(result)
        if not error:
            entry.authors = authors_ordered
        return entry

    def get_typeahead(self, database, query, replace=('', ''), tag_filter=true()):
        query = query or ''
        self.session.connection().connection.connection.create_function("lower", 1, lcase)
        entries = self.session.query(database).filter(tag_filter). \
            filter(func.lower(database.name).ilike("%" + query + "%")).all()
        json_dumps = json.dumps([dict(name=r.name.replace(*replace)) for r in entries])
        return json_dumps

    def check_exists_book(self, authr, title):
        self.session.connection().connection.connection.create_function("lower", 1, lcase)
        q = list()
        authorterms = re.split(r'\s*&\s*', authr)
        for authorterm in authorterms:
            q.append(Books.authors.any(func.lower(Authors.name).ilike("%" + authorterm + "%")))

        return self.session.query(Books)\
            .filter(and_(Books.authors.any(and_(*q)), func.lower(Books.title).ilike("%" + title + "%"))).first()

    # read search results from calibre-database and return it (function is used for feed and simple search
    def get_search_results(self, term):
        term.strip().lower()
        self.session.connection().connection.connection.create_function("lower", 1, lcase)
        q = list()
        authorterms = re.split("[, ]+", term)
        for authorterm in authorterms:
            q.append(Books.authors.any(func.lower(Authors.name).ilike("%" + authorterm + "%")))
        return self.session.query(Books).filter(self.common_filters(True)).filter(
            or_(Books.tags.any(func.lower(Tags.name).ilike("%" + term + "%")),
                Books.series.any(func.lower(Series.name).ilike("%" + term + "%")),
                Books.authors.any(and_(*q)),
                Books.publishers.any(func.lower(Publishers.name).ilike("%" + term + "%")),
                func.lower(Books.title).ilike("%" + term + "%")
                )).order_by(Books.sort).all()

    # Creates for all stored languages a translated speaking name in the array for the UI
    def speaking_language(self, languages=None):
        from . import get_locale

        if not languages:
            languages = self.session.query(Languages) \
                .join(books_languages_link) \
                .join(Books) \
                .filter(self.common_filters()) \
                .group_by(text('books_languages_link.lang_code')).all()
        for lang in languages:
            try:
                cur_l = LC.parse(lang.lang_code)
                lang.name = cur_l.get_language_name(get_locale())
            except UnknownLocaleError:
                lang.name = _(isoLanguages.get(part3=lang.lang_code).name)
        return languages

    def update_title_sort(self, config, conn=None):
        # user defined sort function for calibre databases (Series, etc.)
        def _title_sort(title):
            # calibre sort stuff
            title_pat = re.compile(config.config_title_regex, re.IGNORECASE)
            match = title_pat.search(title)
            if match:
                prep = match.group(1)
                title = title[len(prep):] + ', ' + prep
            return title.strip()

        conn = conn or self.session.connection().connection.connection
        conn.create_function("title_sort", 1, _title_sort)

    def dispose(self):
        # global session

        old_session = self.session
        self.session = None
        if old_session:
            try: old_session.close()
            except: pass
            if old_session.bind:
                try: old_session.bind.dispose()
                except Exception: pass

        for attr in list(Books.__dict__.keys()):
            if attr.startswith("custom_column_"):
                setattr(Books, attr, None)

        for db_class in cc_classes.values():
            Base.metadata.remove(db_class.__table__)
        cc_classes.clear()

        for table in reversed(Base.metadata.sorted_tables):
            name = table.key
            if name.startswith("custom_column_") or name.startswith("books_custom_column_"):
                if table is not None:
                    Base.metadata.remove(table)

    def reconnect_db(self, config, app_db_path):
        self.session.close()
        self.engine.dispose()
        self.setup_db(config, app_db_path)

def lcase(s):
    try:
        return unidecode.unidecode(s.lower())
    except Exception as e:
        log = logger.create()
        log.exception(e)
        return s.lower()
