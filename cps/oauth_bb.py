# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, cervinko, jkrehm, bodybybuddha, ok11,
#                            andy29485, idalin, Kyosfonica, wuqi, Kennyl, lemmsh,
#                            falgh1, grunjol, csitko, ytils, xybydy, trasba, vrabe,
#                            ruben-herold, marblepebble, JackED42, SiphonSquirrel,
#                            apetresc, nanu-c, mutschler, pwr
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
#  along with this program. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function, unicode_literals

from . import services


oauth = None


if services.oauth:
    from flask import Blueprint, flash, redirect, url_for, abort, request, current_app
    from flask_babel import gettext as _
    from flask_login import current_user, login_user, login_required

    from . import logger, ub

    oauth = Blueprint('oauth', __name__)
    log = logger.create()


    # called by flask-dance on successful authorization, provides the token
    def authorized_handler(blueprint, token):
        provider = services.oauth.providers.get(blueprint.name)
        assert provider, "authorized %s: no provider found" % blueprint.name

        # log.debug("authorized %s: %s token %s", provider.id, current_user, token)
        if not token:
            flash(_(u"Failed to log in with %s." % provider.name), category="error")
            return False

        account_id = provider.get_account_id()
        if not account_id:
            flash(_(u"Failed to fetch user info from %s." % provider.name), category="error")
            return False

        result = provider.confirm_token(account_id, token)
        # log.debug("authorized %s: %s updated token => %s", provider.id, current_user, result)
        if not result:
            log.warning("auhorized %s: %s failed to update token", provider.id, current_user)
            return False

        provider.set_session_error(False)  # clear eventual error stored in the session
        if hasattr(result, 'nickname'):  # type: ub.User
            if current_user.is_authenticated:
                # log.debug("authorized %s: current_user %s", blueprint.name, current_user)
                assert current_user.id == result.id
            else:
                log.info("authorized %s: logging in %s", blueprint.name, result)
                login_user(result)

        # Disable Flask-Dance's default behavior for saving the OAuth token
        return True


    # called by flask-dance on receiving an error from the OAuth provider
    def error_handler(blueprint, error, error_description=None, error_uri=None):
        provider = services.oauth.providers.get(blueprint.name)
        assert provider, "error %s: no provider found" % blueprint.name

        log.debug("%s: %s %r", blueprint.name, request.path, request.args)
        log.error("%s: %r", blueprint.name, error)

        flash_text = None
        if isinstance(error, ValueError):
            if error.args[0] == "Cannot set OAuth token without an associated user":
                # flash("%s authorization successful." % provider.name, category="info")
                flash_text = "No associated local user found."

        if not flash_text:
            flash_text = (
                u"OAuth error from {name}! "
                u"{error} description={description} uri={uri}"
            ).format(
                name=provider.name,
                error=error,
                description=error_description,
                uri=error_uri,
            )
        # ToDo: Translate
        flash(flash_text, category="error")
        provider.set_session_error(True)


    def login(provider, success_view_name='web.index', failed_view_name='web.login'):
        if provider.has_session_error():
            log.debug("login %s: %s has error", provider.id, current_user)
            # account authorized, but not linked?
            return redirect(url_for(failed_view_name))

        authorized = provider.is_authorized()
        # log.debug("login %s: %s authorized=%s", provider.id, current_user, authorized)
        if not authorized:
            return redirect(url_for('%s.login' % provider.id))

        # this should have already been cached by authorized_handler
        account_id = provider.get_account_id()
        if not account_id:
            flash(_(u"%s Oauth error, please retry later." % provider.name), category="error")
            return redirect(url_for(failed_view_name))

        assert current_user.is_authenticated, "(%s) login successful, no user?" % provider.id

        result = provider.confirm_user(account_id, current_user)
        # log.debug("login %s: %s updated token => %s", provider.id, current_user, result)
        if not result:
            return redirect(url_for(failed_view_name))

        provider.set_session_error(False)
        return redirect(url_for(success_view_name))


    @oauth.route('/oauth/<provider_id>/link', methods=['GET', 'POST'])
    @login_required
    def link_provider(provider_id):
        # log.debug("link_provider %s: %s", provider_id, current_user)
        provider = services.oauth.providers.get(provider_id)
        if not provider:
            return abort(404)

        authorized = provider.is_authorized()
        if authorized:
            log.warning("link_provider %s: %s already authorized", provider.id, current_user)
            return redirect(url_for('web.profile'))

        # log.debug("link_provider %s: not authorized %s, redirecting to service", provider_id, current_user)
        # TODO find some way to return to web.profile on succeess? right now in oauth lands on web.index
        return redirect(url_for('%s.login' % provider.id))


    @oauth.route('/oauth/<provider_id>/unlink', methods=['GET', 'POST'])
    @login_required
    def unlink_provider(provider_id):
        # log.debug("unlink_provider %s: %s", provider_id, current_user)
        provider = services.oauth.providers.get(provider_id)
        if not provider:
            return abort(404)

        result = provider.unlink(current_user)
        # if result is None:
        #     flash(_(u"Not linked to %(oauth)s.", oauth=provider.name), category="error")
        if result:
            flash(_(u"Unlink to %(oauth)s success.", oauth=provider.name), category="success")
        else:
            flash(_(u"Unlink to %(oauth)s failed.", oauth=provider.name), category="error")
        return redirect(url_for('web.profile'))


    @oauth.route('/oauth/<provider_id>/webhook', methods=['GET', 'POST'])
    def oauth_webhook(provider_id):
        log.debug("oauth_webhook %s: %r", provider_id, request.args)
        return ''


    def _deprecated_callback(provider):
        log.warning(">>> %s has been deprecated", request.path)
        log.warning(">>> please update your %s configuration", provider.name)
        log.warning(">>> the recommended path is %s", url_for(provider.id + '.login'))
        return login(provider)


    def _configure_blueprints():
        for provider in services.oauth.providers.values():
            oap = ub.session.query(ub.OAuthProvider).filter_by(provider_name=provider.id).first()
            if not oap:
                oap = ub.OAuthProvider(provider_name=provider.id)
                ub.session.add(oap)
                ub.session.commit()
            if oap.active:
                provider.set_credentials(oap.oauth_client_id, oap.oauth_client_secret)

            # flask-dance callback endpoints
            current_app.register_blueprint(provider.blueprint, url_prefix='/oauth')
            # login page endpoints
            oauth.add_url_rule('/login/%s' % provider.id, '%s_login' % provider.id, lambda p=provider: login(p))
            # deprecated oauth callbacks
            oauth.add_url_rule('/%s' % provider.id, provider.id, lambda p=provider: _deprecated_callback(p))


    services.oauth.init_storage(ub.OAuth, ub.session, user=current_user)
    services.oauth.init_providers('oauth.{provider}_login', authorized_handler, error_handler)
    _configure_blueprints()
    current_app.register_blueprint(oauth)
