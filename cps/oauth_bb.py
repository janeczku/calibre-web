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
#  along with this program. If not, see <http://www.gnu.org/licenses/>

from __future__ import division, print_function, unicode_literals
import json
from functools import wraps

from flask import session, request, make_response, abort
from flask import Blueprint, flash, redirect, url_for
from flask_babel import gettext as _
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import login_user, current_user
from sqlalchemy.orm.exc import NoResultFound

from . import constants, logger, config, app, ub
from .web import login_required
from .oauth import OAuthBackend, backend_resultcode


oauth_check = {}
oauth = Blueprint('oauth', __name__)
log = logger.create()


def oauth_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if config.config_login_type == constants.LOGIN_OAUTH:
            return f(*args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {'status': 'error', 'message': 'Not Found'}
            response = make_response(json.dumps(data, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            return response, 404
        abort(404)

    return inner


def register_oauth_blueprint(cid, show_name):
    oauth_check[cid] = show_name


def register_user_with_oauth(user=None):
    all_oauth = {}
    for oauth_key in oauth_check.keys():
        if str(oauth_key) + '_oauth_user_id' in session and session[str(oauth_key) + '_oauth_user_id'] != '':
            all_oauth[oauth_key] = oauth_check[oauth_key]
    if len(all_oauth.keys()) == 0:
        return
    if user is None:
        flash(_(u"Register with %(provider)s", provider=", ".join(list(all_oauth.values()))), category="success")
    else:
        for oauth_key in all_oauth.keys():
            # Find this OAuth token in the database, or create it
            query = ub.session.query(ub.OAuth).filter_by(
                provider=oauth_key,
                provider_user_id=session[str(oauth_key) + "_oauth_user_id"],
            )
            try:
                oauth_key = query.one()
                oauth_key.user_id = user.id
            except NoResultFound:
                # no found, return error
                return
            try:
                ub.session.commit()
            except Exception as e:
                log.exception(e)
                ub.session.rollback()


def logout_oauth_user():
    for oauth_key in oauth_check.keys():
        if str(oauth_key) + '_oauth_user_id' in session:
            session.pop(str(oauth_key) + '_oauth_user_id')


if ub.oauth_support:
    oauthblueprints = []
    if not ub.session.query(ub.OAuthProvider).count():
        oauthProvider = ub.OAuthProvider()
        oauthProvider.provider_name = "github"
        oauthProvider.active = False
        ub.session.add(oauthProvider)
        ub.session.commit()
        oauthProvider = ub.OAuthProvider()
        oauthProvider.provider_name = "google"
        oauthProvider.active = False
        ub.session.add(oauthProvider)
        ub.session.commit()

    oauth_ids = ub.session.query(ub.OAuthProvider).all()
    ele1 = dict(provider_name='github',
                id=oauth_ids[0].id,
                active=oauth_ids[0].active,
                oauth_client_id=oauth_ids[0].oauth_client_id,
                scope=None,
                oauth_client_secret=oauth_ids[0].oauth_client_secret,
                obtain_link='https://github.com/settings/developers')
    ele2 = dict(provider_name='google',
                id=oauth_ids[1].id,
                active=oauth_ids[1].active,
                scope=["https://www.googleapis.com/auth/plus.me", "https://www.googleapis.com/auth/userinfo.email"],
                oauth_client_id=oauth_ids[1].oauth_client_id,
                oauth_client_secret=oauth_ids[1].oauth_client_secret,
                obtain_link='https://github.com/settings/developers')
    oauthblueprints.append(ele1)
    oauthblueprints.append(ele2)

    for element in oauthblueprints:
        if element['provider_name'] == 'github':
            blueprint_func = make_github_blueprint
        else:
            blueprint_func = make_google_blueprint
        blueprint = blueprint_func(
            client_id=element['oauth_client_id'],
            client_secret=element['oauth_client_secret'],
            redirect_to="oauth."+element['provider_name']+"_login",
            scope=element['scope']
        )
        element['blueprint'] = blueprint
        element['blueprint'].backend = OAuthBackend(ub.OAuth, ub.session, str(element['id']),
                                                    user=current_user, user_required=True)
        app.register_blueprint(blueprint, url_prefix="/login")
        if element['active']:
            register_oauth_blueprint(element['id'], element['provider_name'])


    @oauth_authorized.connect_via(oauthblueprints[0]['blueprint'])
    def github_logged_in(blueprint, token):
        if not token:
            flash(_(u"Failed to log in with GitHub."), category="error")
            return False

        resp = blueprint.session.get("/user")
        if not resp.ok:
            flash(_(u"Failed to fetch user info from GitHub."), category="error")
            return False

        github_info = resp.json()
        github_user_id = str(github_info["id"])
        return oauth_update_token(str(oauthblueprints[0]['id']), token, github_user_id)


    @oauth_authorized.connect_via(oauthblueprints[1]['blueprint'])
    def google_logged_in(blueprint, token):
        if not token:
            flash(_(u"Failed to log in with Google."), category="error")
            return False

        resp = blueprint.session.get("/oauth2/v2/userinfo")
        if not resp.ok:
            flash(_(u"Failed to fetch user info from Google."), category="error")
            return False

        google_info = resp.json()
        google_user_id = str(google_info["id"])
        return oauth_update_token(str(oauthblueprints[1]['id']), token, google_user_id)


    def oauth_update_token(provider_id, token, provider_user_id):
        session[provider_id + "_oauth_user_id"] = provider_user_id
        session[provider_id + "_oauth_token"] = token

        # Find this OAuth token in the database, or create it
        query = ub.session.query(ub.OAuth).filter_by(
            provider=provider_id,
            provider_user_id=provider_user_id,
        )
        try:
            oauth_entry = query.one()
            # update token
            oauth_entry.token = token
        except NoResultFound:
            oauth_entry = ub.OAuth(
                provider=provider_id,
                provider_user_id=provider_user_id,
                token=token,
            )
        try:
            ub.session.add(oauth_entry)
            ub.session.commit()
        except Exception as e:
            log.exception(e)
            ub.session.rollback()

        # Disable Flask-Dance's default behavior for saving the OAuth token
        # Value differrs depending on flask-dance version
        return backend_resultcode


    def bind_oauth_or_register(provider_id, provider_user_id, redirect_url, provider_name):
        query = ub.session.query(ub.OAuth).filter_by(
            provider=provider_id,
            provider_user_id=provider_user_id,
        )
        try:
            oauth_entry = query.first()
            # already bind with user, just login
            if oauth_entry.user:
                login_user(oauth_entry.user)
                log.debug(u"You are now logged in as: '%s'", oauth_entry.user.nickname)
                flash(_(u"you are now logged in as: '%(nickname)s'", nickname= oauth_entry.user.nickname),
                      category="success")
                return redirect(url_for('web.index'))
            else:
                # bind to current user
                if current_user and current_user.is_authenticated:
                    oauth_entry.user = current_user
                    try:
                        ub.session.add(oauth_entry)
                        ub.session.commit()
                        flash(_(u"Link to %(oauth)s Succeeded", oauth=provider_name), category="success")
                        return redirect(url_for('web.profile'))
                    except Exception as e:
                        log.exception(e)
                        ub.session.rollback()
                else:
                    flash(_(u"Login failed, No User Linked With OAuth Account"), category="error")
                log.info('Login failed, No User Linked With OAuth Account')
                return redirect(url_for('web.login'))
                # return redirect(url_for('web.login'))
                # if config.config_public_reg:
                #   return redirect(url_for('web.register'))
                # else:
                #    flash(_(u"Public registration is not enabled"), category="error")
                #    return redirect(url_for(redirect_url))
        except (NoResultFound, AttributeError):
            return redirect(url_for(redirect_url))


    def get_oauth_status():
        status = []
        query = ub.session.query(ub.OAuth).filter_by(
            user_id=current_user.id,
        )
        try:
            oauths = query.all()
            for oauth_entry in oauths:
                status.append(int(oauth_entry.provider))
            return status
        except NoResultFound:
            return None


    def unlink_oauth(provider):
        if request.host_url + 'me' != request.referrer:
            pass
        query = ub.session.query(ub.OAuth).filter_by(
            provider=provider,
            user_id=current_user.id,
        )
        try:
            oauth_entry = query.one()
            if current_user and current_user.is_authenticated:
                oauth_entry.user = current_user
                try:
                    ub.session.delete(oauth_entry)
                    ub.session.commit()
                    logout_oauth_user()
                    flash(_(u"Unlink to %(oauth)s Succeeded", oauth=oauth_check[provider]), category="success")
                except Exception as e:
                    log.exception(e)
                    ub.session.rollback()
                    flash(_(u"Unlink to %(oauth)s Failed", oauth=oauth_check[provider]), category="error")
        except NoResultFound:
            log.warning("oauth %s for user %d not found", provider, current_user.id)
            flash(_(u"Not Linked to %(oauth)s.", oauth=oauth_check[provider]), category="error")
        return redirect(url_for('web.profile'))


    # notify on OAuth provider error
    @oauth_error.connect_via(oauthblueprints[0]['blueprint'])
    def github_error(blueprint, error, error_description=None, error_uri=None):
        msg = (
            u"OAuth error from {name}! "
            u"error={error} description={description} uri={uri}"
        ).format(
            name=blueprint.name,
            error=error,
            description=error_description,
            uri=error_uri,
        )  # ToDo: Translate
        flash(msg, category="error")


    @oauth.route('/link/github')
    @oauth_required
    def github_login():
        if not github.authorized:
            return redirect(url_for('github.login'))
        account_info = github.get('/user')
        if account_info.ok:
            account_info_json = account_info.json()
            return bind_oauth_or_register(oauthblueprints[0]['id'], account_info_json['id'], 'github.login', 'github')
        flash(_(u"GitHub Oauth error, please retry later."), category="error")
        return redirect(url_for('web.login'))


    @oauth.route('/unlink/github', methods=["GET"])
    @login_required
    def github_login_unlink():
        return unlink_oauth(oauthblueprints[0]['id'])


    @oauth.route('/link/google')
    @oauth_required
    def google_login():
        if not google.authorized:
            return redirect(url_for("google.login"))
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            account_info_json = resp.json()
            return bind_oauth_or_register(oauthblueprints[1]['id'], account_info_json['id'], 'google.login', 'google')
        flash(_(u"Google Oauth error, please retry later."), category="error")
        return redirect(url_for('web.login'))


    @oauth_error.connect_via(oauthblueprints[1]['blueprint'])
    def google_error(blueprint, error, error_description=None, error_uri=None):
        msg = (
            u"OAuth error from {name}! "
            u"error={error} description={description} uri={uri}"
        ).format(
            name=blueprint.name,
            error=error,
            description=error_description,
            uri=error_uri,
        )  # ToDo: Translate
        flash(msg, category="error")


    @oauth.route('/unlink/google', methods=["GET"])
    @login_required
    def google_login_unlink():
        return unlink_oauth(oauthblueprints[1]['blueprint'].name)
