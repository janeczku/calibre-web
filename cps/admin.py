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

from __future__ import division, print_function, unicode_literals
import os
import json
import time
from datetime import datetime, timedelta
try:
    from imp import reload
except ImportError:
    pass

from babel import Locale as LC
from babel.dates import format_datetime
from flask import Blueprint, flash, redirect, url_for, abort, request, make_response, send_from_directory
from flask_login import login_required, current_user, logout_user
from flask_babel import gettext as _
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from . import constants, logger, ldap1
from . import db, ub, web_server, get_locale, config, updater_thread, babel, gdriveutils
from .helper import speaking_language, check_valid_domain, check_unrar, send_test_mail, generate_random_password, \
                    send_registration_mail
from .gdriveutils import is_gdrive_ready, gdrive_support, downloadFile, deleteDatabaseOnChange, listRootFolders
from .web import admin_required, render_title_template,  before_request, unconfigured, login_required_if_no_ano

feature_support = dict()
feature_support['ldap'] = ldap1.ldap_supported()

try:
    from goodreads.client import GoodreadsClient
    feature_support['goodreads'] = True
except ImportError:
    feature_support['goodreads'] = False

# try:
#     import rarfile
#     feature_support['rar'] = True
# except ImportError:
#     feature_support['rar'] = False

try:
    from oauth_bb import oauth_check
    feature_support['oauth'] = True
except ImportError:
    feature_support['oauth'] = False
    oauth_check = {}


feature_support['gdrive'] = gdrive_support
admi = Blueprint('admin', __name__)
log = logger.create()


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
        else:
            showtext['text'] = _(u'Performing shutdown of server, please close window')
        # stop gevent/tornado server
        web_server.stop(task == 0)
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

    allUser = ub.session.query(ub.User).all()
    settings = ub.session.query(ub.Settings).first()
    return render_title_template("admin.html", allUser=allUser, email=settings, config=config, commit=commit,
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
        if "Show_mature_content" in to_save:
            content.config_default_show |= constants.MATURE_CONTENT

        if "config_authors_max" in to_save:
            content.config_authors_max = int(to_save["config_authors_max"])

        # Default user configuration
        content.config_default_role = 0
        if "admin_role" in to_save:
            content.config_default_role |= constants.ROLE_ADMIN
        if "download_role" in to_save:
            content.config_default_role |= constants.ROLE_DOWNLOAD
        if "viewer_role" in to_save:
            content.config_default_role |= constants.ROLE_VIEWER
        if "upload_role" in to_save:
            content.config_default_role |= constants.ROLE_UPLOAD
        if "edit_role" in to_save:
            content.config_default_role |= constants.ROLE_EDIT
        if "delete_role" in to_save:
            content.config_default_role |= constants.ROLE_DELETE_BOOKS
        if "passwd_role" in to_save:
            content.config_default_role |= constants.ROLE_PASSWD
        if "edit_shelf_role" in to_save:
            content.config_default_role |= constants.ROLE_EDIT_SHELFS

        val = 0
        for key, __ in to_save.items():
            if key.startswith('show'):
                val |= int(key[5:])
        content.config_default_show = val

        ub.session.commit()
        flash(_(u"Calibre-Web configuration updated"), category="success")
        config.loadSettings()
        before_request()
        if reboot_required:
            # db.engine.dispose() # ToDo verify correct
            # ub.session.close()
            # ub.engine.dispose()
            # stop Server
            web_server.stop(True)
            log.info('Reboot required, restarting')
    readColumn = db.session.query(db.Custom_Columns)\
            .filter(and_(db.Custom_Columns.datatype == 'bool',db.Custom_Columns.mark_for_delete == 0)).all()
    return render_title_template("config_view_edit.html", conf=config, readColumns=readColumn,
                                 title=_(u"UI Configuration"), page="uiconfig")


@admi.route("/ajax/editdomain", methods=['POST'])
@login_required
@admin_required
def edit_domain():
    # POST /post
    # name:  'username',  //name of field (column in db)
    # pk:    1            //primary key (record id)
    # value: 'superuser!' //new value
    vals = request.form.to_dict()
    answer = ub.session.query(ub.Registration).filter(ub.Registration.id == vals['pk']).first()
    # domain_name = request.args.get('domain')
    answer.domain = vals['value'].replace('*', '%').replace('?', '_').lower()
    ub.session.commit()
    return ""


@admi.route("/ajax/adddomain", methods=['POST'])
@login_required
@admin_required
def add_domain():
    domain_name = request.form.to_dict()['domainname'].replace('*', '%').replace('?', '_').lower()
    check = ub.session.query(ub.Registration).filter(ub.Registration.domain == domain_name).first()
    if not check:
        new_domain = ub.Registration(domain=domain_name)
        ub.session.add(new_domain)
        ub.session.commit()
    return ""


@admi.route("/ajax/deletedomain", methods=['POST'])
@login_required
@admin_required
def delete_domain():
    domain_id = request.form.to_dict()['domainid'].replace('*', '%').replace('?', '_').lower()
    ub.session.query(ub.Registration).filter(ub.Registration.id == domain_id).delete()
    ub.session.commit()
    # If last domain was deleted, add all domains by default
    if not ub.session.query(ub.Registration).count():
        new_domain = ub.Registration(domain="%.%")
        ub.session.add(new_domain)
        ub.session.commit()
    return ""


@admi.route("/ajax/domainlist")
@login_required
@admin_required
def list_domain():
    answer = ub.session.query(ub.Registration).all()
    json_dumps = json.dumps([{"domain": r.domain.replace('%', '*').replace('_', '?'), "id": r.id} for r in answer])
    js = json.dumps(json_dumps.replace('"', "'")).lstrip('"').strip('"')
    response = make_response(js.replace("'", '"'))
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


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
    if not feature_support['gdrive']:
        gdriveError = _('Import of optional Google Drive requirements missing')
    else:
        if not os.path.isfile(gdriveutils.CLIENT_SECRETS):
            gdriveError = _('client_secrets.json is missing or not readable')
        else:
            with open(gdriveutils.CLIENT_SECRETS, 'r') as settings:
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
        if not os.path.isfile(gdriveutils.SETTINGS_YAML):
            content.config_use_google_drive = False
        if "config_use_google_drive" in to_save and not content.config_use_google_drive and not gdriveError:
            if filedata:
                if filedata['web']['redirect_uris'][0].endswith('/'):
                    filedata['web']['redirect_uris'][0] = filedata['web']['redirect_uris'][0][:-1]
                with open(gdriveutils.SETTINGS_YAML, 'w') as f:
                    yaml = "client_config_backend: settings\nclient_config_file: %(client_file)s\n" \
                           "client_config:\n" \
                           "  client_id: %(client_id)s\n  client_secret: %(client_secret)s\n" \
                           "  redirect_uri: %(redirect_uri)s\n\nsave_credentials: True\n" \
                           "save_credentials_backend: file\nsave_credentials_file: %(credential)s\n\n" \
                           "get_refresh_token: True\n\noauth_scope:\n" \
                           "  - https://www.googleapis.com/auth/drive\n"
                    f.write(yaml % {'client_file': gdriveutils.CLIENT_SECRETS,
                                    'client_id': filedata['web']['client_id'],
                                    'client_secret': filedata['web']['client_secret'],
                                    'redirect_uri': filedata['web']['redirect_uris'][0],
                                    'credential': gdriveutils.CREDENTIALS})
            else:
                flash(_(u'client_secrets.json is not configured for web application'), category="error")
                return render_title_template("config_edit.html", config=config, origin=origin,
                                             gdriveError=gdriveError,
                                             gfeature_support=feature_support, title=_(u"Basic Configuration"),
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
                    return render_title_template("config_edit.html", config=config, origin=origin,
                                                 gdriveError=gdriveError,
                                                 feature_support=feature_support, title=_(u"Basic Configuration"),
                                                 page="config")
        if "config_certfile" in to_save:
            if content.config_certfile != to_save["config_certfile"]:
                if os.path.isfile(to_save["config_certfile"]) or to_save["config_certfile"] is u"":
                    content.config_certfile = to_save["config_certfile"]
                    reboot_required = True
                else:
                    ub.session.commit()
                    flash(_(u'Certfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", config=config, origin=origin,
                                                 gdriveError=gdriveError, feature_support=feature_support,
                                                 title=_(u"Basic Configuration"), page="config")
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
        if "config_login_type" in to_save and to_save["config_login_type"] == "1":
            if not to_save["config_ldap_provider_url"] or not to_save["config_ldap_port"] or not to_save["config_ldap_dn"] or not to_save["config_ldap_user_object"]:
                ub.session.commit()
                flash(_(u'Please enter a LDAP provider, port, DN and user object identifier'), category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                             feature_support=feature_support, title=_(u"Basic Configuration"),
                                             page="config")
            elif not to_save["config_ldap_serv_username"] or not to_save["config_ldap_serv_password"]:
                ub.session.commit()
                flash(_(u'Please enter a LDAP service account and password'), category="error")
                return render_title_template("config_edit.html", content=config, origin=origin,
                                             gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                             feature_support=feature_support, title=_(u"Basic Configuration"),
                                             page="config")
            else:
                content.config_use_ldap = 1
                content.config_ldap_provider_url = to_save["config_ldap_provider_url"]
                content.config_ldap_port = to_save["config_ldap_port"]
                content.config_ldap_schema = to_save["config_ldap_schema"]
                content.config_ldap_serv_username = to_save["config_ldap_serv_username"]
                content.config_ldap_serv_password = base64.b64encode(to_save["config_ldap_serv_password"])
                content.config_ldap_dn = to_save["config_ldap_dn"]
                content.config_ldap_user_object = to_save["config_ldap_user_object"]
                reboot_required = True
        content.config_ldap_use_ssl = 0
        content.config_ldap_use_tls = 0
        content.config_ldap_require_cert = 0
        content.config_ldap_openldap = 0
        if "config_ldap_use_ssl" in to_save and to_save["config_ldap_use_ssl"] == "on":
            content.config_ldap_use_ssl = 1
        if "config_ldap_use_tls" in to_save and to_save["config_ldap_use_tls"] == "on":
            content.config_ldap_use_tls = 1
        if "config_ldap_require_cert" in to_save and to_save["config_ldap_require_cert"] == "on":
            content.config_ldap_require_cert = 1
        if "config_ldap_openldap" in to_save and to_save["config_ldap_openldap"] == "on":
            content.config_ldap_openldap = 1
        if "config_ldap_cert_path " in to_save:
            if content.config_ldap_cert_path  != to_save["config_ldap_cert_path "]:
                if os.path.isfile(to_save["config_ldap_cert_path "]) or to_save["config_ldap_cert_path "] is u"":
                    content.config_certfile = to_save["config_ldap_cert_path "]
                else:
                    ub.session.commit()
                    flash(_(u'Certfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", content=config, origin=origin,
                                        gdrive=gdriveutils.gdrive_support, gdriveError=gdriveError,
                                        feature_support=feature_support, title=_(u"Basic Configuration"),
                                        page="config")

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
        if "config_login_type" in to_save and to_save["config_login_type"] == "2":
            if to_save["config_github_oauth_client_id"] == u'' or to_save["config_github_oauth_client_secret"] == u'':
                ub.session.commit()
                flash(_(u'Please enter Github oauth credentials'), category="error")
                return render_title_template("config_edit.html", config=config, origin=origin,
                                             gdriveError=gdriveError, feature_support=feature_support,
                                             title=_(u"Basic Configuration"), page="config")
            else:
                content.config_login_type = constants.LOGIN_OAUTH_GITHUB
                content.config_github_oauth_client_id = to_save["config_github_oauth_client_id"]
                content.config_github_oauth_client_secret = to_save["config_github_oauth_client_secret"]
                reboot_required = True

        # Google OAuth configuration
        if "config_login_type" in to_save and to_save["config_login_type"] == "3":
            if to_save["config_google_oauth_client_id"] == u'' or to_save["config_google_oauth_client_secret"] == u'':
                ub.session.commit()
                flash(_(u'Please enter Google oauth credentials'), category="error")
                return render_title_template("config_edit.html", config=config, origin=origin,
                                             gdriveError=gdriveError, feature_support=feature_support,
                                             title=_(u"Basic Configuration"), page="config")
            else:
                content.config_login_type = constants.LOGIN_OAUTH_GOOGLE
                content.config_google_oauth_client_id = to_save["config_google_oauth_client_id"]
                content.config_google_oauth_client_secret = to_save["config_google_oauth_client_secret"]
                reboot_required = True

        if "config_login_type" in to_save and to_save["config_login_type"] == "0":
            content.config_login_type = constants.LOGIN_STANDARD

        if "config_log_level" in to_save:
            content.config_log_level = int(to_save["config_log_level"])
        if content.config_logfile != to_save["config_logfile"]:
            # check valid path, only path or file
            if not logger.is_valid_logfile(to_save["config_logfile"]):
                    ub.session.commit()
                    flash(_(u'Logfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", config=config, origin=origin,
                                                 gdriveError=gdriveError, feature_support=feature_support,
                                                 title=_(u"Basic Configuration"), page="config")
            content.config_logfile = to_save["config_logfile"]

        content.config_access_log = 0
        if "config_access_log" in to_save and to_save["config_access_log"] == "on":
            content.config_access_log = 1
            reboot_required = True
        if "config_access_log" not in to_save and config.config_access_log:
            reboot_required = True

        if content.config_access_logfile != to_save["config_access_logfile"]:
            # check valid path, only path or file
            if not logger.is_valid_logfile(to_save["config_access_logfile"]):
                    ub.session.commit()
                    flash(_(u'Access Logfile location is not valid, please enter correct path'), category="error")
                    return render_title_template("config_edit.html", config=config, origin=origin,
                                                 gdriveError=gdriveError, feature_support=feature_support,
                                                 title=_(u"Basic Configuration"), page="config")
            content.config_access_logfile = to_save["config_access_logfile"]
            reboot_required = True

        # Rarfile Content configuration
        if "config_rarfile_location" in to_save and to_save['config_rarfile_location'] is not u"":
            check = check_unrar(to_save["config_rarfile_location"].strip())
            if not check[0] :
                content.config_rarfile_location = to_save["config_rarfile_location"].strip()
            else:
                flash(check[1], category="error")
                return render_title_template("config_edit.html", config=config, origin=origin,
                                             feature_support=feature_support, title=_(u"Basic Configuration"))
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
        except Exception as e:
            flash(e, category="error")
            return render_title_template("config_edit.html", config=config, origin=origin,
                                         gdriveError=gdriveError, feature_support=feature_support,
                                         title=_(u"Basic Configuration"), page="config")
        if db_change:
            reload(db)
            if not db.setup_db():
                flash(_(u'DB location is not valid, please enter correct path'), category="error")
                return render_title_template("config_edit.html", config=config, origin=origin,
                                             gdriveError=gdriveError, feature_support=feature_support,
                                             title=_(u"Basic Configuration"), page="config")
        if reboot_required:
            # stop Server
            web_server.stop(True)
            log.info('Reboot required, restarting')
        if origin:
            success = True
    if is_gdrive_ready() and feature_support['gdrive'] is True and config.config_use_google_drive == True:
        gdrivefolders = listRootFolders()
    else:
        gdrivefolders = list()
    return render_title_template("config_edit.html", origin=origin, success=success, config=config,
                                 show_authenticate_google_drive=not is_gdrive_ready(),
                                 gdriveError=gdriveError, gdrivefolders=gdrivefolders, feature_support=feature_support,
                                 title=_(u"Basic Configuration"), page="config")


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
        content.mature_content = "Show_mature_content" in to_save
        if "locale" in to_save:
            content.locale = to_save["locale"]

        val = 0
        for key, __ in to_save.items():
            if key.startswith('show'):
                val += int(key[5:])
        content.sidebar_view = val


        if "show_detail_random" in to_save:
            content.sidebar_view |= constants.DETAIL_RANDOM

        content.role = 0
        if "admin_role" in to_save:
            content.role |= constants.ROLE_ADMIN
        if "download_role" in to_save:
            content.role |= constants.ROLE_DOWNLOAD
        if "upload_role" in to_save:
            content.role |= constants.ROLE_UPLOAD
        if "edit_role" in to_save:
            content.role |= constants.ROLE_EDIT
        if "delete_role" in to_save:
            content.role |= constants.ROLE_DELETE_BOOKS
        if "passwd_role" in to_save:
            content.role |= constants.ROLE_PASSWD
        if "edit_shelf_role" in to_save:
            content.role |= constants.ROLE_EDIT_SHELFS
        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         registered_oauth=oauth_check, title=_(u"Add new user"))
        content.password = generate_password_hash(to_save["password"])
        content.nickname = to_save["nickname"]
        if config.config_public_reg and not check_valid_domain(to_save["email"]):
            flash(_(u"E-mail is not from valid domain"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         registered_oauth=oauth_check, title=_(u"Add new user"))
        else:
            content.email = to_save["email"]
        try:
            ub.session.add(content)
            ub.session.commit()
            flash(_(u"User '%(user)s' created", user=content.nickname), category="success")
            return redirect(url_for('admin.admin'))
        except IntegrityError:
            ub.session.rollback()
            flash(_(u"Found an existing account for this e-mail address or nickname."), category="error")
    else:
        content.role = config.config_default_role
        content.sidebar_view = config.config_default_show
        content.mature_content = bool(config.config_default_show & constants.MATURE_CONTENT)
    return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                 languages=languages, title=_(u"Add new user"), page="newuser",
                                 registered_oauth=oauth_check)


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
                result = send_test_mail(current_user.kindle_mail, current_user.nickname)
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
            if ub.session.query(ub.User).filter(and_(ub.User.role.op('&')
                                                             (constants.ROLE_ADMIN)== constants.ROLE_ADMIN,
                                                         ub.User.id != content.id)).count():
                ub.session.query(ub.User).filter(ub.User.id == content.id).delete()
                ub.session.commit()
                flash(_(u"User '%(nick)s' deleted", nick=content.nickname), category="success")
                return redirect(url_for('admin.admin'))
            else:
                flash(_(u"No admin user remaining, can't delete user", nick=content.nickname), category="error")
                return redirect(url_for('admin.admin'))
        else:
            if "password" in to_save and to_save["password"]:
                content.password = generate_password_hash(to_save["password"])

            if "admin_role" in to_save:
                content.role |= constants.ROLE_ADMIN
            else:
                content.role &= ~constants.ROLE_ADMIN

            if "download_role" in to_save:
                content.role |= constants.ROLE_DOWNLOAD
            else:
                content.role &= ~constants.ROLE_DOWNLOAD

            if "viewer_role" in to_save:
                content.role |= constants.ROLE_VIEWER
            else:
                content.role &= ~constants.ROLE_VIEWER

            if "upload_role" in to_save:
                content.role |= constants.ROLE_UPLOAD
            else:
                content.role &= ~constants.ROLE_UPLOAD

            if "edit_role" in to_save:
                content.role |= constants.ROLE_EDIT
            else:
                content.role &= ~constants.ROLE_EDIT

            if "delete_role" in to_save:
                content.role |= constants.ROLE_DELETE_BOOKS
            else:
                content.role &= ~constants.ROLE_DELETE_BOOKS

            if "passwd_role" in to_save:
                content.role |= constants.ROLE_PASSWD
            else:
                content.role &= ~constants.ROLE_PASSWD

            if "edit_shelf_role" in to_save:
                content.role |= constants.ROLE_EDIT_SHELFS
            else:
                content.role &= ~constants.ROLE_EDIT_SHELFS

            val = [int(k[5:]) for k, __ in to_save.items() if k.startswith('show_')]
            sidebar = ub.get_sidebar_config()
            for element in sidebar:
                if element['visibility'] in val and not content.check_visibility(element['visibility']):
                    content.sidebar_view |= element['visibility']
                elif not element['visibility'] in val and content.check_visibility(element['visibility']):
                    content.sidebar_view &= ~element['visibility']

            if "Show_detail_random" in to_save:
                content.sidebar_view |= constants.DETAIL_RANDOM
            else:
                content.sidebar_view &= ~constants.DETAIL_RANDOM

            content.mature_content = "Show_mature_content" in to_save

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
                                 content=content, downloads=downloads, registered_oauth=oauth_check,
                                 title=_(u"Edit User %(nick)s", nick=content.nickname), page="edituser")


@admi.route("/admin/resetpassword/<int:user_id>")
@login_required
@admin_required
def reset_password(user_id):
    if not config.config_public_reg:
        abort(404)
    if current_user is not None and current_user.is_authenticated:
        existing_user = ub.session.query(ub.User).filter(ub.User.id == user_id).first()
        password = generate_random_password()
        existing_user.password = generate_password_hash(password)
        try:
            ub.session.commit()
            send_registration_mail(existing_user.email, existing_user.nickname, password, True)
            flash(_(u"Password for user %(user)s reset", user=existing_user.nickname), category="success")
        except Exception:
            ub.session.rollback()
            flash(_(u"An unknown error occurred. Please try again later."), category="error")
    return redirect(url_for('admin.admin'))


@admi.route("/admin/logfile")
@login_required
@admin_required
def view_logfile():
    logfiles = {}
    logfiles[0] = logger.get_logfile(config.config_logfile)
    logfiles[1] = logger.get_accesslogfile(config.config_access_logfile)
    return render_title_template("logviewer.html",title=_(u"Logfile viewer"), accesslog_enable=config.config_access_log,
                                 logfiles=logfiles, page="logfile")


@admi.route("/ajax/log/<int:logtype>")
@login_required
@admin_required
def send_logfile(logtype):
    if logtype == 1:
        logfile = logger.get_accesslogfile(config.config_access_logfile)
        return send_from_directory(os.path.dirname(logfile),
                                   os.path.basename(logfile))
    if logtype == 0:
        logfile = logger.get_logfile(config.config_logfile)
        return send_from_directory(os.path.dirname(logfile),
                                   os.path.basename(logfile))
    else:
        return ""


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
            updater_thread.status = 0
            updater_thread.start()
            status['status'] = updater_thread.get_update_status()
    elif request.method == "GET":
        try:
            status['status'] = updater_thread.get_update_status()
            if status['status']  == -1:
                status['status'] = 7
        except Exception:
            status['status'] = 11
    return json.dumps(status)
