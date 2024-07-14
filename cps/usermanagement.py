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

from functools import wraps

from sqlalchemy.sql.expression import func
from .cw_login import login_required

from flask import request, g
from flask_httpauth import HTTPBasicAuth
from werkzeug.datastructures import Authorization
from werkzeug.security import check_password_hash

from . import lm, ub, config, logger, limiter, constants, services


log = logger.create()


'''class HTTPProxyAuth(HTTPAuth):
    def __init__(self, scheme='Proxy', realm=None, header=None):
        super(HTTPProxyAuth, self).__init__(scheme, realm, header)
        self.user = None
        self.verify_user_callback = None

    def set_user(self, username):
        self.user = username if username else None

    def verify_login(self, f):
        self.verify_user_callback = f
        return f

    def login_required(self, f=None, role=None, optional=None):
        if f is not None and \
                (role is not None or optional is not None):  # pragma: no cover
            raise ValueError(
                'role and optional are the only supported arguments')

        def login_required_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                if self.user:
                    g.flask_httpauth_user = self.user
                    return self.ensure_sync(f)(*args, **kwargs)
            return decorated

        if f:
            return login_required_internal(f)
        return login_required_internal



    def authenticate(self, _auth, stored_password=None):
        req = getattr(_auth, 'req', '')
        if self.verify_user_callback:
            return self.ensure_sync(self.verify_user_callback)(req)'''


auth = HTTPBasicAuth()
# proxy_auth = HTTPProxyAuth()


@auth.verify_password
def verify_password(username, password):
    user = ub.session.query(ub.User).filter(func.lower(ub.User.name) == username.lower()).first()
    if user:
        if user.name.lower() == "guest":
            if config.config_anonbrowse == 1:
                return user
        if config.config_login_type == constants.LOGIN_LDAP and services.ldap:
            login_result, error = services.ldap.bind_user(user.name, password)
            if login_result:
                [limiter.limiter.storage.clear(k.key) for k in limiter.current_limits]
                return user
            if error is not None:
                log.error(error)
        elif check_password_hash(str(user.password), password):
            [limiter.limiter.storage.clear(k.key) for k in limiter.current_limits]
            return user
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    log.warning('OPDS Login failed for user "%s" IP-address: %s', username, ip_address)
    return None


def requires_basic_auth_if_no_ano(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        authorisation = auth.get_auth()
        status = None
        user = None
        if config.config_allow_reverse_proxy_header_login and not authorisation:
            user = load_user_from_reverse_proxy_header(request)
        if config.config_anonbrowse == 1 and not authorisation:
            authorisation = Authorization(
                b"Basic", {'username': "Guest", 'password': ""})
        if not user:
            user = auth.authenticate(authorisation, "")
        if user in (False, None):
            status = 401
        if status:
            try:
                return auth.auth_error_callback(status)
            except TypeError:
                return auth.auth_error_callback()
        g.flask_httpauth_user = user if user is not True \
            else auth.username if auth else None
        return auth.ensure_sync(f)(*args, **kwargs)
    return decorated


def login_required_if_no_ano(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if config.config_allow_reverse_proxy_header_login:
            user = load_user_from_reverse_proxy_header(request)
            if user:
                g.flask_httpauth_user = user
                return func(*args, **kwargs)
                # proxy_auth.set_user(user)
                # return proxy_auth.login_required(func)(*args, **kwargs)
            g.flask_httpauth_user = None
        if config.config_anonbrowse == 1:
            return func(*args, **kwargs)
        return login_required(func)(*args, **kwargs)

    return decorated_view


def user_login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if config.config_allow_reverse_proxy_header_login:
            user = load_user_from_reverse_proxy_header(request)
            if user:
                g.flask_httpauth_user = user
                return func(*args, **kwargs)
            g.flask_httpauth_user = None
        return login_required(func)(*args, **kwargs)

    return decorated_view


def load_user_from_reverse_proxy_header(req):
    rp_header_name = config.config_reverse_proxy_login_header_name
    if rp_header_name:
        rp_header_username = req.headers.get(rp_header_name)
        if rp_header_username:
            user = ub.session.query(ub.User).filter(func.lower(ub.User.name) == rp_header_username.lower()).first()
            if user:
                [limiter.limiter.storage.clear(k.key) for k in limiter.current_limits]
                return user
    return None


@lm.user_loader
def load_user(user_id, random, session_key):
    user = ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()
    entry = ub.session.query(ub.User_Sessions).filter(ub.User_Sessions.random == random,
                                                       ub.User_Sessions.session_key == session_key).first()
    if entry and entry.id == user.id:
        return user
    else:
        return None

