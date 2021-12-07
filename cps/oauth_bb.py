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

import json
from functools import wraps

from flask import session, request, make_response, abort
from flask import Blueprint, flash, redirect, url_for
from flask_babel import gettext as _
from flask_dance.consumer import oauth_authorized, oauth_error, OAuth2ConsumerBlueprint
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.contrib.google import make_google_blueprint, google
from oauthlib.oauth2 import TokenExpiredError, InvalidGrantError
from flask_login import login_user, current_user, login_required
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import func, and_

from . import constants, logger, config, app, ub

try:
    from .oauth import OAuthBackend, backend_resultcode
except NameError:
    pass


oauth_check = {}
oauthblueprints = []
oauth = Blueprint('oauth', __name__)
log = logger.create()
generic = None


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
            ub.session_commit("User {} with OAuth for provider {} registered".format(user.name, oauth_key))


def logout_oauth_user():
    for oauth_key in oauth_check.keys():
        if str(oauth_key) + '_oauth_user_id' in session:
            session.pop(str(oauth_key) + '_oauth_user_id')
            unlink_oauth(oauth_key)


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
    ub.session.add(oauth_entry)
    ub.session_commit()

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
            log.debug(u"You are now logged in as: '%s'", oauth_entry.user.name)
            flash(_(u"you are now logged in as: '%(nickname)s'", nickname= oauth_entry.user.name),
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
                    log.info("Link to {} Succeeded".format(provider_name))
                    return redirect(url_for('web.profile'))
                except Exception as ex:
                    log.debug_or_exception(ex)
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
                log.info("Unlink to {} Succeeded".format(oauth_check[provider]))
            except Exception as ex:
                log.debug_or_exception(ex)
                ub.session.rollback()
                flash(_(u"Unlink to %(oauth)s Failed", oauth=oauth_check[provider]), category="error")
    except NoResultFound:
        log.warning("oauth %s for user %d not found", provider, current_user.id)
        flash(_(u"Not Linked to %(oauth)s", oauth=provider), category="error")
    return redirect(url_for('web.profile'))

def generate_oauth_blueprints():
    global generic

    if not ub.session.query(ub.OAuthProvider).count():
        for provider in ("github", "google", "generic"):
            oauthProvider = ub.OAuthProvider()
            oauthProvider.provider_name = provider
            oauthProvider.active = False
            ub.session.add(oauthProvider)
            ub.session_commit("{} Blueprint Created".format(provider))

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
                scope=["https://www.googleapis.com/auth/userinfo.email"],
                oauth_client_id=oauth_ids[1].oauth_client_id,
                oauth_client_secret=oauth_ids[1].oauth_client_secret,
                obtain_link='https://console.developers.google.com/apis/credentials')
    ele3 = dict(provider_name='generic',
                id=oauth_ids[2].id,
                active=oauth_ids[2].active,
                scope=oauth_ids[2].scope,
                oauth_client_id=oauth_ids[2].oauth_client_id,
                oauth_client_secret=oauth_ids[2].oauth_client_secret,
                oauth_base_url=oauth_ids[2].oauth_base_url,
                oauth_auth_url=oauth_ids[2].oauth_auth_url,
                oauth_token_url=oauth_ids[2].oauth_token_url,
                username_mapper=oauth_ids[2].username_mapper,
                email_mapper=oauth_ids[2].email_mapper,
                login_button=oauth_ids[2].login_button)
    oauthblueprints.append(ele1)
    oauthblueprints.append(ele2)
    oauthblueprints.append(ele3)

    for element in oauthblueprints:
        if element['provider_name'] == 'github':
            blueprint_func = make_github_blueprint
        elif element['provider_name'] == 'google':
            blueprint_func = make_google_blueprint
        else:
            blueprint_func = OAuth2ConsumerBlueprint

        if element['provider_name'] in ('github', 'google'):
            blueprint = blueprint_func(
                client_id=element['oauth_client_id'],
                client_secret=element['oauth_client_secret'],
                redirect_url="oauth."+element['provider_name']+"_login",
                scope=element['scope']
            )
        else:
            base_url = element.get('oauth_base_url') or ''
            token_url = element.get('oauth_token_url') or ''
            auth_url = element.get('oauth_auth_url') or ''
            blueprint = blueprint_func(
                "generic",
                __name__,
                client_id=element['oauth_client_id'],
                client_secret=element['oauth_client_secret'],
                base_url=base_url,
                authorization_url=base_url + auth_url,
                token_url=base_url + token_url,
                redirect_to='oauth.'+element['provider_name']+'_login',
            )
            generic = blueprint
        element['blueprint'] = blueprint
        element['blueprint'].backend = OAuthBackend(ub.OAuth, ub.session, str(element['id']),
                                                    user=current_user, user_required=True)
        app.register_blueprint(blueprint, url_prefix="/login")
        if element['active']:
            register_oauth_blueprint(element['id'], element['provider_name'])
    return oauthblueprints


if ub.oauth_support:
    oauthblueprints = generate_oauth_blueprints()

    @oauth_authorized.connect_via(oauthblueprints[0]['blueprint'])
    def github_logged_in(blueprint, token):
        if not token:
            flash(_(u"Failed to log in with GitHub."), category="error")
            log.error("Failed to log in with GitHub")
            return False

        resp = blueprint.session.get("/user")
        if not resp.ok:
            flash(_(u"Failed to fetch user info from GitHub."), category="error")
            log.error("Failed to fetch user info from GitHub")
            return False

        github_info = resp.json()
        github_user_id = str(github_info["id"])
        return oauth_update_token(str(oauthblueprints[0]['id']), token, github_user_id)


    @oauth_authorized.connect_via(oauthblueprints[1]['blueprint'])
    def google_logged_in(blueprint, token):
        if not token:
            flash(_(u"Failed to log in with Google."), category="error")
            log.error("Failed to log in with Google")
            return False

        resp = blueprint.session.get("/oauth2/v2/userinfo")
        if not resp.ok:
            flash(_(u"Failed to fetch user info from Google."), category="error")
            log.error("Failed to fetch user info from Google")
            return False

        google_info = resp.json()
        google_user_id = str(google_info["id"])
        return oauth_update_token(str(oauthblueprints[1]['id']), token, google_user_id)


    @oauth_authorized.connect_via(oauthblueprints[2]['blueprint'])
    def generic_logged_in(blueprint, token):
        global generic

        if not token:
            flash(_(u"Failed to log in with generic OAuth provider."), category="error")
            log.error("Failed to log in with generic OAuth2 provider")
            return False

        resp = blueprint.session.get(blueprint.base_url + "/protocol/openid-connect/userinfo")
        if not resp.ok:
            flash(_(u"Failed to fetch user info from generic OAuth2 provider."), category="error")
            log.error("Failed to fetch user info from generic OAuth2 provider")
            return False

        username_mapper = oauthblueprints[2].get('username_mapper') or 'username'
        email_mapper = oauthblueprints[2].get('email_mapper') or 'email'

        generic_info = resp.json()
        generic_user_email = str(generic_info[email_mapper])
        generic_user_username = str(generic_info[username_mapper])

        user = (
            ub.session.query(ub.User)
            .filter(and_(func.lower(ub.User.name) == generic_user_username,
                    func.lower(ub.User.email) == generic_user_email))
        ).first()

        if user is None:
            user = ub.User()
            user.name = generic_user_username
            user.email = generic_user_email
            user.role = constants.ROLE_USER
            ub.session.add(user)
            ub.session_commit()

        result = oauth_update_token(str(oauthblueprints[2]['id']), token, user.id)

        query = ub.session.query(ub.OAuth).filter_by(
            provider=str(oauthblueprints[2]['id']),
            provider_user_id=user.id,
        )
        oauth_entry = query.first()
        oauth_entry.user = user
        ub.session_commit()

        return result


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


    @oauth_error.connect_via(oauthblueprints[2]['blueprint'])
    def generic_error(blueprint, error, error_description=None, error_uri=None):
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
    try:
        account_info = github.get('/user')
        if account_info.ok:
            account_info_json = account_info.json()
            return bind_oauth_or_register(oauthblueprints[0]['id'], account_info_json['id'], 'github.login', 'github')
        flash(_(u"GitHub Oauth error, please retry later."), category="error")
        log.error("GitHub Oauth error, please retry later")
    except (InvalidGrantError, TokenExpiredError) as e:
        flash(_(u"GitHub Oauth error: {}").format(e), category="error")
        log.error(e)
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
    try:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            account_info_json = resp.json()
            return bind_oauth_or_register(oauthblueprints[1]['id'], account_info_json['id'], 'google.login', 'google')
        flash(_(u"Google Oauth error, please retry later."), category="error")
        log.error("Google Oauth error, please retry later")
    except (InvalidGrantError, TokenExpiredError) as e:
        flash(_(u"Google Oauth error: {}").format(e), category="error")
        log.error(e)
    return redirect(url_for('web.login'))


@oauth.route('/unlink/google', methods=["GET"])
@login_required
def google_login_unlink():
    return unlink_oauth(oauthblueprints[1]['id'])


@oauth.route('/link/generic')
@oauth_required
def generic_login():
    global generic

    if not generic.session.authorized:
        return redirect(url_for("generic.login"))
    try:
        resp = generic.session.get(generic.base_url + "/protocol/openid-connect/userinfo")
        if resp.ok:
            account_info_json = resp.json()

            username_mapper = oauthblueprints[2].get('username_mapper') or 'username'
            email_mapper = oauthblueprints[2].get('email_mapper') or 'email'

            email = str(account_info_json[email_mapper])
            username = str(account_info_json[username_mapper])

            user = (
                ub.session.query(ub.User)
                .filter(and_(func.lower(ub.User.name) == username,
                        func.lower(ub.User.email) == email))
            ).first()

            return bind_oauth_or_register(oauthblueprints[2]['id'], user.id, 'generic.login', 'generic')
        flash(_(u"generic OAuth2 error, please retry later."), category="error")
        log.error("generic OAuth2 error, please retry later")
    except (InvalidGrantError, TokenExpiredError) as e:
        log.error(e)
    return redirect(url_for("generic.login"))


@oauth.route('/unlink/generic', methods=["GET"])
@login_required
def generic_login_unlink():
    return unlink_oauth(oauthblueprints[2]['id'])
