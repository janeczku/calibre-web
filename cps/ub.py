#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import *
from sqlalchemy import exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
from flask_login import AnonymousUserMixin
import os
import config
import traceback
from werkzeug.security import generate_password_hash
from flask_babel import gettext as _

dbpath = os.path.join(config.APP_DB_ROOT, "app.db")
engine = create_engine('sqlite:///{0}'.format(dbpath), echo=False)
Base = declarative_base()

ROLE_USER = 0
ROLE_ADMIN = 1
ROLE_DOWNLOAD = 2
ROLE_UPLOAD = 4 
ROLE_EDIT = 8
ROLE_PASSWD = 16
ROLE_ANONYMOUS = 32
DEFAULT_PASS = "admin123"


class UserBase():
    def is_authenticated(self):
        return True

    def role_admin(self):
        if self.role is not None:
            return True if self.role & ROLE_ADMIN == ROLE_ADMIN else False
        else:
            return False

    def role_download(self):
        if self.role is not None:
            return True if self.role & ROLE_DOWNLOAD == ROLE_DOWNLOAD else False
        else:
            return False

    def role_upload(self):
        if self.role is not None:
            return True if self.role & ROLE_UPLOAD == ROLE_UPLOAD else False
        else:
            return False

    def role_edit(self):
        if self.role is not None:
            return True if self.role & ROLE_EDIT == ROLE_EDIT else False
        else:
            return False

    def role_passwd(self):
        if self.role is not None:
            return True if self.role & ROLE_PASSWD == ROLE_PASSWD else False
        else:
            return False

    def role_anonymous(self):
        if self.role is not None:
            return True if self.role & ROLE_ANONYMOUS == ROLE_ANONYMOUS else False
        else:
            return False

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def filter_language(self):
        return self.default_language

    def show_random_books(self):
        return self.random_books

    def show_language(self):
        return self.language_books

    def show_hot_books(self):
        return self.hot_books

    def show_series(self):
        return self.series_books

    def show_category(self):
        return self.category_books

    def __repr__(self):
        return '<User %r>' % self.nickname


class User(UserBase,Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    nickname = Column(String(64), unique=True)
    email = Column(String(120), unique=True, default="")
    role = Column(SmallInteger, default=ROLE_USER)
    password = Column(String)
    kindle_mail = Column(String(120), default="")
    shelf = relationship('Shelf', backref='user', lazy='dynamic')
    downloads = relationship('Downloads', backref='user', lazy='dynamic')
    locale = Column(String(2), default="en")
    random_books = Column(Integer, default=1)
    language_books = Column(Integer, default=1)
    series_books = Column(Integer, default=1)
    category_books = Column(Integer, default=1)
    hot_books = Column(Integer, default=1)
    default_language = Column(String(3), default="all")


class Anonymous(AnonymousUserMixin,UserBase):
    def __init__(self):
        self.loadSettings()

    def loadSettings(self):
        data=session.query(User).filter(User.role.op('&')(ROLE_ANONYMOUS) == ROLE_ANONYMOUS).first()
        self.nickname = data.nickname
        self.role = data.role
        self.random_books = data.random_books
        self.default_language = data.default_language
        self.language_books = data.language_books
        self.series_books = data.series_books
        self.category_books = data.category_books
        self.hot_books = data.hot_books
        self.default_language = data.default_language
        self.locale = data.locale

    def role_admin(self):
        return False

    def is_active(self):
        return False

    def is_anonymous(self):
        return config.ANON_BROWSE


class Shelf(Base):
    __tablename__ = 'shelf'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    is_public = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey('user.id'))

    def __repr__(self):
        return '<Shelf %r>' % self.name

class BookShelf(Base):
    __tablename__ = 'book_shelf_link'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer)
    order = Column(Integer)
    shelf = Column(Integer, ForeignKey('shelf.id'))

    def __repr__(self):
        return '<Book %r>' % self.id


class Downloads(Base):
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer)
    user_id = Column(Integer, ForeignKey('user.id'))

    def __repr__(self):
        return '<Download %r' % self.book_id

class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    mail_server = Column(String)
    mail_port = Column(Integer, default = 25)
    mail_use_ssl = Column(SmallInteger, default = 0)
    mail_login = Column(String)
    mail_password = Column(String)
    mail_from = Column(String)

    def __repr__(self):
        #return '<Smtp %r>' % (self.mail_server)
        pass


def migrate_Database():
    if session.query(User).filter(User.role.op('&')(ROLE_ANONYMOUS) == ROLE_ANONYMOUS).first() is None:
        create_anonymous_user()
    try:
        session.query(exists().where(User.random_books)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE user ADD column random_books INTEGER DEFAULT 1")
        conn.execute("ALTER TABLE user ADD column locale String(2) DEFAULT 'en'")
        conn.execute("ALTER TABLE user ADD column default_language String(3) DEFAULT 'all'")
        session.commit()
    try:
        session.query(exists().where(User.language_books)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE user ADD column language_books INTEGER DEFAULT 1")
        conn.execute("ALTER TABLE user ADD column series_books INTEGER DEFAULT 1")
        conn.execute("ALTER TABLE user ADD column category_books INTEGER DEFAULT 1")
        conn.execute("ALTER TABLE user ADD column hot_books INTEGER DEFAULT 1")
        session.commit()
    try:
        session.query(exists().where(BookShelf.order)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE book_shelf_link ADD column `order` INTEGER DEFAULT 1")
        session.commit()


def create_default_config():
    settings = Settings()
    settings.mail_server = "mail.example.com"
    settings.mail_port = 25
    settings.mail_use_ssl = 0
    settings.mail_login = "mail@example.com"
    settings.mail_password = "mypassword"
    settings.mail_from = "automailer <mail@example.com>"

    session.add(settings)
    session.commit()


def get_mail_settings():
    settings = session.query(Settings).first()

    if not settings:
        return {}

    data = {
        'mail_server': settings.mail_server,
        'mail_port': settings.mail_port,
        'mail_use_ssl': settings.mail_use_ssl,
        'mail_login': settings.mail_login,
        'mail_password': settings.mail_password,
        'mail_from': settings.mail_from
    }

    return data

def create_anonymous_user():
    user = User()
    user.nickname = _("Guest")
    user.email='no@email'
    user.role = ROLE_ANONYMOUS
    user.password = generate_password_hash('1')

    session.add(user)
    try:
        session.commit()
    except:
        session.rollback()
        pass


def create_admin_user():
    user = User()
    user.nickname = "admin"
    user.role = ROLE_USER + ROLE_ADMIN + ROLE_DOWNLOAD + ROLE_UPLOAD + ROLE_EDIT + ROLE_PASSWD
    user.password = generate_password_hash(DEFAULT_PASS)

    session.add(user)
    try:
        session.commit()
    except:
        session.rollback()
        pass

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

if not os.path.exists(dbpath):
    try:
        Base.metadata.create_all(engine)
        create_default_config()
        create_admin_user()
        create_anonymous_user()
    except Exception:
        pass
else:
    migrate_Database()
