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


from __future__ import division, print_function, unicode_literals
import os
import json
import sys

from sqlalchemy import exc, Column, String, Integer, SmallInteger, Boolean, BLOB
from sqlalchemy.ext.declarative import declarative_base

from . import constants, cli, logger, ub


log = logger.create()
_Base = declarative_base()

class _Flask_Settings(_Base):
    __tablename__ = 'flask_settings'

    id = Column(Integer, primary_key=True)
    flask_session_key = Column(BLOB, default="")

    def __init__(self, key):
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
    mail_password = Column(String, default='mypassword')
    mail_from = Column(String, default='automailer <mail@example.com>')
    mail_size = Column(Integer, default=25*1024*1024)

    config_calibre_dir = Column(String)
    config_port = Column(Integer, default=constants.DEFAULT_PORT)
    config_certfile = Column(String)
    config_keyfile = Column(String)

    config_calibre_web_title = Column(String, default=u'Calibre-Web')
    config_books_per_page = Column(Integer, default=60)
    config_random_books = Column(Integer, default=4)
    config_authors_max = Column(Integer, default=0)
    config_read_column = Column(Integer, default=0)
    config_title_regex = Column(String, default=u'^(A|The|An|Der|Die|Das|Den|Ein|Eine|Einen|Dem|Des|Einem|Eines)\s+')
    config_mature_content_tags = Column(String, default='')
    config_theme = Column(Integer, default=0)

    config_log_level = Column(SmallInteger, default=logger.DEFAULT_LOG_LEVEL)
    config_logfile = Column(String)
    config_access_log = Column(SmallInteger, default=0)
    config_access_logfile = Column(String)

    config_uploading = Column(SmallInteger, default=0)
    config_anonbrowse = Column(SmallInteger, default=0)
    config_public_reg = Column(SmallInteger, default=0)
    config_remote_login = Column(Boolean, default=False)
    config_kobo_sync = Column(Boolean, default=False)

    config_default_role = Column(SmallInteger, default=0)
    config_default_show = Column(SmallInteger, default=constants.ADMIN_USER_SIDEBAR)
    config_columns_to_ignore = Column(String)

    config_denied_tags = Column(String, default="")
    config_allowed_tags = Column(String, default="")
    config_restricted_column = Column(SmallInteger, default=0)
    config_denied_column_value = Column(String, default="")
    config_allowed_column_value = Column(String, default="")

    config_use_google_drive = Column(Boolean, default=False)
    config_google_drive_folder = Column(String)
    config_google_drive_watch_changes_response = Column(String)

    config_use_goodreads = Column(Boolean, default=False)
    config_goodreads_api_key = Column(String)
    config_goodreads_api_secret = Column(String)
    config_register_email = Column(Boolean, default=False)
    config_login_type = Column(Integer, default=0)

    config_kobo_proxy = Column(Boolean, default=False)


    config_ldap_provider_url = Column(String, default='example.org')
    config_ldap_port = Column(SmallInteger, default=389)
    config_ldap_authentication = Column(SmallInteger, default=constants.LDAP_AUTH_SIMPLE)
    config_ldap_serv_username = Column(String, default='cn=admin,dc=example,dc=org')
    config_ldap_serv_password = Column(String, default="")
    config_ldap_encryption = Column(SmallInteger, default=0)
    config_ldap_cert_path = Column(String, default="")
    config_ldap_dn = Column(String, default='dc=example,dc=org')
    config_ldap_user_object = Column(String, default='uid=%s')
    config_ldap_openldap = Column(Boolean, default=True)
    config_ldap_group_object_filter = Column(String, default='(&(objectclass=posixGroup)(cn=%s))')
    config_ldap_group_members_field = Column(String, default='memberUid')
    config_ldap_group_name = Column(String, default='calibreweb')

    config_kepubifypath = Column(String, default=None)
    config_converterpath = Column(String, default=None)
    config_calibre = Column(String)
    config_rarfile_location = Column(String, default=None)
    config_upload_formats = Column(String, default=','.join(constants.EXTENSIONS_UPLOAD))

    config_updatechannel = Column(Integer, default=constants.UPDATE_STABLE)

    config_reverse_proxy_login_header_name = Column(String)
    config_allow_reverse_proxy_header_login = Column(Boolean, default=False)

    def __repr__(self):
        return self.__class__.__name__


# Class holds all application specific settings in calibre-web
class _ConfigSQL(object):
    # pylint: disable=no-member
    def __init__(self, session):
        self._session = session
        self._settings = None
        self.db_configured = None
        self.config_calibre_dir = None
        self.load()

        change = False
        if self.config_converterpath == None:
            change = True
            self.config_converterpath = autodetect_calibre_binary()

        if self.config_kepubifypath == None:
            change = True
            self.config_kepubifypath = autodetect_kepubify_binary()

        if self.config_rarfile_location == None:
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
        if cli.certfilepath:
            return cli.certfilepath
        if cli.certfilepath == "":
            return None
        return self.config_certfile

    def get_config_keyfile(self):
        if cli.keyfilepath:
            return cli.keyfilepath
        if cli.certfilepath == "":
            return None
        return self.config_keyfile

    def get_config_ipaddress(self):
        return cli.ipadress or ""

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
        mct = self.config_denied_tags.split(",")
        return [t.strip() for t in mct]

    def list_allowed_tags(self):
        mct = self.config_allowed_tags.split(",")
        return [t.strip() for t in mct]

    def list_denied_column_values(self):
        mct = self.config_denied_column_value.split(",")
        return [t.strip() for t in mct]

    def list_allowed_column_values(self):
        mct = self.config_allowed_column_value.split(",")
        return [t.strip() for t in mct]

    def get_log_level(self):
        return logger.get_level_name(self.config_log_level)

    def get_mail_settings(self):
        return {k:v for k, v in self.__dict__.items() if k.startswith('mail_')}

    def get_mail_server_configured(self):
        return not bool(self.mail_server == constants.DEFAULT_MAIL_SERVER)


    def set_from_dictionary(self, dictionary, field, convertor=None, default=None, encode=None):
        '''Possibly updates a field of this object.
        The new value, if present, is grabbed from the given dictionary, and optionally passed through a convertor.

        :returns: `True` if the field has changed value
        '''
        new_value = dictionary.get(field, default)
        if new_value is None:
            # log.debug("_ConfigSQL set_from_dictionary field '%s' not found", field)
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

        # log.debug("_ConfigSQL set_from_dictionary '%s' = %r (was %r)", field, new_value, current_value)
        setattr(self, field, new_value)
        return True

    def load(self):
        '''Load all configuration values from the underlying storage.'''
        s = self._read_from_storage()  # type: _Settings
        for k, v in s.__dict__.items():
            if k[0] != '_':
                if v is None:
                    # if the storage column has no value, apply the (possible) default
                    column = s.__class__.__dict__.get(k)
                    if column.default is not None:
                        v = column.default.arg
                setattr(self, k, v)

        if self.config_google_drive_watch_changes_response:
            self.config_google_drive_watch_changes_response = \
                json.loads(self.config_google_drive_watch_changes_response)

        have_metadata_db = bool(self.config_calibre_dir)
        if have_metadata_db:
            if not self.config_use_google_drive:
                db_file = os.path.join(self.config_calibre_dir, 'metadata.db')
                have_metadata_db = os.path.isfile(db_file)
        self.db_configured = have_metadata_db
        constants.EXTENSIONS_UPLOAD = [x.lstrip().rstrip() for x in self.config_upload_formats.split(',')]
        logfile = logger.setup(self.config_logfile, self.config_log_level)
        if logfile != self.config_logfile:
            log.warning("Log path %s not valid, falling back to default", self.config_logfile)
            self.config_logfile = logfile
            self._session.merge(s)
            self._session.commit()

    def save(self):
        '''Apply all configuration values to the underlying storage.'''
        s = self._read_from_storage()  # type: _Settings

        if self.config_google_drive_watch_changes_response:
            self.config_google_drive_watch_changes_response = json.dumps(
                self.config_google_drive_watch_changes_response)

        for k, v in self.__dict__.items():
            if k[0] == '_':
                continue
            if hasattr(s, k):
                setattr(s, k, v)

        log.debug("_ConfigSQL updating storage")
        self._session.merge(s)
        self._session.commit()
        self.load()

    def invalidate(self, error=None):
        if error:
            log.error(error)
        log.warning("invalidating configuration")
        self.db_configured = False
        self.config_calibre_dir = None
        self.save()


def _migrate_table(session, orm_class):
    changed = False

    for column_name, column in orm_class.__dict__.items():
        if column_name[0] != '_':
            try:
                session.query(column).first()
            except exc.OperationalError as err:
                log.debug("%s: %s", column_name, err.args[0])
                if column.default is not None:
                    if sys.version_info < (3, 0):
                        if isinstance(column.default.arg, unicode):
                            column.default.arg = column.default.arg.encode('utf-8')
                if column.default is None:
                    column_default = ""
                else:
                    if isinstance(column.default.arg, bool):
                        column_default = ("DEFAULT %r" % int(column.default.arg))
                    else:
                        column_default = ("DEFAULT %r" % column.default.arg)
                alter_table = "ALTER TABLE %s ADD COLUMN `%s` %s %s" % (orm_class.__tablename__,
                                                                        column_name,
                                                                        column.type,
                                                                        column_default)
                log.debug(alter_table)
                session.execute(alter_table)
                changed = True

    if changed:
        session.commit()


def autodetect_calibre_binary():
    if sys.platform == "win32":
        calibre_path = ["C:\\program files\calibre\ebook-convert.exe",
                        "C:\\program files(x86)\calibre\ebook-convert.exe",
                        "C:\\program files(x86)\calibre2\ebook-convert.exe",
                        "C:\\program files\calibre2\ebook-convert.exe"]
    else:
        calibre_path = ["/opt/calibre/ebook-convert"]
    for element in calibre_path:
        if os.path.isfile(element) and os.access(element, os.X_OK):
            return element
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

def _migrate_database(session):
    # make sure the table is created, if it does not exist
    _Base.metadata.create_all(session.bind)
    _migrate_table(session, _Settings)
    _migrate_table(session, _Flask_Settings)


def load_configuration(session):
    _migrate_database(session)

    if not session.query(_Settings).count():
        session.add(_Settings())
        session.commit()
    conf = _ConfigSQL(session)
    # Migrate from global restrictions to user based restrictions
    if bool(conf.config_default_show & constants.MATURE_CONTENT) and conf.config_denied_tags == "":
        conf.config_denied_tags = conf.config_mature_content_tags
        conf.save()
        session.query(ub.User).filter(ub.User.mature_content != True). \
            update({"denied_tags": conf.config_mature_content_tags}, synchronize_session=False)
        session.commit()
    return conf

def get_flask_session_key(session):
    flask_settings = session.query(_Flask_Settings).one_or_none()
    if flask_settings == None:
        flask_settings = _Flask_Settings(os.urandom(32))
        session.add(flask_settings)
        session.commit()
    return flask_settings.flask_session_key
