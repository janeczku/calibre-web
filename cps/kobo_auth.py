#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 shavitmichael, OzzieIsaacs
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


"""This module is used to control authentication/authorization of Kobo sync requests.
This module also includes research notes into the auth protocol used by Kobo devices.

Log-in:
When first booting a Kobo device the user must sign into a Kobo (or affiliate) account.
Upon successful sign-in, the user is redirected to
    https://auth.kobobooks.com/CrossDomainSignIn?id=<some id>
which serves the following response:
    <script type='text/javascript'>
        location.href='kobo://UserAuthenticated?userId=<redacted>&userKey<redacted>&email=<redacted>&returnUrl=https%3a%2f%2fwww.kobo.com';
    </script>
And triggers the insertion of a userKey into the device's User table.

Together, the device's DeviceId and UserKey act as an *irrevocable* authentication
token to most (if not all) Kobo APIs. In fact, in most cases only the UserKey is
required to authorize the API call.

Changing Kobo password *does not* invalidate user keys! This is apparently a known
issue for a few years now https://www.mobileread.com/forums/showpost.php?p=3476851&postcount=13
(although this poster hypothesised that Kobo could blacklist a DeviceId, many endpoints
will still grant access given the userkey.)

Official Kobo Store Api authorization:
* For most of the endpoints we care about (sync, metadata, tags, etc), the userKey is
passed in the x-kobo-userkey header, and is sufficient to authorize the API call.
* Some endpoints (e.g: AnnotationService) instead make use of Bearer tokens pass through
an authorization header. To get a BearerToken, the device makes a POST request to the
v1/auth/device endpoint with the secret UserKey and the device's DeviceId.
* The book download endpoint passes an auth token as a URL param instead of a header.

Our implementation:
We pretty much ignore all of the above. To authenticate the user, we generate a random
and unique token that they append to the CalibreWeb Url when setting up the api_store
setting on the device.
Thus, every request from the device to the api_store will hit CalibreWeb with the
auth_token in the url (e.g: https://mylibrary.com/<auth_token>/v1/library/sync).
In addition, once authenticated we also set the login cookie on the response that will
be sent back for the duration of the session to authorize subsequent API calls (in
particular calls to non-Kobo specific endpoints such as the CalibreWeb book download).
"""

from binascii import hexlify
from datetime import datetime
from os import urandom
from functools import wraps

from flask import g, Blueprint, abort, request
from .cw_login import login_user, current_user
from flask_babel import gettext as _
from flask_limiter import RateLimitExceeded

from . import logger, config, calibre_db, db, helper, ub, lm, limiter
from .render_template import render_title_template
from .usermanagement import user_login_required


log = logger.create()

kobo_auth = Blueprint("kobo_auth", __name__, url_prefix="/kobo_auth")


@kobo_auth.route("/generate_auth_token/<int:user_id>")
@user_login_required
def generate_auth_token(user_id):
    warning = False
    host_list = request.host.rsplit(':')
    if len(host_list) == 1:
        host = ':'.join(host_list)
    else:
        host = ':'.join(host_list[0:-1])
    if host.startswith('127.') or host.lower() == 'localhost' or host.startswith('[::ffff:7f') or host == "[::1]":
        warning = _('Please access Calibre-Web from non localhost to get valid api_endpoint for kobo device')

    # Generate auth token if none is existing for this user
    auth_token = ub.session.query(ub.RemoteAuthToken).filter(
        ub.RemoteAuthToken.user_id == user_id
    ).filter(ub.RemoteAuthToken.token_type==1).first()

    if not auth_token:
        auth_token = ub.RemoteAuthToken()
        auth_token.user_id = user_id
        auth_token.expiration = datetime.max
        auth_token.auth_token = (hexlify(urandom(16))).decode("utf-8")
        auth_token.token_type = 1

        ub.session.add(auth_token)
        ub.session_commit()

    books = calibre_db.session.query(db.Books).join(db.Data).all()

    for book in books:
        formats = [data.format for data in book.data]
        if 'KEPUB' not in formats and config.config_kepubifypath and 'EPUB' in formats:
            helper.convert_book_format(book.id, config.config_calibre_dir, 'EPUB', 'KEPUB', current_user.name)

    return render_title_template(
        "generate_kobo_auth_url.html",
        title=_("Kobo Setup"),
        auth_token=auth_token.auth_token,
        warning=warning
    )


@kobo_auth.route("/deleteauthtoken/<int:user_id>", methods=["POST"])
@user_login_required
def delete_auth_token(user_id):
    # Invalidate any previously generated Kobo Auth token for this user
    ub.session.query(ub.RemoteAuthToken).filter(ub.RemoteAuthToken.user_id == user_id)\
        .filter(ub.RemoteAuthToken.token_type==1).delete()

    return ub.session_commit()


def disable_failed_auth_redirect_for_blueprint(bp):
    lm.blueprint_login_views[bp.name] = None


def get_auth_token():
    if "auth_token" in g:
        return g.get("auth_token")
    else:
        return None


def register_url_value_preprocessor(kobo):
    @kobo.url_value_preprocessor
    # pylint: disable=unused-variable
    def pop_auth_token(__, values):
        g.auth_token = values.pop("auth_token")


def requires_kobo_auth(f):
    @wraps(f)
    def inner(*args, **kwargs):
        auth_token = get_auth_token()
        if auth_token is not None:
            try:
                limiter.check()
            except RateLimitExceeded:
                return abort(429)
            except (ConnectionError, Exception) as e:
                log.error("Connection error to limiter backend: %s", e)
                return abort(429)
            user = (
                ub.session.query(ub.User)
                .join(ub.RemoteAuthToken)
                .filter(ub.RemoteAuthToken.auth_token == auth_token).filter(ub.RemoteAuthToken.token_type==1)
                .first()
            )
            if user is not None:
                login_user(user)
                [limiter.limiter.storage.clear(k.key) for k in limiter.current_limits]
                return f(*args, **kwargs)
        log.debug("Received Kobo request without a recognizable auth token.")
        return abort(401)
    return inner
