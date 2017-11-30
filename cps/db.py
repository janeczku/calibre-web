#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
import os
import re
import ast
from ub import config
import ub

session = None
cc_exceptions = ['datetime', 'comments', 'float', 'composite', 'series']
cc_classes = None
engine = None


# user defined sort function for calibre databases (Series, etc.)
def title_sort(title):
    # calibre sort stuff
    title_pat = re.compile(config.config_title_regex, re.IGNORECASE)
    match = title_pat.search(title)
    if match:
        prep = match.group(1)
        title = title.replace(prep, '') + ', ' + prep
    return title.strip()


def lcase(s):
    return s.lower()


def ucase(s):
    return s.upper()


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
    type = Column(String)
    val = Column(String)
    book = Column(Integer, ForeignKey('books.id'))

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
        else:
            return self.type

    def __repr__(self):
        if self.type == "amazon":
            return u"https://amzn.com/{0}".format(self.val)
        elif self.type == "isbn":
            return u"http://www.worldcat.org/isbn/{0}".format(self.val)
        elif self.type == "doi":
            return u"http://dx.doi.org/{0}".format(self.val)
        elif self.type == "goodreads":
            return u"http://www.goodreads.com/book/show/{0}".format(self.val)
        elif self.type == "douban":
            return u"https://book.douban.com/subject/{0}".format(self.val)
        elif self.type == "google":
            return u"https://books.google.com/books?id={0}".format(self.val)
        elif self.type == "kobo":
            return u"https://www.kobo.com/ebook/{0}".format(self.val)
        else:
            return u""


class Comments(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    text = Column(String)
    book = Column(Integer, ForeignKey('books.id'))

    def __init__(self, text, book):
        self.text = text
        self.book = book

    def __repr__(self):
        return u"<Comments({0})>".format(self.text)


class Tags(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return u"<Tags('{0})>".format(self.name)


class Authors(Base):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    sort = Column(String)
    link = Column(String)

    def __init__(self, name, sort, link):
        self.name = name
        self.sort = sort
        self.link = link

    def __repr__(self):
        return u"<Authors('{0},{1}{2}')>".format(self.name, self.sort, self.link)


class Series(Base):
    __tablename__ = 'series'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    sort = Column(String)

    def __init__(self, name, sort):
        self.name = name
        self.sort = sort

    def __repr__(self):
        return u"<Series('{0},{1}')>".format(self.name, self.sort)


class Ratings(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True)
    rating = Column(Integer)

    def __init__(self, rating):
        self.rating = rating

    def __repr__(self):
        return u"<Ratings('{0}')>".format(self.rating)


class Languages(Base):
    __tablename__ = 'languages'

    id = Column(Integer, primary_key=True)
    lang_code = Column(String)

    def __init__(self, lang_code):
        self.lang_code = lang_code

    def __repr__(self):
        return u"<Languages('{0}')>".format(self.lang_code)


class Publishers(Base):
    __tablename__ = 'publishers'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    sort = Column(String)

    def __init__(self, name, sort):
        self.name = name
        self.sort = sort

    def __repr__(self):
        return u"<Publishers('{0},{1}')>".format(self.name, self.sort)


class Data(Base):
    __tablename__ = 'data'

    id = Column(Integer, primary_key=True)
    book = Column(Integer, ForeignKey('books.id'))
    format = Column(String)
    uncompressed_size = Column(Integer)
    name = Column(String)

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

    id = Column(Integer, primary_key=True)
    title = Column(String)
    sort = Column(String)
    author_sort = Column(String)
    timestamp = Column(String)
    pubdate = Column(String)
    series_index = Column(String)
    last_modified = Column(String)
    path = Column(String)
    has_cover = Column(Integer)
    uuid = Column(String)

    authors = relationship('Authors', secondary=books_authors_link, backref='books')
    tags = relationship('Tags', secondary=books_tags_link, backref='books')
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
        return display_dict


def setup_db():
    global engine
    global session
    global cc_classes

    if config.config_calibre_dir is None or config.config_calibre_dir == u'':
        content = ub.session.query(ub.Settings).first()
        content.config_calibre_dir = None
        content.db_configured = False
        ub.session.commit()
        config.loadSettings()
        return False

    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
    engine = create_engine('sqlite:///' + dbpath, echo=False, isolation_level="SERIALIZABLE")
    try:
        conn = engine.connect()
    except Exception:
        content = ub.session.query(ub.Settings).first()
        content.config_calibre_dir = None
        content.db_configured = False
        ub.session.commit()
        config.loadSettings()
        return False
    content = ub.session.query(ub.Settings).first()
    content.db_configured = True
    ub.session.commit()
    config.loadSettings()
    conn.connection.create_function('title_sort', 1, title_sort)
    conn.connection.create_function('lower', 1, lcase)
    conn.connection.create_function('upper', 1, ucase)

    if not cc_classes:
        cc = conn.execute("SELECT id, datatype FROM custom_columns")

        cc_ids = []
        books_custom_column_links = {}
        cc_classes = {}
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
                else:
                    ccdict = {'__tablename__': 'custom_column_' + str(row.id),
                              'id': Column(Integer, primary_key=True),
                              'value': Column(String)}
                cc_classes[row.id] = type('Custom_Column_' + str(row.id), (Base,), ccdict)

        for cc_id in cc_ids:
            if (cc_id[1] == 'bool') or (cc_id[1] == 'int'):
                setattr(Books, 'custom_column_' + str(cc_id[0]), relationship(cc_classes[cc_id[0]],
                                                                           primaryjoin=(
                                                                           Books.id == cc_classes[cc_id[0]].book),
                                                                           backref='books'))
            else:
                setattr(Books, 'custom_column_' + str(cc_id[0]), relationship(cc_classes[cc_id[0]],
                                                                           secondary=books_custom_column_links[cc_id[0]],
                                                                           backref='books'))

    # Base.metadata.create_all(engine)
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return True
