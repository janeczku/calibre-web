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

import traceback

from flask import render_template, request, flash, make_response
from flask_limiter import RateLimitExceeded
from flask_babel import gettext as _
from werkzeug.exceptions import default_exceptions
try:
    from werkzeug.exceptions import FailedDependency
except ImportError:
    from werkzeug.exceptions import UnprocessableEntity as FailedDependency

from . import config, app, logger, services
from .render_template import render_title_template
from .web import render_login
from .usermanagement import auth
from cps.string_helper import strip_whitespaces

log = logger.create()

# custom error page

def error_http(error):
    headers = {'WWW-Authenticate': 'Basic realm="calibre-web"'} if error.code == 401 else {}
    return render_template('http_error.html',
                           error_code="Error {0}".format(error.code),
                           error_name=error.name,
                           issue=False,
                           goto_admin=False,
                           unconfigured=not config.db_configured,
                           instance=config.config_calibre_web_title
                           ), error.code, headers


def internal_error(error):
    if (isinstance(error.original_exception, AttributeError) and
        error.original_exception.args[0] == "'NoneType' object has no attribute 'query'"
        and error.original_exception.name == "query"):
        return render_template('http_error.html',
                               error_code="Database Error",
                               error_name='The library used is invalid or has permission errors',
                               issue=False,
                               goto_admin=True,
                               unconfigured=False,
                               error_stack="",
                               instance=config.config_calibre_web_title
                               ), 500
    return render_template('http_error.html',
                           error_code="500 Internal Server Error",
                           error_name='The server encountered an internal error and was unable to complete your '
                                      'request. There is an error in the application.',
                           issue=True,
                           goto_admin=False,
                           unconfigured=False,
                           error_stack=traceback.format_exc().split("\n"),
                           instance=config.config_calibre_web_title
                           ), 500


def init_errorhandler():
    # http error handling
    for ex in default_exceptions:
        if ex < 500:
            app.register_error_handler(ex, error_http)
        elif ex == 500:
            app.register_error_handler(ex, internal_error)

    if services.ldap:
        # Only way of catching the LDAPException upon logging in with LDAP server down
        @app.errorhandler(services.ldap.LDAPException)
        # pylint: disable=unused-variable
        def handle_exception(e):
            log.debug('LDAP server not accessible while trying to login to opds feed')
            return error_http(FailedDependency())


@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(__):
    log.error("Rate limit exceeded {}".format(request.endpoint))
    if "register" in request.endpoint:
        flash(_(u"Please wait one minute to register next user"), category="error")
        return render_title_template('register.html', config=config, title=_("Register"), page="register")
    elif "login" in request.endpoint:
        form = request.form.to_dict()
        username = strip_whitespaces(form.get('username', "")).lower().replace("\n", "").replace("\r", "")
        flash(_("Please wait one minute before next login"), category="error")
        return render_login(username, form.get("password", ""))
    elif "opds" in request.endpoint:
        return auth.auth_error_callback(429)
    else:
        return make_response('', 429)


