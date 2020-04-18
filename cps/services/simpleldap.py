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

from __future__ import division, print_function, unicode_literals
import base64

from flask_simpleldap import LDAP, LDAPException

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
        app.config['LDAP_REQUIRE_CERT'] = True
        app.config['LDAP_CERT_PATH'] = config.config_ldap_cert_path
    app.config['LDAP_BASE_DN'] = config.config_ldap_dn
    app.config['LDAP_USER_OBJECT_FILTER'] = config.config_ldap_user_object

    app.config['LDAP_USE_TLS'] = bool(config.config_ldap_encryption == 1)
    app.config['LDAP_USE_SSL'] = bool(config.config_ldap_encryption == 2)
    app.config['LDAP_OPENLDAP'] = bool(config.config_ldap_openldap)
    app.config['LDAP_GROUP_OBJECT_FILTER'] = config.config_ldap_group_object_filter
    app.config['LDAP_GROUP_MEMBERS_FIELD'] = config.config_ldap_group_members_field
    # app.config['LDAP_CUSTOM_OPTIONS'] = {'OPT_NETWORK_TIMEOUT': 10}

    _ldap.init_app(app)


def get_object_details(user=None, group=None, query_filter=None, dn_only=False):
    return _ldap.get_object_details(user, group, query_filter, dn_only)


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
            error = ("LDAP admin login failed")
            return None, error
        if ex.message == "Can't contact LDAP server":
            # log.warning('LDAP Server down: %s', ex)
            error = ('LDAP Server down: %s' % ex)
            return None,  error
        else:
            error = ('LDAP Server error: %s' % ex.message)
            return None, error
