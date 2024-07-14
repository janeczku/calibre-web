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

import os
import re
import json
from datetime import datetime
from urllib.parse import quote
import unidecode
from weakref import WeakSet

from sqlite3 import OperationalError as sqliteOperationalError
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, ForeignKey, CheckConstraint
from sqlalchemy import String, Integer, Boolean, TIMESTAMP, Float
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.exc import OperationalError
try:
    # Compatibility with sqlalchemy 2.0
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.expression import and_, true, false, text, func, or_
from sqlalchemy.ext.associationproxy import association_proxy
from .cw_login import current_user
from flask_babel import gettext as _
from flask_babel import get_locale
from flask import flash

from . import logger, ub, isoLanguages
from .pagination import Pagination


log = logger.create()

cc_exceptions = ['composite', 'series']
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


class Library_Id(Base):
    __tablename__ = 'library_id'
    id = Column(Integer, primary_key=True)
    uuid = Column(String, nullable=False)


class Identifiers(Base):
    __tablename__ = 'identifiers'

    id = Column(Integer, primary_key=True)
    type = Column(String(collation='NOCASE'), nullable=False, default="isbn")
    val = Column(String(collation='NOCASE'), nullable=False)
    book = Column(Integer, ForeignKey('books.id'), nullable=False)

    def __init__(self, val, id_type, book):
        super().__init__()
        self.val = val
        self.type = id_type
        self.book = book

    def format_type(self):
        format_type = self.type.lower()
        if format_type == 'amazon':
            return "Amazon"
        elif format_type.startswith("amazon_"):
            return "Amazon.{0}".format(format_type[7:])
        elif format_type == "isbn":
            return "ISBN"
        elif format_type == "doi":
            return "DOI"
        elif format_type == "douban":
            return "Douban"
        elif format_type == "goodreads":
            return "Goodreads"
        elif format_type == "babelio":
            return "Babelio"
        elif format_type == "google":
            return "Google Books"
        elif format_type == "kobo":
            return "Kobo"
        elif format_type == "barnesnoble":
            return "Barnes & Noble"
        elif format_type == "litres":
            return "ЛитРес"
        elif format_type == "issn":
            return "ISSN"
        elif format_type == "isfdb":
            return "ISFDB"
        if format_type == "lubimyczytac":
            return "Lubimyczytac"
        if format_type == "databazeknih":
            return "Databáze knih"
        else:
            return self.type

    def __repr__(self):
        format_type = self.type.lower()
        if format_type == "amazon" or format_type == "asin":
            return "https://amazon.com/dp/{0}".format(self.val)
        elif format_type.startswith('amazon_'):
            return "https://amazon.{0}/dp/{1}".format(format_type[7:], self.val)
        elif format_type == "isbn":
            return "https://www.worldcat.org/isbn/{0}".format(self.val)
        elif format_type == "doi":
            return "https://dx.doi.org/{0}".format(self.val)
        elif format_type == "goodreads":
            return "https://www.goodreads.com/book/show/{0}".format(self.val)
        elif format_type == "babelio":
            return "https://www.babelio.com/livres/titre/{0}".format(self.val)
        elif format_type == "douban":
            return "https://book.douban.com/subject/{0}".format(self.val)
        elif format_type == "google":
            return "https://books.google.com/books?id={0}".format(self.val)
        elif format_type == "kobo":
            return "https://www.kobo.com/ebook/{0}".format(self.val)
        elif format_type == "barnesnoble":
            return "https://www.barnesandnoble.com/w/{0}".format(self.val)
        elif format_type == "lubimyczytac":
            return "https://lubimyczytac.pl/ksiazka/{0}/ksiazka".format(self.val)
        elif format_type == "litres":
            return "https://www.litres.ru/{0}".format(self.val)
        elif format_type == "issn":
            return "https://portal.issn.org/resource/ISSN/{0}".format(self.val)
        elif format_type == "isfdb":
            return "http://www.isfdb.org/cgi-bin/pl.cgi?{0}".format(self.val)
        elif format_type == "databazeknih":
            return "https://www.databazeknih.cz/knihy/{0}".format(self.val)
        elif self.val.lower().startswith("javascript:"):
            return quote(self.val)
        elif self.val.lower().startswith("data:"):
            link, __, __ = str.partition(self.val, ",")
            return link
        else:
            return "{0}".format(self.val)


class Comments(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    book = Column(Integer, ForeignKey('books.id'), nullable=False, unique=True)
    text = Column(String(collation='NOCASE'), nullable=False)

    def __init__(self, comment, book):
        super().__init__()
        self.text = comment
        self.book = book

    def get(self):
        return self.text

    def __repr__(self):
        return "<Comments({0})>".format(self.text)


class Tags(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(collation='NOCASE'), unique=True, nullable=False)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def get(self):
        return self.name

    def __eq__(self, other):
        return self.name == other

    def __repr__(self):
        return "<Tags('{0})>".format(self.name)


class Authors(Base):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'), unique=True, nullable=False)
    sort = Column(String(collation='NOCASE'))
    link = Column(String, nullable=False, default="")

    def __init__(self, name, sort, link=""):
        super().__init__()
        self.name = name
        self.sort = sort
        self.link = link

    def get(self):
        return self.name

    def __eq__(self, other):
        return self.name == other

    def __repr__(self):
        return "<Authors('{0},{1}{2}')>".format(self.name, self.sort, self.link)


class Series(Base):
    __tablename__ = 'series'

    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'), unique=True, nullable=False)
    sort = Column(String(collation='NOCASE'))

    def __init__(self, name, sort):
        super().__init__()
        self.name = name
        self.sort = sort

    def get(self):
        return self.name

    def __eq__(self, other):
        return self.name == other

    def __repr__(self):
        return "<Series('{0},{1}')>".format(self.name, self.sort)


class Ratings(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True)
    rating = Column(Integer, CheckConstraint('rating>-1 AND rating<11'), unique=True)

    def __init__(self, rating):
        super().__init__()
        self.rating = rating

    def get(self):
        return self.rating

    def __eq__(self, other):
        return self.rating == other

    def __repr__(self):
        return "<Ratings('{0}')>".format(self.rating)


class Languages(Base):
    __tablename__ = 'languages'

    id = Column(Integer, primary_key=True)
    lang_code = Column(String(collation='NOCASE'), nullable=False, unique=True)

    def __init__(self, lang_code):
        super().__init__()
        self.lang_code = lang_code

    def get(self):
        if hasattr(self, "language_name"):
            return self.language_name
        else:
            return self.lang_code

    def __eq__(self, other):
        return self.lang_code == other

    def __repr__(self):
        return "<Languages('{0}')>".format(self.lang_code)


class Publishers(Base):
    __tablename__ = 'publishers'

    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'), nullable=False, unique=True)
    sort = Column(String(collation='NOCASE'))

    def __init__(self, name, sort):
        super().__init__()
        self.name = name
        self.sort = sort

    def get(self):
        return self.name

    def __eq__(self, other):
        return self.name == other

    def __repr__(self):
        return "<Publishers('{0},{1}')>".format(self.name, self.sort)


class Data(Base):
    __tablename__ = 'data'
    __table_args__ = {'schema': 'calibre'}

    id = Column(Integer, primary_key=True)
    book = Column(Integer, ForeignKey('books.id'), nullable=False)
    format = Column(String(collation='NOCASE'), nullable=False)
    uncompressed_size = Column(Integer, nullable=False)
    name = Column(String, nullable=False)

    def __init__(self, book, book_format, uncompressed_size, name):
        super().__init__()
        self.book = book
        self.format = book_format
        self.uncompressed_size = uncompressed_size
        self.name = name

    # ToDo: Check
    def get(self):
        return self.name

    def __repr__(self):
        return "<Data('{0},{1}{2}{3}')>".format(self.book, self.format, self.uncompressed_size, self.name)


class Metadata_Dirtied(Base):
    __tablename__ = 'metadata_dirtied'
    id = Column(Integer, primary_key=True, autoincrement=True)
    book = Column(Integer, ForeignKey('books.id'), nullable=False, unique=True)

    def __init__(self, book):
        super().__init__()
        self.book = book


class Books(Base):
    __tablename__ = 'books'

    DEFAULT_PUBDATE = datetime(101, 1, 1, 0, 0, 0, 0)  # ("0101-01-01 00:00:00+00:00")

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(collation='NOCASE'), nullable=False, default='Unknown')
    sort = Column(String(collation='NOCASE'))
    author_sort = Column(String(collation='NOCASE'))
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    pubdate = Column(TIMESTAMP, default=DEFAULT_PUBDATE)
    series_index = Column(String, nullable=False, default="1.0")
    last_modified = Column(TIMESTAMP, default=datetime.utcnow)
    path = Column(String, default="", nullable=False)
    has_cover = Column(Integer, default=0)
    uuid = Column(String)
    isbn = Column(String(collation='NOCASE'), default="")
    flags = Column(Integer, nullable=False, default=1)

    authors = relationship(Authors, secondary=books_authors_link, backref='books')
    tags = relationship(Tags, secondary=books_tags_link, backref='books', order_by="Tags.name")
    comments = relationship(Comments, backref='books')
    data = relationship(Data, backref='books')
    series = relationship(Series, secondary=books_series_link, backref='books')
    ratings = relationship(Ratings, secondary=books_ratings_link, backref='books')
    languages = relationship(Languages, secondary=books_languages_link, backref='books')
    publishers = relationship(Publishers, secondary=books_publishers_link, backref='books')
    identifiers = relationship(Identifiers, backref='books')

    def __init__(self, title, sort, author_sort, timestamp, pubdate, series_index, last_modified, path, has_cover,
                 authors, tags, languages=None):
        super().__init__()
        self.title = title
        self.sort = sort
        self.author_sort = author_sort
        self.timestamp = timestamp
        self.pubdate = pubdate
        self.series_index = series_index
        self.last_modified = last_modified
        self.path = path
        self.has_cover = (has_cover is not None)

    def __repr__(self):
        return "<Books('{0},{1}{2}{3}{4}{5}{6}{7}{8}')>".format(self.title, self.sort, self.author_sort,
                                                                self.timestamp, self.pubdate, self.series_index,
                                                                self.last_modified, self.path, self.has_cover)

    @property
    def atom_timestamp(self):
        return self.timestamp.strftime('%Y-%m-%dT%H:%M:%S+00:00') or ''


class CustomColumns(Base):
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
        display_dict = json.loads(self.display)
        return display_dict

    def to_json(self, value, extra, sequence):
        content = dict()
        content['table'] = "custom_column_" + str(self.id)
        content['column'] = "value"
        content['datatype'] = self.datatype
        content['is_multiple'] = None if not self.is_multiple else "|"
        content['kind'] = "field"
        content['name'] = self.name
        content['search_terms'] = ['#' + self.label]
        content['label'] = self.label
        content['colnum'] = self.id
        content['display'] = self.get_display_dict()
        content['is_custom'] = True
        content['is_category'] = self.datatype in ['text', 'rating', 'enumeration', 'series']
        content['link_column'] = "value"
        content['category_sort'] = "value"
        content['is_csp'] = False
        content['is_editable'] = self.editable
        content['rec_index'] = sequence + 22     # toDo why ??
        if isinstance(value, datetime):
            content['#value#'] = {"__class__": "datetime.datetime",
                                  "__value__": value.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
        else:
            content['#value#'] = value
        content['#extra#'] = extra
        content['is_multiple2'] = {} if not self.is_multiple else {"cache_to_list": "|", "ui_to_list": ",",
                                                                   "list_to_ui": ", "}
        return json.dumps(content, ensure_ascii=False)


class AlchemyEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(o) if not x.startswith('_') and x != 'metadata' and x != "password"]:
                if field == 'books':
                    continue
                data = o.__getattribute__(field)
                try:
                    if isinstance(data, str):
                        data = data.replace("'", "\'")
                    elif isinstance(data, InstrumentedList):
                        el = list()
                        # ele = None
                        for ele in data:
                            if hasattr(ele, 'value'):       # converter for custom_column values
                                el.append(str(ele.value))
                            elif ele.get:
                                el.append(ele.get())
                            else:
                                el.append(json.dumps(ele, cls=AlchemyEncoder))
                        if field == 'authors':
                            data = " & ".join(el)
                        else:
                            data = ",".join(el)
                        if data == '[]':
                            data = ""
                    else:
                        json.dumps(data)
                    fields[field] = data
                except Exception:
                    fields[field] = ""
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, o)


class CalibreDB:
    _init = False
    engine = None
    config = None
    session_factory = None
    # This is a WeakSet so that references here don't keep other CalibreDB
    # instances alive once they reach the end of their respective scopes
    instances = WeakSet()

    def __init__(self, expire_on_commit=True, init=False):
        """ Initialize a new CalibreDB session
        """
        self.session = None
        if init:
            self.init_db(expire_on_commit)

    def init_db(self, expire_on_commit=True):
        if self._init:
            self.init_session(expire_on_commit)

        self.instances.add(self)

    def init_session(self, expire_on_commit=True):
        self.session = self.session_factory()
        self.session.expire_on_commit = expire_on_commit
        self.update_title_sort(self.config)

    @classmethod
    def setup_db_cc_classes(cls, cc):
        cc_ids = []
        books_custom_column_links = {}
        for row in cc:
            if row.datatype not in cc_exceptions:
                if row.datatype == 'series':
                    dicttable = {'__tablename__': 'books_custom_column_' + str(row.id) + '_link',
                                 'id': Column(Integer, primary_key=True),
                                 'book': Column(Integer, ForeignKey('books.id'),
                                                primary_key=True),
                                 'map_value': Column('value', Integer,
                                                     ForeignKey('custom_column_' +
                                                                str(row.id) + '.id'),
                                                     primary_key=True),
                                 'extra': Column(Float),
                                 'asoc': relationship('custom_column_' + str(row.id), uselist=False),
                                 'value': association_proxy('asoc', 'value')
                                 }
                    books_custom_column_links[row.id] = type(str('books_custom_column_' + str(row.id) + '_link'),
                                                             (Base,), dicttable)
                if row.datatype in ['rating', 'text', 'enumeration']:
                    books_custom_column_links[row.id] = Table('books_custom_column_' + str(row.id) + '_link',
                                                              Base.metadata,
                                                              Column('book', Integer, ForeignKey('books.id'),
                                                                     primary_key=True),
                                                              Column('value', Integer,
                                                                     ForeignKey('custom_column_' +
                                                                                str(row.id) + '.id'),
                                                                     primary_key=True)
                                                              )
                cc_ids.append([row.id, row.datatype])

                ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                          'id': Column(Integer, primary_key=True)}
                if row.datatype == 'float':
                    ccdict['value'] = Column(Float)
                elif row.datatype == 'int':
                    ccdict['value'] = Column(Integer)
                elif row.datatype == 'datetime':
                    ccdict['value'] = Column(TIMESTAMP)
                elif row.datatype == 'bool':
                    ccdict['value'] = Column(Boolean)
                else:
                    ccdict['value'] = Column(String)
                if row.datatype in ['float', 'int', 'bool', 'datetime', 'comments']:
                    ccdict['book'] = Column(Integer, ForeignKey('books.id'))
                cc_classes[row.id] = type(str('custom_column_' + str(row.id)), (Base,), ccdict)

        for cc_id in cc_ids:
            if cc_id[1] in ['bool', 'int', 'float', 'datetime', 'comments']:
                setattr(Books,
                        'custom_column_' + str(cc_id[0]),
                        relationship(cc_classes[cc_id[0]],
                                     primaryjoin=(
                                         Books.id == cc_classes[cc_id[0]].book),
                                     backref='books'))
            elif cc_id[1] == 'series':
                setattr(Books,
                        'custom_column_' + str(cc_id[0]),
                        relationship(books_custom_column_links[cc_id[0]],
                                     backref='books'))
            else:
                setattr(Books,
                        'custom_column_' + str(cc_id[0]),
                        relationship(cc_classes[cc_id[0]],
                                     secondary=books_custom_column_links[cc_id[0]],
                                     backref='books'))

        return cc_classes

    @classmethod
    def check_valid_db(cls, config_calibre_dir, app_db_path, config_calibre_uuid):
        if not config_calibre_dir:
            return False, False
        dbpath = os.path.join(config_calibre_dir, "metadata.db")
        if not os.path.exists(dbpath):
            return False, False
        try:
            check_engine = create_engine('sqlite://',
                                         echo=False,
                                         isolation_level="SERIALIZABLE",
                                         connect_args={'check_same_thread': False},
                                         poolclass=StaticPool)
            with check_engine.begin() as connection:
                connection.execute(text("attach database '{}' as calibre;".format(dbpath)))
                connection.execute(text("attach database '{}' as app_settings;".format(app_db_path)))
                local_session = scoped_session(sessionmaker())
                local_session.configure(bind=connection)
                database_uuid = local_session().query(Library_Id).one_or_none()
                # local_session.dispose()

            check_engine.connect()
            db_change = config_calibre_uuid != database_uuid.uuid
        except Exception:
            return False, False
        return True, db_change

    @classmethod
    def update_config(cls, config):
        cls.config = config

    @classmethod
    def setup_db(cls, config_calibre_dir, app_db_path):
        cls.dispose()

        if not config_calibre_dir:
            cls.config.invalidate()
            return None

        dbpath = os.path.join(config_calibre_dir, "metadata.db")
        if not os.path.exists(dbpath):
            cls.config.invalidate()
            return None

        try:
            cls.engine = create_engine('sqlite://',
                                       echo=False,
                                       isolation_level="SERIALIZABLE",
                                       connect_args={'check_same_thread': False},
                                       poolclass=StaticPool)
            with cls.engine.begin() as connection:
                connection.execute(text("attach database '{}' as calibre;".format(dbpath)))
                connection.execute(text("attach database '{}' as app_settings;".format(app_db_path)))

            conn = cls.engine.connect()
            # conn.text_factory = lambda b: b.decode(errors = 'ignore') possible fix for #1302
        except Exception as ex:
            cls.config.invalidate(ex)
            return None

        cls.config.db_configured = True

        if not cc_classes:
            try:
                cc = conn.execute(text("SELECT id, datatype FROM custom_columns"))
                cls.setup_db_cc_classes(cc)
            except OperationalError as e:
                log.error_or_exception(e)
                return None

        cls.session_factory = scoped_session(sessionmaker(autocommit=False,
                                                          autoflush=True,
                                                          bind=cls.engine, future=True))
        for inst in cls.instances:
            inst.init_session()

        cls._init = True

    def get_book(self, book_id):
        return self.session.query(Books).filter(Books.id == book_id).first()

    def get_filtered_book(self, book_id, allow_show_archived=False):
        return self.session.query(Books).filter(Books.id == book_id). \
            filter(self.common_filters(allow_show_archived)).first()

    def get_book_read_archived(self, book_id, read_column, allow_show_archived=False):
        if not read_column:
            bd = (self.session.query(Books, ub.ReadBook.read_status, ub.ArchivedBook.is_archived).select_from(Books)
                  .join(ub.ReadBook, and_(ub.ReadBook.user_id == int(current_user.id), ub.ReadBook.book_id == book_id),
                  isouter=True))
        else:
            try:
                read_column = cc_classes[read_column]
                bd = (self.session.query(Books, read_column.value, ub.ArchivedBook.is_archived).select_from(Books)
                      .join(read_column, read_column.book == book_id,
                      isouter=True))
            except (KeyError, AttributeError, IndexError):
                log.error("Custom Column No.{} does not exist in calibre database".format(read_column))
                # Skip linking read column and return None instead of read status
                bd = self.session.query(Books, None, ub.ArchivedBook.is_archived)
        return (bd.filter(Books.id == book_id)
                .join(ub.ArchivedBook, and_(Books.id == ub.ArchivedBook.book_id,
                                            int(current_user.id) == ub.ArchivedBook.user_id), isouter=True)
                .filter(self.common_filters(allow_show_archived)).first())

    def get_book_by_uuid(self, book_uuid):
        return self.session.query(Books).filter(Books.uuid == book_uuid).first()

    def get_book_format(self, book_id, file_format):
        return self.session.query(Data).filter(Data.book == book_id).filter(Data.format == file_format).first()

    def set_metadata_dirty(self, book_id):
        if not self.session.query(Metadata_Dirtied).filter(Metadata_Dirtied.book == book_id).one_or_none():
            self.session.add(Metadata_Dirtied(book_id))

    def delete_dirty_metadata(self, book_id):
        try:
            self.session.query(Metadata_Dirtied).filter(Metadata_Dirtied.book == book_id).delete()
            self.session.commit()
        except (OperationalError) as e:
            self.session.rollback()
            log.error("Database error: {}".format(e))

    # Language and content filters for displaying in the UI
    def common_filters(self, allow_show_archived=False, return_all_languages=False):
        if not allow_show_archived:
            archived_books = (ub.session.query(ub.ArchivedBook)
                              .filter(ub.ArchivedBook.user_id==int(current_user.id))
                              .filter(ub.ArchivedBook.is_archived==True)
                              .all())
            archived_book_ids = [archived_book.book_id for archived_book in archived_books]
            archived_filter = Books.id.notin_(archived_book_ids)
        else:
            archived_filter = true()

        if current_user.filter_language() == "all" or return_all_languages:
            lang_filter = true()
        else:
            lang_filter = Books.languages.any(Languages.lang_code == current_user.filter_language())
        negtags_list = current_user.list_denied_tags()
        postags_list = current_user.list_allowed_tags()
        neg_content_tags_filter = false() if negtags_list == [''] else Books.tags.any(Tags.name.in_(negtags_list))
        pos_content_tags_filter = true() if postags_list == [''] else Books.tags.any(Tags.name.in_(postags_list))
        if self.config.config_restricted_column:
            try:
                pos_cc_list = current_user.allowed_column_value.split(',')
                pos_content_cc_filter = true() if pos_cc_list == [''] else \
                    getattr(Books, 'custom_column_' + str(self.config.config_restricted_column)). \
                    any(cc_classes[self.config.config_restricted_column].value.in_(pos_cc_list))
                neg_cc_list = current_user.denied_column_value.split(',')
                neg_content_cc_filter = false() if neg_cc_list == [''] else \
                    getattr(Books, 'custom_column_' + str(self.config.config_restricted_column)). \
                    any(cc_classes[self.config.config_restricted_column].value.in_(neg_cc_list))
            except (KeyError, AttributeError, IndexError):
                pos_content_cc_filter = false()
                neg_content_cc_filter = true()
                log.error("Custom Column No.{} does not exist in calibre database".format(
                    self.config.config_restricted_column))
                flash(_("Custom Column No.%(column)d does not exist in calibre database",
                        column=self.config.config_restricted_column),
                      category="error")

        else:
            pos_content_cc_filter = true()
            neg_content_cc_filter = false()
        return and_(lang_filter, pos_content_tags_filter, ~neg_content_tags_filter,
                    pos_content_cc_filter, ~neg_content_cc_filter, archived_filter)

    def generate_linked_query(self, config_read_column, database):
        if not config_read_column:
            query = (self.session.query(database, ub.ArchivedBook.is_archived, ub.ReadBook.read_status)
                     .select_from(Books)
                     .outerjoin(ub.ReadBook,
                                and_(ub.ReadBook.user_id == int(current_user.id), ub.ReadBook.book_id == Books.id)))
        else:
            try:
                read_column = cc_classes[config_read_column]
                query = (self.session.query(database, ub.ArchivedBook.is_archived, read_column.value)
                         .select_from(Books)
                         .outerjoin(read_column, read_column.book == Books.id))
            except (KeyError, AttributeError, IndexError):
                log.error("Custom Column No.{} does not exist in calibre database".format(config_read_column))
                # Skip linking read column and return None instead of read status
                query = self.session.query(database, None, ub.ArchivedBook.is_archived)
        return query.outerjoin(ub.ArchivedBook, and_(Books.id == ub.ArchivedBook.book_id,
                                                     int(current_user.id) == ub.ArchivedBook.user_id))

    @staticmethod
    def get_checkbox_sorted(inputlist, state, offset, limit, order, combo=False):
        outcome = list()
        if combo:
            elementlist = {ele[0].id: ele for ele in inputlist}
        else:
            elementlist = {ele.id: ele for ele in inputlist}
        for entry in state:
            try:
                outcome.append(elementlist[entry])
            except KeyError:
                pass
            del elementlist[entry]
        for entry in elementlist:
            outcome.append(elementlist[entry])
        if order == "asc":
            outcome.reverse()
        return outcome[offset:offset + limit]

    # Fill indexpage with all requested data from database
    def fill_indexpage(self, page, pagesize, database, db_filter, order,
                       join_archive_read=False, config_read_column=0, *join):
        return self.fill_indexpage_with_archived_books(page, database, pagesize, db_filter, order, False,
                                                       join_archive_read, config_read_column, *join)

    def fill_indexpage_with_archived_books(self, page, database, pagesize, db_filter, order, allow_show_archived,
                                           join_archive_read, config_read_column, *join):
        pagesize = pagesize or self.config.config_books_per_page
        if current_user.show_detail_random():
            random_query = self.generate_linked_query(config_read_column, database)
            randm = (random_query.filter(self.common_filters(allow_show_archived))
                     .order_by(func.random())
                     .limit(self.config.config_random_books).all())
        else:
            randm = false()
        if join_archive_read:
            query = self.generate_linked_query(config_read_column, database)
        else:
            query = self.session.query(database)
        off = int(int(pagesize) * (page - 1))

        indx = len(join)
        element = 0
        while indx:
            if indx >= 3:
                query = query.outerjoin(join[element], join[element+1]).outerjoin(join[element+2])
                indx -= 3
                element += 3
            elif indx == 2:
                query = query.outerjoin(join[element], join[element+1])
                indx -= 2
                element += 2
            elif indx == 1:
                query = query.outerjoin(join[element])
                indx -= 1
                element += 1
        query = query.filter(db_filter)\
            .filter(self.common_filters(allow_show_archived))
        entries = list()
        pagination = list()
        try:
            pagination = Pagination(page, pagesize, query.count())
            entries = query.order_by(*order).offset(off).limit(pagesize).all()
        except Exception as ex:
            log.error_or_exception(ex)
        # display authors in right order
        entries = self.order_authors(entries, True, join_archive_read)
        return entries, randm, pagination

    # Orders all Authors in the list according to authors sort
    def order_authors(self, entries, list_return=False, combined=False):
        for entry in entries:
            if combined:
                sort_authors = entry.Books.author_sort.split('&')
                ids = [a.id for a in entry.Books.authors]

            else:
                sort_authors = entry.author_sort.split('&')
                ids = [a.id for a in entry.authors]
            authors_ordered = list()
            # error = False
            for auth in sort_authors:
                results = self.session.query(Authors).filter(Authors.sort == auth.lstrip().strip()).all()
                # ToDo: How to handle not found author name
                if not len(results):
                    log.error("Author {} not found to display name in right order".format(auth.strip()))
                    # error = True
                    break
                for r in results:
                    if r.id in ids:
                        authors_ordered.append(r)
                        ids.remove(r.id)
            for author_id in ids:
                result = self.session.query(Authors).filter(Authors.id == author_id).first()
                authors_ordered.append(result)

            if list_return:
                if combined:
                    entry.Books.authors = authors_ordered
                else:
                    entry.ordered_authors = authors_ordered
            else:
                return authors_ordered
        return entries

    def get_typeahead(self, database, query, replace=('', ''), tag_filter=true()):
        query = query or ''
        self.session.connection().connection.connection.create_function("lower", 1, lcase)
        entries = self.session.query(database).filter(tag_filter). \
            filter(func.lower(database.name).ilike("%" + query + "%")).all()
        # json_dumps = json.dumps([dict(name=escape(r.name.replace(*replace))) for r in entries])
        json_dumps = json.dumps([dict(name=r.name.replace(*replace)) for r in entries])
        return json_dumps

    def check_exists_book(self, authr, title):
        self.session.connection().connection.connection.create_function("lower", 1, lcase)
        q = list()
        author_terms = re.split(r'\s*&\s*', authr)
        for author_term in author_terms:
            q.append(Books.authors.any(func.lower(Authors.name).ilike("%" + author_term + "%")))

        return self.session.query(Books) \
            .filter(and_(Books.authors.any(and_(*q)), func.lower(Books.title).ilike("%" + title + "%"))).first()

    def search_query(self, term, config, *join):
        term.strip().lower()
        self.session.connection().connection.connection.create_function("lower", 1, lcase)
        q = list()
        author_terms = re.split("[, ]+", term)
        for author_term in author_terms:
            q.append(Books.authors.any(func.lower(Authors.name).ilike("%" + author_term + "%")))
        query = self.generate_linked_query(config.config_read_column, Books)
        if len(join) == 6:
            query = query.outerjoin(join[0], join[1]).outerjoin(join[2]).outerjoin(join[3], join[4]).outerjoin(join[5])
        if len(join) == 3:
            query = query.outerjoin(join[0], join[1]).outerjoin(join[2])
        elif len(join) == 2:
            query = query.outerjoin(join[0], join[1])
        elif len(join) == 1:
            query = query.outerjoin(join[0])

        cc = self.get_cc_columns(config, filter_config_custom_read=True)
        filter_expression = [Books.tags.any(func.lower(Tags.name).ilike("%" + term + "%")),
                             Books.series.any(func.lower(Series.name).ilike("%" + term + "%")),
                             Books.authors.any(and_(*q)),
                             Books.publishers.any(func.lower(Publishers.name).ilike("%" + term + "%")),
                             func.lower(Books.title).ilike("%" + term + "%")]
        for c in cc:
            if c.datatype not in ["datetime", "rating", "bool", "int", "float"]:
                filter_expression.append(
                    getattr(Books,
                            'custom_column_' + str(c.id)).any(
                        func.lower(cc_classes[c.id].value).ilike("%" + term + "%")))
        return query.filter(self.common_filters(True)).filter(or_(*filter_expression))

    def get_cc_columns(self, config, filter_config_custom_read=False):
        tmp_cc = self.session.query(CustomColumns).filter(CustomColumns.datatype.notin_(cc_exceptions)).all()
        cc = []
        r = None
        if config.config_columns_to_ignore:
            r = re.compile(config.config_columns_to_ignore)

        for col in tmp_cc:
            if filter_config_custom_read and config.config_read_column and config.config_read_column == col.id:
                continue
            if r and r.match(col.name):
                continue
            cc.append(col)

        return cc

    # read search results from calibre-database and return it (function is used for feed and simple search
    def get_search_results(self, term, config, offset=None, order=None, limit=None, *join):
        order = order[0] if order else [Books.sort]
        pagination = None
        result = self.search_query(term, config, *join).order_by(*order).all()
        result_count = len(result)
        if offset is not None and limit is not None:
            offset = int(offset)
            limit_all = offset + int(limit)
            pagination = Pagination((offset / (int(limit)) + 1), limit, result_count)
        else:
            offset = 0
            limit_all = result_count

        ub.store_combo_ids(result)
        entries = self.order_authors(result[offset:limit_all], list_return=True, combined=True)

        return entries, result_count, pagination

    # Creates for all stored languages a translated speaking name in the array for the UI
    def speaking_language(self, languages=None, return_all_languages=False, with_count=False, reverse_order=False):

        if with_count:
            if not languages:
                languages = self.session.query(Languages, func.count('books_languages_link.book'))\
                    .join(books_languages_link).join(Books)\
                    .filter(self.common_filters(return_all_languages=return_all_languages)) \
                    .group_by(text('books_languages_link.lang_code')).all()
            tags = list()
            for lang in languages:
                tag = Category(isoLanguages.get_language_name(get_locale(), lang[0].lang_code), lang[0].lang_code)
                tags.append([tag, lang[1]])
            # Append all books without language to list
            if not return_all_languages:
                no_lang_count = (self.session.query(Books)
                                 .outerjoin(books_languages_link).outerjoin(Languages)
                                 .filter(Languages.lang_code==None)
                                 .filter(self.common_filters())
                                 .count())
                if no_lang_count:
                    tags.append([Category(_("None"), "none"), no_lang_count])
            return sorted(tags, key=lambda x: x[0].name.lower(), reverse=reverse_order)
        else:
            if not languages:
                languages = self.session.query(Languages) \
                    .join(books_languages_link) \
                    .join(Books) \
                    .filter(self.common_filters(return_all_languages=return_all_languages)) \
                    .group_by(text('books_languages_link.lang_code')).all()
            for lang in languages:
                lang.name = isoLanguages.get_language_name(get_locale(), lang.lang_code)
            return sorted(languages, key=lambda x: x.name, reverse=reverse_order)

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

        try:
            # sqlalchemy <1.4.24
            conn = conn or self.session.connection().connection.driver_connection
        except AttributeError:
            # sqlalchemy >1.4.24 and sqlalchemy 2.0
            conn = conn or self.session.connection().connection.connection
        try:
            conn.create_function("title_sort", 1, _title_sort)
        except sqliteOperationalError:
            pass

    @classmethod
    def dispose(cls):
        # global session

        for inst in cls.instances:
            old_session = inst.session
            inst.session = None
            if old_session:
                try:
                    old_session.close()
                except Exception:
                    pass
                if old_session.bind:
                    try:
                        old_session.bind.dispose()
                    except Exception:
                        pass

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
        self.dispose()
        self.engine.dispose()
        self.setup_db(config.config_calibre_dir, app_db_path)
        self.update_config(config)


def lcase(s):
    try:
        return unidecode.unidecode(s.lower())
    except Exception as ex:
        _log = logger.create()
        _log.error_or_exception(ex)
        return s.lower()


class Category:
    name = None
    id = None
    count = None
    rating = None

    def __init__(self, name, cat_id, rating=None):
        self.name = name
        self.id = cat_id
        self.rating = rating
        self.count = 1
