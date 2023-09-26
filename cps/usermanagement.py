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
from werkzeug.security import check_password_hash
from flask_login import login_required, login_user
from flask import request, Response

from . import lm, ub, config, constants, services, logger, limiter

from .helper import generate_random_password, generate_password_hash, check_email

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
        if not auth or auth.type != 'basic':
            if config.config_anonbrowse != 1:
                user = load_user_from_reverse_proxy_header(request)
                if user:
                    return f(*args, **kwargs)
                return _authenticate()
            else:
                return f(*args, **kwargs)
        if config.config_login_type == constants.LOGIN_LDAP and services.ldap:
            login_result, error = services.ldap.bind_user(auth.username, auth.password)
            if login_result:
                user = _fetch_user_by_name(auth.username)
                [limiter.limiter.storage.clear(k.key) for k in limiter.current_limits]
                login_user(user)
                return f(*args, **kwargs)
            elif login_result is not None:
                log.error(error)
                return _authenticate()
        user = _load_user_from_auth_header(auth.username, auth.password)
        if not user:
            return _authenticate()
        return f(*args, **kwargs)
    return decorated


def _load_user_from_auth_header(username, password):
    limiter.check()
    user = _fetch_user_by_name(username)
    if bool(user and check_password_hash(str(user.password), password)) and user.name != "Guest":
        [limiter.limiter.storage.clear(k.key) for k in limiter.current_limits]
        login_user(user)
        return user
    else:
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        log.warning('OPDS Login failed for user "%s" IP-address: %s', username, ip_address)
        return None


def _authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def _fetch_user_by_name(username):
    return ub.session.query(ub.User).filter(func.lower(ub.User.name) == username.lower()).first()


@lm.user_loader
def load_user(user_id):
    user = ub.session.query(ub.User).filter(ub.User.id == int(user_id)).first()
    return user


@lm.request_loader
def load_user_from_reverse_proxy_header(req):
    if config.config_allow_reverse_proxy_header_login:
        rp_header_name = config.config_reverse_proxy_login_header_name
        if rp_header_name:
            rp_header_username = req.headers.get(rp_header_name)
            if rp_header_username:
                user = _fetch_user_by_name(rp_header_username)
                if not user and config.config_reverse_proxy_create_users:
                    create_user_from_reverse_proxy_header(req)
                    user = _fetch_user_by_name(rp_header_username)

                if user:
                    [limiter.limiter.storage.clear(k.key) for k in limiter.current_limits]
                    login_user(user)
                    return user
    return None


def create_user_from_reverse_proxy_header(req):
    rp_header_name = config.config_reverse_proxy_login_header_name
    username = req.headers.get(rp_header_name)

    # does the user have an email address in the headers?
    rp_email_header_name = config.config_reverse_proxy_email_header_name
    if rp_email_header_name:
        try:
            email = check_email(req.headers.get(rp_email_header_name))
        except Exception:
            log.debug('No email address found in Reverse Proxy headers')
            email = username + '@localhost'

    # generate a random password
    password = generate_random_password(config.config_password_min_length)
    pwhash = generate_password_hash(password)

    user = ub.User()
    user.name = username
    user.password = pwhash
    user.email = email
    user.default_language = config.config_default_language
    user.locale = config.config_default_locale
    user.role = config.config_default_role
    user.sidebar_view = config.config_default_show
    user.allowed_tags = config.config_allowed_tags
    user.denied_tags = config.config_denied_tags
    user.allowed_column_value = config.config_allowed_column_value
    user.denied_column_value = config.config_denied_column_value

    # save the user
    ub.session.add(user)
    try:
        ub.session.commit()
    except Exception as ex:
        log.warning("Failed to create Reverse Proxy user: %s - %s", username, ex)
        ub.session.rollback()
