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
from urllib.parse import urljoin

import requests
from flask import (
    Blueprint,
    abort,
    flash,
    make_response,
    redirect,
    request,
    session,
    url_for,
)
from flask_babel import gettext as _
from flask_dance.consumer import OAuth2ConsumerBlueprint, oauth_authorized, oauth_error
from flask_dance.contrib.github import github, make_github_blueprint
from flask_dance.contrib.google import google, make_google_blueprint
from oauthlib.oauth2 import InvalidGrantError, TokenExpiredError
from sqlalchemy.orm.exc import NoResultFound

from . import app, config, constants, logger, ub
from .cw_login import current_user, login_user
from .usermanagement import user_login_required

try:
    from .oauth import OAuthBackend, backend_resultcode
except NameError:
    pass


oauth_check = {}
oauthblueprints = []
oauth = Blueprint("oauth", __name__)
log = logger.create()


def oauth_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if config.config_login_type == constants.LOGIN_OAUTH:
            return f(*args, **kwargs)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = {"status": "error", "message": "Not Found"}
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
        if (
            str(oauth_key) + "_oauth_user_id" in session
            and session[str(oauth_key) + "_oauth_user_id"] != ""
        ):
            all_oauth[oauth_key] = oauth_check[oauth_key]
    if len(all_oauth.keys()) == 0:
        return
    if user is None:
        flash(
            _(
                "Register with %(provider)s",
                provider=", ".join(list(all_oauth.values())),
            ),
            category="success",
        )
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
            ub.session_commit(
                "User {} with OAuth for provider {} registered".format(
                    user.name, oauth_key
                )
            )


def logout_oauth_user():
    for oauth_key in oauth_check.keys():
        if str(oauth_key) + "_oauth_user_id" in session:
            session.pop(str(oauth_key) + "_oauth_user_id")


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


def bind_oauth_or_register(
    provider_id, provider_user_id, redirect_url, provider_name, user_info=None
):
    query = ub.session.query(ub.OAuth).filter_by(
        provider=provider_id,
        provider_user_id=provider_user_id,
    )
    try:
        oauth_entry = query.first()
        # already bind with user, just login
        if oauth_entry and oauth_entry.user:
            login_user(oauth_entry.user)
            log.debug("You are now logged in as: '%s'", oauth_entry.user.name)
            flash(
                _(
                    "Success! You are now logged in as: %(nickname)s",
                    nickname=oauth_entry.user.name,
                ),
                category="success",
            )
            return redirect(url_for("web.index"))
        else:
            # bind to current user if logged in
            if current_user and current_user.is_authenticated:
                if oauth_entry:
                    oauth_entry.user = current_user
                else:
                    oauth_entry = ub.OAuth(
                        provider=provider_id,
                        provider_user_id=provider_user_id,
                        user=current_user,
                    )
                try:
                    ub.session.add(oauth_entry)
                    ub.session.commit()
                    flash(
                        _("Link to %(oauth)s Succeeded", oauth=provider_name),
                        category="success",
                    )
                    log.info("Link to {} Succeeded".format(provider_name))
                    return redirect(url_for("web.profile"))
                except Exception as ex:
                    log.error_or_exception(ex)
                    ub.session.rollback()
            else:
                # Check if auto-creation is enabled for this provider
                provider_config = None
                for blueprint_config in oauthblueprints:
                    if str(blueprint_config["id"]) == str(provider_id):
                        provider_config = blueprint_config
                        break

                if (
                    provider_config
                    and provider_config.get("oauth_auto_create_user", False)
                    and user_info
                ):
                    # Auto-create user
                    try:
                        new_user = ub.User()

                        # Generate username from OAuth data
                        username = (
                            user_info.get("username")
                            or user_info.get("email", "").split("@")[0]
                            or f"oauth_user_{provider_user_id}"
                        )

                        # Ensure username is unique
                        base_username = username
                        counter = 1
                        while (
                            ub.session.query(ub.User)
                            .filter(ub.User.name == username)
                            .first()
                        ):
                            username = f"{base_username}_{counter}"
                            counter += 1

                        new_user.name = username
                        new_user.email = user_info.get("email", "")
                        new_user.role = config.config_default_role
                        new_user.sidebar_view = config.config_default_show
                        new_user.locale = config.config_default_locale

                        # Add user to session
                        ub.session.add(new_user)
                        ub.session.flush()  # Get the user ID

                        # Create OAuth entry for the new user
                        if oauth_entry:
                            oauth_entry.user = new_user
                        else:
                            oauth_entry = ub.OAuth(
                                provider=provider_id,
                                provider_user_id=provider_user_id,
                                user=new_user,
                            )

                        ub.session.add(oauth_entry)
                        ub.session.commit()

                        # Log in the new user
                        login_user(new_user)
                        flash(
                            _(
                                "Welcome! Your account has been created automatically. You are now logged in as: %(nickname)s",
                                nickname=new_user.name,
                            ),
                            category="success",
                        )
                        log.info(
                            "Auto-created user {} from {} OAuth".format(
                                new_user.name, provider_name
                            )
                        )
                        return redirect(url_for("web.index"))

                    except Exception as ex:
                        log.error_or_exception(ex)
                        ub.session.rollback()
                        flash(
                            _("Failed to create user account automatically"),
                            category="error",
                        )
                        return redirect(url_for("web.login"))
                else:
                    flash(
                        _("Login failed, No User Linked With OAuth Account"),
                        category="error",
                    )
                log.info("Login failed, No User Linked With OAuth Account")
                return redirect(url_for("web.login"))
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
    if request.host_url + "me" != request.referrer:
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
                flash(
                    _("Unlink to %(oauth)s Succeeded", oauth=oauth_check[provider]),
                    category="success",
                )
                log.info("Unlink to {} Succeeded".format(oauth_check[provider]))
            except Exception as ex:
                log.error_or_exception(ex)
                ub.session.rollback()
                flash(
                    _("Unlink to %(oauth)s Failed", oauth=oauth_check[provider]),
                    category="error",
                )
    except NoResultFound:
        log.warning("oauth %s for user %d not found", provider, current_user.id)
        flash(_("Not Linked to %(oauth)s", oauth=provider), category="error")
    return redirect(url_for("web.profile"))


def get_generic_oauth_user_info(blueprint, token, provider_config):
    """
    Get user information from a generic OAuth2/OpenID Connect provider
    """
    if not token:
        return None

    # Make request to userinfo endpoint
    try:
        headers = {"Authorization": "Bearer {}".format(token["access_token"])}
        resp = requests.get(provider_config["oauth_userinfo_url"], headers=headers)

        if not resp.ok:
            log.error(
                "Failed to fetch user info from {}: {}".format(
                    provider_config["provider_name"], resp.status_code
                )
            )
            return None

        user_info = resp.json()

        # Extract user ID - try multiple common fields
        user_id = None
        for id_field in ["sub", "id", "user_id", "oid"]:
            if id_field in user_info:
                user_id = str(user_info[id_field])
                break

        if not user_id:
            log.error(
                "Could not extract user ID from {} response".format(
                    provider_config["provider_name"]
                )
            )
            return None

        return {
            "id": user_id,
            "username": user_info.get(
                provider_config["oauth_userinfo_username_field"], ""
            ),
            "email": user_info.get(provider_config["oauth_userinfo_email_field"], ""),
            "name": user_info.get("name", ""),
            "raw": user_info,
        }

    except Exception as e:
        log.error(
            "Error fetching user info from {}: {}".format(
                provider_config["provider_name"], e
            )
        )
        return None


def generate_oauth_blueprints():
    for provider in ("github", "google", "oidc"):
        existing_provider = (
            ub.session.query(ub.OAuthProvider).filter_by(provider_name=provider).first()
        )
        if not existing_provider:
            oauthProvider = ub.OAuthProvider()
            oauthProvider.provider_name = provider
            oauthProvider.active = False
            ub.session.add(oauthProvider)
            ub.session_commit("{} Blueprint Created".format(provider))

    oauth_ids = ub.session.query(ub.OAuthProvider).all()

    # Clear existing blueprints
    oauthblueprints.clear()

    for provider_config in oauth_ids:
        if provider_config.provider_name == "github":
            ele = dict(
                provider_name="github",
                id=provider_config.id,
                active=provider_config.active,
                oauth_client_id=provider_config.oauth_client_id,
                scope=None,
                oauth_client_secret=provider_config.oauth_client_secret,
                obtain_link="https://github.com/settings/developers",
            )
        elif provider_config.provider_name == "google":
            ele = dict(
                provider_name="google",
                id=provider_config.id,
                active=provider_config.active,
                scope=["https://www.googleapis.com/auth/userinfo.email"],
                oauth_client_id=provider_config.oauth_client_id,
                oauth_client_secret=provider_config.oauth_client_secret,
                obtain_link="https://console.developers.google.com/apis/credentials",
            )
        elif provider_config.provider_name == "oidc":
            ele = dict(
                provider_name="oidc",
                id=provider_config.id,
                active=provider_config.active,
                oauth_client_id=provider_config.oauth_client_id,
                oauth_client_secret=provider_config.oauth_client_secret,
                oauth_authorization_url=provider_config.oauth_authorization_url,
                oauth_token_url=provider_config.oauth_token_url,
                oauth_userinfo_url=provider_config.oauth_userinfo_url,
                oauth_scope=(
                    provider_config.oauth_scope.split(",")
                    if provider_config.oauth_scope
                    else ["openid", "profile", "email"]
                ),
                oauth_userinfo_username_field=provider_config.oauth_userinfo_username_field
                or "preferred_username",
                oauth_userinfo_email_field=provider_config.oauth_userinfo_email_field
                or "email",
                oauth_auto_create_user=provider_config.oauth_auto_create_user or False,
                obtain_link=None,
            )
        else:
            continue

        oauthblueprints.append(ele)

    for element in oauthblueprints:
        if element["provider_name"] == "github":
            blueprint_func = make_github_blueprint
            blueprint = blueprint_func(
                client_id=element["oauth_client_id"],
                client_secret=element["oauth_client_secret"],
                redirect_to="oauth." + element["provider_name"] + "_login",
                scope=element["scope"],
            )
        elif element["provider_name"] == "google":
            blueprint_func = make_google_blueprint
            blueprint = blueprint_func(
                client_id=element["oauth_client_id"],
                client_secret=element["oauth_client_secret"],
                redirect_to="oauth." + element["provider_name"] + "_login",
                scope=element["scope"],
            )
        elif element["provider_name"] == "oidc":
            # OIDC provider using generic OAuth2
            blueprint = OAuth2ConsumerBlueprint(
                element["provider_name"],
                __name__,
                client_id=element["oauth_client_id"],
                client_secret=element["oauth_client_secret"],
                base_url=(
                    element["oauth_authorization_url"].rsplit("/", 1)[0]
                    if element["oauth_authorization_url"]
                    else None
                ),
                authorization_url=element["oauth_authorization_url"],
                token_url=element["oauth_token_url"],
                redirect_to="oauth." + element["provider_name"] + "_login",
                scope=element["oauth_scope"],
            )
        else:
            continue

        element["blueprint"] = blueprint
        element["blueprint"].backend = OAuthBackend(
            ub.OAuth,
            ub.session,
            str(element["id"]),
            user=current_user,
            user_required=True,
        )
        app.register_blueprint(blueprint, url_prefix="/login")
        if element["active"]:
            register_oauth_blueprint(element["id"], element["provider_name"])
    return oauthblueprints


if ub.oauth_support:
    oauthblueprints = generate_oauth_blueprints()

    # Find providers by name
    github_blueprint = None
    google_blueprint = None
    oidc_blueprint = None

    for blueprint_config in oauthblueprints:
        if blueprint_config["provider_name"] == "github":
            github_blueprint = blueprint_config
        elif blueprint_config["provider_name"] == "google":
            google_blueprint = blueprint_config
        elif blueprint_config["provider_name"] == "oidc":
            oidc_blueprint = blueprint_config

    # GitHub handlers
    if github_blueprint:

        @oauth_authorized.connect_via(github_blueprint["blueprint"])
        def github_logged_in(blueprint, token):
            if not token:
                flash(_("Failed to log in with GitHub."), category="error")
                log.error("Failed to log in with GitHub")
                return False

            resp = blueprint.session.get("/user")
            if not resp.ok:
                flash(_("Failed to fetch user info from GitHub."), category="error")
                log.error("Failed to fetch user info from GitHub")
                return False

            github_info = resp.json()
            github_user_id = str(github_info["id"])
            return oauth_update_token(
                str(github_blueprint["id"]), token, github_user_id
            )

    # Google handlers
    if google_blueprint:

        @oauth_authorized.connect_via(google_blueprint["blueprint"])
        def google_logged_in(blueprint, token):
            if not token:
                flash(_("Failed to log in with Google."), category="error")
                log.error("Failed to log in with Google")
                return False

            resp = blueprint.session.get("/oauth2/v2/userinfo")
            if not resp.ok:
                flash(_("Failed to fetch user info from Google."), category="error")
                log.error("Failed to fetch user info from Google")
                return False

            google_info = resp.json()
            google_user_id = str(google_info["id"])
            return oauth_update_token(
                str(google_blueprint["id"]), token, google_user_id
            )

    # OIDC handlers
    if oidc_blueprint:

        @oauth_authorized.connect_via(oidc_blueprint["blueprint"])
        def oidc_logged_in(blueprint, token):
            if not token:
                flash(_("Failed to log in with OIDC."), category="error")
                log.error("Failed to log in with OIDC")
                return False

            user_info = get_generic_oauth_user_info(blueprint, token, oidc_blueprint)
            if not user_info:
                flash(_("Failed to fetch user info from OIDC."), category="error")
                log.error("Failed to fetch user info from OIDC")
                return False

            return oauth_update_token(str(oidc_blueprint["id"]), token, user_info["id"])

    # Error handlers
    if github_blueprint:

        @oauth_error.connect_via(github_blueprint["blueprint"])
        def github_error(blueprint, error, error_description=None, error_uri=None):
            msg = (
                "OAuth error from {name}! "
                "error={error} description={description} uri={uri}"
            ).format(
                name=blueprint.name,
                error=error,
                description=error_description,
                uri=error_uri,
            )  # ToDo: Translate
            flash(msg, category="error")

    if google_blueprint:

        @oauth_error.connect_via(google_blueprint["blueprint"])
        def google_error(blueprint, error, error_description=None, error_uri=None):
            msg = (
                "OAuth error from {name}! "
                "error={error} description={description} uri={uri}"
            ).format(
                name=blueprint.name,
                error=error,
                description=error_description,
                uri=error_uri,
            )  # ToDo: Translate
            flash(msg, category="error")

    if oidc_blueprint:

        @oauth_error.connect_via(oidc_blueprint["blueprint"])
        def oidc_error(blueprint, error, error_description=None, error_uri=None):
            msg = (
                "OAuth error from {name}! "
                "error={error} description={description} uri={uri}"
            ).format(
                name=blueprint.name,
                error=error,
                description=error_description,
                uri=error_uri,
            )  # ToDo: Translate
            flash(msg, category="error")


@oauth.route("/link/github")
@oauth_required
def github_login():
    if not github.authorized:
        return redirect(url_for("github.login"))
    try:
        account_info = github.get("/user")
        if account_info.ok:
            account_info_json = account_info.json()
            # Find GitHub blueprint
            github_id = None
            for blueprint_config in oauthblueprints:
                if blueprint_config["provider_name"] == "github":
                    github_id = blueprint_config["id"]
                    break
            if github_id:
                # Prepare user_info for auto-creation
                user_info = {
                    "id": str(account_info_json["id"]),
                    "username": account_info_json.get("login", ""),
                    "email": account_info_json.get("email", ""),
                    "name": account_info_json.get("name", ""),
                    "raw": account_info_json,
                }
                return bind_oauth_or_register(
                    github_id,
                    account_info_json["id"],
                    "github.login",
                    "github",
                    user_info,
                )
        flash(_("GitHub Oauth error, please retry later."), category="error")
        log.error("GitHub Oauth error, please retry later")
    except (InvalidGrantError, TokenExpiredError) as e:
        flash(_("GitHub Oauth error: {}").format(e), category="error")
        log.error(e)
    return redirect(url_for("web.login"))


@oauth.route("/unlink/github", methods=["GET"])
@user_login_required
def github_login_unlink():
    # Find GitHub blueprint
    github_id = None
    for blueprint_config in oauthblueprints:
        if blueprint_config["provider_name"] == "github":
            github_id = blueprint_config["id"]
            break
    if github_id:
        return unlink_oauth(github_id)
    return redirect(url_for("web.profile"))


@oauth.route("/link/google")
@oauth_required
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))
    try:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            account_info_json = resp.json()
            # Find Google blueprint
            google_id = None
            for blueprint_config in oauthblueprints:
                if blueprint_config["provider_name"] == "google":
                    google_id = blueprint_config["id"]
                    break
            if google_id:
                # Prepare user_info for auto-creation
                user_info = {
                    "id": account_info_json["id"],
                    "username": account_info_json.get("email", "").split("@")[0],
                    "email": account_info_json.get("email", ""),
                    "name": account_info_json.get("name", ""),
                    "raw": account_info_json,
                }
                return bind_oauth_or_register(
                    google_id,
                    account_info_json["id"],
                    "google.login",
                    "google",
                    user_info,
                )
        flash(_("Google Oauth error, please retry later."), category="error")
        log.error("Google Oauth error, please retry later")
    except (InvalidGrantError, TokenExpiredError) as e:
        flash(_("Google Oauth error: {}").format(e), category="error")
        log.error(e)
    return redirect(url_for("web.login"))


@oauth.route("/unlink/google", methods=["GET"])
@user_login_required
def google_login_unlink():
    # Find Google blueprint
    google_id = None
    for blueprint_config in oauthblueprints:
        if blueprint_config["provider_name"] == "google":
            google_id = blueprint_config["id"]
            break
    if google_id:
        return unlink_oauth(google_id)
    return redirect(url_for("web.profile"))


@oauth.route("/link/oidc")
@oauth_required
def oidc_login():
    # Find OIDC blueprint
    oidc_blueprint_config = None
    for blueprint_config in oauthblueprints:
        if blueprint_config["provider_name"] == "oidc":
            oidc_blueprint_config = blueprint_config
            break

    if not oidc_blueprint_config:
        flash(_("OIDC provider not configured."), category="error")
        return redirect(url_for("web.login"))

    blueprint = oidc_blueprint_config["blueprint"]

    # Check if we're already authorized via Flask-Dance
    if not blueprint.session.authorized or blueprint.session.token["expires_in"] < 0:
        # Not authorized yet, redirect to OAuth authorization URL
        return redirect(url_for("oidc.login"))

    try:
        # We're authorized, get user info from the userinfo endpoint
        userinfo_url = oidc_blueprint_config["oauth_userinfo_url"]
        if not userinfo_url:
            flash(_("OIDC userinfo URL not configured."), category="error")
            return redirect(url_for("web.login"))

        resp = blueprint.session.get(userinfo_url)
        if resp.ok:
            user_info_json = resp.json()

            # Extract user ID using the same logic as get_generic_oauth_user_info
            user_id = None
            for id_field in ["sub", "id", "user_id", "oid"]:
                if id_field in user_info_json:
                    user_id = str(user_info_json[id_field])
                    break

            if user_id:
                # Prepare user_info for auto-creation
                user_info = {
                    "id": user_id,
                    "username": user_info_json.get(
                        oidc_blueprint_config["oauth_userinfo_username_field"], ""
                    ),
                    "email": user_info_json.get(
                        oidc_blueprint_config["oauth_userinfo_email_field"], ""
                    ),
                    "name": user_info_json.get("name", ""),
                    "raw": user_info_json,
                }
                return bind_oauth_or_register(
                    oidc_blueprint_config["id"],
                    user_id,
                    "oidc.login",
                    "oidc",
                    user_info,
                )
            else:
                flash(
                    _("Could not extract user ID from OIDC response."), category="error"
                )
                log.error("Could not extract user ID from OIDC response")
        else:
            flash(_("Failed to fetch user info from OIDC provider."), category="error")
            log.error(
                "Failed to fetch user info from OIDC provider: {}".format(
                    resp.status_code
                )
            )
    except (InvalidGrantError, TokenExpiredError) as e:
        blueprint.session.token = None  # invalidate session
        flash(_("OIDC OAuth error: {}").format(str(e)), category="error")
        log.error(e)
    except Exception as e:
        flash(_("OIDC OAuth error, please retry later."), category="error")
        log.error("OIDC OAuth error: {}".format(str(e)))
    return redirect(url_for("web.login"))


@oauth.route("/unlink/oidc", methods=["GET"])
@user_login_required
def oidc_login_unlink():
    # Find OIDC blueprint
    oidc_id = None
    for blueprint_config in oauthblueprints:
        if blueprint_config["provider_name"] == "oidc":
            oidc_id = blueprint_config["id"]
            break
    if oidc_id:
        return unlink_oauth(oidc_id)
    return redirect(url_for("web.profile"))
