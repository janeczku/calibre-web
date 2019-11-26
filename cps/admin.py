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
import base64
import json
import time
from datetime import datetime, timedelta

from babel import Locale as LC
from babel.dates import format_datetime
from flask import Blueprint, flash, redirect, url_for, abort, request, make_response, send_from_directory
from flask_login import login_required, current_user, logout_user
from flask_babel import gettext as _
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import func
from werkzeug.security import generate_password_hash

from . import constants, logger, helper, services
from . import db, ub, web_server, get_locale, config, updater_thread, babel, gdriveutils
from .helper import speaking_language, check_valid_domain, send_test_mail, generate_random_password, send_registration_mail
from .gdriveutils import is_gdrive_ready, gdrive_support
from .web import admin_required, render_title_template, before_request, unconfigured, login_required_if_no_ano

feature_support = {
        'ldap': False, # bool(services.ldap),
        'goodreads': bool(services.goodreads_support)
    }

# try:
#     import rarfile
#     feature_support['rar'] = True
# except ImportError:
#     feature_support['rar'] = False

try:
    from .oauth_bb import oauth_check, oauthblueprints
    feature_support['oauth'] = True
except ImportError:
    feature_support['oauth'] = False
    oauthblueprints = []
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
    if task in (0, 1):  # valid commandos received
        # close all database connections
        db.dispose()
        ub.dispose()

        showtext = {}
        if task == 0:
            showtext['text'] = _(u'Server restarted, please reload page')
        else:
            showtext['text'] = _(u'Performing shutdown of server, please close window')
        # stop gevent/tornado server
        web_server.stop(task == 0)
        return json.dumps(showtext)

    if task == 2:
        log.warning("reconnecting to calibre database")
        db.setup_db(config)
        return '{}'

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
    email_settings = config.get_mail_settings()
    return render_title_template("admin.html", allUser=allUser, email=email_settings, config=config, commit=commit,
                                 title=_(u"Admin page"), page="admin")


@admi.route("/admin/config", methods=["GET", "POST"])
@login_required
@admin_required
def configuration():
    if request.method == "POST":
        return _configuration_update_helper()
    return _configuration_result()


@admi.route("/admin/viewconfig")
@login_required
@admin_required
def view_configuration():
    readColumn = db.session.query(db.Custom_Columns)\
            .filter(and_(db.Custom_Columns.datatype == 'bool',db.Custom_Columns.mark_for_delete == 0)).all()
    return render_title_template("config_view_edit.html", conf=config, readColumns=readColumn,
                                 title=_(u"UI Configuration"), page="uiconfig")


@admi.route("/admin/viewconfig", methods=["POST"])
@login_required
@admin_required
def update_view_configuration():
    reboot_required = False
    to_save = request.form.to_dict()

    _config_string = lambda x: config.set_from_dictionary(to_save, x, lambda y: y.strip() if y else y)
    _config_int = lambda x: config.set_from_dictionary(to_save, x, int)

    _config_string("config_calibre_web_title")
    _config_string("config_columns_to_ignore")
    _config_string("config_mature_content_tags")
    reboot_required |= _config_string("config_title_regex")

    _config_int("config_read_column")
    _config_int("config_theme")
    _config_int("config_random_books")
    _config_int("config_books_per_page")
    _config_int("config_authors_max")

    config.config_default_role = constants.selected_roles(to_save)
    config.config_default_role &= ~constants.ROLE_ANONYMOUS

    config.config_default_show = sum(int(k[5:]) for k in to_save if k.startswith('show_'))
    if "Show_mature_content" in to_save:
        config.config_default_show |= constants.MATURE_CONTENT

    config.save()
    flash(_(u"Calibre-Web configuration updated"), category="success")
    before_request()
    if reboot_required:
        db.dispose()
        ub.dispose()
        web_server.stop(True)

    return view_configuration()


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
    if request.method == "POST":
        return _configuration_update_helper()
    return _configuration_result()


def _configuration_update_helper():
    reboot_required = False
    db_change = False
    to_save = request.form.to_dict()

    _config_string = lambda x: config.set_from_dictionary(to_save, x, lambda y: y.strip() if y else y)
    _config_int = lambda x: config.set_from_dictionary(to_save, x, int)
    _config_checkbox = lambda x: config.set_from_dictionary(to_save, x, lambda y: y == "on", False)
    _config_checkbox_int = lambda x: config.set_from_dictionary(to_save, x, lambda y: 1 if (y == "on") else 0, 0)

    db_change |= _config_string("config_calibre_dir")

    # Google drive setup
    if not os.path.isfile(gdriveutils.SETTINGS_YAML):
        config.config_use_google_drive = False

    gdrive_secrets = {}
    gdriveError = gdriveutils.get_error_text(gdrive_secrets)
    if "config_use_google_drive" in to_save and not config.config_use_google_drive and not gdriveError:
        with open(gdriveutils.CLIENT_SECRETS, 'r') as settings:
            gdrive_secrets = json.load(settings)['web']
        if not gdrive_secrets:
            return _configuration_result('client_secrets.json is not configured for web application')
        gdriveutils.update_settings(
                            gdrive_secrets['client_id'],
                            gdrive_secrets['client_secret'],
                            gdrive_secrets['redirect_uris'][0]
                        )

    # always show google drive settings, but in case of error deny support
    config.config_use_google_drive = (not gdriveError) and ("config_use_google_drive" in to_save)
    if _config_string("config_google_drive_folder"):
        gdriveutils.deleteDatabaseOnChange()

    reboot_required |= _config_int("config_port")

    reboot_required |= _config_string("config_keyfile")
    if config.config_keyfile and not os.path.isfile(config.config_keyfile):
        return _configuration_result('Keyfile location is not valid, please enter correct path', gdriveError)

    reboot_required |= _config_string("config_certfile")
    if config.config_certfile and not os.path.isfile(config.config_certfile):
        return _configuration_result('Certfile location is not valid, please enter correct path', gdriveError)

    _config_checkbox_int("config_uploading")
    _config_checkbox_int("config_anonbrowse")
    _config_checkbox_int("config_public_reg")

    _config_int("config_ebookconverter")
    _config_string("config_calibre")
    _config_string("config_converterpath")

    if _config_int("config_login_type"):
        reboot_required |= config.config_login_type != constants.LOGIN_STANDARD

    #LDAP configurator,
    if config.config_login_type == constants.LOGIN_LDAP:
        _config_string("config_ldap_provider_url")
        _config_int("config_ldap_port")
        _config_string("config_ldap_schema")
        _config_string("config_ldap_dn")
        _config_string("config_ldap_user_object")
        if not config.config_ldap_provider_url or not config.config_ldap_port or not config.config_ldap_dn or not config.config_ldap_user_object:
            return _configuration_result('Please enter a LDAP provider, port, DN and user object identifier', gdriveError)

        _config_string("config_ldap_serv_username")
        if not config.config_ldap_serv_username or "config_ldap_serv_password" not in to_save:
            return _configuration_result('Please enter a LDAP service account and password', gdriveError)
        config.set_from_dictionary(to_save, "config_ldap_serv_password", base64.b64encode)

    _config_checkbox("config_ldap_use_ssl")
    _config_checkbox("config_ldap_use_tls")
    _config_checkbox("config_ldap_openldap")
    _config_checkbox("config_ldap_require_cert")
    _config_string("config_ldap_cert_path")
    if config.config_ldap_cert_path and not os.path.isfile(config.config_ldap_cert_path):
        return _configuration_result('LDAP Certfile location is not valid, please enter correct path', gdriveError)

    # Remote login configuration
    _config_checkbox("config_remote_login")
    if not config.config_remote_login:
        ub.session.query(ub.RemoteAuthToken).delete()

    # Goodreads configuration
    _config_checkbox("config_use_goodreads")
    _config_string("config_goodreads_api_key")
    _config_string("config_goodreads_api_secret")
    if services.goodreads_support:
        services.goodreads_support.connect(config.config_goodreads_api_key,
                                           config.config_goodreads_api_secret,
                                           config.config_use_goodreads)

    _config_int("config_updatechannel")

    # GitHub OAuth configuration
    if config.config_login_type == constants.LOGIN_OAUTH:
        active_oauths = 0

        for element in oauthblueprints:
            if to_save["config_"+str(element['id'])+"_oauth_client_id"] \
               and to_save["config_"+str(element['id'])+"_oauth_client_secret"]:
                active_oauths += 1
                element["active"] = 1
                ub.session.query(ub.OAuthProvider).filter(ub.OAuthProvider.id == element['id']).update(
                    {"oauth_client_id":to_save["config_"+str(element['id'])+"_oauth_client_id"],
                    "oauth_client_secret":to_save["config_"+str(element['id'])+"_oauth_client_secret"],
                    "active":1})
                if to_save["config_" + str(element['id']) + "_oauth_client_id"] != element['oauth_client_id'] \
                    or to_save["config_" + str(element['id']) + "_oauth_client_secret"] != element['oauth_client_secret']:
                    reboot_required = True
                    element['oauth_client_id'] = to_save["config_"+str(element['id'])+"_oauth_client_id"]
                    element['oauth_client_secret'] = to_save["config_"+str(element['id'])+"_oauth_client_secret"]
            else:
                ub.session.query(ub.OAuthProvider).filter(ub.OAuthProvider.id == element['id']).update(
                    {"active":0})
                element["active"] = 0

    _config_int("config_log_level")
    _config_string("config_logfile")
    if not logger.is_valid_logfile(config.config_logfile):
        return _configuration_result('Logfile location is not valid, please enter correct path', gdriveError)

    reboot_required |= _config_checkbox_int("config_access_log")
    reboot_required |= _config_string("config_access_logfile")
    if not logger.is_valid_logfile(config.config_access_logfile):
        return _configuration_result('Access Logfile location is not valid, please enter correct path', gdriveError)

    # Rarfile Content configuration
    _config_string("config_rarfile_location")
    unrar_status = helper.check_unrar(config.config_rarfile_location)
    if unrar_status:
        return _configuration_result(unrar_status, gdriveError)

    try:
        metadata_db = os.path.join(config.config_calibre_dir, "metadata.db")
        if config.config_use_google_drive and is_gdrive_ready() and not os.path.exists(metadata_db):
            gdriveutils.downloadFile(None, "metadata.db", metadata_db)
            db_change = True
    except Exception as e:
        return _configuration_result('%s' % e, gdriveError)

    if db_change:
        # reload(db)
        if not db.setup_db(config):
            return _configuration_result('DB location is not valid, please enter correct path', gdriveError)

    config.save()
    flash(_(u"Calibre-Web configuration updated"), category="success")
    if reboot_required:
        web_server.stop(True)

    return _configuration_result(None, gdriveError)


def _configuration_result(error_flash=None, gdriveError=None):
    gdrive_authenticate = not is_gdrive_ready()
    gdrivefolders = []
    if gdriveError is None:
        gdriveError = gdriveutils.get_error_text()
    if gdriveError:
        gdriveError = _(gdriveError)
    else:
        if config.config_use_google_drive and not gdrive_authenticate:
            gdrivefolders = gdriveutils.listRootFolders()

    show_back_button = current_user.is_authenticated
    show_login_button = config.db_configured and not current_user.is_authenticated
    if error_flash:
        config.load()
        flash(_(error_flash), category="error")
        show_login_button = False

    return render_title_template("config_edit.html", config=config, provider=oauthblueprints,
                                 show_back_button=show_back_button, show_login_button=show_login_button,
                                 show_authenticate_google_drive=gdrive_authenticate,
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
        content.locale = to_save.get("locale", content.locale)

        content.sidebar_view = sum(int(key[5:]) for key in to_save if key.startswith('show_'))
        if "show_detail_random" in to_save:
            content.sidebar_view |= constants.DETAIL_RANDOM

        content.role = constants.selected_roles(to_save)

        if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
            flash(_(u"Please fill out all fields!"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         registered_oauth=oauth_check, title=_(u"Add new user"))
        content.password = generate_password_hash(to_save["password"])
        existing_user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == to_save["nickname"].lower())\
            .first()
        existing_email = ub.session.query(ub.User).filter(ub.User.email == to_save["email"].lower())\
            .first()
        if not existing_user and not existing_email:
            content.nickname = to_save["nickname"]
            if config.config_public_reg and not check_valid_domain(to_save["email"]):
                flash(_(u"E-mail is not from valid domain"), category="error")
                return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                             registered_oauth=oauth_check, title=_(u"Add new user"))
            else:
                content.email = to_save["email"]
        else:
            flash(_(u"Found an existing account for this e-mail address or nickname."), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                     languages=languages, title=_(u"Add new user"), page="newuser",
                                     registered_oauth=oauth_check)
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


@admi.route("/admin/mailsettings")
@login_required
@admin_required
def edit_mailsettings():
    content = config.get_mail_settings()
    # log.debug("edit_mailsettings %r", content)
    return render_title_template("email_edit.html", content=content, title=_(u"Edit e-mail server settings"),
                                 page="mailset")


@admi.route("/admin/mailsettings", methods=["POST"])
@login_required
@admin_required
def update_mailsettings():
    to_save = request.form.to_dict()
    log.debug("update_mailsettings %r", to_save)

    _config_string = lambda x: config.set_from_dictionary(to_save, x, lambda y: y.strip() if y else y)
    _config_int = lambda x: config.set_from_dictionary(to_save, x, int)

    _config_string("mail_server")
    _config_int("mail_port")
    _config_int("mail_use_ssl")
    _config_string("mail_login")
    _config_string("mail_password")
    _config_string("mail_from")
    config.save()

    if to_save.get("test"):
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

    return edit_mailsettings()


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
            anonymous = content.is_anonymous
            content.role = constants.selected_roles(to_save)
            if anonymous:
                content.role |= constants.ROLE_ANONYMOUS
            else:
                content.role &= ~constants.ROLE_ANONYMOUS

            val = [int(k[5:]) for k in to_save if k.startswith('show_')]
            sidebar = ub.get_sidebar_config()
            for element in sidebar:
                value = element['visibility']
                if value in val and not content.check_visibility(value):
                    content.sidebar_view |= value
                elif not value in val and content.check_visibility(value):
                    content.sidebar_view &= ~value

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
                existing_email = ub.session.query(ub.User).filter(ub.User.email == to_save["email"].lower()) \
                    .first()
                if not existing_email:
                    content.email = to_save["email"]
                else:
                    flash(_(u"Found an existing account for this e-mail address."), category="error")
                    return render_title_template("user_edit.html", translations=translations, languages=languages,
                                                 new_user=0, content=content, downloads=downloads, registered_oauth=oauth_check,
                                                 title=_(u"Edit User %(nick)s", nick=content.nickname), page="edituser")
            if "nickname" in to_save and to_save["nickname"] != content.nickname:
                # Query User nickname, if not existing, change
                if not ub.session.query(ub.User).filter(ub.User.nickname == to_save["nickname"]).scalar():
                    content.nickname = to_save["nickname"]
                else:
                    flash(_(u"This username is already taken"), category="error")
                    return render_title_template("user_edit.html",
                                                 translations=translations,
                                                 languages=languages,
                                                 new_user=0, content=content,
                                                 downloads=downloads,
                                                 registered_oauth=oauth_check,
                                                 title=_(u"Edit User %(nick)s",
                                                         nick=content.nickname),
                                                 page="edituser")

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
    return updater_thread.get_available_updates(request.method, locale=get_locale())


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
