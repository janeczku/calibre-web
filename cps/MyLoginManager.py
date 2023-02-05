# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, cervinko, jkrehm, bodybybuddha, ok11,
#                            andy29485, idalin, Kyosfonica, wuqi, Kennyl, lemmsh,
#                            falgh1, grunjol, csitko, ytils, xybydy, trasba, vrabe,
#                            ruben-herold, marblepebble, JackED42, SiphonSquirrel,
#                            apetresc, nanu-c, mutschler, GammaC0de, vuolter
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


from flask_login import LoginManager, confirm_login
from flask import session, current_app
from flask_login.utils import decode_cookie
from flask_login.signals import user_loaded_from_cookie

class MyLoginManager(LoginManager):
    def _session_protection_failed(self):
        _session = session._get_current_object()
        ident = self._session_identifier_generator()
        if(_session and not (len(_session) == 1
                             and _session.get('csrf_token', None))) and ident != _session.get('_id', None):
            return super(). _session_protection_failed()
        return False

    def _load_user_from_remember_cookie(self, cookie):
        user_id = decode_cookie(cookie)
        if user_id is not None:
            session["_user_id"] = user_id
            session["_fresh"] = False
            user = None
            if self._user_callback:
                user = self._user_callback(user_id)
            if user is not None:
                app = current_app._get_current_object()
                user_loaded_from_cookie.send(app, user=user)
                # if session was restored from remember me cookie make login valid
                confirm_login()
                return user
        return None
