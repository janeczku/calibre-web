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

import json
from datetime import datetime
from functools import wraps

from flask import Blueprint, request, make_response, abort, url_for, flash, redirect
from .cw_login import login_user, current_user
from flask_babel import gettext as _
from sqlalchemy.sql.expression import true

from . import config, logger, ub
from .render_template import render_title_template
from .usermanagement import user_login_required


remotelogin = Blueprint('remotelogin', __name__)
log = logger.create()


def remote_login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if config.config_remote_login:
            return f(*args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {'status': 'error', 'message': 'Forbidden'}
            response = make_response(json.dumps(data, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return response, 403
        abort(403)

    return inner

@remotelogin.route('/remote/login')
@remote_login_required
def remote_login():
    auth_token = ub.RemoteAuthToken()
    ub.session.add(auth_token)
    ub.session_commit()
    verify_url = url_for('remotelogin.verify_token', token=auth_token.auth_token, _external=true)
    log.debug("Remot Login request with token: %s", auth_token.auth_token)
    return render_title_template('remote_login.html', title=_("Login"), token=auth_token.auth_token,
                                 verify_url=verify_url, page="remotelogin")


@remotelogin.route('/verify/<token>')
@remote_login_required
@user_login_required
def verify_token(token):
    auth_token = ub.session.query(ub.RemoteAuthToken).filter(ub.RemoteAuthToken.auth_token == token).first()

    # Token not found
    if auth_token is None:
        flash(_("Token not found"), category="error")
        log.error("Remote Login token not found")
        return redirect(url_for('web.index'))

    # Token expired
    elif datetime.now() > auth_token.expiration:
        ub.session.delete(auth_token)
        ub.session_commit()

        flash(_("Token has expired"), category="error")
        log.error("Remote Login token expired")
        return redirect(url_for('web.index'))

    # Update token with user information
    auth_token.user_id = current_user.id
    auth_token.verified = True
    ub.session_commit()

    flash(_("Success! Please return to your device"), category="success")
    log.debug("Remote Login token for userid %s verified", auth_token.user_id)
    return redirect(url_for('web.index'))


@remotelogin.route('/ajax/verify_token', methods=['POST'])
@remote_login_required
def token_verified():
    token = request.form['token']
    auth_token = ub.session.query(ub.RemoteAuthToken).filter(ub.RemoteAuthToken.auth_token == token).first()

    data = {}

    # Token not found
    if auth_token is None:
        data['status'] = 'error'
        data['message'] = _("Token not found")

    # Token expired
    elif datetime.now() > auth_token.expiration:
        ub.session.delete(auth_token)
        ub.session_commit()

        data['status'] = 'error'
        data['message'] = _("Token has expired")

    elif not auth_token.verified:
        data['status'] = 'not_verified'

    else:
        user = ub.session.query(ub.User).filter(ub.User.id == auth_token.user_id).first()
        login_user(user)

        ub.session.delete(auth_token)
        ub.session_commit("User {} logged in via remotelogin, token deleted".format(user.name))

        data['status'] = 'success'
        log.debug("Remote Login for userid %s succeeded", user.id)
        flash(_("Success! You are now logged in as: %(nickname)s", nickname=user.name), category="success")

    response = make_response(json.dumps(data, ensure_ascii=False))
    response.headers["Content-Type"] = "application/json; charset=utf-8"

    return response
