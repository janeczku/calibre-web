#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import *
from sqlalchemy import exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *
from flask_login import AnonymousUserMixin
import sys
import os
import logging
from werkzeug.security import generate_password_hash
from flask_babel import gettext as _
import json
import datetime
from binascii import hexlify
import cli

engine = create_engine('sqlite:///{0}'.format(cli.settingspath), echo=False)
Base = declarative_base()

ROLE_USER = 0
ROLE_ADMIN = 1
ROLE_DOWNLOAD = 2
ROLE_UPLOAD = 4
ROLE_EDIT = 8
ROLE_PASSWD = 16
ROLE_ANONYMOUS = 32
ROLE_EDIT_SHELFS = 64
ROLE_DELETE_BOOKS = 128


DETAIL_RANDOM = 1
SIDEBAR_LANGUAGE = 2
SIDEBAR_SERIES = 4
SIDEBAR_CATEGORY = 8
SIDEBAR_HOT = 16
SIDEBAR_RANDOM = 32
SIDEBAR_AUTHOR = 64
SIDEBAR_BEST_RATED = 128
SIDEBAR_READ_AND_UNREAD = 256
SIDEBAR_RECENT = 512
SIDEBAR_SORTED = 1024


DEFAULT_PASS = "admin123"
DEFAULT_PORT = int(os.environ.get("CALIBRE_PORT", 8083))


DEVELOPMENT = False


class UserBase:
    @property
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
        return bool((self.role is not None)and(self.role & ROLE_UPLOAD == ROLE_UPLOAD))

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

    def role_edit_shelfs(self):
        if self.role is not None:
            return True if self.role & ROLE_EDIT_SHELFS == ROLE_EDIT_SHELFS else False
        else:
            return False

    def role_delete_books(self):
        return bool((self.role is not None)and(self.role & ROLE_DELETE_BOOKS == ROLE_DELETE_BOOKS))

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def filter_language(self):
        return self.default_language

    def show_random_books(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_RANDOM == SIDEBAR_RANDOM))

    def show_language(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_LANGUAGE == SIDEBAR_LANGUAGE))

    def show_hot_books(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_HOT == SIDEBAR_HOT))

    def show_recent(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_RECENT == SIDEBAR_RECENT))

    def show_sorted(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_SORTED == SIDEBAR_SORTED))

    def show_series(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_SERIES == SIDEBAR_SERIES))

    def show_category(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_CATEGORY == SIDEBAR_CATEGORY))

    def show_author(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_AUTHOR == SIDEBAR_AUTHOR))

    def show_best_rated_books(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_BEST_RATED == SIDEBAR_BEST_RATED))

    def show_read_and_unread(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & SIDEBAR_READ_AND_UNREAD == SIDEBAR_READ_AND_UNREAD))

    def show_detail_random(self):
        return bool((self.sidebar_view is not None)and(self.sidebar_view & DETAIL_RANDOM == DETAIL_RANDOM))

    def __repr__(self):
        return '<User %r>' % self.nickname


# Baseclass for Users in Calibre-web, settings which are depending on certain users are stored here. It is derived from
# User Base (all access methods are declared there)
class User(UserBase, Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    nickname = Column(String(64), unique=True)
    email = Column(String(120), unique=True, default="")
    role = Column(SmallInteger, default=ROLE_USER)
    password = Column(String)
    kindle_mail = Column(String(120), default="")
    shelf = relationship('Shelf', backref='user', lazy='dynamic', order_by='Shelf.name')
    downloads = relationship('Downloads', backref='user', lazy='dynamic')
    locale = Column(String(2), default="en")
    sidebar_view = Column(Integer, default=1)
    default_language = Column(String(3), default="all")
    mature_content = Column(Boolean, default=True)


# Class for anonymous user is derived from User base and complets overrides methods and properties for the
# anonymous user
class Anonymous(AnonymousUserMixin, UserBase):
    def __init__(self):
        self.loadSettings()

    def loadSettings(self):
        data = session.query(User).filter(User.role.op('&')(ROLE_ANONYMOUS) == ROLE_ANONYMOUS).first()  # type: User
        settings = session.query(Settings).first()
        self.nickname = data.nickname
        self.role = data.role
        self.id=data.id
        self.sidebar_view = data.sidebar_view
        self.default_language = data.default_language
        self.locale = data.locale
        self.mature_content = data.mature_content
        self.anon_browse = settings.config_anonbrowse

    def role_admin(self):
        return False

    @property
    def is_active(self):
        return False

    @property
    def is_anonymous(self):
        return self.anon_browse

    @property
    def is_authenticated(self):
        return False


# Baseclass representing Shelfs in calibre-web inapp.db
class Shelf(Base):
    __tablename__ = 'shelf'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    is_public = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey('user.id'))

    def __repr__(self):
        return '<Shelf %r>' % self.name


# Baseclass representing Relationship between books and Shelfs in Calibre-web in app.db (N:M)
class BookShelf(Base):
    __tablename__ = 'book_shelf_link'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer)
    order = Column(Integer)
    shelf = Column(Integer, ForeignKey('shelf.id'))

    def __repr__(self):
        return '<Book %r>' % self.id


class ReadBook(Base):
    __tablename__ = 'book_read_link'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, unique=False)
    user_id = Column(Integer, ForeignKey('user.id'), unique=False)
    is_read = Column(Boolean, unique=False)


class Bookmark(Base):
    __tablename__ = 'bookmark'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    book_id = Column(Integer)
    format = Column(String(collation='NOCASE'))
    bookmark_key = Column(String)


# Baseclass representing Downloads from calibre-web in app.db
class Downloads(Base):
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer)
    user_id = Column(Integer, ForeignKey('user.id'))

    def __repr__(self):
        return '<Download %r' % self.book_id


# Baseclass for representing settings in app.db with email server settings and Calibre database settings
# (application settings)
class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    mail_server = Column(String)
    mail_port = Column(Integer, default=25)
    mail_use_ssl = Column(SmallInteger, default=0)
    mail_login = Column(String)
    mail_password = Column(String)
    mail_from = Column(String)
    config_calibre_dir = Column(String)
    config_port = Column(Integer, default=DEFAULT_PORT)
    config_calibre_web_title = Column(String, default=u'Calibre-web')
    config_books_per_page = Column(Integer, default=60)
    config_random_books = Column(Integer, default=4)
    config_title_regex = Column(String, default=u'^(A|The|An|Der|Die|Das|Den|Ein|Eine|Einen|Dem|Des|Einem|Eines)\s+')
    config_log_level = Column(SmallInteger, default=logging.INFO)
    config_uploading = Column(SmallInteger, default=0)
    config_anonbrowse = Column(SmallInteger, default=0)
    config_public_reg = Column(SmallInteger, default=0)
    config_default_role = Column(SmallInteger, default=0)
    config_default_show = Column(SmallInteger, default=2047)
    config_columns_to_ignore = Column(String)
    config_use_google_drive = Column(Boolean)
    config_google_drive_client_id = Column(String)
    config_google_drive_client_secret = Column(String)
    config_google_drive_folder = Column(String)
    config_google_drive_calibre_url_base = Column(String)
    config_google_drive_watch_changes_response = Column(String)
    config_remote_login = Column(Boolean)
    config_use_goodreads = Column(Boolean)
    config_goodreads_api_key = Column(String)
    config_goodreads_api_secret = Column(String)
    config_mature_content_tags = Column(String)  # type: str
    config_logfile = Column(String)

    def __repr__(self):
        pass


class RemoteAuthToken(Base):
    __tablename__ = 'remote_auth_token'

    id = Column(Integer, primary_key=True)
    auth_token = Column(String(8), unique=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    verified = Column(Boolean, default=False)
    expiration = Column(DateTime)

    def __init__(self):
        self.auth_token = hexlify(os.urandom(4))
        self.expiration = datetime.datetime.now() + datetime.timedelta(minutes=10)  # 10 min from now

    def __repr__(self):
        return '<Token %r>' % self.id


# Class holds all application specific settings in calibre-web
class Config:
    def __init__(self):
        self.config_main_dir = os.path.join(os.path.normpath(os.path.dirname(
            os.path.realpath(__file__)) + os.sep + ".." + os.sep))
        self.db_configured = None
        self.config_logfile = None
        self.loadSettings()

    def loadSettings(self):
        data = session.query(Settings).first()  # type: Settings
        self.config_calibre_dir = data.config_calibre_dir
        self.config_port = data.config_port
        self.config_calibre_web_title = data.config_calibre_web_title
        self.config_books_per_page = data.config_books_per_page
        self.config_random_books = data.config_random_books
        self.config_title_regex = data.config_title_regex
        self.config_log_level = data.config_log_level
        self.config_uploading = data.config_uploading
        self.config_anonbrowse = data.config_anonbrowse
        self.config_public_reg = data.config_public_reg
        self.config_default_role = data.config_default_role
        self.config_default_show = data.config_default_show
        self.config_columns_to_ignore = data.config_columns_to_ignore
        self.config_use_google_drive = data.config_use_google_drive
        self.config_google_drive_client_id = data.config_google_drive_client_id
        self.config_google_drive_client_secret = data.config_google_drive_client_secret
        self.config_google_drive_calibre_url_base = data.config_google_drive_calibre_url_base
        self.config_google_drive_folder = data.config_google_drive_folder
        if data.config_google_drive_watch_changes_response:
            self.config_google_drive_watch_changes_response = json.loads(data.config_google_drive_watch_changes_response)
        else:
            self.config_google_drive_watch_changes_response=None
        self.config_columns_to_ignore = data.config_columns_to_ignore
        self.db_configured = bool(self.config_calibre_dir is not None and
                (not self.config_use_google_drive or os.path.exists(self.config_calibre_dir + '/metadata.db')))
        self.config_remote_login = data.config_remote_login
        self.config_use_goodreads = data.config_use_goodreads
        self.config_goodreads_api_key = data.config_goodreads_api_key
        self.config_goodreads_api_secret = data.config_goodreads_api_secret
        self.config_mature_content_tags = data.config_mature_content_tags
        if data.config_logfile:
            self.config_logfile = data.config_logfile

    @property
    def get_main_dir(self):
        return self.config_main_dir

    def get_config_logfile(self):
        if not self.config_logfile:
            return os.path.join(self.get_main_dir, "calibre-web.log")
        else:
            if os.path.dirname(self.config_logfile):
                return self.config_logfile
            else:
                return os.path.join(self.get_main_dir, self.config_logfile)

    def role_admin(self):
        if self.config_default_role is not None:
            return True if self.config_default_role & ROLE_ADMIN == ROLE_ADMIN else False
        else:
            return False

    def role_download(self):
        if self.config_default_role is not None:
            return True if self.config_default_role & ROLE_DOWNLOAD == ROLE_DOWNLOAD else False
        else:
            return False

    def role_upload(self):
        if self.config_default_role is not None:
            return True if self.config_default_role & ROLE_UPLOAD == ROLE_UPLOAD else False
        else:
            return False

    def role_edit(self):
        if self.config_default_role is not None:
            return True if self.config_default_role & ROLE_EDIT == ROLE_EDIT else False
        else:
            return False

    def role_passwd(self):
        if self.config_default_role is not None:
            return True if self.config_default_role & ROLE_PASSWD == ROLE_PASSWD else False
        else:
            return False

    def role_edit_shelfs(self):
        if self.config_default_role is not None:
            return True if self.config_default_role & ROLE_EDIT_SHELFS == ROLE_EDIT_SHELFS else False
        else:
            return False

    def role_delete_books(self):
        return bool((self.config_default_role is not None) and
                    (self.config_default_role & ROLE_DELETE_BOOKS == ROLE_DELETE_BOOKS))

    def show_detail_random(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & DETAIL_RANDOM == DETAIL_RANDOM))

    def show_language(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_LANGUAGE == SIDEBAR_LANGUAGE))

    def show_series(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_SERIES == SIDEBAR_SERIES))

    def show_category(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_CATEGORY == SIDEBAR_CATEGORY))

    def show_hot_books(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_HOT == SIDEBAR_HOT))

    def show_random_books(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_RANDOM == SIDEBAR_RANDOM))

    def show_author(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_AUTHOR == SIDEBAR_AUTHOR))

    def show_best_rated_books(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_BEST_RATED == SIDEBAR_BEST_RATED))

    def show_read_and_unread(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_READ_AND_UNREAD == SIDEBAR_READ_AND_UNREAD))

    def show_recent(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_RECENT == SIDEBAR_RECENT))

    def show_sorted(self):
        return bool((self.config_default_show is not None) and
                    (self.config_default_show & SIDEBAR_SORTED == SIDEBAR_SORTED))

    def mature_content_tags(self):
        if sys.version_info > (3, 0): # Python3 str, Python2 unicode
            lstrip = str.lstrip
        else:
            lstrip = unicode.lstrip
        return list(map(lstrip, self.config_mature_content_tags.split(",")))

    def get_Log_Level(self):
        ret_value = ""
        if self.config_log_level == logging.INFO:
            ret_value = 'INFO'
        elif self.config_log_level == logging.DEBUG:
            ret_value = 'DEBUG'
        elif self.config_log_level == logging.WARNING:
            ret_value = 'WARNING'
        elif self.config_log_level == logging.ERROR:
            ret_value = 'ERROR'
        return ret_value


# Migrate database to current version, has to be updated after every database change. Currently migration from
# everywhere to curent should work. Migration is done by checking if relevant coloums are existing, and than adding
# rows with SQL commands
def migrate_Database():
    if not engine.dialect.has_table(engine.connect(), "book_read_link"):
        ReadBook.__table__.create(bind=engine)
    if not engine.dialect.has_table(engine.connect(), "bookmark"):
        Bookmark.__table__.create(bind=engine)

    try:
        session.query(exists().where(User.locale)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE user ADD column locale String(2) DEFAULT 'en'")
        conn.execute("ALTER TABLE user ADD column default_language String(3) DEFAULT 'all'")
        session.commit()
    try:
        session.query(exists().where(Settings.config_calibre_dir)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_calibre_dir` String")
        conn.execute("ALTER TABLE Settings ADD column `config_port` INTEGER DEFAULT 8083")
        conn.execute("ALTER TABLE Settings ADD column `config_calibre_web_title` String DEFAULT 'Calibre-web'")
        conn.execute("ALTER TABLE Settings ADD column `config_books_per_page` INTEGER DEFAULT 60")
        conn.execute("ALTER TABLE Settings ADD column `config_random_books` INTEGER DEFAULT 4")
        conn.execute("ALTER TABLE Settings ADD column `config_title_regex` String DEFAULT "
            "'^(A|The|An|Der|Die|Das|Den|Ein|Eine|Einen|Dem|Des|Einem|Eines)\s+'")
        conn.execute("ALTER TABLE Settings ADD column `config_log_level` SmallInteger DEFAULT " + str(logging.INFO))
        conn.execute("ALTER TABLE Settings ADD column `config_uploading` SmallInteger DEFAULT 0")
        conn.execute("ALTER TABLE Settings ADD column `config_anonbrowse` SmallInteger DEFAULT 0")
        conn.execute("ALTER TABLE Settings ADD column `config_public_reg` SmallInteger DEFAULT 0")
        session.commit()

    try:
        session.query(exists().where(Settings.config_use_google_drive)).scalar()
    except exc.OperationalError:
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_use_google_drive` INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE Settings ADD column `config_google_drive_client_id` String DEFAULT ''")
        conn.execute("ALTER TABLE Settings ADD column `config_google_drive_client_secret` String DEFAULT ''")
        conn.execute("ALTER TABLE Settings ADD column `config_google_drive_calibre_url_base` INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE Settings ADD column `config_google_drive_folder` String DEFAULT ''")
        conn.execute("ALTER TABLE Settings ADD column `config_google_drive_watch_changes_response` String DEFAULT ''")
    try:
        session.query(exists().where(Settings.config_columns_to_ignore)).scalar()
    except exc.OperationalError:
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_columns_to_ignore` String DEFAULT ''")
        session.commit()
    try:
        session.query(exists().where(Settings.config_default_role)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_default_role` SmallInteger DEFAULT 0")
        session.commit()
    try:
        session.query(exists().where(BookShelf.order)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE book_shelf_link ADD column 'order' INTEGER DEFAULT 1")
        session.commit()
    try:
        create = False
        session.query(exists().where(User.sidebar_view)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE user ADD column `sidebar_view` Integer DEFAULT 1")
        session.commit()
        create = True
    try:
        if create:
            conn = engine.connect()
            conn.execute("SELECT language_books FROM user")
            session.commit()
    except exc.OperationalError:
        conn = engine.connect()
        conn.execute("UPDATE user SET 'sidebar_view' = (random_books* :side_random + language_books * :side_lang "
            "+ series_books * :side_series + category_books * :side_category + hot_books * "
            ":side_hot + :side_autor + :detail_random)"
            ,{'side_random': SIDEBAR_RANDOM, 'side_lang': SIDEBAR_LANGUAGE, 'side_series': SIDEBAR_SERIES,
            'side_category': SIDEBAR_CATEGORY, 'side_hot': SIDEBAR_HOT, 'side_autor': SIDEBAR_AUTHOR,
            'detail_random': DETAIL_RANDOM})
        session.commit()
    try:
        session.query(exists().where(User.mature_content)).scalar()
    except exc.OperationalError:
        conn = engine.connect()
        conn.execute("ALTER TABLE user ADD column `mature_content` INTEGER DEFAULT 1")
    if session.query(User).filter(User.role.op('&')(ROLE_ANONYMOUS) == ROLE_ANONYMOUS).first() is None:
        create_anonymous_user()
    try:
        session.query(exists().where(Settings.config_remote_login)).scalar()
    except exc.OperationalError:
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_remote_login` INTEGER DEFAULT 0")
    try:
        session.query(exists().where(Settings.config_use_goodreads)).scalar()
    except exc.OperationalError:
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_use_goodreads` INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE Settings ADD column `config_goodreads_api_key` String DEFAULT ''")
        conn.execute("ALTER TABLE Settings ADD column `config_goodreads_api_secret` String DEFAULT ''")
    try:
        session.query(exists().where(Settings.config_mature_content_tags)).scalar()
    except exc.OperationalError:
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_mature_content_tags` String DEFAULT ''")
    try:
        session.query(exists().where(Settings.config_default_show)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_default_show` SmallInteger DEFAULT 2047")
        session.commit()
    try:
        session.query(exists().where(Settings.config_logfile)).scalar()
        session.commit()
    except exc.OperationalError:  # Database is not compatible, some rows are missing
        conn = engine.connect()
        conn.execute("ALTER TABLE Settings ADD column `config_logfile` String DEFAULT ''")
        session.commit()


def clean_database():
    # Remove expired remote login tokens
    now = datetime.datetime.now()
    session.query(RemoteAuthToken).filter(now > RemoteAuthToken.expiration).delete()


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


# Generate user Guest (translated text), as anoymous user, no rights
def create_anonymous_user():
    user = User()
    user.nickname = _("Guest")
    user.email = 'no@email'
    user.role = ROLE_ANONYMOUS
    user.password = generate_password_hash('1')

    session.add(user)
    try:
        session.commit()
    except Exception:
        session.rollback()


# Generate User admin with admin123 password, and access to everything
def create_admin_user():
    user = User()
    user.nickname = "admin"
    user.role = ROLE_USER + ROLE_ADMIN + ROLE_DOWNLOAD + ROLE_UPLOAD + ROLE_EDIT + ROLE_DELETE_BOOKS + ROLE_PASSWD
    user.sidebar_view = DETAIL_RANDOM + SIDEBAR_LANGUAGE + SIDEBAR_SERIES + SIDEBAR_CATEGORY + SIDEBAR_HOT + \
            SIDEBAR_RANDOM + SIDEBAR_AUTHOR + SIDEBAR_BEST_RATED + SIDEBAR_READ_AND_UNREAD + SIDEBAR_RECENT + \
            SIDEBAR_SORTED

    user.password = generate_password_hash(DEFAULT_PASS)

    session.add(user)
    try:
        session.commit()
    except Exception:
        session.rollback()


# Open session for database connection
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

# generate database and admin and guest user, if no database is existing
if not os.path.exists(cli.settingspath):
    try:
        Base.metadata.create_all(engine)
        create_default_config()
        create_admin_user()
        create_anonymous_user()
    except Exception:
        raise
else:
    Base.metadata.create_all(engine)
    migrate_Database()
    clean_database()

# Generate global Settings Object accecable from every file
config = Config()
