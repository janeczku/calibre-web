# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019 mutschler, jkrehm, cervinko, janeczku, OzzieIsaacs, csitko
#                            ok11, issmirnov, idalin
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
import sys
import datetime
import itertools
import uuid
from flask import session as flask_session
from binascii import hexlify

from flask_login import AnonymousUserMixin, current_user
from flask_login import user_logged_in

try:
    from flask_dance.consumer.backend.sqla import OAuthConsumerMixin
    oauth_support = True
except ImportError as e:
    # fails on flask-dance >1.3, due to renaming
    try:
        from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
        oauth_support = True
    except ImportError as e:
        oauth_support = False
from sqlalchemy import create_engine, exc, exists, event, text
from sqlalchemy import Column, ForeignKey
from sqlalchemy import String, Integer, SmallInteger, Boolean, DateTime, Float, JSON
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql.expression import func
try:
    # Compatibility with sqlalchemy 2.0
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker, Session, scoped_session
from werkzeug.security import generate_password_hash

from . import constants, logger, cli

log = logger.create()

session = None
app_DB_path = None
Base = declarative_base()
searched_ids = {}

logged_in = dict()


def signal_store_user_session(object, user):
    store_user_session()

def store_user_session():
    if flask_session.get('user_id', ""):
        flask_session['_user_id'] = flask_session.get('user_id', "")
    if flask_session.get('_user_id', ""):
        try:
            if not check_user_session(flask_session.get('_user_id', ""), flask_session.get('_id', "")):
                user_session = User_Sessions(flask_session.get('_user_id', ""), flask_session.get('_id', ""))
                session.add(user_session)
                session.commit()
                log.debug("Login and store session : " + flask_session.get('_id', ""))
            else:
                log.debug("Found stored session: " + flask_session.get('_id', ""))
        except (exc.OperationalError, exc.InvalidRequestError) as e:
            session.rollback()
            log.exception(e)
    else:
        log.error("No user id in session")

def delete_user_session(user_id, session_key):
    try:
        log.debug("Deleted session_key: " + session_key)
        session.query(User_Sessions).filter(User_Sessions.user_id==user_id,
                                            User_Sessions.session_key==session_key).delete()
        session.commit()
    except (exc.OperationalError, exc.InvalidRequestError):
        session.rollback()
        log.exception(e)


def check_user_session(user_id, session_key):
    try:
        return bool(session.query(User_Sessions).filter(User_Sessions.user_id==user_id,
                                                       User_Sessions.session_key==session_key).one_or_none())
    except (exc.OperationalError, exc.InvalidRequestError):
        session.rollback()
        log.exception(e)


user_logged_in.connect(signal_store_user_session)

def store_ids(result):
    ids = list()
    for element in result:
        ids.append(element.id)
    searched_ids[current_user.id] = ids


class UserBase:

    @property
    def is_authenticated(self):
        return self.is_active

    def _has_role(self, role_flag):
        return constants.has_flag(self.role, role_flag)

    def role_admin(self):
        return self._has_role(constants.ROLE_ADMIN)

    def role_download(self):
        return self._has_role(constants.ROLE_DOWNLOAD)

    def role_upload(self):
        return self._has_role(constants.ROLE_UPLOAD)

    def role_edit(self):
        return self._has_role(constants.ROLE_EDIT)

    def role_passwd(self):
        return self._has_role(constants.ROLE_PASSWD)

    def role_anonymous(self):
        return self._has_role(constants.ROLE_ANONYMOUS)

    def role_edit_shelfs(self):
        return self._has_role(constants.ROLE_EDIT_SHELFS)

    def role_delete_books(self):
        return self._has_role(constants.ROLE_DELETE_BOOKS)

    def role_viewer(self):
        return self._has_role(constants.ROLE_VIEWER)

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return self.role_anonymous()

    def get_id(self):
        return str(self.id)

    def filter_language(self):
        return self.default_language

    def check_visibility(self, value):
        if value == constants.SIDEBAR_RECENT:
            return True
        return constants.has_flag(self.sidebar_view, value)

    def show_detail_random(self):
        return self.check_visibility(constants.DETAIL_RANDOM)

    def list_denied_tags(self):
        mct = self.denied_tags or ""
        return [t.strip() for t in mct.split(",")]

    def list_allowed_tags(self):
        mct = self.allowed_tags or ""
        return [t.strip() for t in mct.split(",")]

    def list_denied_column_values(self):
        mct = self.denied_column_value or ""
        return [t.strip() for t in mct.split(",")]

    def list_allowed_column_values(self):
        mct = self.allowed_column_value or ""
        return [t.strip() for t in mct.split(",")]

    def get_view_property(self, page, prop):
        if not self.view_settings.get(page):
            return None
        return self.view_settings[page].get(prop)

    def set_view_property(self, page, prop, value):
        if not self.view_settings.get(page):
            self.view_settings[page] = dict()
        self.view_settings[page][prop] = value
        try:
            flag_modified(self, "view_settings")
        except AttributeError:
            pass
        try:
            session.commit()
        except (exc.OperationalError, exc.InvalidRequestError):
            session.rollback()
            # ToDo: Error message

    def __repr__(self):
        return '<User %r>' % self.name


# Baseclass for Users in Calibre-Web, settings which are depending on certain users are stored here. It is derived from
# User Base (all access methods are declared there)
class User(UserBase, Base):
    __tablename__ = 'user'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    email = Column(String(120), unique=True, default="")
    role = Column(SmallInteger, default=constants.ROLE_USER)
    password = Column(String)
    kindle_mail = Column(String(120), default="")
    shelf = relationship('Shelf', backref='user', lazy='dynamic', order_by='Shelf.name')
    downloads = relationship('Downloads', backref='user', lazy='dynamic')
    locale = Column(String(2), default="en")
    sidebar_view = Column(Integer, default=1)
    default_language = Column(String(3), default="all")
    denied_tags = Column(String, default="")
    allowed_tags = Column(String, default="")
    denied_column_value = Column(String, default="")
    allowed_column_value = Column(String, default="")
    remote_auth_token = relationship('RemoteAuthToken', backref='user', lazy='dynamic')
    view_settings = Column(JSON, default={})
    kobo_only_shelves_sync = Column(Integer, default=0)


if oauth_support:
    class OAuth(OAuthConsumerMixin, Base):
        provider_user_id = Column(String(256))
        user_id = Column(Integer, ForeignKey(User.id))
        user = relationship(User)


class OAuthProvider(Base):
    __tablename__ = 'oauthProvider'

    id = Column(Integer, primary_key=True)
    provider_name = Column(String)
    oauth_client_id = Column(String)
    oauth_client_secret = Column(String)
    active = Column(Boolean)


# Class for anonymous user is derived from User base and completly overrides methods and properties for the
# anonymous user
class Anonymous(AnonymousUserMixin, UserBase):
    def __init__(self):
        self.loadSettings()

    def loadSettings(self):
        data = session.query(User).filter(User.role.op('&')(constants.ROLE_ANONYMOUS) == constants.ROLE_ANONYMOUS)\
            .first()  # type: User
        self.name = data.name
        self.role = data.role
        self.id=data.id
        self.sidebar_view = data.sidebar_view
        self.default_language = data.default_language
        self.locale = data.locale
        self.kindle_mail = data.kindle_mail
        self.denied_tags = data.denied_tags
        self.allowed_tags = data.allowed_tags
        self.denied_column_value = data.denied_column_value
        self.allowed_column_value = data.allowed_column_value
        self.view_settings = data.view_settings
        self.kobo_only_shelves_sync = data.kobo_only_shelves_sync


    def role_admin(self):
        return False

    @property
    def is_active(self):
        return False

    @property
    def is_anonymous(self):
        return True

    @property
    def is_authenticated(self):
        return False

    def get_view_property(self, page, prop):
        if 'view' in flask_session:
            if not flask_session['view'].get(page):
                return None
            return flask_session['view'][page].get(prop)
        return None

    def set_view_property(self, page, prop, value):
        if not 'view' in flask_session:
            flask_session['view'] = dict()
        if not flask_session['view'].get(page):
            flask_session['view'][page] = dict()
        flask_session['view'][page][prop] = value

class User_Sessions(Base):
    __tablename__ = 'user_session'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    session_key = Column(String, default="")

    def __init__(self, user_id, session_key):
        self.user_id = user_id
        self.session_key = session_key


# Baseclass representing Shelfs in calibre-web in app.db
class Shelf(Base):
    __tablename__ = 'shelf'

    id = Column(Integer, primary_key=True)
    uuid = Column(String, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    is_public = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey('user.id'))
    kobo_sync = Column(Boolean, default=False)
    books = relationship("BookShelf", backref="ub_shelf", cascade="all, delete-orphan", lazy="dynamic")
    created = Column(DateTime, default=datetime.datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return '<Shelf %d:%r>' % (self.id, self.name)


# Baseclass representing Relationship between books and Shelfs in Calibre-Web in app.db (N:M)
class BookShelf(Base):
    __tablename__ = 'book_shelf_link'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer)
    order = Column(Integer)
    shelf = Column(Integer, ForeignKey('shelf.id'))
    date_added = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return '<Book %r>' % self.id


# This table keeps track of deleted Shelves so that deletes can be propagated to any paired Kobo device.
class ShelfArchive(Base):
    __tablename__ = 'shelf_archive'

    id = Column(Integer, primary_key=True)
    uuid = Column(String)
    user_id = Column(Integer, ForeignKey('user.id'))
    last_modified = Column(DateTime, default=datetime.datetime.utcnow)


class ReadBook(Base):
    __tablename__ = 'book_read_link'

    STATUS_UNREAD = 0
    STATUS_FINISHED = 1
    STATUS_IN_PROGRESS = 2

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, unique=False)
    user_id = Column(Integer, ForeignKey('user.id'), unique=False)
    read_status = Column(Integer, unique=False, default=STATUS_UNREAD, nullable=False)
    kobo_reading_state = relationship("KoboReadingState", uselist=False,
                                      primaryjoin="and_(ReadBook.user_id == foreign(KoboReadingState.user_id), "
                                                  "ReadBook.book_id == foreign(KoboReadingState.book_id))",
                                      cascade="all",
                                      backref=backref("book_read_link",
                                                      uselist=False))
    last_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_time_started_reading = Column(DateTime, nullable=True)
    times_started_reading = Column(Integer, default=0, nullable=False)


class Bookmark(Base):
    __tablename__ = 'bookmark'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    book_id = Column(Integer)
    format = Column(String(collation='NOCASE'))
    bookmark_key = Column(String)


# Baseclass representing books that are archived on the user's Kobo device.
class ArchivedBook(Base):
    __tablename__ = 'archived_book'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    book_id = Column(Integer)
    is_archived = Column(Boolean, unique=False)
    last_modified = Column(DateTime, default=datetime.datetime.utcnow)


class KoboSyncedBooks(Base):
    __tablename__ = 'kobo_synced_books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    book_id = Column(Integer)

# The Kobo ReadingState API keeps track of 4 timestamped entities:
#   ReadingState, StatusInfo, Statistics, CurrentBookmark
# Which we map to the following 4 tables:
#   KoboReadingState, ReadBook, KoboStatistics and KoboBookmark
class KoboReadingState(Base):
    __tablename__ = 'kobo_reading_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    book_id = Column(Integer)
    last_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    priority_timestamp = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    current_bookmark = relationship("KoboBookmark", uselist=False, backref="kobo_reading_state", cascade="all, delete")
    statistics = relationship("KoboStatistics", uselist=False, backref="kobo_reading_state", cascade="all, delete")


class KoboBookmark(Base):
    __tablename__ = 'kobo_bookmark'

    id = Column(Integer, primary_key=True)
    kobo_reading_state_id = Column(Integer, ForeignKey('kobo_reading_state.id'))
    last_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    location_source = Column(String)
    location_type = Column(String)
    location_value = Column(String)
    progress_percent = Column(Float)
    content_source_progress_percent = Column(Float)


class KoboStatistics(Base):
    __tablename__ = 'kobo_statistics'

    id = Column(Integer, primary_key=True)
    kobo_reading_state_id = Column(Integer, ForeignKey('kobo_reading_state.id'))
    last_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    remaining_time_minutes = Column(Integer)
    spent_reading_minutes = Column(Integer)


# Updates the last_modified timestamp in the KoboReadingState table if any of its children tables are modified.
@event.listens_for(Session, 'before_flush')
def receive_before_flush(session, flush_context, instances):
    for change in itertools.chain(session.new, session.dirty):
        if isinstance(change, (ReadBook, KoboStatistics, KoboBookmark)):
            if change.kobo_reading_state:
                change.kobo_reading_state.last_modified = datetime.datetime.utcnow()
    # Maintain the last_modified bit for the Shelf table.
    for change in itertools.chain(session.new, session.deleted):
        if isinstance(change, BookShelf):
            change.ub_shelf.last_modified = datetime.datetime.utcnow()


# Baseclass representing Downloads from calibre-web in app.db
class Downloads(Base):
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer)
    user_id = Column(Integer, ForeignKey('user.id'))

    def __repr__(self):
        return '<Download %r' % self.book_id


# Baseclass representing allowed domains for registration
class Registration(Base):
    __tablename__ = 'registration'

    id = Column(Integer, primary_key=True)
    domain = Column(String)
    allow = Column(Integer)

    def __repr__(self):
        return u"<Registration('{0}')>".format(self.domain)


class RemoteAuthToken(Base):
    __tablename__ = 'remote_auth_token'

    id = Column(Integer, primary_key=True)
    auth_token = Column(String, unique=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    verified = Column(Boolean, default=False)
    expiration = Column(DateTime)
    token_type = Column(Integer, default=0)

    def __init__(self):
        self.auth_token = (hexlify(os.urandom(4))).decode('utf-8')
        self.expiration = datetime.datetime.now() + datetime.timedelta(minutes=10)  # 10 min from now

    def __repr__(self):
        return '<Token %r>' % self.id


# Add missing tables during migration of database
def add_missing_tables(engine, session):
    if not engine.dialect.has_table(engine.connect(), "book_read_link"):
        ReadBook.__table__.create(bind=engine)
    if not engine.dialect.has_table(engine.connect(), "bookmark"):
        Bookmark.__table__.create(bind=engine)
    if not engine.dialect.has_table(engine.connect(), "kobo_reading_state"):
        KoboReadingState.__table__.create(bind=engine)
    if not engine.dialect.has_table(engine.connect(), "kobo_bookmark"):
        KoboBookmark.__table__.create(bind=engine)
    if not engine.dialect.has_table(engine.connect(), "kobo_statistics"):
        KoboStatistics.__table__.create(bind=engine)
    if not engine.dialect.has_table(engine.connect(), "archived_book"):
        ArchivedBook.__table__.create(bind=engine)
    if not engine.dialect.has_table(engine.connect(), "registration"):
        Registration.__table__.create(bind=engine)
        with engine.connect() as conn:
            conn.execute("insert into registration (domain, allow) values('%.%',1)")
        session.commit()


# migrate all settings missing in registration table
def migrate_registration_table(engine, session):
    try:
        session.query(exists().where(Registration.allow)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some columns are missing
        with engine.connect() as conn:
            conn.execute("ALTER TABLE registration ADD column 'allow' INTEGER")
            conn.execute("update registration set 'allow' = 1")
        session.commit()
    try:
        # Handle table exists, but no content
        cnt = session.query(Registration).count()
        if not cnt:
            with engine.connect() as conn:
                conn.execute("insert into registration (domain, allow) values('%.%',1)")
            session.commit()
    except exc.OperationalError:  # Database is not writeable
        print('Settings database is not writeable. Exiting...')
        sys.exit(2)


# Remove login capability of user Guest
def migrate_guest_password(engine):
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            conn.execute(text("UPDATE user SET password='' where name = 'Guest' and password !=''"))
            trans.commit()
    except exc.OperationalError:
        print('Settings database is not writeable. Exiting...')
        sys.exit(2)


def migrate_shelfs(engine, session):
    try:
        session.query(exists().where(Shelf.uuid)).scalar()
    except exc.OperationalError:
        with engine.connect() as conn:
            conn.execute("ALTER TABLE shelf ADD column 'uuid' STRING")
            conn.execute("ALTER TABLE shelf ADD column 'created' DATETIME")
            conn.execute("ALTER TABLE shelf ADD column 'last_modified' DATETIME")
            conn.execute("ALTER TABLE book_shelf_link ADD column 'date_added' DATETIME")
            conn.execute("ALTER TABLE shelf ADD column 'kobo_sync' BOOLEAN DEFAULT false")
        for shelf in session.query(Shelf).all():
            shelf.uuid = str(uuid.uuid4())
            shelf.created = datetime.datetime.now()
            shelf.last_modified = datetime.datetime.now()
        for book_shelf in session.query(BookShelf).all():
            book_shelf.date_added = datetime.datetime.now()
        session.commit()

    try:
        session.query(exists().where(Shelf.kobo_sync)).scalar()
    except exc.OperationalError:
        with engine.connect() as conn:

            conn.execute("ALTER TABLE shelf ADD column 'kobo_sync' BOOLEAN DEFAULT false")
        session.commit()

    try:
        session.query(exists().where(BookShelf.order)).scalar()
    except exc.OperationalError:  # Database is not compatible, some columns are missing
        with engine.connect() as conn:
            conn.execute("ALTER TABLE book_shelf_link ADD column 'order' INTEGER DEFAULT 1")
        session.commit()


def migrate_readBook(engine, session):
    try:
        session.query(exists().where(ReadBook.read_status)).scalar()
    except exc.OperationalError:
        with engine.connect() as conn:
            conn.execute("ALTER TABLE book_read_link ADD column 'read_status' INTEGER DEFAULT 0")
            conn.execute("UPDATE book_read_link SET 'read_status' = 1 WHERE is_read")
            conn.execute("ALTER TABLE book_read_link ADD column 'last_modified' DATETIME")
            conn.execute("ALTER TABLE book_read_link ADD column 'last_time_started_reading' DATETIME")
            conn.execute("ALTER TABLE book_read_link ADD column 'times_started_reading' INTEGER DEFAULT 0")
        session.commit()
    test = session.query(ReadBook).filter(ReadBook.last_modified == None).all()
    for book in test:
        book.last_modified = datetime.datetime.utcnow()
    session.commit()


def migrate_remoteAuthToken(engine, session):
    try:
        session.query(exists().where(RemoteAuthToken.token_type)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some columns are missing
        with engine.connect() as conn:
            conn.execute("ALTER TABLE remote_auth_token ADD column 'token_type' INTEGER DEFAULT 0")
            conn.execute("update remote_auth_token set 'token_type' = 0")
        session.commit()

# Migrate database to current version, has to be updated after every database change. Currently migration from
# everywhere to current should work. Migration is done by checking if relevant columns are existing, and than adding
# rows with SQL commands
def migrate_Database(session):
    engine = session.bind
    add_missing_tables(engine, session)
    migrate_registration_table(engine, session)
    migrate_readBook(engine, session)
    migrate_remoteAuthToken(engine, session)
    migrate_shelfs(engine, session)
    try:
        create = False
        session.query(exists().where(User.sidebar_view)).scalar()
    except exc.OperationalError:  # Database is not compatible, some columns are missing
        with engine.connect() as conn:
            conn.execute("ALTER TABLE user ADD column `sidebar_view` Integer DEFAULT 1")
        session.commit()
        create = True
    try:
        if create:
            with engine.connect() as conn:
                conn.execute("SELECT language_books FROM user")
            session.commit()
    except exc.OperationalError:
        with engine.connect() as conn:
            conn.execute("UPDATE user SET 'sidebar_view' = (random_books* :side_random + language_books * :side_lang "
                     "+ series_books * :side_series + category_books * :side_category + hot_books * "
                     ":side_hot + :side_autor + :detail_random)",
                     {'side_random': constants.SIDEBAR_RANDOM, 'side_lang': constants.SIDEBAR_LANGUAGE,
                      'side_series': constants.SIDEBAR_SERIES, 'side_category': constants.SIDEBAR_CATEGORY,
                      'side_hot': constants.SIDEBAR_HOT, 'side_autor': constants.SIDEBAR_AUTHOR,
                      'detail_random': constants.DETAIL_RANDOM})
        session.commit()
    try:
        session.query(exists().where(User.denied_tags)).scalar()
    except exc.OperationalError:  # Database is not compatible, some columns are missing
        with engine.connect() as conn:
            conn.execute("ALTER TABLE user ADD column `denied_tags` String DEFAULT ''")
            conn.execute("ALTER TABLE user ADD column `allowed_tags` String DEFAULT ''")
            conn.execute("ALTER TABLE user ADD column `denied_column_value` String DEFAULT ''")
            conn.execute("ALTER TABLE user ADD column `allowed_column_value` String DEFAULT ''")
        session.commit()
    try:
        session.query(exists().where(User.view_settings)).scalar()
    except exc.OperationalError:
        with engine.connect() as conn:
            conn.execute("ALTER TABLE user ADD column `view_settings` VARCHAR(10) DEFAULT '{}'")
        session.commit()
    try:
        session.query(exists().where(User.kobo_only_shelves_sync)).scalar()
    except exc.OperationalError:
        with engine.connect() as conn:
            conn.execute("ALTER TABLE user ADD column `kobo_only_shelves_sync` SMALLINT DEFAULT 0")
        session.commit()

    try:
        # check if name is in User table instead of nickname
        session.query(exists().where(User.name)).scalar()
    except exc.OperationalError:
        # Create new table user_id and copy contents of table user into it
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE user_id (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,"
                     "name VARCHAR(64),"
                     "email VARCHAR(120),"
                     "role SMALLINT,"
                     "password VARCHAR,"
                     "kindle_mail VARCHAR(120),"
                     "locale VARCHAR(2),"
                     "sidebar_view INTEGER,"
                     "default_language VARCHAR(3),"                     
                     "denied_tags VARCHAR,"
                     "allowed_tags VARCHAR,"
                     "denied_column_value VARCHAR,"
                     "allowed_column_value VARCHAR,"
                     "view_settings JSON,"
                     "kobo_only_shelves_sync SMALLINT,"                              
                     "UNIQUE (name),"
                     "UNIQUE (email))"))
            conn.execute(text("INSERT INTO user_id(id, name, email, role, password, kindle_mail,locale,"
                     "sidebar_view, default_language, denied_tags, allowed_tags, denied_column_value, "
                     "allowed_column_value, view_settings, kobo_only_shelves_sync)"
                     "SELECT id, nickname, email, role, password, kindle_mail, locale,"
                     "sidebar_view, default_language, denied_tags, allowed_tags, denied_column_value, "
                     "allowed_column_value, view_settings, kobo_only_shelves_sync FROM user"))
            # delete old user table and rename new user_id table to user:
            conn.execute(text("DROP TABLE user"))
            conn.execute(text("ALTER TABLE user_id RENAME TO user"))
        session.commit()
    if session.query(User).filter(User.role.op('&')(constants.ROLE_ANONYMOUS) == constants.ROLE_ANONYMOUS).first() \
       is None:
        create_anonymous_user(session)

    migrate_guest_password(engine)


def clean_database(session):
    # Remove expired remote login tokens
    now = datetime.datetime.now()
    session.query(RemoteAuthToken).filter(now > RemoteAuthToken.expiration).\
        filter(RemoteAuthToken.token_type != 1).delete()
    session.commit()


# Save downloaded books per user in calibre-web's own database
def update_download(book_id, user_id):
    check = session.query(Downloads).filter(Downloads.user_id == user_id).filter(Downloads.book_id == book_id).first()

    if not check:
        new_download = Downloads(user_id=user_id, book_id=book_id)
        session.add(new_download)
        try:
            session.commit()
        except exc.OperationalError:
            session.rollback()


# Delete non exisiting downloaded books in calibre-web's own database
def delete_download(book_id):
    session.query(Downloads).filter(book_id == Downloads.book_id).delete()
    try:
        session.commit()
    except exc.OperationalError:
        session.rollback()

# Generate user Guest (translated text), as anonymous user, no rights
def create_anonymous_user(session):
    user = User()
    user.name = "Guest"
    user.email = 'no@email'
    user.role = constants.ROLE_ANONYMOUS
    user.password = ''

    session.add(user)
    try:
        session.commit()
    except Exception:
        session.rollback()


# Generate User admin with admin123 password, and access to everything
def create_admin_user(session):
    user = User()
    user.name = "admin"
    user.role = constants.ADMIN_USER_ROLES
    user.sidebar_view = constants.ADMIN_USER_SIDEBAR

    user.password = generate_password_hash(constants.DEFAULT_PASSWORD)

    session.add(user)
    try:
        session.commit()
    except Exception:
        session.rollback()


def init_db(app_db_path):
    # Open session for database connection
    global session
    global app_DB_path

    app_DB_path = app_db_path
    engine = create_engine(u'sqlite:///{0}'.format(app_db_path), echo=False)

    Session = scoped_session(sessionmaker())
    Session.configure(bind=engine)
    session = Session()

    if os.path.exists(app_db_path):
        Base.metadata.create_all(engine)
        migrate_Database(session)
        clean_database(session)
    else:
        Base.metadata.create_all(engine)
        create_admin_user(session)
        create_anonymous_user(session)

    if cli.user_credentials:
        username, password = cli.user_credentials.split(':', 1)
        user = session.query(User).filter(func.lower(User.name) == username.lower()).first()
        if user:
            if not password:
                print("Empty password is not allowed")
                sys.exit(4)
            user.password = generate_password_hash(password)
            if session_commit() == "":
                print("Password for user '{}' changed".format(username))
                sys.exit(0)
            else:
                print("Failed changing password")
                sys.exit(3)
        else:
            print("Username '{}' not valid, can't change password".format(username))
            sys.exit(3)


def dispose():
    global session

    old_session = session
    session = None
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

def session_commit(success=None):
    try:
        session.commit()
        if success:
            log.info(success)
    except (exc.OperationalError, exc.InvalidRequestError) as e:
        session.rollback()
        log.debug_or_exception(e)
    return ""
