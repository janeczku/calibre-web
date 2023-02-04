# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2020 OzzieIsaacs
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
import binascii
from functools import wraps

from sqlalchemy.sql.expression import func
from werkzeug.security import check_password_hash
from flask_login import login_required, login_user
from flask import request, Response

from . import lm, ub, config, constants, services, logger

log = logger.create()

def login_required_if_no_ano(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if config.config_anonbrowse == 1:
            return func(*args, **kwargs)
        return login_required(func)(*args, **kwargs)

    return decorated_view

def requires_basic_auth_if_no_ano(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if config.config_anonbrowse != 1:
            if not auth or auth.type != 'basic' or not check_auth(auth.username, auth.password):
                return authenticate()
            print("opds_requires_basic_auth")
            user = load_user_from_auth_header(auth.username, auth.password)
            if not user:
                return None
            login_user(user)
        return f(*args, **kwargs)
    if config.config_login_type == constants.LOGIN_LDAP and services.ldap and config.config_anonbrowse != 1:
        return services.ldap.basic_auth_required(f)

    return decorated


def check_auth(username, password):
    try:
        username = username.encode('windows-1252')
    except UnicodeEncodeError:
        username = username.encode('utf-8')
    user = ub.session.query(ub.User).filter(func.lower(ub.User.name) ==
                                            username.decode('utf-8').lower()).first()
    if bool(user and check_password_hash(str(user.password), password)):
        return True
    else:
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        log.warning('OPDS Login failed for user "%s" IP-address: %s', username.decode('utf-8'), ip_address)
        return False


def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})



def _fetch_user_by_name(username):
    return ub.session.query(ub.User).filter(func.lower(ub.User.name) == username.lower()).first()


@lm.user_loader
def load_user(user_id):
    print("load_user: {}".format(user_id))
    return ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()


@lm.request_loader
def load_user_from_request(request):
    print("load_from_request")
    if config.config_allow_reverse_proxy_header_login:
        rp_header_name = config.config_reverse_proxy_login_header_name
        if rp_header_name:
            rp_header_username = request.headers.get(rp_header_name)
            if rp_header_username:
                user = _fetch_user_by_name(rp_header_username)
                if user:
                    login_user(user)
                    return user

    #auth_header = request.headers.get("Authorization")
    #if auth_header:
    #    user = load_user_from_auth_header(auth_header)
    #    if user:
    #        login_user(user)
    #        return user

    return None


def load_user_from_auth_header(basic_username, basic_password):
    #if header_val.startswith('Basic '):
    #    header_val = header_val.replace('Basic ', '', 1)
    #basic_username = basic_password = ''  # nosec
    #try:
    #    header_val = base64.b64decode(header_val).decode('utf-8')
    #    # Users with colon are invalid: rfc7617 page 4
    #    basic_username = header_val.split(':', 1)[0]
    #    basic_password = header_val.split(':', 1)[1]
    #except (TypeError, UnicodeDecodeError, binascii.Error):
    #    pass
    user = _fetch_user_by_name(basic_username)
    if user and config.config_login_type == constants.LOGIN_LDAP and services.ldap:
        if services.ldap.bind_user(str(user.password), basic_password):
            login_user(user)
            return user
    if user and check_password_hash(str(user.password), basic_password):
        login_user(user)
        return user
    return None
