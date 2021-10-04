# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, pwr
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

import base64

from flask_simpleldap import LDAP, LDAPException
from flask_simpleldap import ldap as pyLDAP
from .. import constants, logger

try:
    from ldap.pkginfo import __version__ as ldapVersion
except ImportError:
    pass

log = logger.create()
_ldap = LDAP()


def init_app(app, config):
    if config.config_login_type != constants.LOGIN_LDAP:
        return

    app.config['LDAP_HOST'] = config.config_ldap_provider_url
    app.config['LDAP_PORT'] = config.config_ldap_port
    app.config['LDAP_CUSTOM_OPTIONS'] = {pyLDAP.OPT_REFERRALS: 0}
    if config.config_ldap_encryption == 2:
        app.config['LDAP_SCHEMA'] = 'ldaps'
    else:
        app.config['LDAP_SCHEMA'] = 'ldap'
    if config.config_ldap_authentication > constants.LDAP_AUTH_ANONYMOUS:
        if config.config_ldap_authentication > constants.LDAP_AUTH_UNAUTHENTICATE:
            if config.config_ldap_serv_password is None:
                config.config_ldap_serv_password = ''
            app.config['LDAP_PASSWORD'] = base64.b64decode(config.config_ldap_serv_password)
        else:
            app.config['LDAP_PASSWORD'] = base64.b64decode("")
        app.config['LDAP_USERNAME'] = config.config_ldap_serv_username
    else:
        app.config['LDAP_USERNAME'] = ""
        app.config['LDAP_PASSWORD'] = base64.b64decode("")
    if bool(config.config_ldap_cert_path):
        app.config['LDAP_CUSTOM_OPTIONS'].update({
            pyLDAP.OPT_X_TLS_REQUIRE_CERT: pyLDAP.OPT_X_TLS_DEMAND,
            pyLDAP.OPT_X_TLS_CACERTFILE: config.config_ldap_cacert_path,
            pyLDAP.OPT_X_TLS_CERTFILE: config.config_ldap_cert_path,
            pyLDAP.OPT_X_TLS_KEYFILE: config.config_ldap_key_path,
            pyLDAP.OPT_X_TLS_NEWCTX: 0
            })

    app.config['LDAP_BASE_DN'] = config.config_ldap_dn
    app.config['LDAP_USER_OBJECT_FILTER'] = config.config_ldap_user_object

    app.config['LDAP_USE_TLS'] = bool(config.config_ldap_encryption == 1)
    app.config['LDAP_USE_SSL'] = bool(config.config_ldap_encryption == 2)
    app.config['LDAP_OPENLDAP'] = bool(config.config_ldap_openldap)
    app.config['LDAP_GROUP_OBJECT_FILTER'] = config.config_ldap_group_object_filter
    app.config['LDAP_GROUP_MEMBERS_FIELD'] = config.config_ldap_group_members_field

    try:
        _ldap.init_app(app)
    except ValueError:
        if bool(config.config_ldap_cert_path):
            app.config['LDAP_CUSTOM_OPTIONS'].pop(pyLDAP.OPT_X_TLS_NEWCTX)
        try:
            _ldap.init_app(app)
        except RuntimeError as e:
            log.error(e)
    except RuntimeError as e:
        log.error(e)


def get_object_details(user=None,query_filter=None):
    return _ldap.get_object_details(user, query_filter=query_filter)


def bind():
    return _ldap.bind()


def get_group_members(group):
    return _ldap.get_group_members(group)


def basic_auth_required(func):
    return _ldap.basic_auth_required(func)


def bind_user(username, password):
    '''Attempts a LDAP login.

    :returns: True if login succeeded, False if login failed, None if server unavailable.
    '''
    try:
        if _ldap.get_object_details(username):
            result = _ldap.bind_user(username, password)
            log.debug("LDAP login '%s': %r", username, result)
            return result is not None, None
        return None, None       # User not found
    except (TypeError, AttributeError, KeyError) as ex:
        error = ("LDAP bind_user: %s" % ex)
        return None, error
    except LDAPException as ex:
        if ex.message == 'Invalid credentials':
            error = "LDAP admin login failed"
            return None, error
        if ex.message == "Can't contact LDAP server":
            # log.warning('LDAP Server down: %s', ex)
            error = ('LDAP Server down: %s' % ex)
            return None,  error
        else:
            error = ('LDAP Server error: %s' % ex.message)
            return None, error
