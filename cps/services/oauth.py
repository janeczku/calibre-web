# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, jim3ma, pwr
#
#  Licensed under GLPv3. See the project's LICENSE file for details.

from __future__ import division, print_function, unicode_literals

from flask import session as flask_session
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_dance.contrib.github import make_github_blueprint
from flask_dance.contrib.google import make_google_blueprint
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from .. import logger


log = logger.create()
providers = {}

_SUPPORTED = {
    'github': ('GitHub', make_github_blueprint,
               'https://github.com/settings/developers', '/user'),
    'google': ('Google', make_google_blueprint,
               'https://console.developers.google.com/apis/credentials', '/oauth2/v2/userinfo')
}


class _Provider(object):
    '''
    Wrapper over an external OAuth provider.
    Works with the current flask session to store/cache some of the state.
    '''
    def __init__(self, id_, redirect_to):
        self.id = id_

        name, make_oauth_blueprint, obtain_link, account_info_path = _SUPPORTED[id_]
        self.blueprint = make_oauth_blueprint(storage=_STORAGE)
        assert id_ == self.blueprint.name, "provider '%s' should have been named '%s'" % (id_, self.blueprint.name)
        self.blueprint.redirect_to = redirect_to

        self.name = name
        self.redirect_to = redirect_to
        self.obtain_link = obtain_link
        self.account_info_path = account_info_path
        self.client_id = ''
        self.client_secret = ''
        self.active = False
        # log.debug("created provider %s (%s)", self.id, self.name)

    def set_credentials(self, client_id, client_secret):
        # log.debug("%s: discarding credentials %s/%s", self.id, self.blueprint._client_id, self.blueprint.client_secret)
        self.client_id = client_id or ''
        self.client_secret = client_secret or ''
        self.active = bool(self.client_id) and bool(self.client_secret)
        self.blueprint._client_id = self.client_id or None
        self.blueprint.client_secret = self.client_secret or None
        self.blueprint.teardown_session()

    def is_authorized(self):
        '''
        Checks if the current flask session has an authorization from the OAuth provider.
        '''
        try:
            return self.blueprint.session.authorized
        except ValueError:
            return False

    def confirm_token(self, provider_user_id, token):
        # log.debug("confirm_token %s: pid=%s token=%s", self.id, provider_user_id, bool(token))
        oauth = _STORAGE.find_oauth(self.id, provider_user_id)
        if not oauth:
            return False

        if not _STORAGE.update_oauth(oauth, provider_user_id, token=token):
            return False

        flask_session[self.id + '_oauth_user_id'] = provider_user_id
        flask_session[self.id + '_oauth_token'] = token

        if oauth.user:
            return oauth.user
        return True

    def confirm_user(self, provider_user_id, user):
        # log.debug("confirm_user %s: pid=%s user=%s", self.id, provider_user_id, user)
        oauth = _STORAGE.find_oauth(self.id, provider_user_id, user=user)
        if not oauth:
            return False

        if not _STORAGE.update_oauth(oauth, provider_user_id, user=user):
            return False

        flask_session[self.id + '_oauth_user_id'] = provider_user_id
        flask_session[self.id + '_oauth_token'] = oauth.token
        return True

    def has_token_for(self, user):
        '''
        Does the given user have a valid token.
        '''
        return bool(_STORAGE.get(self.blueprint, user_id=user.id))

    def get_account_id(self):
        '''
        Retrieve an account id from the OAuth provider.
        May use an already-cached value in the flask session,
        or may cause a http request to be called.
        '''
        cached_id = flask_session.get(self.id + '_oauth_user_id')
        if cached_id:
            # log.debug("%s: cached account id %s", self.id, cached_id)
            return cached_id

        # http request to the OAuth provider for the account information
        account_info = self.blueprint.session.get(self.account_info_path)
        if account_info and account_info.ok:
            account_info = account_info.json()
            # log.debug("account info: %s", account_info)
            return account_info['id']
        return None

    def unlink(self, user):
        '''
        Destroys the local OAuth token for the given user.
        '''
        # log.debug("unlink %s: %s", self.id, user)
        try:
            _STORAGE.delete(self.blueprint, user, user.id)
        except Exception as ex:
            log.error("unlink %s: %s: %s", self.id, user, ex)
            return False

        self.clear_session()
        return True

    # def register_user(self, user):
    #     provider_user_id = flask_session.get(self.id + '_oauth_user_id')
    #     if provider_user_id:
    #         _STORAGE.register_user(self.blueprint, provider_user_id, user)

    def set_session_error(self, has_error=True):
        '''
        Flags the current flask session with an OAuth error.
        Used by callbacks to update the authorization status out-of-band.
        '''
        if has_error:
            clear_session()
        flask_session[self.id + '_oauth_error'] = has_error

    def has_session_error(self):
        '''
        Checks (and clears) the flask-session's OAuth error flag.
        '''
        return flask_session.pop(self.id + '_oauth_error', False)

    def clear_session(self):
        '''
        Clear all OAuth data (for this provider) from the current flask session.
        '''
        flask_session.pop(self.id + '_oauth_user_id', None)
        flask_session.pop(self.id + '_oauth_token', None)
        flask_session.pop(self.id + '_oauth_error', None)


class _TokenCache(object):
    '''
    In-memory token cache for the backend.
    '''
    def __init__(self):
        self._cache = {}

    def get(self, key):
        value = self._cache.get(key, None)
        # log.debug("_TokenCache.get %s => %r", key, value)
        return value

    def set(self, key, value):
        # log.debug("_TokenCache.set %s = %r", key, value)
        self._cache[key] = value

    def delete(self, key):
        # log.debug("_TokenCache.delete %s", key)
        self._cache.pop(key, None)


class _SQLStorage(SQLAlchemyStorage):
    # def get(self, blueprint, user=None, user_id=None):
    #     token = SQLAlchemyStorage.get(self, blueprint, user, user_id)
    #     log.debug("_SQLStorage.get %s %r %r => %s", blueprint.name, user, user_id, token)
    #     return token
    #
    # def set(self, blueprint, token, user=None, user_id=None):
    #     log.debug("_SQLStorage.set %s %s %r %r", blueprint.name, token, user, user_id)
    #     SQLAlchemyStorage.set(self, blueprint, token, user, user_id)
    #
    # def delete(self, blueprint, user=None, user_id=None):
    #     log.debug("_SQLStorage.delete %s %r %r", blueprint.name, user, user_id)
    #     SQLAlchemyStorage.delete(self, blueprint, user, user_id)

    # def register_user(self, blueprint, provider_user_id, user):
    #     log.debug("register_user %s: %s %s", blueprint.name, provider_user_id, user)
    #     query = self.session.query(self.model).filter_by(
    #         provider=blueprint.name,
    #         provider_user_id=provider_user_id,
    #     )
    #     try:
    #         oauth = query.one()
    #         oauth.user_id = user.id
    #     except NoResultFound:
    #         # no found, return error
    #         return False
    #
    #     try:
    #         self.session.commit()
    #         return True
    #     except Exception as ex:
    #         log.error("register_user %s: %s: %s", blueprint.name, user, ex)
    #         self.session.rollback()
    #         return False

    def cleanup_oauth(self, provider_id, provider_user_id, user=None):
        '''
        Remove partially-filled oauth tokens (have either just the user_id or just provider_user_id).
        '''
        # log.debug("cleanup_oauth: %s %s %s", provider_id, provider_user_id, user)
        try:
            query = self.session.query(self.model).filter_by(provider=provider_id, provider_user_id=provider_user_id)
            query = query.filter(self.model.user_id.is_(None))
            query.delete()
        except Exception as ex:
            log.error("cleanup_tokens %s: %s: %s", provider_id, provider_user_id, ex)

        if user:
            try:
                query = self.session.query(self.model).filter_by(provider=provider_id, user_id=user.id)
                query = query.filter(self.model.provider_user_id.is_(None))
                query.delete()
            except Exception as ex:
                log.error("cleanup_tokens %s: %s: %s", provider_id, user, ex)

    def find_oauth(self, provider_id, provider_user_id, user=None, please_dont_cycle=False):
        # log.debug("find_oauth %s: pid=%s user=%s", provider_id, provider_user_id, user)
        query = self.session.query(self.model).filter_by(provider=provider_id)
        if user:
            query = query.filter_by(user_id=user.id)
        else:
            query = query.filter_by(provider_user_id=provider_user_id)

        try:
            oauth = query.one()
        except NoResultFound:
            # alright, time to create a new one
            oauth = self.model(provider=provider_id, provider_user_id=provider_user_id)
            # log.debug("find_oauth %s: no oauth found for %s, creating", provider_id, user)
        except MultipleResultsFound:
            # most likely, partially-filled data from failed previous attempts
            if please_dont_cycle:
                log.warning("find_oauth %s: cleaning multiple results for %s failed, giving up", provider_id, user)
                return None
            log.warning("find_oauth %s: multiple results for user %s", provider_id, user)
            self.cleanup_oauth(provider_id, provider_user_id, user)
            return self.find_oauth(provider_id, provider_user_id, user, please_dont_cycle=True)

        # log.debug("find_oauth %s: got pid=%s uid=%s token=%s",
        #           provider_id, oauth.provider_user_id, oauth.user_id, bool(oauth.token))
        return oauth

    def update_oauth(self, oauth, provider_user_id, user=None, token=None):
        # log.debug("update_oauth: %s pid=%s user=%s token=%s", oauth.provider, provider_user_id, user, bool(token))
        if oauth.provider_user_id == provider_user_id:
            # avoid touching the database with no data change
            if user and oauth.user_id == user.id:
                return oauth
            if token and oauth.token == token:
                return oauth

        oauth.provider_user_id = provider_user_id
        if user:
            assert not oauth.user_id or oauth.user_id == user.id
            oauth.user_id = user.id
        if token:
            oauth.token = token

        try:
            self.session.add(oauth)
            self.session.commit()
            return oauth
        except Exception as ex:
            log.error("update_oauth: failed for %s: %s", user, ex)
            self.session.rollback()
            return None


_STORAGE = _SQLStorage(None, None, cache=_TokenCache())


def init_storage(db_model, db_session, user=None, user_id=None):
    _STORAGE.model = db_model
    _STORAGE.session = db_session
    _STORAGE.user = user
    _STORAGE.user_id = user_id
    _STORAGE.user_required = user is not None or user_id is not None


def init_providers(redirect_pattern, authorized_handler, error_handler):
    for provider_id in _SUPPORTED:
        redirect_to = redirect_pattern.format(provider=provider_id)

        provider = _Provider(provider_id, redirect_to)
        oauth_authorized.connect(authorized_handler, sender=provider.blueprint, weak=False)
        oauth_error.connect(error_handler, sender=provider.blueprint, weak=False)

        providers[provider.id] = provider


# def register_user(user):
#     for provider in providers.values():
#         provider.register_user(user)


def clear_session():
    for provider in providers.values():
        provider.clear_session()
