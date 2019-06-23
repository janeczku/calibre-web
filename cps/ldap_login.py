# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2019 Krakinou
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
import base64

try:
   from flask_simpleldap import LDAP # , LDAPException
   ldap_support = True
except ImportError:
   ldap_support = False

from . import config, logger

log = logger.create()

class Ldap():

    def __init__(self):
        self.ldap = None
        return

    def init_app(self, app):
        if ldap_support and config.config_login_type == 1:
            app.config['LDAP_HOST'] = config.config_ldap_provider_url
            app.config['LDAP_PORT'] = config.config_ldap_port
            app.config['LDAP_SCHEMA'] = config.config_ldap_schema
            app.config['LDAP_USERNAME'] = config.config_ldap_user_object.replace('%s', config.config_ldap_serv_username)\
                                          + ',' + config.config_ldap_dn
            app.config['LDAP_PASSWORD'] = base64.b64decode(config.config_ldap_serv_password)
            if config.config_ldap_use_ssl:
                app.config['LDAP_USE_SSL'] = True
            if config.config_ldap_use_tls:
                app.config['LDAP_USE_TLS'] = True
            app.config['LDAP_REQUIRE_CERT'] = config.config_ldap_require_cert
            if config.config_ldap_require_cert:
                app.config['LDAP_CERT_PATH'] = config.config_ldap_cert_path
            app.config['LDAP_BASE_DN'] = config.config_ldap_dn
            app.config['LDAP_USER_OBJECT_FILTER'] = config.config_ldap_user_object
            if config.config_ldap_openldap:
                app.config['LDAP_OPENLDAP'] = True

        #    app.config['LDAP_BASE_DN'] = 'ou=users,dc=yunohost,dc=org'
        #    app.config['LDAP_USER_OBJECT_FILTER'] = '(uid=%s)'
            self.ldap = LDAP(app)

        elif config.config_login_type == 1 and not ldap_support:
            log.error('Cannot activate ldap support, did you run \'pip install --target vendor -r optional-requirements.txt\'?')

    @classmethod
    def ldap_supported(cls):
        return ldap_support
