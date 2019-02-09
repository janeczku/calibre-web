#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 Krakinou
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

import ldap
from cps import ub, app, request
from flask import flash, url_for
from redirect import redirect_back
from flask_login import login_user
from flask_babel import gettext as _

def login(form, user):
    try:
        ub.User.try_login(form['username'], form['password'])
        login_user(user, remember=True)
        flash(_(u"you are now logged in as: '%(nickname)s'", nickname=user.nickname), category="success")
        return redirect_back(url_for("web.index"))
    except ldap.INVALID_CREDENTIALS:
        ipAdress = request.headers.get('X-Forwarded-For', request.remote_addr)
        app.logger.info('LDAP Login failed for user "' + form['username'] + '" IP-adress: ' + ipAdress)
        flash(_(u"Wrong Username or Password"), category="error")

def logout():
    pass
