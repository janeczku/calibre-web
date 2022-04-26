# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 jim3ma
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

from flask import session

try:
    from flask_dance.consumer.storage.sqla import SQLAlchemyStorage as SQLAlchemyBackend
    from flask_dance.consumer.storage.sqla import first, _get_real_user
    from sqlalchemy.orm.exc import NoResultFound
    backend_resultcode = True  # prevent storing values with this resultcode
except ImportError:
    pass


class OAuthBackend(SQLAlchemyBackend):
    """
    Stores and retrieves OAuth tokens using a relational database through
    the `SQLAlchemy`_ ORM.

    .. _SQLAlchemy: https://www.sqlalchemy.org/
    """
    def __init__(self, model, session, provider_id,
                 user=None, user_id=None, user_required=None, anon_user=None,
                 cache=None):
        self.provider_id = provider_id
        super(OAuthBackend, self).__init__(model, session, user, user_id, user_required, anon_user, cache)

    def get(self, blueprint, user=None, user_id=None):
        if self.provider_id + '_oauth_token' in session and session[self.provider_id + '_oauth_token'] != '':
            return session[self.provider_id + '_oauth_token']
        # check cache
        cache_key = self.make_cache_key(blueprint=blueprint, user=user, user_id=user_id)
        token = self.cache.get(cache_key)
        if token:
            return token

        # if not cached, make database queries
        query = (
            self.session.query(self.model)
            .filter_by(provider=self.provider_id)
        )
        uid = first([user_id, self.user_id, blueprint.config.get("user_id")])
        u = first(_get_real_user(ref, self.anon_user)
                  for ref in (user, self.user, blueprint.config.get("user")))

        use_provider_user_id = False
        if self.provider_id + '_oauth_user_id' in session and session[self.provider_id + '_oauth_user_id'] != '':
            query = query.filter_by(provider_user_id=session[self.provider_id + '_oauth_user_id'])
            use_provider_user_id = True

        if self.user_required and not u and not uid and not use_provider_user_id:
            # raise ValueError("Cannot get OAuth token without an associated user")
            return None
        # check for user ID
        if hasattr(self.model, "user_id") and uid:
            query = query.filter_by(user_id=uid)
        # check for user (relationship property)
        elif hasattr(self.model, "user") and u:
            query = query.filter_by(user=u)
        # if we have the property, but not value, filter by None
        elif hasattr(self.model, "user_id"):
            query = query.filter_by(user_id=None)
        # run query
        try:
            token = query.one().token
        except NoResultFound:
            token = None

        # cache the result
        self.cache.set(cache_key, token)

        return token

    def set(self, blueprint, token, user=None, user_id=None):
        uid = first([user_id, self.user_id, blueprint.config.get("user_id")])
        u = first(_get_real_user(ref, self.anon_user)
                  for ref in (user, self.user, blueprint.config.get("user")))

        if self.user_required and not u and not uid:
            raise ValueError("Cannot set OAuth token without an associated user")

        # if there was an existing model, delete it
        existing_query = (
            self.session.query(self.model)
            .filter_by(provider=self.provider_id)
        )
        # check for user ID
        has_user_id = hasattr(self.model, "user_id")
        if has_user_id and uid:
            existing_query = existing_query.filter_by(user_id=uid)
        # check for user (relationship property)
        has_user = hasattr(self.model, "user")
        if has_user and u:
            existing_query = existing_query.filter_by(user=u)
        # queue up delete query -- won't be run until commit()
        existing_query.delete()
        # create a new model for this token
        kwargs = {
            "provider": self.provider_id,
            "token": token,
        }
        if has_user_id and uid:
            kwargs["user_id"] = uid
        if has_user and u:
            kwargs["user"] = u
        self.session.add(self.model(**kwargs))
        # commit to delete and add simultaneously
        self.session.commit()
        # invalidate cache
        self.cache.delete(self.make_cache_key(
            blueprint=blueprint, user=user, user_id=user_id
        ))

    def delete(self, blueprint, user=None, user_id=None):
        query = (
            self.session.query(self.model)
            .filter_by(provider=self.provider_id)
        )
        uid = first([user_id, self.user_id, blueprint.config.get("user_id")])
        u = first(_get_real_user(ref, self.anon_user)
                  for ref in (user, self.user, blueprint.config.get("user")))

        if self.user_required and not u and not uid:
            raise ValueError("Cannot delete OAuth token without an associated user")

        # check for user ID
        if hasattr(self.model, "user_id") and uid:
            query = query.filter_by(user_id=uid)
        # check for user (relationship property)
        elif hasattr(self.model, "user") and u:
            query = query.filter_by(user=u)
        # if we have the property, but not value, filter by None
        elif hasattr(self.model, "user_id"):
            query = query.filter_by(user_id=None)
        # run query
        query.delete()
        self.session.commit()
        # invalidate cache
        self.cache.delete(self.make_cache_key(
            blueprint=blueprint, user=user, user_id=user_id,
        ))
