#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, cervinko, jkrehm, bodybybuddha, ok11,
#                            andy29485, idalin, Kyosfonica, wuqi, Kennyl, lemmsh,
#                            falgh1, grunjol, csitko, ytils, xybydy, trasba, vrabe,
#                            ruben-herold, marblepebble, JackED42, SiphonSquirrel,
#                            apetresc, nanu-c, mutschler
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
from flask import Blueprint
from flask import abort, request
from flask_login import login_required, current_user
from web import admin_required, render_title_template, flash, redirect, url_for, before_request, logout_user, \
    speaking_language, unconfigured
from cps import db, ub, Server, get_locale, config, app, updater_thread, babel
import json
from datetime import datetime, timedelta
import time
from babel.dates import format_datetime
from flask_babel import gettext as _
from babel import Locale as LC
from sqlalchemy.exc import IntegrityError
from gdriveutils import is_gdrive_ready, gdrive_support, downloadFile, deleteDatabaseOnChange, listRootFolders
from web import login_required_if_no_ano, check_valid_domain
import helper
from werkzeug.security import generate_password_hash

try:
    from goodreads.client import GoodreadsClient
    goodreads_support = True
except ImportError:
    goodreads_support = False

try:
    import rarfile
    rar_support = True
except ImportError:
    rar_support = False


admi = Blueprint('admin', __name__)


@admi.route("/admin")
@login_required
def admin_forbidden():
    abort(403)


@admi.route("/shutdown")
@login_required
@admin_required
def shutdown():
    task = int(request.args.get("parameter").strip())
    if task == 1 or task == 0:  # valid commandos received
        # close all database connections
        db.session.close()
        db.engine.dispose()
        ub.session.close()
        ub.engine.dispose()

        showtext = {}
        if task == 0:
            showtext['text'] = _(u'Server restarted, please reload page')
            Server.setRestartTyp(True)
        else:
            showtext['text'] = _(u'Performing shutdown of server, please close window')
            Server.setRestartTyp(False)
        # stop gevent/tornado server
        Server.stopServer()
        return json.dumps(showtext)
    else:
        if task == 2:
            db.session.close()
            db.engine.dispose()
            db.setup_db()
            return json.dumps({})
        abort(404)


@admi.route("/admin/view")
@login_required
@admin_required
def admin():
    version = updater_thread.get_current_version_info()
    if version is False:
        commit = _(u'Unknown')
    else:
        if 'datetime' in version:
            commit = version['datetime']

            tz = timedelta(seconds=time.timezone if (time.localtime().tm_isdst == 0) else time.altzone)
            form_date = datetime.strptime(commit[:19], "%Y-%m-%dT%H:%M:%S")
            if len(commit) > 19:    # check if string has timezone
                if commit[19] == '+':
                    form_date -= timedelta(hours=int(commit[20:22]), minutes=int(commit[23:]))
                elif commit[19] == '-':
                    form_date += timedelta(hours=int(commit[20:22]), minutes=int(commit[23:]))
            commit = format_datetime(form_date - tz, format='short', locale=get_locale())
        else:
            commit = version['version']

    content = ub.session.query(ub.User).all()
    settings = ub.session.query(ub.Settings).first()
    return render_title_template("admin.html", content=content, email=settings, config=config, commit=commit,
                                 title=_(u"Admin page"), page="admin")


@admi.route("/admin/config", methods=["GET", "POST"])
@login_required
@admin_required
def configuration():
    return configuration_helper(0)


@admi.route("/admin/viewconfig", methods=["GET", "POST"])
@login_required
@admin_required
def view_configuration():
    reboot_required = False
    if request.method == "POST":
        to_save = request.form.to_dict()
        content = ub.session.query(ub.Settings).first()
        if "config_calibre_web_title" in to_save:
            content.config_calibre_web_title = to_save["config_calibre_web_title"]
        if "config_columns_to_ignore" in to_save:
            content.config_columns_to_ignore = to_save["config_columns_to_ignore"]
        if "config_read_column" in to_save:
            content.config_read_column = int(to_save["config_read_column"])
        if "config_theme" in to_save:
            content.config_theme = int(to_save["config_theme"])
        if "config_title_regex" in to_save:
            if content.config_title_regex != to_save["config_title_regex"]:
                content.config_title_regex = to_save["config_title_regex"]
                reboot_required = True
        if "config_random_books" in to_save:
            content.config_random_books = int(to_save["config_random_books"])
        if "config_books_per_page" in to_save:
            content.config_books_per_page = int(to_save["config_books_per_page"])
        # Mature Content configuration
        if "config_mature_content_tags" in to_save:
            content.config_mature_content_tags = to_save["config_mature_content_tags"].strip()

        # Default user configuration
        content.config_default_role = 0
        if "admin_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_ADMIN
        if "download_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_DOWNLOAD
        if "upload_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_UPLOAD
        if "edit_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_EDIT
        if "delete_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_DELETE_BOOKS
        if "passwd_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_PASSWD
        if "edit_shelf_role" in to_save:
            content.config_default_role = content.config_default_role + ub.ROLE_EDIT_SHELFS

        content.config_default_show = 0
        if "show_detail_random" in to_save:
            content.config_default_show = content.config_default_show + ub.DETAIL_RANDOM
        if "show_language" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_LANGUAGE
        if "show_series" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_SERIES
        if "show_category" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_CATEGORY
        if "show_hot" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_HOT
        if "show_random" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_RANDOM
        if "show_author" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_AUTHOR
        if "show_publisher" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_PUBLISHER
        if "show_best_rated" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_BEST_RATED
        if "show_read_and_unread" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_READ_AND_UNREAD
        if "show_recent" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_RECENT
        if "show_sorted" in to_save:
            content.config_default_show = content.config_default_show + ub.SIDEBAR_SORTED
        if "show_mature_content" in to_save:
            content.config_default_show = content.config_default_show + ub.MATURE_CONTENT
        ub.session.commit()
        flash(_(u"Calibre-Web configuration updated"), category="success")
        config.loadSettings()
        before_request()
        if reboot_required:
            # db.engine.dispose() # ToDo verify correct
            # ub.session.close()
            # ub.engine.dispose()
            # stop Server
            Server.setRestartTyp(True)
            Server.stopServer()
            app.logger.info('Reboot required, restarting')
    readColumn = db.session.query(db.Custom_Columns)\
            .filter(db.and_(db.Custom_Columns.datatype == 'bool',db.Custom_Columns.mark_for_delete == 0)).all()
    return render_title_template("config_view_edit.html", content=config, readColumns=readColumn,
                                 title=_(u"UI Configuration"), page="uiconfig")


@admi.route("/config", methods=["GET", "POST"])
@unconfigured
def basic_configuration():
    logout_user()
    return configuration_helper(1)


def configuration_helper(origin):
    reboot_required = False
    gdriveError = None
    db_change = False
    success = False
    filedata = None
    if gdrive_support is False:
        gdriveError = _('Import of optional Google Drive requirements missing')
    else:
        if not os.path.isfile(os.path.join(config.get_main_dir, 'client_secrets.json')):
            gdriveError = _('client_secrets.json is missing or not readable')
        else:
            with open(os.path.join(config.get_main_dir, 'client_secrets.json'), 'r') as settings:
                filedata = json.load(settings)
            if 'web' not in filedata:
                gdriveError = _('client_secrets.json is not configured for web application')
    if request.method == "POST":
        to_save = request.form.to_dict()
        content = ub.session.query(ub.Settings).first()  # type: ub.Settings
        if "config_calibre_dir" in to_save:
            if content.config_calibre_dir != to_save["config_calibre_dir"]:
                content.config_calibre_dir = to_save["config_calibre_dir"]
                db_change = True
        # Google drive setup
        if not os.path.isfile(os.path.join(config.get_main_dir, 'settings.yaml')):
            content.config_use_google_drive = False
        if "config_use_google_drive" in to_save and not content.config_use_google_drive and not gdriveError:
            if filedata:
                if filedata['web']['redirect_uris'][0].endswith('/'):
                    filedata['web']['redirect_uris'][0] = filedata['web']['redirect_uris'][0][:-1]
                with open(os.path.join(config.get_main_dir, 'settings.yaml'), 'w') as f:
                    yaml = "client_config_backend: settings\nclient_config_file: %(client_file)s\n" \
                           "client_config:\n" \
                           "  client_id: %(client_id)s\n  client_secret: %(client_secret)s\n" \
                           "  redirect_uri: %(redirect_uri)s\n\nsave_credentials: True\n" \
                           "save_credentials_backend: file\nsave_credentials_file: %(credential)s\n\n" \
                           "get_refresh_token: True\n\noauth_scope:\n" \
                           "  - https://www.googleapis.com/auth/drive\n"
                    f.write(yaml % {'client_file': os.path.join(config.get_main_dir, 'client_secrets.json'),
                                    'client_id': filedata['web']['client_id'],
                                    'client_secret': filedata['web']['client_secret'],
                                    'redirect_uri': filedata['web']['redirect_uris'][0],
                                    'credential': os.path.join(config.get_main_dir, 'gdrive_credentials')})
            else:
                flash(_(u'client_secrets.json is not configured for web application'), category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdrive_support, gdriveError=gdriveError,
                                             goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                             page="config")
        # always show google drive settings, but in case of error deny support
        if "config_use_google_drive" in to_save and not gdriveError:
            content.config_use_google_drive = "config_use_google_drive" in to_save
        else:
            content.config_use_google_drive = 0
        if "config_google_drive_folder" in to_save:
            if content.config_google_drive_folder != to_save["config_google_drive_folder"]:
                content.config_google_drive_folder = to_save["config_google_drive_folder"]
                deleteDatabaseOnChange()

        if "config_port" in to_save:
            if content.config_port != int(to_save["config_port"]):
                content.config_port = int(to_save["config_port"])
                reboot_required = True
        if "config_keyfile" in to_save:
            if content.config_keyfile != to_save["config_keyfile"]:
                if os.path.isfile(to_save["config_keyfile"]) or to_save["config_keyfile"] is u"":
                    content.config_keyfile = to_save["config_keyfile"]
                    reboot_required = True
                else:
                    ub.session.commit()
                    flash(_(u'Keyfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", content=config, origin=origin,
                                                 gdrive=gdrive_support, gdriveError=gdriveError,
                                                 goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                                 page="config")
        if "config_certfile" in to_save:
            if content.config_certfile != to_save["config_certfile"]:
                if os.path.isfile(to_save["config_certfile"]) or to_save["config_certfile"] is u"":
                    content.config_certfile = to_save["config_certfile"]
                    reboot_required = True
                else:
                    ub.session.commit()
                    flash(_(u'Certfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", content=config, origin=origin,
                                                 gdrive=gdrive_support, gdriveError=gdriveError,
                                                 goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                                 page="config")
        content.config_uploading = 0
        content.config_anonbrowse = 0
        content.config_public_reg = 0
        if "config_uploading" in to_save and to_save["config_uploading"] == "on":
            content.config_uploading = 1
        if "config_anonbrowse" in to_save and to_save["config_anonbrowse"] == "on":
            content.config_anonbrowse = 1
        if "config_public_reg" in to_save and to_save["config_public_reg"] == "on":
            content.config_public_reg = 1

        if "config_converterpath" in to_save:
            content.config_converterpath = to_save["config_converterpath"].strip()
        if "config_calibre" in to_save:
            content.config_calibre = to_save["config_calibre"].strip()
        if "config_ebookconverter" in to_save:
            content.config_ebookconverter = int(to_save["config_ebookconverter"])

        #LDAP configurator,
        if "config_use_ldap" in to_save and to_save["config_use_ldap"] == "on":
            if "config_ldap_provider_url" not in to_save or "config_ldap_dn" not in to_save:
                ub.session.commit()
                flash(_(u'Please enter a LDAP provider and a DN'), category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdrive_support, gdriveError=gdriveError,
                                             goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                             page="config")
            else:
                content.config_use_ldap = 1
                content.config_ldap_provider_url = to_save["config_ldap_provider_url"]
                content.config_ldap_dn = to_save["config_ldap_dn"]
                db_change = True

        # Remote login configuration
        content.config_remote_login = ("config_remote_login" in to_save and to_save["config_remote_login"] == "on")
        if not content.config_remote_login:
            ub.session.query(ub.RemoteAuthToken).delete()

        # Goodreads configuration
        content.config_use_goodreads = ("config_use_goodreads" in to_save and to_save["config_use_goodreads"] == "on")
        if "config_goodreads_api_key" in to_save:
            content.config_goodreads_api_key = to_save["config_goodreads_api_key"]
        if "config_goodreads_api_secret" in to_save:
            content.config_goodreads_api_secret = to_save["config_goodreads_api_secret"]
        if "config_updater" in to_save:
            content.config_updatechannel = int(to_save["config_updater"])

        # GitHub OAuth configuration
        content.config_use_github_oauth = ("config_use_github_oauth" in to_save and
                                           to_save["config_use_github_oauth"] == "on")
        if "config_github_oauth_client_id" in to_save:
            content.config_github_oauth_client_id = to_save["config_github_oauth_client_id"]
        if "config_github_oauth_client_secret" in to_save:
            content.config_github_oauth_client_secret = to_save["config_github_oauth_client_secret"]

        if content.config_github_oauth_client_id != config.config_github_oauth_client_id or \
                content.config_github_oauth_client_secret != config.config_github_oauth_client_secret:
            reboot_required = True

        # Google OAuth configuration
        content.config_use_google_oauth = ("config_use_google_oauth" in to_save and
                                           to_save["config_use_google_oauth"] == "on")
        if "config_google_oauth_client_id" in to_save:
            content.config_google_oauth_client_id = to_save["config_google_oauth_client_id"]
        if "config_google_oauth_client_secret" in to_save:
            content.config_google_oauth_client_secret = to_save["config_google_oauth_client_secret"]

        if content.config_google_oauth_client_id != config.config_google_oauth_client_id or \
                content.config_google_oauth_client_secret != config.config_google_oauth_client_secret:
            reboot_required = True

        if "config_log_level" in to_save:
            content.config_log_level = int(to_save["config_log_level"])
        if content.config_logfile != to_save["config_logfile"]:
            # check valid path, only path or file
            if os.path.dirname(to_save["config_logfile"]):
                if os.path.exists(os.path.dirname(to_save["config_logfile"])) and \
                        os.path.basename(to_save["config_logfile"]) and not os.path.isdir(to_save["config_logfile"]):
                    content.config_logfile = to_save["config_logfile"]
                else:
                    ub.session.commit()
                    flash(_(u'Logfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", content=config, origin=origin,
                                                 gdrive=gdrive_support, gdriveError=gdriveError,
                                                 goodreads=goodreads_support, title=_(u"Basic Configuration"),
                                                 page="config")
            else:
                content.config_logfile = to_save["config_logfile"]
            reboot_required = True

        # Rarfile Content configuration
        if "config_rarfile_location" in to_save and to_save['config_rarfile_location'] is not u"":
            check = helper.check_unrar(to_save["config_rarfile_location"].strip())
            if not check[0] :
                content.config_rarfile_location = to_save["config_rarfile_location"].strip()
            else:
                flash(check[1], category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdrive_support, goodreads=goodreads_support,
                                             rarfile_support=rar_support, title=_(u"Basic Configuration"))
        try:
            if content.config_use_google_drive and is_gdrive_ready() and not \
                    os.path.exists(os.path.join(content.config_calibre_dir, "metadata.db")):
                downloadFile(None, "metadata.db", config.config_calibre_dir + "/metadata.db")
            if db_change:
                if config.db_configured:
                    db.session.close()
                    db.engine.dispose()
            ub.session.commit()
            flash(_(u"Calibre-Web configuration updated"), category="success")
            config.loadSettings()
            app.logger.setLevel(config.config_log_level)
            logging.getLogger("book_formats").setLevel(config.config_log_level)
        except Exception as e:
            flash(e, category="error")
            return render_title_template("config_edit.html", content=config, origin=origin,
                                         gdrive=gdrive_support, gdriveError=gdriveError,
                                         goodreads=goodreads_support, rarfile_support=rar_support,
                                         title=_(u"Basic Configuration"), page="config")
        if db_change:
            reload(db)
            if not db.setup_db():
                flash(_(u'DB location is not valid, please enter correct path'), category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdrive_support, gdriveError=gdriveError,
                                             goodreads=goodreads_support, rarfile_support=rar_support,
                                             title=_(u"Basic Configuration"), page="config")
        if reboot_required:
            # stop Server
            Server.setRestartTyp(True)
            Server.stopServer()
            app.logger.info('Reboot required, restarting')
        if origin:
            success = True
    if is_gdrive_ready() and gdrive_support is True:  # and config.config_use_google_drive == True:
        gdrivefolders = listRootFolders()
    else:
        gdrivefolders = list()
    return render_title_template("config_edit.html", origin=origin, success=success, content=config,
                                 show_authenticate_google_drive=not is_gdrive_ready(),
                                 gdrive=gdrive_support, gdriveError=gdriveError,
                                 gdrivefolders=gdrivefolders, rarfile_support=rar_support,
                                 goodreads=goodreads_support, title=_(u"Basic Configuration"), page="config")


@admi.route("/admin/user/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_user():
    content = ub.User()
    languages = speaking_language()
    translations = [LC('en')] + babel.list_translations()
    if request.method == "POST":
        to_save = request.form.to_dict()
        content.default_language = to_save["default_language"]
        content.mature_content = "show_mature_content" in to_save
        if "locale" in to_save:
            content.locale = to_save["locale"]
        content.sidebar_view = 0
        if "show_random" in to_save:
            content.sidebar_view += ub.SIDEBAR_RANDOM
        if "show_language" in to_save:
            content.sidebar_view += ub.SIDEBAR_LANGUAGE
        if "show_series" in to_save:
            content.sidebar_view += ub.SIDEBAR_SERIES
        if "show_category" in to_save:
            content.sidebar_view += ub.SIDEBAR_CATEGORY
        if "show_hot" in to_save:
            content.sidebar_view += ub.SIDEBAR_HOT
        if "show_read_and_unread" in to_save:
            content.sidebar_view += ub.SIDEBAR_READ_AND_UNREAD
        if "show_best_rated" in to_save:
            content.sidebar_view += ub.SIDEBAR_BEST_RATED
        if "show_author" in to_save:
            content.sidebar_view += ub.SIDEBAR_AUTHOR
        if "show_publisher" in to_save:
            content.sidebar_view += ub.SIDEBAR_PUBLISHER
        if "show_detail_random" in to_save:
            content.sidebar_view += ub.DETAIL_RANDOM
        if "show_sorted" in to_save:
            content.sidebar_view += ub.SIDEBAR_SORTED
        if "show_recent" in to_save:
            content.sidebar_view += ub.SIDEBAR_RECENT

        content.role = 0
        if "admin_role" in to_save:
            content.role = content.role + ub.ROLE_ADMIN
        if "download_role" in to_save:
            content.role = content.role + ub.ROLE_DOWNLOAD
        if "upload_role" in to_save:
            content.role = content.role + ub.ROLE_UPLOAD
        if "edit_role" in to_save:
            content.role = content.role + ub.ROLE_EDIT
        if "delete_role" in to_save:
            content.role = content.role + ub.ROLE_DELETE_BOOKS
        if "passwd_role" in to_save:
            content.role = content.role + ub.ROLE_PASSWD
        if "edit_shelf_role" in to_save:
            content.role = content.role + ub.ROLE_EDIT_SHELFS
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         title=_(u"Add new user"))
        content.password = generate_password_hash(to_save["password"])
        content.nickname = to_save["nickname"]
        if config.config_public_reg and not check_valid_domain(to_save["email"]):
            flash(_(u"E-mail is not from valid domain"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         title=_(u"Add new user"))
        else:
            content.email = to_save["email"]
        try:
            ub.session.add(content)
            ub.session.commit()
            flash(_(u"User '%(user)s' created", user=content.nickname), category="success")
            return redirect(url_for('admin'))
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"Found an existing account for this e-mail address or nickname."), category="error")
    else:
        content.role = config.config_default_role
        content.sidebar_view = config.config_default_show
        content.mature_content = bool(config.config_default_show & ub.MATURE_CONTENT)
    return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                 languages=languages, title=_(u"Add new user"), page="newuser")


@admi.route("/admin/mailsettings", methods=["GET", "POST"])
@login_required
@admin_required
def edit_mailsettings():
    content = ub.session.query(ub.Settings).first()
    if request.method == "POST":
        to_save = request.form.to_dict()
        content.mail_server = to_save["mail_server"]
        content.mail_port = int(to_save["mail_port"])
        content.mail_login = to_save["mail_login"]
        content.mail_password = to_save["mail_password"]
        content.mail_from = to_save["mail_from"]
        content.mail_use_ssl = int(to_save["mail_use_ssl"])
        try:
            ub.session.commit()
        except Exception as e:
            flash(e, category="error")
        if "test" in to_save and to_save["test"]:
            if current_user.kindle_mail:
                result = helper.send_test_mail(current_user.kindle_mail, current_user.nickname)
                if result is None:
                    flash(_(u"Test e-mail successfully send to %(kindlemail)s", kindlemail=current_user.kindle_mail),
                          category="success")
                else:
                    flash(_(u"There was an error sending the Test e-mail: %(res)s", res=result), category="error")
            else:
                flash(_(u"Please configure your kindle e-mail address first..."), category="error")
        else:
            flash(_(u"E-mail server settings updated"), category="success")
    return render_title_template("email_edit.html", content=content, title=_(u"Edit e-mail server settings"),
                                 page="mailset")


@admi.route("/admin/user/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    content = ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()  # type: ub.User
    downloads = list()
    languages = speaking_language()
    translations = babel.list_translations() + [LC('en')]
    for book in content.downloads:
        downloadbook = db.session.query(db.Books).filter(db.Books.id == book.book_id).first()
        if downloadbook:
            downloads.append(downloadbook)
        else:
            ub.delete_download(book.book_id)
            # ub.session.query(ub.Downloads).filter(book.book_id == ub.Downloads.book_id).delete()
            # ub.session.commit()
    if request.method == "POST":
        to_save = request.form.to_dict()
        if "delete" in to_save:
            ub.session.query(ub.User).filter(ub.User.id == content.id).delete()
            ub.session.commit()
            flash(_(u"User '%(nick)s' deleted", nick=content.nickname), category="success")
            return redirect(url_for('admin'))
        else:
            if "password" in to_save and to_save["password"]:
                content.password = generate_password_hash(to_save["password"])

            if "admin_role" in to_save and not content.role_admin():
                content.role = content.role + ub.ROLE_ADMIN
            elif "admin_role" not in to_save and content.role_admin():
                content.role = content.role - ub.ROLE_ADMIN

            if "download_role" in to_save and not content.role_download():
                content.role = content.role + ub.ROLE_DOWNLOAD
            elif "download_role" not in to_save and content.role_download():
                content.role = content.role - ub.ROLE_DOWNLOAD

            if "upload_role" in to_save and not content.role_upload():
                content.role = content.role + ub.ROLE_UPLOAD
            elif "upload_role" not in to_save and content.role_upload():
                content.role = content.role - ub.ROLE_UPLOAD

            if "edit_role" in to_save and not content.role_edit():
                content.role = content.role + ub.ROLE_EDIT
            elif "edit_role" not in to_save and content.role_edit():
                content.role = content.role - ub.ROLE_EDIT

            if "delete_role" in to_save and not content.role_delete_books():
                content.role = content.role + ub.ROLE_DELETE_BOOKS
            elif "delete_role" not in to_save and content.role_delete_books():
                content.role = content.role - ub.ROLE_DELETE_BOOKS

            if "passwd_role" in to_save and not content.role_passwd():
                content.role = content.role + ub.ROLE_PASSWD
            elif "passwd_role" not in to_save and content.role_passwd():
                content.role = content.role - ub.ROLE_PASSWD

            if "edit_shelf_role" in to_save and not content.role_edit_shelfs():
                content.role = content.role + ub.ROLE_EDIT_SHELFS
            elif "edit_shelf_role" not in to_save and content.role_edit_shelfs():
                content.role = content.role - ub.ROLE_EDIT_SHELFS

            if "show_random" in to_save and not content.show_random_books():
                content.sidebar_view += ub.SIDEBAR_RANDOM
            elif "show_random" not in to_save and content.show_random_books():
                content.sidebar_view -= ub.SIDEBAR_RANDOM

            if "show_language" in to_save and not content.show_language():
                content.sidebar_view += ub.SIDEBAR_LANGUAGE
            elif "show_language" not in to_save and content.show_language():
                content.sidebar_view -= ub.SIDEBAR_LANGUAGE

            if "show_series" in to_save and not content.show_series():
                content.sidebar_view += ub.SIDEBAR_SERIES
            elif "show_series" not in to_save and content.show_series():
                content.sidebar_view -= ub.SIDEBAR_SERIES

            if "show_category" in to_save and not content.show_category():
                content.sidebar_view += ub.SIDEBAR_CATEGORY
            elif "show_category" not in to_save and content.show_category():
                content.sidebar_view -= ub.SIDEBAR_CATEGORY

            if "show_recent" in to_save and not content.show_recent():
                content.sidebar_view += ub.SIDEBAR_RECENT
            elif "show_recent" not in to_save and content.show_recent():
                content.sidebar_view -= ub.SIDEBAR_RECENT

            if "show_sorted" in to_save and not content.show_sorted():
                content.sidebar_view += ub.SIDEBAR_SORTED
            elif "show_sorted" not in to_save and content.show_sorted():
                content.sidebar_view -= ub.SIDEBAR_SORTED

            if "show_publisher" in to_save and not content.show_publisher():
                content.sidebar_view += ub.SIDEBAR_PUBLISHER
            elif "show_publisher" not in to_save and content.show_publisher():
                content.sidebar_view -= ub.SIDEBAR_PUBLISHER

            if "show_hot" in to_save and not content.show_hot_books():
                content.sidebar_view += ub.SIDEBAR_HOT
            elif "show_hot" not in to_save and content.show_hot_books():
                content.sidebar_view -= ub.SIDEBAR_HOT

            if "show_best_rated" in to_save and not content.show_best_rated_books():
                content.sidebar_view += ub.SIDEBAR_BEST_RATED
            elif "show_best_rated" not in to_save and content.show_best_rated_books():
                content.sidebar_view -= ub.SIDEBAR_BEST_RATED

            if "show_read_and_unread" in to_save and not content.show_read_and_unread():
                content.sidebar_view += ub.SIDEBAR_READ_AND_UNREAD
            elif "show_read_and_unread" not in to_save and content.show_read_and_unread():
                content.sidebar_view -= ub.SIDEBAR_READ_AND_UNREAD

            if "show_author" in to_save and not content.show_author():
                content.sidebar_view += ub.SIDEBAR_AUTHOR
            elif "show_author" not in to_save and content.show_author():
                content.sidebar_view -= ub.SIDEBAR_AUTHOR

            if "show_detail_random" in to_save and not content.show_detail_random():
                content.sidebar_view += ub.DETAIL_RANDOM
            elif "show_detail_random" not in to_save and content.show_detail_random():
                content.sidebar_view -= ub.DETAIL_RANDOM

            content.mature_content = "show_mature_content" in to_save

            if "default_language" in to_save:
                content.default_language = to_save["default_language"]
            if "locale" in to_save and to_save["locale"]:
                content.locale = to_save["locale"]
            if to_save["email"] and to_save["email"] != content.email:
                content.email = to_save["email"]
            if "kindle_mail" in to_save and to_save["kindle_mail"] != content.kindle_mail:
                content.kindle_mail = to_save["kindle_mail"]
        try:
            ub.session.commit()
            flash(_(u"User '%(nick)s' updated", nick=content.nickname), category="success")
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"An unknown error occured."), category="error")
    return render_title_template("user_edit.html", translations=translations, languages=languages, new_user=0,
                                 content=content, downloads=downloads, title=_(u"Edit User %(nick)s",
                                                                               nick=content.nickname), page="edituser")


@admi.route("/admin/resetpassword/<int:user_id>")
@login_required
@admin_required
def reset_password(user_id):
    if not config.config_public_reg:
        abort(404)
    if current_user is not None and current_user.is_authenticated:
        existing_user = ub.session.query(ub.User).filter(ub.User.id == user_id).first()
        password = helper.generate_random_password()
        existing_user.password = generate_password_hash(password)
        try:
            ub.session.commit()
            helper.send_registration_mail(existing_user.email, existing_user.nickname, password, True)
            flash(_(u"Password for user %(user)s reset", user=existing_user.nickname), category="success")
        except Exception:
            ub.session.rollback()
            flash(_(u"An unknown error occurred. Please try again later."), category="error")
    return redirect(url_for('admin'))


@admi.route("/get_update_status", methods=['GET'])
@login_required_if_no_ano
def get_update_status():
    return updater_thread.get_available_updates(request.method)


@admi.route("/get_updater_status", methods=['GET', 'POST'])
@login_required
@admin_required
def get_updater_status():
    status = {}
    if request.method == "POST":
        commit = request.form.to_dict()
        if "start" in commit and commit['start'] == 'True':
            text = {
                "1": _(u'Requesting update package'),
                "2": _(u'Downloading update package'),
                "3": _(u'Unzipping update package'),
                "4": _(u'Replacing files'),
                "5": _(u'Database connections are closed'),
                "6": _(u'Stopping server'),
                "7": _(u'Update finished, please press okay and reload page'),
                "8": _(u'Update failed:') + u' ' + _(u'HTTP Error'),
                "9": _(u'Update failed:') + u' ' + _(u'Connection error'),
                "10": _(u'Update failed:') + u' ' + _(u'Timeout while establishing connection'),
                "11": _(u'Update failed:') + u' ' + _(u'General error')
            }
            status['text'] = text
            # helper.updater_thread = helper.Updater()
            updater_thread.start()
            status['status'] = updater_thread.get_update_status()
    elif request.method == "GET":
        try:
            status['status'] = updater_thread.get_update_status()
        except AttributeError:
            # thread is not active, occurs after restart on update
            status['status'] = 7
        except Exception:
            status['status'] = 11
    return json.dumps(status)
