from flask.signals import Namespace

_signals = Namespace()

#: Sent when a user is logged in. In addition to the app (which is the
#: sender), it is passed `user`, which is the user being logged in.
user_logged_in = _signals.signal("logged-in")

#: Sent when a user is logged out. In addition to the app (which is the
#: sender), it is passed `user`, which is the user being logged out.
user_logged_out = _signals.signal("logged-out")

#: Sent when the user is loaded from the cookie. In addition to the app (which
#: is the sender), it is passed `user`, which is the user being reloaded.
user_loaded_from_cookie = _signals.signal("loaded-from-cookie")

#: Sent when the user is loaded from the header. In addition to the app (which
#: is the #: sender), it is passed `user`, which is the user being reloaded.
_user_loaded_from_header = _signals.signal("loaded-from-header")

#: Sent when the user is loaded from the request. In addition to the app (which
#: is the #: sender), it is passed `user`, which is the user being reloaded.
user_loaded_from_request = _signals.signal("loaded-from-request")

#: Sent when a user's login is confirmed, marking it as fresh. (It is not
#: called for a normal login.)
#: It receives no additional arguments besides the app.
user_login_confirmed = _signals.signal("login-confirmed")

#: Sent when the `unauthorized` method is called on a `LoginManager`. It
#: receives no additional arguments besides the app.
user_unauthorized = _signals.signal("unauthorized")

#: Sent when the `needs_refresh` method is called on a `LoginManager`. It
#: receives no additional arguments besides the app.
user_needs_refresh = _signals.signal("needs-refresh")

#: Sent whenever the user is accessed/loaded
#: receives no additional arguments besides the app.
user_accessed = _signals.signal("accessed")

#: Sent whenever session protection takes effect, and a session is either
#: marked non-fresh or deleted. It receives no additional arguments besides
#: the app.
session_protected = _signals.signal("session-protected")


def __getattr__(name):
    if name == "user_loaded_from_header":
        import warnings

        warnings.warn(
            "'user_loaded_from_header' is deprecated and will be"
            " removed in Flask-Login 0.7. Use"
            " 'user_loaded_from_request' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _user_loaded_from_header

    raise AttributeError(name)
