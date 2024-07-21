# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2019 OzzieIsaacs, pwr
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

import os
import sys
import json

from sqlalchemy import Column, String, Integer, SmallInteger, Boolean, BLOB, JSON
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import text
from sqlalchemy import exists
from cryptography.fernet import Fernet
import cryptography.exceptions
from base64 import urlsafe_b64decode
try:
    # Compatibility with sqlalchemy 2.0
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

from . import constants, logger
from .subproc_wrapper import process_wait


log = logger.create()
_Base = declarative_base()


class _Flask_Settings(_Base):
    __tablename__ = 'flask_settings'

    id = Column(Integer, primary_key=True)
    flask_session_key = Column(BLOB, default=b"")

    def __init__(self, key):
        super().__init__()
        self.flask_session_key = key


# Baseclass for representing settings in app.db with email server settings and Calibre database settings
# (application settings)
class _Settings(_Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    mail_server = Column(String, default=constants.DEFAULT_MAIL_SERVER)
    mail_port = Column(Integer, default=25)
    mail_use_ssl = Column(SmallInteger, default=0)
    mail_login = Column(String, default='mail@example.com')
    mail_password_e = Column(String)
    mail_password = Column(String)
    mail_from = Column(String, default='automailer <mail@example.com>')
    mail_size = Column(Integer, default=25*1024*1024)
    mail_server_type = Column(SmallInteger, default=0)
    mail_gmail_token = Column(JSON, default={})

    config_calibre_dir = Column(String)
    config_calibre_uuid = Column(String)
    config_calibre_split = Column(Boolean, default=False)
    config_calibre_split_dir = Column(String)
    config_port = Column(Integer, default=constants.DEFAULT_PORT)
    config_external_port = Column(Integer, default=constants.DEFAULT_PORT)
    config_certfile = Column(String)
    config_keyfile = Column(String)
    config_trustedhosts = Column(String, default='')
    config_calibre_web_title = Column(String, default='Calibre-Web')
    config_books_per_page = Column(Integer, default=60)
    config_random_books = Column(Integer, default=4)
    config_authors_max = Column(Integer, default=0)
    config_read_column = Column(Integer, default=0)
    config_title_regex = Column(String,
                                default=r'^(A|The|An|Der|Die|Das|Den|Ein|Eine'
                                        r'|Einen|Dem|Des|Einem|Eines|Le|La|Les|L\'|Un|Une)\s+')
    config_theme = Column(Integer, default=0)

    config_log_level = Column(SmallInteger, default=logger.DEFAULT_LOG_LEVEL)
    config_logfile = Column(String, default=logger.DEFAULT_LOG_FILE)
    config_access_log = Column(SmallInteger, default=0)
    config_access_logfile = Column(String, default=logger.DEFAULT_ACCESS_LOG)

    config_uploading = Column(SmallInteger, default=0)
    config_anonbrowse = Column(SmallInteger, default=0)
    config_public_reg = Column(SmallInteger, default=0)
    config_remote_login = Column(Boolean, default=False)
    config_kobo_sync = Column(Boolean, default=False)

    config_default_role = Column(SmallInteger, default=0)
    config_default_show = Column(SmallInteger, default=constants.ADMIN_USER_SIDEBAR)
    config_default_language = Column(String(3), default="all")
    config_default_locale = Column(String(2), default="en")
    config_columns_to_ignore = Column(String)

    config_denied_tags = Column(String, default="")
    config_allowed_tags = Column(String, default="")
    config_restricted_column = Column(SmallInteger, default=0)
    config_denied_column_value = Column(String, default="")
    config_allowed_column_value = Column(String, default="")

    config_use_google_drive = Column(Boolean, default=False)
    config_google_drive_folder = Column(String)
    config_google_drive_watch_changes_response = Column(JSON, default={})

    config_use_goodreads = Column(Boolean, default=False)
    config_goodreads_api_key = Column(String)
    config_register_email = Column(Boolean, default=False)
    config_login_type = Column(Integer, default=0)

    config_kobo_proxy = Column(Boolean, default=False)

    config_ldap_provider_url = Column(String, default='example.org')
    config_ldap_port = Column(SmallInteger, default=389)
    config_ldap_authentication = Column(SmallInteger, default=constants.LDAP_AUTH_SIMPLE)
    config_ldap_serv_username = Column(String, default='cn=admin,dc=example,dc=org')
    config_ldap_serv_password_e = Column(String)
    config_ldap_serv_password = Column(String)
    config_ldap_encryption = Column(SmallInteger, default=0)
    config_ldap_cacert_path = Column(String, default="")
    config_ldap_cert_path = Column(String, default="")
    config_ldap_key_path = Column(String, default="")
    config_ldap_dn = Column(String, default='dc=example,dc=org')
    config_ldap_user_object = Column(String, default='uid=%s')
    config_ldap_member_user_object = Column(String, default='')
    config_ldap_openldap = Column(Boolean, default=True)
    config_ldap_group_object_filter = Column(String, default='(&(objectclass=posixGroup)(cn=%s))')
    config_ldap_group_members_field = Column(String, default='memberUid')
    config_ldap_group_name = Column(String, default='calibreweb')

    config_kepubifypath = Column(String, default=None)
    config_converterpath = Column(String, default=None)
    config_binariesdir = Column(String, default=None)
    config_calibre = Column(String)
    config_rarfile_location = Column(String, default=None)
    config_upload_formats = Column(String, default=','.join(constants.EXTENSIONS_UPLOAD))
    config_unicode_filename = Column(Boolean, default=False)
    config_embed_metadata = Column(Boolean, default=True)

    config_updatechannel = Column(Integer, default=constants.UPDATE_STABLE)

    config_reverse_proxy_login_header_name = Column(String)
    config_allow_reverse_proxy_header_login = Column(Boolean, default=False)

    schedule_start_time = Column(Integer, default=4)
    schedule_duration = Column(Integer, default=10)
    schedule_generate_book_covers = Column(Boolean, default=False)
    schedule_generate_series_covers = Column(Boolean, default=False)
    schedule_reconnect = Column(Boolean, default=False)
    schedule_metadata_backup = Column(Boolean, default=False)

    config_password_policy = Column(Boolean, default=True)
    config_password_min_length = Column(Integer, default=8)
    config_password_number = Column(Boolean, default=True)
    config_password_lower = Column(Boolean, default=True)
    config_password_upper = Column(Boolean, default=True)
    config_password_character = Column(Boolean, default=True)
    config_password_special = Column(Boolean, default=True)
    config_session = Column(Integer, default=1)
    config_ratelimiter = Column(Boolean, default=True)
    config_limiter_uri = Column(String, default="")
    config_limiter_options = Column(String, default="")
    config_check_extensions = Column(Boolean, default=True)

    def __repr__(self):
        return self.__class__.__name__


# Class holds all application specific settings in calibre-web
class ConfigSQL(object):
    # pylint: disable=no-member
    def __init__(self):
        '''self.config_calibre_uuid = None
        self.config_calibre_split_dir = None
        self.dirty = None
        self.config_logfile = None
        self.config_upload_formats = None
        self.mail_gmail_token = None
        self.mail_server_type = None
        self.mail_server = None
        self.config_log_level = None
        self.config_allowed_column_value = None
        self.config_denied_column_value = None
        self.config_allowed_tags = None
        self.config_denied_tags = None
        self.config_default_show = None
        self.config_default_role = None
        self.config_keyfile = None
        self.config_certfile = None
        self.config_rarfile_location = None
        self.config_kepubifypath = None
        self.config_binariesdir = None'''
        self.__dict__["dirty"] = list()

    def init_config(self, session, secret_key, cli):
        self._session = session
        self._settings = None
        self.db_configured = None
        self.config_calibre_dir = None
        self._fernet = Fernet(secret_key)
        self.cli = cli
        self.load()

        change = False

        if self.config_binariesdir is None:
            change = True
            self.config_binariesdir = autodetect_calibre_binaries()
            self.config_converterpath = autodetect_converter_binary(self.config_binariesdir)

        if self.config_kepubifypath is None:
            change = True
            self.config_kepubifypath = autodetect_kepubify_binary()

        if self.config_rarfile_location is None:
            change = True
            self.config_rarfile_location = autodetect_unrar_binary()
        if change:
            self.save()

    def _read_from_storage(self):
        if self._settings is None:
            log.debug("_ConfigSQL._read_from_storage")
            self._settings = self._session.query(_Settings).first()
        return self._settings

    def get_config_certfile(self):
        if self.cli.certfilepath:
            return self.cli.certfilepath
        if self.cli.certfilepath == "":
            return None
        return self.config_certfile

    def get_config_keyfile(self):
        if self.cli.keyfilepath:
            return self.cli.keyfilepath
        if self.cli.certfilepath == "":
            return None
        return self.config_keyfile

    def get_config_ipaddress(self):
        return self.cli.ip_address or ""

    def _has_role(self, role_flag):
        return constants.has_flag(self.config_default_role, role_flag)

    def role_admin(self):
        return self._has_role(constants.ROLE_ADMIN)

    def role_download(self):
        return self._has_role(constants.ROLE_DOWNLOAD)

    def role_viewer(self):
        return self._has_role(constants.ROLE_VIEWER)

    def role_upload(self):
        return self._has_role(constants.ROLE_UPLOAD)

    def role_edit(self):
        return self._has_role(constants.ROLE_EDIT)

    def role_passwd(self):
        return self._has_role(constants.ROLE_PASSWD)

    def role_edit_shelfs(self):
        return self._has_role(constants.ROLE_EDIT_SHELFS)

    def role_delete_books(self):
        return self._has_role(constants.ROLE_DELETE_BOOKS)

    def show_element_new_user(self, value):
        return constants.has_flag(self.config_default_show, value)

    def show_detail_random(self):
        return self.show_element_new_user(constants.DETAIL_RANDOM)

    def list_denied_tags(self):
        mct = self.config_denied_tags or ""
        return [t.strip() for t in mct.split(",")]

    def list_allowed_tags(self):
        mct = self.config_allowed_tags or ""
        return [t.strip() for t in mct.split(",")]

    def list_denied_column_values(self):
        mct = self.config_denied_column_value or ""
        return [t.strip() for t in mct.split(",")]

    def list_allowed_column_values(self):
        mct = self.config_allowed_column_value or ""
        return [t.strip() for t in mct.split(",")]

    def get_log_level(self):
        return logger.get_level_name(self.config_log_level)

    def get_mail_settings(self):
        return {k: v for k, v in self.__dict__.items() if k.startswith('mail_')}

    def get_mail_server_configured(self):
        return bool((self.mail_server != constants.DEFAULT_MAIL_SERVER and self.mail_server_type == 0)
                    or (self.mail_gmail_token != {} and self.mail_server_type == 1))

    def get_scheduled_task_settings(self):
        return {k: v for k, v in self.__dict__.items() if k.startswith('schedule_')}

    def set_from_dictionary(self, dictionary, field, convertor=None, default=None, encode=None):
        """Possibly updates a field of this object.
        The new value, if present, is grabbed from the given dictionary, and optionally passed through a convertor.

        :returns: `True` if the field has changed value
        """
        new_value = dictionary.get(field, default)
        if new_value is None:
            return False

        if field not in self.__dict__:
            log.warning("_ConfigSQL trying to set unknown field '%s' = %r", field, new_value)
            return False

        if convertor is not None:
            if encode:
                new_value = convertor(new_value.encode(encode))
            else:
                new_value = convertor(new_value)

        current_value = self.__dict__.get(field)
        if current_value == new_value:
            return False

        setattr(self, field, new_value)
        return True

    def to_dict(self):
        storage = {}
        for k, v in self.__dict__.items():
            if k[0] != '_' and not k.endswith("_e") and not k == "cli":
                storage[k] = v
        return storage

    def load(self):
        """Load all configuration values from the underlying storage."""
        s = self._read_from_storage()  # type: _Settings
        for k, v in s.__dict__.items():
            if k[0] != '_':
                if v is None:
                    # if the storage column has no value, apply the (possible) default
                    column = s.__class__.__dict__.get(k)
                    if column.default is not None:
                        v = column.default.arg
                if k.endswith("_e") and v is not None:
                    try:
                        setattr(self, k, self._fernet.decrypt(v).decode())
                    except cryptography.fernet.InvalidToken:
                        setattr(self, k, "")
                else:
                    setattr(self, k, v)

        have_metadata_db = bool(self.config_calibre_dir)
        if have_metadata_db:
            db_file = os.path.join(self.config_calibre_dir, 'metadata.db')
            have_metadata_db = os.path.isfile(db_file)
        self.db_configured = have_metadata_db
        # constants.EXTENSIONS_UPLOAD = [x.lstrip().rstrip().lower() for x in self.config_upload_formats.split(',')]
        from . import cli_param
        if os.environ.get('FLASK_DEBUG'):
            logfile = logger.setup(logger.LOG_TO_STDOUT, logger.logging.DEBUG)
        else:
            # pylint: disable=access-member-before-definition
            logfile = logger.setup(cli_param.logpath or self.config_logfile, self.config_log_level)
        if logfile != os.path.abspath(self.config_logfile):
            if logfile != os.path.abspath(cli_param.logpath):
                log.warning("Log path %s not valid, falling back to default", self.config_logfile)
            self.config_logfile = logfile
            s.config_logfile = logfile
            self._session.merge(s)
            try:
                self._session.commit()
            except OperationalError as e:
                log.error('Database error: %s', e)
                self._session.rollback()
        self.__dict__["dirty"] = list()

    def save(self):
        """Apply all configuration values to the underlying storage."""
        s = self._read_from_storage()  # type: _Settings

        for k in self.dirty:
            if k[0] == '_':
                continue
            if hasattr(s, k):
                if k.endswith("_e"):
                    setattr(s, k, self._fernet.encrypt(self.__dict__[k].encode()))
                else:
                    setattr(s, k, self.__dict__[k])

        log.debug("_ConfigSQL updating storage")
        self._session.merge(s)
        try:
            self._session.commit()
        except OperationalError as e:
            log.error('Database error: %s', e)
            self._session.rollback()
        self.load()

    def invalidate(self, error=None):
        if error:
            log.error(error)
        log.warning("invalidating configuration")
        self.db_configured = False
        self.save()

    def get_book_path(self):
        return self.config_calibre_split_dir if self.config_calibre_split_dir else self.config_calibre_dir

    def store_calibre_uuid(self, calibre_db, Library_table):
        try:
            calibre_uuid = calibre_db.session.query(Library_table).one_or_none()
            if self.config_calibre_uuid != calibre_uuid.uuid:
                self.config_calibre_uuid = calibre_uuid.uuid
                self.save()
        except AttributeError:
            pass

    def __setattr__(self, attr_name, attr_value):
        super().__setattr__(attr_name, attr_value)
        self.__dict__["dirty"].append(attr_name)


def _encrypt_fields(session, secret_key):
    try:
        session.query(exists().where(_Settings.mail_password_e)).scalar()
    except OperationalError:
        with session.bind.connect() as conn:
            conn.execute(text("ALTER TABLE settings ADD column 'mail_password_e' String"))
            conn.execute(text("ALTER TABLE settings ADD column 'config_ldap_serv_password_e' String"))
        session.commit()
        crypter = Fernet(secret_key)
        settings = session.query(_Settings.mail_password, _Settings.config_ldap_serv_password).first()
        if settings.mail_password:
            session.query(_Settings).update(
                {_Settings.mail_password_e: crypter.encrypt(settings.mail_password.encode())})
        if settings.config_ldap_serv_password:
            session.query(_Settings).update(
                {_Settings.config_ldap_serv_password_e: crypter.encrypt(settings.config_ldap_serv_password.encode())})
        session.commit()


def _migrate_table(session, orm_class, secret_key=None):
    if secret_key:
        _encrypt_fields(session, secret_key)
    changed = False

    for column_name, column in orm_class.__dict__.items():
        if column_name[0] != '_':
            try:
                session.query(column).first()
            except OperationalError as err:
                log.debug("%s: %s", column_name, err.args[0])
                if column.default is None:
                    column_default = ""
                else:
                    if isinstance(column.default.arg, bool):
                        column_default = "DEFAULT {}".format(int(column.default.arg))
                    else:
                        column_default = "DEFAULT `{}`".format(column.default.arg)
                if isinstance(column.type, JSON):
                    column_type = "JSON"
                else:
                    column_type = column.type
                alter_table = text("ALTER TABLE %s ADD COLUMN `%s` %s %s" % (orm_class.__tablename__,
                                                                             column_name,
                                                                             column_type,
                                                                             column_default))
                log.debug(alter_table)
                session.execute(alter_table)
                changed = True
            except json.decoder.JSONDecodeError as e:
                log.error("Database corrupt column: {}".format(column_name))
                log.debug(e)

    if changed:
        try:
            session.commit()
        except OperationalError:
            session.rollback()


def autodetect_calibre_binaries():
    if sys.platform == "win32":
        calibre_path = ["C:\\program files\\calibre\\",
                        "C:\\program files(x86)\\calibre\\",
                        "C:\\program files(x86)\\calibre2\\",
                        "C:\\program files\\calibre2\\"]
    else:
        calibre_path = ["/opt/calibre/"]
    for element in calibre_path:
        supported_binary_paths = [os.path.join(element, binary)
                                  for binary in constants.SUPPORTED_CALIBRE_BINARIES.values()]
        if all(os.path.isfile(binary_path) and os.access(binary_path, os.X_OK)
               for binary_path in supported_binary_paths):
            values = [process_wait([binary_path, "--version"],
                                   pattern=r'\(calibre (.*)\)') for binary_path in supported_binary_paths]
            if all(values):
                version = values[0].group(1)
                log.debug("calibre version %s", version)
                return element 
    return ""


def autodetect_converter_binary(calibre_path):
    if sys.platform == "win32":
        converter_path = os.path.join(calibre_path, "ebook-convert.exe")
    else:
        converter_path = os.path.join(calibre_path, "ebook-convert")
    if calibre_path and os.path.isfile(converter_path) and os.access(converter_path, os.X_OK):
        return converter_path
    return ""


def autodetect_unrar_binary():
    if sys.platform == "win32":
        calibre_path = ["C:\\program files\\WinRar\\unRAR.exe",
                        "C:\\program files(x86)\\WinRar\\unRAR.exe"]
    else:
        calibre_path = ["/usr/bin/unrar"]
    for element in calibre_path:
        if os.path.isfile(element) and os.access(element, os.X_OK):
            return element
    return ""


def autodetect_kepubify_binary():
    if sys.platform == "win32":
        calibre_path = ["C:\\program files\\kepubify\\kepubify-windows-64Bit.exe",
                        "C:\\program files(x86)\\kepubify\\kepubify-windows-64Bit.exe"]
    else:
        calibre_path = ["/opt/kepubify/kepubify-linux-64bit", "/opt/kepubify/kepubify-linux-32bit"]
    for element in calibre_path:
        if os.path.isfile(element) and os.access(element, os.X_OK):
            return element
    return ""


def _migrate_database(session, secret_key):
    # make sure the table is created, if it does not exist
    _Base.metadata.create_all(session.bind)
    _migrate_table(session, _Settings, secret_key)
    _migrate_table(session, _Flask_Settings)


def load_configuration(session, secret_key):
    _migrate_database(session, secret_key)
    if not session.query(_Settings).count():
        session.add(_Settings())
        session.commit()


def get_flask_session_key(_session):
    flask_settings = _session.query(_Flask_Settings).one_or_none()
    if flask_settings is None:
        flask_settings = _Flask_Settings(os.urandom(32))
        _session.add(flask_settings)
        _session.commit()
    return flask_settings.flask_session_key


def get_encryption_key(key_path):
    key_file = os.path.join(key_path, ".key")
    generate = True
    error = ""
    key = None
    if os.path.exists(key_file) and os.path.getsize(key_file) > 32:
        with open(key_file, "rb") as f:
            key = f.read()
        try:
            urlsafe_b64decode(key)
            generate = False
        except ValueError:
            pass
    if generate:
        key = Fernet.generate_key()
        try:
            with open(key_file, "wb") as f:
                f.write(key)
        except PermissionError as e:
            error = e
    return key, error
