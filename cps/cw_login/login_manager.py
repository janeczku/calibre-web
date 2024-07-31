from datetime import datetime
from datetime import timedelta
import hashlib

from flask import abort
from flask import current_app
from flask import flash
from flask import g
from flask import has_app_context
from flask import redirect
from flask import request
from flask import session
from itsdangerous import URLSafeSerializer
from flask.json.tag import TaggedJSONSerializer

from .config import AUTH_HEADER_NAME
from .config import COOKIE_DURATION
from .config import COOKIE_HTTPONLY
from .config import COOKIE_NAME
from .config import COOKIE_SAMESITE
from .config import COOKIE_SECURE
from .config import ID_ATTRIBUTE
from .config import LOGIN_MESSAGE
from .config import LOGIN_MESSAGE_CATEGORY
from .config import REFRESH_MESSAGE
from .config import REFRESH_MESSAGE_CATEGORY
from .config import SESSION_KEYS
from .config import USE_SESSION_FOR_NEXT
from .mixins import AnonymousUserMixin
from .signals import session_protected
from .signals import user_accessed
from .signals import user_loaded_from_cookie
from .signals import user_loaded_from_request
from .signals import user_needs_refresh
from .signals import user_unauthorized
from .utils import _create_identifier
from .utils import _user_context_processor
from .utils import confirm_login
from .utils import expand_login_view
from .utils import login_url as make_login_url
from .utils import make_next_param


class LoginManager:
    """This object is used to hold the settings used for logging in. Instances
    of :class:`LoginManager` are *not* bound to specific apps, so you can
    create one in the main body of your code and then bind it to your
    app in a factory function.
    """

    def __init__(self, app=None, add_context_processor=True):
        #: A class or factory function that produces an anonymous user, which
        #: is used when no one is logged in.
        self.anonymous_user = AnonymousUserMixin

        #: The name of the view to redirect to when the user needs to log in.
        #: (This can be an absolute URL as well, if your authentication
        #: machinery is external to your application.)
        self.login_view = None

        #: Names of views to redirect to when the user needs to log in,
        #: per blueprint. If the key value is set to None the value of
        #: :attr:`login_view` will be used instead.
        self.blueprint_login_views = {}

        #: The message to flash when a user is redirected to the login page.
        self.login_message = LOGIN_MESSAGE

        #: The message category to flash when a user is redirected to the login
        #: page.
        self.login_message_category = LOGIN_MESSAGE_CATEGORY

        #: The name of the view to redirect to when the user needs to
        #: reauthenticate.
        self.refresh_view = None

        #: The message to flash when a user is redirected to the 'needs
        #: refresh' page.
        self.needs_refresh_message = REFRESH_MESSAGE

        #: The message category to flash when a user is redirected to the
        #: 'needs refresh' page.
        self.needs_refresh_message_category = REFRESH_MESSAGE_CATEGORY

        #: The mode to use session protection in. This can be either
        #: ``'basic'`` (the default) or ``'strong'``, or ``None`` to disable
        #: it.
        self.session_protection = "basic"

        #: If present, used to translate flash messages ``self.login_message``
        #: and ``self.needs_refresh_message``
        self.localize_callback = None

        self.unauthorized_callback = None

        self.needs_refresh_callback = None

        self.id_attribute = ID_ATTRIBUTE

        self._user_callback = None

        self._header_callback = None

        self._request_callback = None

        self._session_identifier_generator = _create_identifier

        if app is not None:
            self.init_app(app, add_context_processor)

    def setup_app(self, app, add_context_processor=True):  # pragma: no cover
        """
        This method has been deprecated. Please use
        :meth:`LoginManager.init_app` instead.
        """
        import warnings

        warnings.warn(
            "'setup_app' is deprecated and will be removed in"
            " Flask-Login 0.7. Use 'init_app' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.init_app(app, add_context_processor)

    def init_app(self, app, add_context_processor=True):
        """
        Configures an application. This registers an `after_request` call, and
        attaches this `LoginManager` to it as `app.login_manager`.

        :param app: The :class:`flask.Flask` object to configure.
        :type app: :class:`flask.Flask`
        :param add_context_processor: Whether to add a context processor to
            the app that adds a `current_user` variable to the template.
            Defaults to ``True``.
        :type add_context_processor: bool
        """
        app.login_manager = self
        app.after_request(self._update_remember_cookie)

        if add_context_processor:
            app.context_processor(_user_context_processor)

    def unauthorized(self):
        """
        This is called when the user is required to log in. If you register a
        callback with :meth:`LoginManager.unauthorized_handler`, then it will
        be called. Otherwise, it will take the following actions:

            - Flash :attr:`LoginManager.login_message` to the user.

            - If the app is using blueprints find the login view for
              the current blueprint using `blueprint_login_views`. If the app
              is not using blueprints or the login view for the current
              blueprint is not specified use the value of `login_view`.

            - Redirect the user to the login view. (The page they were
              attempting to access will be passed in the ``next`` query
              string variable, so you can redirect there if present instead
              of the homepage. Alternatively, it will be added to the session
              as ``next`` if USE_SESSION_FOR_NEXT is set.)

        If :attr:`LoginManager.login_view` is not defined, then it will simply
        raise a HTTP 401 (Unauthorized) error instead.

        This should be returned from a view or before/after_request function,
        otherwise the redirect will have no effect.
        """
        user_unauthorized.send(current_app._get_current_object())

        if self.unauthorized_callback:
            return self.unauthorized_callback()

        if request.blueprint in self.blueprint_login_views:
            login_view = self.blueprint_login_views[request.blueprint]
        else:
            login_view = self.login_view

        if not login_view:
            abort(401)

        if self.login_message:
            if self.localize_callback is not None:
                flash(
                    self.localize_callback(self.login_message),
                    category=self.login_message_category,
                )
            else:
                flash(self.login_message, category=self.login_message_category)

        config = current_app.config
        if config.get("USE_SESSION_FOR_NEXT", USE_SESSION_FOR_NEXT):
            login_url = expand_login_view(login_view)
            session["_id"] = self._session_identifier_generator()
            session["next"] = make_next_param(login_url, request.url)
            redirect_url = make_login_url(login_view)
        else:
            redirect_url = make_login_url(login_view, next_url=request.url)

        return redirect(redirect_url)

    def user_loader(self, callback):
        """
        This sets the callback for reloading a user from the session. The
        function you set should take a user ID (a ``str``) and return a
        user object, or ``None`` if the user does not exist.

        :param callback: The callback for retrieving a user object.
        :type callback: callable
        """
        self._user_callback = callback
        return self.user_callback

    @property
    def user_callback(self):
        """Gets the user_loader callback set by user_loader decorator."""
        return self._user_callback

    def request_loader(self, callback):
        """
        This sets the callback for loading a user from a Flask request.
        The function you set should take Flask request object and
        return a user object, or `None` if the user does not exist.

        :param callback: The callback for retrieving a user object.
        :type callback: callable
        """
        self._request_callback = callback
        return self.request_callback

    @property
    def request_callback(self):
        """Gets the request_loader callback set by request_loader decorator."""
        return self._request_callback

    def unauthorized_handler(self, callback):
        """
        This will set the callback for the `unauthorized` method, which among
        other things is used by `login_required`. It takes no arguments, and
        should return a response to be sent to the user instead of their
        normal view.

        :param callback: The callback for unauthorized users.
        :type callback: callable
        """
        self.unauthorized_callback = callback
        return callback

    def needs_refresh_handler(self, callback):
        """
        This will set the callback for the `needs_refresh` method, which among
        other things is used by `fresh_login_required`. It takes no arguments,
        and should return a response to be sent to the user instead of their
        normal view.

        :param callback: The callback for unauthorized users.
        :type callback: callable
        """
        self.needs_refresh_callback = callback
        return callback

    def needs_refresh(self):
        """
        This is called when the user is logged in, but they need to be
        reauthenticated because their session is stale. If you register a
        callback with `needs_refresh_handler`, then it will be called.
        Otherwise, it will take the following actions:

            - Flash :attr:`LoginManager.needs_refresh_message` to the user.

            - Redirect the user to :attr:`LoginManager.refresh_view`. (The page
              they were attempting to access will be passed in the ``next``
              query string variable, so you can redirect there if present
              instead of the homepage.)

        If :attr:`LoginManager.refresh_view` is not defined, then it will
        simply raise a HTTP 401 (Unauthorized) error instead.

        This should be returned from a view or before/after_request function,
        otherwise the redirect will have no effect.
        """
        user_needs_refresh.send(current_app._get_current_object())

        if self.needs_refresh_callback:
            return self.needs_refresh_callback()

        if not self.refresh_view:
            abort(401)

        if self.needs_refresh_message:
            if self.localize_callback is not None:
                flash(
                    self.localize_callback(self.needs_refresh_message),
                    category=self.needs_refresh_message_category,
                )
            else:
                flash(
                    self.needs_refresh_message,
                    category=self.needs_refresh_message_category,
                )

        config = current_app.config
        if config.get("USE_SESSION_FOR_NEXT", USE_SESSION_FOR_NEXT):
            login_url = expand_login_view(self.refresh_view)
            session["_id"] = self._session_identifier_generator()
            session["next"] = make_next_param(login_url, request.url)
            redirect_url = make_login_url(self.refresh_view)
        else:
            login_url = self.refresh_view
            redirect_url = make_login_url(login_url, next_url=request.url)

        return redirect(redirect_url)

    def _update_request_context_with_user(self, user=None):
        """Store the given user as ctx.user."""

        if user is None:
            user = self.anonymous_user()

        g._login_user = user

    def _load_user(self):
        """Loads user from session or remember_me cookie as applicable"""

        if self._user_callback is None and self._request_callback is None:
            raise Exception(
                "Missing user_loader or request_loader. Refer to "
                "https://flask-login.readthedocs.io/#how-it-works "
                "for more info."
            )

        user_accessed.send(current_app._get_current_object())

        # Check SESSION_PROTECTION
        if self._session_protection_failed():
            return self._update_request_context_with_user()

        user = None

        # Load user from Flask Session
        user_id = session.get("_user_id")
        user_random = session.get("_random")
        user_session_key = session.get("_id")
        if (user_id is not None
            and user_random is not None
            and user_session_key is not None
            and self._user_callback is not None):
              user = self._user_callback(user_id, user_random, user_session_key)

        # Load user from Remember Me Cookie or Request Loader
        if user is None:
            config = current_app.config
            cookie_name = config.get("REMEMBER_COOKIE_NAME", COOKIE_NAME)
            header_name = config.get("AUTH_HEADER_NAME", AUTH_HEADER_NAME)
            has_cookie = (
                cookie_name in request.cookies and session.get("_remember") != "clear"
            )
            if has_cookie:
                cookie = request.cookies[cookie_name]
                user = self._load_user_from_remember_cookie(cookie)
            elif self._request_callback:
                user = self._load_user_from_request(request)
            elif header_name in request.headers:
                header = request.headers[header_name]
                user = self._load_user_from_header(header)
        if not user:
            self._update_request_context_with_user()
        return self._update_request_context_with_user(user)

    def _session_protection_failed(self):
        sess = session._get_current_object()
        ident = self._session_identifier_generator()

        app = current_app._get_current_object()
        mode = app.config.get("SESSION_PROTECTION", self.session_protection)

        if not mode or mode not in ["basic", "strong"]:
            return False

        # if the sess is empty, it's an anonymous user or just logged out
        # so we can skip this
        if sess and ident != sess.get("_id", None):
            if mode == "basic" or sess.permanent:
                if sess.get("_fresh") is not False:
                    sess["_fresh"] = False
                session_protected.send(app)
                return False
            elif mode == "strong":
                for k in SESSION_KEYS:
                    sess.pop(k, None)

                sess["_remember"] = "clear"
                session_protected.send(app)
                return True

        return False

    def _load_user_from_remember_cookie(self, cookie):
        signer_kwargs = dict(
            key_derivation="hmac", digest_method=hashlib.sha1
        )
        try:
            remember_dict = URLSafeSerializer(
                current_app.secret_key,
                salt="remember",
                serializer=TaggedJSONSerializer(),
                signer_kwargs=signer_kwargs,
            ).loads(cookie)
        except Exception:
            return None

        if remember_dict['user'] is not None:
            session["_user_id"] = remember_dict['user']
            if "_random" not in session:
                session["_random"] = remember_dict['random']
            session["_fresh"] = False
            user = None
            if self._user_callback:
                user = self._user_callback(remember_dict['user'], session["_random"], None)
            if user is not None:
                app = current_app._get_current_object()
                user_loaded_from_cookie.send(app, user=user)
                # if session was restored from remember me cookie make login valid
                confirm_login()
                return user
        return None

    def _load_user_from_header(self, header):
        if self._header_callback:
            user = self._header_callback(header)
            if user is not None:
                app = current_app._get_current_object()

                from .signals import _user_loaded_from_header

                _user_loaded_from_header.send(app, user=user)
                return user
        return None

    def _load_user_from_request(self, request):
        if self._request_callback:
            user = self._request_callback(request)
            if user is not None:
                app = current_app._get_current_object()
                user_loaded_from_request.send(app, user=user)
                return user
        return None

    def _update_remember_cookie(self, response):
        # Don't modify the session unless there's something to do.
        if "_remember" not in session and current_app.config.get(
            "REMEMBER_COOKIE_REFRESH_EACH_REQUEST"
        ):
            session["_remember"] = "set"

        if "_remember" in session:
            operation = session.pop("_remember", None)

            if operation == "set" and "_user_id" in session:
                self._set_cookie(response)
            elif operation == "clear":
                self._clear_cookie(response)

        return response

    def _set_cookie(self, response):
        # cookie settings
        config = current_app.config
        cookie_name = config.get("REMEMBER_COOKIE_NAME", COOKIE_NAME)
        domain = config.get("REMEMBER_COOKIE_DOMAIN")
        path = config.get("REMEMBER_COOKIE_PATH", "/")

        secure = config.get("REMEMBER_COOKIE_SECURE", COOKIE_SECURE)
        httponly = config.get("REMEMBER_COOKIE_HTTPONLY", COOKIE_HTTPONLY)
        samesite = config.get("REMEMBER_COOKIE_SAMESITE", COOKIE_SAMESITE)

        if "_remember_seconds" in session:
            duration = timedelta(seconds=session["_remember_seconds"])
        else:
            duration = config.get("REMEMBER_COOKIE_DURATION", COOKIE_DURATION)

        # prepare data
        max_age = int(current_app.permanent_session_lifetime.total_seconds())
        signer_kwargs = dict(
            key_derivation="hmac", digest_method=hashlib.sha1
        )
        # save
        data = URLSafeSerializer(
            current_app.secret_key,
            salt="remember",
            serializer=TaggedJSONSerializer(),
            signer_kwargs=signer_kwargs,
        ).dumps({"user":session["_user_id"], "random":session["_random"]})

        if isinstance(duration, int):
            duration = timedelta(seconds=duration)

        try:
            expires = datetime.utcnow() + duration
        except TypeError as e:
            raise Exception(
                "REMEMBER_COOKIE_DURATION must be a datetime.timedelta,"
                f" instead got: {duration}"
            ) from e

        # actually set it
        response.set_cookie(
            cookie_name,
            value=data,
            expires=expires,
            domain=domain,
            path=path,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    def _clear_cookie(self, response):
        config = current_app.config
        cookie_name = config.get("REMEMBER_COOKIE_NAME", COOKIE_NAME)
        domain = config.get("REMEMBER_COOKIE_DOMAIN")
        path = config.get("REMEMBER_COOKIE_PATH", "/")
        response.delete_cookie(cookie_name, domain=domain, path=path)

    @property
    def _login_disabled(self):
        """Legacy property, use app.config['LOGIN_DISABLED'] instead."""
        import warnings

        warnings.warn(
            "'_login_disabled' is deprecated and will be removed in"
            " Flask-Login 0.7. Use 'LOGIN_DISABLED' in 'app.config'"
            " instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        if has_app_context():
            return current_app.config.get("LOGIN_DISABLED", False)
        return False

    @_login_disabled.setter
    def _login_disabled(self, newvalue):
        """Legacy property setter, use app.config['LOGIN_DISABLED'] instead."""
        import warnings

        warnings.warn(
            "'_login_disabled' is deprecated and will be removed in"
            " Flask-Login 0.7. Use 'LOGIN_DISABLED' in 'app.config'"
            " instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        current_app.config["LOGIN_DISABLED"] = newvalue
