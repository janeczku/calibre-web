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
import re
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

from . import constants, logger, helper, services
from . import db, calibre_db, ub, web_server, get_locale, config, updater_thread, babel, gdriveutils
from .helper import check_valid_domain, send_test_mail, reset_password, generate_password_hash
from .gdriveutils import is_gdrive_ready, gdrive_support
from .web import admin_required, render_title_template, before_request, unconfigured, login_required_if_no_ano

log = logger.create()

feature_support = {
        'ldap': bool(services.ldap),
        'goodreads': bool(services.goodreads_support),
        'kobo':  bool(services.kobo)
    }

try:
    import rarfile
    feature_support['rar'] = True
except ImportError:
    feature_support['rar'] = False

try:
    from .oauth_bb import oauth_check, oauthblueprints
    feature_support['oauth'] = True
except ImportError as err:
    log.debug('Cannot import Flask-Dance, login with Oauth will not work: %s', err)
    feature_support['oauth'] = False
    oauthblueprints = []
    oauth_check = {}


feature_support['gdrive'] = gdrive_support
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
    showtext = {}
    if task in (0, 1):  # valid commandos received
        # close all database connections
        calibre_db.dispose()
        ub.dispose()

        if task == 0:
            showtext['text'] = _(u'Server restarted, please reload page')
        else:
            showtext['text'] = _(u'Performing shutdown of server, please close window')
        # stop gevent/tornado server
        web_server.stop(task == 0)
        return json.dumps(showtext)

    if task == 2:
        log.warning("reconnecting to calibre database")
        calibre_db.setup_db(config, ub.app_DB_path)
        showtext['text'] = _(u'Reconnect successful')
        return json.dumps(showtext)

    showtext['text'] = _(u'Unknown command')
    return json.dumps(showtext), 400


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
    readColumn = calibre_db.session.query(db.Custom_Columns)\
            .filter(and_(db.Custom_Columns.datatype == 'bool', db.Custom_Columns.mark_for_delete == 0)).all()
    restrictColumns= calibre_db.session.query(db.Custom_Columns)\
            .filter(and_(db.Custom_Columns.datatype == 'text', db.Custom_Columns.mark_for_delete == 0)).all()
    return render_title_template("config_view_edit.html", conf=config, readColumns=readColumn,
                                 restrictColumns=restrictColumns,
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
    reboot_required |= _config_string("config_title_regex")

    _config_int("config_read_column")
    _config_int("config_theme")
    _config_int("config_random_books")
    _config_int("config_books_per_page")
    _config_int("config_authors_max")
    _config_int("config_restricted_column")

    config.config_default_role = constants.selected_roles(to_save)
    config.config_default_role &= ~constants.ROLE_ANONYMOUS

    config.config_default_show = sum(int(k[5:]) for k in to_save if k.startswith('show_'))
    if "Show_detail_random" in to_save:
        config.config_default_show |= constants.DETAIL_RANDOM

    config.save()
    flash(_(u"Calibre-Web configuration updated"), category="success")
    before_request()
    if reboot_required:
        db.dispose()
        ub.dispose()
        web_server.stop(True)

    return view_configuration()


@admi.route("/ajax/editdomain/<int:allow>", methods=['POST'])
@login_required
@admin_required
def edit_domain(allow):
    # POST /post
    # name:  'username',  //name of field (column in db)
    # pk:    1            //primary key (record id)
    # value: 'superuser!' //new value
    vals = request.form.to_dict()
    answer = ub.session.query(ub.Registration).filter(ub.Registration.id == vals['pk']).first()
    answer.domain = vals['value'].replace('*', '%').replace('?', '_').lower()
    ub.session.commit()
    return ""


@admi.route("/ajax/adddomain/<int:allow>", methods=['POST'])
@login_required
@admin_required
def add_domain(allow):
    domain_name = request.form.to_dict()['domainname'].replace('*', '%').replace('?', '_').lower()
    check = ub.session.query(ub.Registration).filter(ub.Registration.domain == domain_name).filter(ub.Registration.allow == allow).first()
    if not check:
        new_domain = ub.Registration(domain=domain_name, allow=allow)
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
    if not ub.session.query(ub.Registration).filter(ub.Registration.allow==1).count():
        new_domain = ub.Registration(domain="%.%",allow=1)
        ub.session.add(new_domain)
        ub.session.commit()
    return ""


@admi.route("/ajax/domainlist/<int:allow>")
@login_required
@admin_required
def list_domain(allow):
    answer = ub.session.query(ub.Registration).filter(ub.Registration.allow == allow).all()
    json_dumps = json.dumps([{"domain": r.domain.replace('%', '*').replace('_', '?'), "id": r.id} for r in answer])
    js = json.dumps(json_dumps.replace('"', "'")).lstrip('"').strip('"')
    response = make_response(js.replace("'", '"'))
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

@admi.route("/ajax/editrestriction/<int:res_type>", methods=['POST'])
@login_required
@admin_required
def edit_restriction(res_type):
    element = request.form.to_dict()
    if element['id'].startswith('a'):
        if res_type == 0:  # Tags as template
            elementlist = config.list_allowed_tags()
            elementlist[int(element['id'][1:])]=element['Element']
            config.config_allowed_tags = ','.join(elementlist)
            config.save()
        if res_type == 1:  # CustomC
            elementlist = config.list_allowed_column_values()
            elementlist[int(element['id'][1:])]=element['Element']
            config.config_allowed_column_value = ','.join(elementlist)
            config.save()
        if res_type == 2:  # Tags per user
            usr_id = os.path.split(request.referrer)[-1]
            if usr_id.isdigit() == True:
                usr = ub.session.query(ub.User).filter(ub.User.id == int(usr_id)).first()
            else:
                usr = current_user
            elementlist = usr.list_allowed_tags()
            elementlist[int(element['id'][1:])]=element['Element']
            usr.allowed_tags = ','.join(elementlist)
            ub.session.commit()
        if res_type == 3:  # CColumn per user
            usr_id = os.path.split(request.referrer)[-1]
            if usr_id.isdigit() == True:
                usr = ub.session.query(ub.User).filter(ub.User.id == int(usr_id)).first()
            else:
                usr = current_user
            elementlist = usr.list_allowed_column_values()
            elementlist[int(element['id'][1:])]=element['Element']
            usr.allowed_column_value = ','.join(elementlist)
            ub.session.commit()
    if element['id'].startswith('d'):
        if res_type == 0:  # Tags as template
            elementlist = config.list_denied_tags()
            elementlist[int(element['id'][1:])]=element['Element']
            config.config_denied_tags = ','.join(elementlist)
            config.save()
        if res_type == 1:  # CustomC
            elementlist = config.list_denied_column_values()
            elementlist[int(element['id'][1:])]=element['Element']
            config.config_denied_column_value = ','.join(elementlist)
            config.save()
        if res_type == 2:  # Tags per user
            usr_id = os.path.split(request.referrer)[-1]
            if usr_id.isdigit() == True:
                usr = ub.session.query(ub.User).filter(ub.User.id == int(usr_id)).first()
            else:
                usr = current_user
            elementlist = usr.list_denied_tags()
            elementlist[int(element['id'][1:])]=element['Element']
            usr.denied_tags = ','.join(elementlist)
            ub.session.commit()
        if res_type == 3:  # CColumn per user
            usr_id = os.path.split(request.referrer)[-1]
            if usr_id.isdigit() == True:
                usr = ub.session.query(ub.User).filter(ub.User.id == int(usr_id)).first()
            else:
                usr = current_user
            elementlist = usr.list_denied_column_values()
            elementlist[int(element['id'][1:])]=element['Element']
            usr.denied_column_value = ','.join(elementlist)
            ub.session.commit()
    return ""

def restriction_addition(element, list_func):
    elementlist = list_func()
    if elementlist == ['']:
        elementlist = []
    if not element['add_element'] in elementlist:
        elementlist += [element['add_element']]
    return ','.join(elementlist)


def restriction_deletion(element, list_func):
    elementlist = list_func()
    if element['Element'] in elementlist:
        elementlist.remove(element['Element'])
    return ','.join(elementlist)


@admi.route("/ajax/addrestriction/<int:res_type>", methods=['POST'])
@login_required
@admin_required
def add_restriction(res_type):
    element = request.form.to_dict()
    if res_type == 0:  # Tags as template
        if 'submit_allow' in element:
            config.config_allowed_tags = restriction_addition(element, config.list_allowed_tags)
            config.save()
        elif 'submit_deny' in element:
            config.config_denied_tags = restriction_addition(element, config.list_denied_tags)
            config.save()
    if res_type == 1:  # CCustom as template
        if 'submit_allow' in element:
            config.config_allowed_column_value = restriction_addition(element, config.list_denied_column_values)
            config.save()
        elif 'submit_deny' in element:
            config.config_denied_column_value = restriction_addition(element, config.list_allowed_column_values)
            config.save()
    if res_type == 2:  # Tags per user
        usr_id = os.path.split(request.referrer)[-1]
        if usr_id.isdigit() == True:
            usr = ub.session.query(ub.User).filter(ub.User.id == int(usr_id)).first()
        else:
            usr = current_user
        if 'submit_allow' in element:
            usr.allowed_tags = restriction_addition(element, usr.list_allowed_tags)
            ub.session.commit()
        elif 'submit_deny' in element:
            usr.denied_tags = restriction_addition(element, usr.list_denied_tags)
            ub.session.commit()
    if res_type == 3:  # CustomC per user
        usr_id = os.path.split(request.referrer)[-1]
        if usr_id.isdigit() == True:
            usr = ub.session.query(ub.User).filter(ub.User.id == int(usr_id)).first()
        else:
            usr = current_user
        if 'submit_allow' in element:
            usr.allowed_column_value = restriction_addition(element, usr.list_allowed_column_values)
            ub.session.commit()
        elif 'submit_deny' in element:
            usr.denied_column_value = restriction_addition(element, usr.list_denied_column_values)
            ub.session.commit()
    return ""

@admi.route("/ajax/deleterestriction/<int:res_type>", methods=['POST'])
@login_required
@admin_required
def delete_restriction(res_type):
    element = request.form.to_dict()
    if res_type == 0:  # Tags as template
        if element['id'].startswith('a'):
            config.config_allowed_tags = restriction_deletion(element, config.list_allowed_tags)
            config.save()
        elif element['id'].startswith('d'):
            config.config_denied_tags = restriction_deletion(element, config.list_denied_tags)
            config.save()
    elif res_type == 1:  # CustomC as template
        if element['id'].startswith('a'):
            config.config_allowed_column_value = restriction_deletion(element, config.list_allowed_column_values)
            config.save()
        elif element['id'].startswith('d'):
            config.config_denied_column_value = restriction_deletion(element, config.list_denied_column_values)
            config.save()
    elif res_type == 2:  # Tags per user
        usr_id = os.path.split(request.referrer)[-1]
        if usr_id.isdigit() == True:
            usr = ub.session.query(ub.User).filter(ub.User.id == int(usr_id)).first()
        else:
            usr = current_user
        if element['id'].startswith('a'):
            usr.allowed_tags = restriction_deletion(element, usr.list_allowed_tags)
            ub.session.commit()
        elif element['id'].startswith('d'):
            usr.denied_tags = restriction_deletion(element, usr.list_denied_tags)
            ub.session.commit()
    elif res_type == 3:  # Columns per user
        usr_id = os.path.split(request.referrer)[-1]
        if usr_id.isdigit() == True:    # select current user if admins are editing their own rights
            usr = ub.session.query(ub.User).filter(ub.User.id == int(usr_id)).first()
        else:
            usr = current_user
        if element['id'].startswith('a'):
            usr.allowed_column_value = restriction_deletion(element, usr.list_allowed_column_values)
            ub.session.commit()
        elif element['id'].startswith('d'):
            usr.denied_column_value = restriction_deletion(element, usr.list_denied_column_values)
            ub.session.commit()
    return ""


@admi.route("/ajax/listrestriction/<int:res_type>")
@login_required
@admin_required
def list_restriction(res_type):
    if res_type == 0:   # Tags as template
        restrict = [{'Element': x, 'type':_('Deny'), 'id': 'd'+str(i) }
                    for i,x in enumerate(config.list_denied_tags()) if x != '' ]
        allow = [{'Element': x, 'type':_('Allow'), 'id': 'a'+str(i) }
                 for i,x in enumerate(config.list_allowed_tags()) if x != '']
        json_dumps = restrict + allow
    elif res_type == 1:  # CustomC as template
        restrict = [{'Element': x, 'type':_('Deny'), 'id': 'd'+str(i) }
                    for i,x in enumerate(config.list_denied_column_values()) if x != '' ]
        allow = [{'Element': x, 'type':_('Allow'), 'id': 'a'+str(i) }
                 for i,x in enumerate(config.list_allowed_column_values()) if x != '']
        json_dumps = restrict + allow
    elif res_type == 2:  # Tags per user
        usr_id = os.path.split(request.referrer)[-1]
        if usr_id.isdigit() == True:
            usr = ub.session.query(ub.User).filter(ub.User.id == usr_id).first()
        else:
            usr = current_user
        restrict = [{'Element': x, 'type':_('Deny'), 'id': 'd'+str(i) }
                    for i,x in enumerate(usr.list_denied_tags()) if x != '' ]
        allow = [{'Element': x, 'type':_('Allow'), 'id': 'a'+str(i) }
                 for i,x in enumerate(usr.list_allowed_tags()) if x != '']
        json_dumps = restrict + allow
    elif res_type == 3:  # CustomC per user
        usr_id = os.path.split(request.referrer)[-1]
        if usr_id.isdigit() == True:
            usr = ub.session.query(ub.User).filter(ub.User.id==usr_id).first()
        else:
            usr = current_user
        restrict = [{'Element': x, 'type':_('Deny'), 'id': 'd'+str(i) }
                    for i,x in enumerate(usr.list_denied_column_values()) if x != '' ]
        allow = [{'Element': x, 'type':_('Allow'), 'id': 'a'+str(i) }
                 for i,x in enumerate(usr.list_allowed_column_values()) if x != '']
        json_dumps = restrict + allow
    else:
        json_dumps=""
    js = json.dumps(json_dumps)
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


def _config_int(to_save, x, func=int):
    return config.set_from_dictionary(to_save, x, func)


def _config_checkbox(to_save, x):
    return config.set_from_dictionary(to_save, x, lambda y: y == "on", False)


def _config_checkbox_int(to_save, x):
    return config.set_from_dictionary(to_save, x, lambda y: 1 if (y == "on") else 0, 0)


def _config_string(to_save, x):
    return config.set_from_dictionary(to_save, x, lambda y: y.strip() if y else y)


def _configuration_gdrive_helper(to_save):
    if not os.path.isfile(gdriveutils.SETTINGS_YAML):
        config.config_use_google_drive = False

    gdrive_secrets = {}
    gdriveError = gdriveutils.get_error_text(gdrive_secrets)
    if "config_use_google_drive" in to_save and not config.config_use_google_drive and not gdriveError:
        with open(gdriveutils.CLIENT_SECRETS, 'r') as settings:
            gdrive_secrets = json.load(settings)['web']
        if not gdrive_secrets:
            return _configuration_result(_('client_secrets.json Is Not Configured For Web Application'))
        gdriveutils.update_settings(
                            gdrive_secrets['client_id'],
                            gdrive_secrets['client_secret'],
                            gdrive_secrets['redirect_uris'][0]
                        )

    # always show google drive settings, but in case of error deny support
    config.config_use_google_drive = (not gdriveError) and ("config_use_google_drive" in to_save)
    if _config_string(to_save, "config_google_drive_folder"):
        gdriveutils.deleteDatabaseOnChange()
    return gdriveError

def _configuration_oauth_helper(to_save):
    active_oauths = 0
    reboot_required = False
    for element in oauthblueprints:
        if to_save["config_" + str(element['id']) + "_oauth_client_id"] != element['oauth_client_id'] \
            or to_save["config_" + str(element['id']) + "_oauth_client_secret"] != element['oauth_client_secret']:
            reboot_required = True
            element['oauth_client_id'] = to_save["config_" + str(element['id']) + "_oauth_client_id"]
            element['oauth_client_secret'] = to_save["config_" + str(element['id']) + "_oauth_client_secret"]
        if to_save["config_" + str(element['id']) + "_oauth_client_id"] \
            and to_save["config_" + str(element['id']) + "_oauth_client_secret"]:
            active_oauths += 1
            element["active"] = 1
        else:
            element["active"] = 0
        ub.session.query(ub.OAuthProvider).filter(ub.OAuthProvider.id == element['id']).update(
            {"oauth_client_id": to_save["config_" + str(element['id']) + "_oauth_client_id"],
             "oauth_client_secret": to_save["config_" + str(element['id']) + "_oauth_client_secret"],
             "active": element["active"]})
    return reboot_required

def _configuration_logfile_helper(to_save, gdriveError):
    reboot_required = False
    reboot_required |= _config_int(to_save, "config_log_level")
    reboot_required |= _config_string(to_save, "config_logfile")
    if not logger.is_valid_logfile(config.config_logfile):
        return reboot_required, _configuration_result(_('Logfile Location is not Valid, Please Enter Correct Path'), gdriveError)

    reboot_required |= _config_checkbox_int(to_save, "config_access_log")
    reboot_required |= _config_string(to_save, "config_access_logfile")
    if not logger.is_valid_logfile(config.config_access_logfile):
        return reboot_required, _configuration_result(_('Access Logfile Location is not Valid, Please Enter Correct Path'), gdriveError)
    return reboot_required, None

def _configuration_ldap_helper(to_save, gdriveError):
    reboot_required = False
    reboot_required |= _config_string(to_save, "config_ldap_provider_url")
    reboot_required |= _config_int(to_save, "config_ldap_port")
    reboot_required |= _config_int(to_save, "config_ldap_authentication")
    reboot_required |= _config_string(to_save, "config_ldap_dn")
    reboot_required |= _config_string(to_save, "config_ldap_serv_username")
    reboot_required |= _config_string(to_save, "config_ldap_user_object")
    reboot_required |= _config_string(to_save, "config_ldap_group_object_filter")
    reboot_required |= _config_string(to_save, "config_ldap_group_members_field")
    reboot_required |= _config_checkbox(to_save, "config_ldap_openldap")
    reboot_required |= _config_int(to_save, "config_ldap_encryption")
    reboot_required |= _config_string(to_save, "config_ldap_cert_path")
    _config_string(to_save, "config_ldap_group_name")
    if "config_ldap_serv_password" in to_save and to_save["config_ldap_serv_password"] != "":
        reboot_required |= 1
        config.set_from_dictionary(to_save, "config_ldap_serv_password", base64.b64encode, encode='UTF-8')
    config.save()

    if not config.config_ldap_provider_url \
        or not config.config_ldap_port \
        or not config.config_ldap_dn \
        or not config.config_ldap_user_object:
        return reboot_required, _configuration_result(_('Please Enter a LDAP Provider, '
                                       'Port, DN and User Object Identifier'), gdriveError)

    if config.config_ldap_authentication > constants.LDAP_AUTH_ANONYMOUS:
        if config.config_ldap_authentication > constants.LDAP_AUTH_UNAUTHENTICATE:
            if not config.config_ldap_serv_username or not bool(config.config_ldap_serv_password):
                return reboot_required, _configuration_result('Please Enter a LDAP Service Account and Password', gdriveError)
        else:
            if not config.config_ldap_serv_username:
                return reboot_required, _configuration_result('Please Enter a LDAP Service Account', gdriveError)

    if config.config_ldap_group_object_filter:
        if config.config_ldap_group_object_filter.count("%s") != 1:
            return reboot_required, _configuration_result(_('LDAP Group Object Filter Needs to Have One "%s" Format Identifier'),
                                         gdriveError)
        if config.config_ldap_group_object_filter.count("(") != config.config_ldap_group_object_filter.count(")"):
            return reboot_required, _configuration_result(_('LDAP Group Object Filter Has Unmatched Parenthesis'),
                                         gdriveError)

    if config.config_ldap_user_object.count("%s") != 1:
        return reboot_required, _configuration_result(_('LDAP User Object Filter needs to Have One "%s" Format Identifier'),
                                     gdriveError)
    if config.config_ldap_user_object.count("(") != config.config_ldap_user_object.count(")"):
        return reboot_required, _configuration_result(_('LDAP User Object Filter Has Unmatched Parenthesis'),
                                     gdriveError)

    if config.config_ldap_cert_path and not os.path.isdir(config.config_ldap_cert_path):
        return reboot_required, _configuration_result(_('LDAP Certificate Location is not Valid, Please Enter Correct Path'),
                                     gdriveError)
    return reboot_required, None


def _configuration_update_helper():
    reboot_required = False
    db_change = False
    to_save = request.form.to_dict()

    to_save['config_calibre_dir'] = re.sub('[\\/]metadata\.db$', '', to_save['config_calibre_dir'], flags=re.IGNORECASE)
    db_change |= _config_string(to_save, "config_calibre_dir")

    # Google drive setup
    gdriveError = _configuration_gdrive_helper(to_save)

    reboot_required |= _config_int(to_save, "config_port")

    reboot_required |= _config_string(to_save, "config_keyfile")
    if config.config_keyfile and not os.path.isfile(config.config_keyfile):
        return _configuration_result(_('Keyfile Location is not Valid, Please Enter Correct Path'), gdriveError)

    reboot_required |= _config_string(to_save, "config_certfile")
    if config.config_certfile and not os.path.isfile(config.config_certfile):
        return _configuration_result(_('Certfile Location is not Valid, Please Enter Correct Path'), gdriveError)

    _config_checkbox_int(to_save, "config_uploading")
    _config_checkbox_int(to_save, "config_anonbrowse")
    _config_checkbox_int(to_save, "config_public_reg")
    _config_checkbox_int(to_save, "config_register_email")
    reboot_required |= _config_checkbox_int(to_save, "config_kobo_sync")
    _config_checkbox_int(to_save, "config_kobo_proxy")

    _config_string(to_save, "config_upload_formats")
    constants.EXTENSIONS_UPLOAD = [x.lstrip().rstrip() for x in config.config_upload_formats.split(',')]

    _config_string(to_save, "config_calibre")
    _config_string(to_save, "config_converterpath")
    _config_string(to_save, "config_kepubifypath")

    reboot_required |= _config_int(to_save, "config_login_type")

    #LDAP configurator,
    if config.config_login_type == constants.LOGIN_LDAP:
        reboot, message = _configuration_ldap_helper(to_save, gdriveError)
        if message:
            return message
        reboot_required |= reboot

    # Remote login configuration
    _config_checkbox(to_save, "config_remote_login")
    if not config.config_remote_login:
        ub.session.query(ub.RemoteAuthToken).filter(ub.RemoteAuthToken.token_type==0).delete()

    # Goodreads configuration
    _config_checkbox(to_save, "config_use_goodreads")
    _config_string(to_save, "config_goodreads_api_key")
    _config_string(to_save, "config_goodreads_api_secret")
    if services.goodreads_support:
        services.goodreads_support.connect(config.config_goodreads_api_key,
                                           config.config_goodreads_api_secret,
                                           config.config_use_goodreads)

    _config_int(to_save, "config_updatechannel")

    # Reverse proxy login configuration
    _config_checkbox(to_save, "config_allow_reverse_proxy_header_login")
    _config_string(to_save, "config_reverse_proxy_login_header_name")

    # OAuth configuration
    if config.config_login_type == constants.LOGIN_OAUTH:
        reboot_required |= _configuration_oauth_helper(to_save)

    reboot, message = _configuration_logfile_helper(to_save, gdriveError)
    if message:
        return message
    reboot_required |= reboot
    # Rarfile Content configuration
    _config_string(to_save, "config_rarfile_location")
    if "config_rarfile_location" in to_save:
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
        if not calibre_db.setup_db(config, ub.app_DB_path):
            return _configuration_result(_('DB Location is not Valid, Please Enter Correct Path'), gdriveError)
        if not os.access(os.path.join(config.config_calibre_dir, "metadata.db"), os.W_OK):
            flash(_(u"DB is not Writeable"), category="warning")

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
        # if config.config_use_google_drive and\
        if not gdrive_authenticate:
            gdrivefolders = gdriveutils.listRootFolders()

    show_back_button = current_user.is_authenticated
    show_login_button = config.db_configured and not current_user.is_authenticated
    if error_flash:
        config.load()
        flash(error_flash, category="error")
        show_login_button = False

    return render_title_template("config_edit.html", config=config, provider=oauthblueprints,
                                 show_back_button=show_back_button, show_login_button=show_login_button,
                                 show_authenticate_google_drive=gdrive_authenticate,
                                 gdriveError=gdriveError, gdrivefolders=gdrivefolders, feature_support=feature_support,
                                 title=_(u"Basic Configuration"), page="config")


def _handle_new_user(to_save, content,languages, translations, kobo_support):
    content.default_language = to_save["default_language"]
    # content.mature_content = "Show_mature_content" in to_save
    content.locale = to_save.get("locale", content.locale)

    content.sidebar_view = sum(int(key[5:]) for key in to_save if key.startswith('show_'))
    if "show_detail_random" in to_save:
        content.sidebar_view |= constants.DETAIL_RANDOM

    content.role = constants.selected_roles(to_save)

    if not to_save["nickname"] or not to_save["email"] or not to_save["password"]:
        flash(_(u"Please fill out all fields!"), category="error")
        return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                     registered_oauth=oauth_check, kobo_support=kobo_support,
                                     title=_(u"Add new user"))
    content.password = generate_password_hash(to_save["password"])
    existing_user = ub.session.query(ub.User).filter(func.lower(ub.User.nickname) == to_save["nickname"].lower()) \
        .first()
    existing_email = ub.session.query(ub.User).filter(ub.User.email == to_save["email"].lower()) \
        .first()
    if not existing_user and not existing_email:
        content.nickname = to_save["nickname"]
        if config.config_public_reg and not check_valid_domain(to_save["email"]):
            flash(_(u"E-mail is not from valid domain"), category="error")
            return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                         registered_oauth=oauth_check, kobo_support=kobo_support,
                                         title=_(u"Add new user"))
        else:
            content.email = to_save["email"]
    else:
        flash(_(u"Found an existing account for this e-mail address or nickname."), category="error")
        return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                     languages=languages, title=_(u"Add new user"), page="newuser",
                                     kobo_support=kobo_support, registered_oauth=oauth_check)
    try:
        content.allowed_tags = config.config_allowed_tags
        content.denied_tags = config.config_denied_tags
        content.allowed_column_value = config.config_allowed_column_value
        content.denied_column_value = config.config_denied_column_value
        ub.session.add(content)
        ub.session.commit()
        flash(_(u"User '%(user)s' created", user=content.nickname), category="success")
        return redirect(url_for('admin.admin'))
    except IntegrityError:
        ub.session.rollback()
        flash(_(u"Found an existing account for this e-mail address or nickname."), category="error")


def _handle_edit_user(to_save, content,languages, translations, kobo_support, downloads):
    if "delete" in to_save:
        if ub.session.query(ub.User).filter(ub.User.role.op('&')(constants.ROLE_ADMIN) == constants.ROLE_ADMIN,
                                            ub.User.id != content.id).count():
            ub.session.query(ub.User).filter(ub.User.id == content.id).delete()
            ub.session.commit()
            flash(_(u"User '%(nick)s' deleted", nick=content.nickname), category="success")
            return redirect(url_for('admin.admin'))
        else:
            flash(_(u"No admin user remaining, can't delete user", nick=content.nickname), category="error")
            return redirect(url_for('admin.admin'))
    else:
        if not ub.session.query(ub.User).filter(ub.User.role.op('&')(constants.ROLE_ADMIN) == constants.ROLE_ADMIN,
                                                ub.User.id != content.id).count() and \
            not 'admin_role' in to_save:
            flash(_(u"No admin user remaining, can't remove admin role", nick=content.nickname), category="error")
            return redirect(url_for('admin.admin'))

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
                return render_title_template("user_edit.html",
                                             translations=translations,
                                             languages=languages,
                                             mail_configured=config.get_mail_server_configured(),
                                             kobo_support=kobo_support,
                                             new_user=0,
                                             content=content,
                                             downloads=downloads,
                                             registered_oauth=oauth_check,
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
                                             mail_configured=config.get_mail_server_configured(),
                                             new_user=0, content=content,
                                             downloads=downloads,
                                             registered_oauth=oauth_check,
                                             kobo_support=kobo_support,
                                             title=_(u"Edit User %(nick)s", nick=content.nickname),
                                             page="edituser")

        if "kindle_mail" in to_save and to_save["kindle_mail"] != content.kindle_mail:
            content.kindle_mail = to_save["kindle_mail"]
    try:
        ub.session.commit()
        flash(_(u"User '%(nick)s' updated", nick=content.nickname), category="success")
    except IntegrityError:
        ub.session.rollback()
        flash(_(u"An unknown error occured."), category="error")


@admi.route("/admin/user/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_user():
    content = ub.User()
    languages = calibre_db.speaking_language()
    translations = [LC('en')] + babel.list_translations()
    kobo_support = feature_support['kobo'] and config.config_kobo_sync
    if request.method == "POST":
        to_save = request.form.to_dict()
        _handle_new_user(to_save, content, languages, translations, kobo_support)
    else:
        content.role = config.config_default_role
        content.sidebar_view = config.config_default_show
    return render_title_template("user_edit.html", new_user=1, content=content, translations=translations,
                                 languages=languages, title=_(u"Add new user"), page="newuser",
                                 kobo_support=kobo_support, registered_oauth=oauth_check)


@admi.route("/admin/mailsettings")
@login_required
@admin_required
def edit_mailsettings():
    content = config.get_mail_settings()
    return render_title_template("email_edit.html", content=content, title=_(u"Edit E-mail Server Settings"),
                                 page="mailset")


@admi.route("/admin/mailsettings", methods=["POST"])
@login_required
@admin_required
def update_mailsettings():
    to_save = request.form.to_dict()
    # log.debug("update_mailsettings %r", to_save)

    _config_string(to_save, "mail_server")
    _config_int(to_save, "mail_port")
    _config_int(to_save, "mail_use_ssl")
    _config_string(to_save, "mail_login")
    _config_string(to_save, "mail_password")
    _config_string(to_save, "mail_from")
    _config_int(to_save, "mail_size", lambda y: int(y)*1024*1024)
    config.save()

    if to_save.get("test"):
        if current_user.email:
            result = send_test_mail(current_user.email, current_user.nickname)
            if result is None:
                flash(_(u"Test e-mail successfully send to %(kindlemail)s", kindlemail=current_user.email),
                      category="success")
            else:
                flash(_(u"There was an error sending the Test e-mail: %(res)s", res=result), category="error")
        else:
            flash(_(u"Please configure your e-mail address first..."), category="error")
    else:
        flash(_(u"E-mail server settings updated"), category="success")

    return edit_mailsettings()


@admi.route("/admin/user/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    content = ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()  # type: ub.User
    if not content:
        flash(_(u"User not found"), category="error")
        return redirect(url_for('admin.admin'))
    downloads = list()
    languages = calibre_db.speaking_language()
    translations = babel.list_translations() + [LC('en')]
    kobo_support = feature_support['kobo'] and config.config_kobo_sync
    for book in content.downloads:
        downloadbook = calibre_db.get_book(book.book_id)
        if downloadbook:
            downloads.append(downloadbook)
        else:
            ub.delete_download(book.book_id)
    if request.method == "POST":
        to_save = request.form.to_dict()
        _handle_edit_user(to_save, content, languages, translations, kobo_support, downloads)
    return render_title_template("user_edit.html",
                                 translations=translations,
                                 languages=languages,
                                 new_user=0,
                                 content=content,
                                 downloads=downloads,
                                 registered_oauth=oauth_check,
                                 mail_configured=config.get_mail_server_configured(),
                                 kobo_support=kobo_support,
                                 title=_(u"Edit User %(nick)s", nick=content.nickname), page="edituser")


@admi.route("/admin/resetpassword/<int:user_id>")
@login_required
@admin_required
def reset_user_password(user_id):
    if current_user is not None and current_user.is_authenticated:
        ret, message = reset_password(user_id)
        if ret == 1:
            log.debug(u"Password for user %s reset", message)
            flash(_(u"Password for user %(user)s reset", user=message), category="success")
        elif ret == 0:
            log.error(u"An unknown error occurred. Please try again later.")
            flash(_(u"An unknown error occurred. Please try again later."), category="error")
        else:
            log.error(u"Please configure the SMTP mail settings first...")
            flash(_(u"Please configure the SMTP mail settings first..."), category="error")
    return redirect(url_for('admin.admin'))


@admi.route("/admin/logfile")
@login_required
@admin_required
def view_logfile():
    logfiles = {}
    logfiles[0] = logger.get_logfile(config.config_logfile)
    logfiles[1] = logger.get_accesslogfile(config.config_access_logfile)
    return render_title_template("logviewer.html",
                                 title=_(u"Logfile viewer"),
                                 accesslog_enable=config.config_access_log,
                                 log_enable=bool(config.config_logfile != logger.LOG_TO_STDOUT),
                                 logfiles=logfiles,
                                 page="logfile")


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
    log.info(u"Update status requested")
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
                "11": _(u'Update failed:') + u' ' + _(u'General error'),
                "12": _(u'Update failed:') + u' ' + _(u'Update File Could Not be Saved in Temp Dir')
            }
            status['text'] = text
            updater_thread.status = 0
            updater_thread.resume()
            status['status'] = updater_thread.get_update_status()
    elif request.method == "GET":
        try:
            status['status'] = updater_thread.get_update_status()
            if status['status']  == -1:
                status['status'] = 7
        except Exception:
            status['status'] = 11
    return json.dumps(status)
