from datetime import timedelta

#: The default name of the "remember me" cookie (``remember_token``)
COOKIE_NAME = "remember_token"

#: The default time before the "remember me" cookie expires (365 days).
COOKIE_DURATION = timedelta(days=365)

#: Whether the "remember me" cookie requires Secure; defaults to ``False``
COOKIE_SECURE = False

#: Whether the "remember me" cookie uses HttpOnly or not; defaults to ``True``
COOKIE_HTTPONLY = True

#: Whether the "remember me" cookie requires same origin; defaults to ``None``
COOKIE_SAMESITE = None

#: The default flash message to display when users need to log in.
LOGIN_MESSAGE = "Please log in to access this page."

#: The default flash message category to display when users need to log in.
LOGIN_MESSAGE_CATEGORY = "message"

#: The default flash message to display when users need to reauthenticate.
REFRESH_MESSAGE = "Please reauthenticate to access this page."

#: The default flash message category to display when users need to
#: reauthenticate.
REFRESH_MESSAGE_CATEGORY = "message"

#: The default attribute to retreive the str id of the user
ID_ATTRIBUTE = "get_id"

#: Default name of the auth header (``Authorization``)
AUTH_HEADER_NAME = "Authorization"

#: A set of session keys that are populated by Flask-Login. Use this set to
#: purge keys safely and accurately.
SESSION_KEYS = {
    "_user_id",
    "_remember",
    "_remember_seconds",
    "_id",
    "_fresh",
    "next",
}

#: A set of HTTP methods which are exempt from `login_required` and
#: `fresh_login_required`. By default, this is just ``OPTIONS``.
EXEMPT_METHODS = {"OPTIONS"}

#: If true, the page the user is attempting to access is stored in the session
#: rather than a url parameter when redirecting to the login view; defaults to
#: ``False``.
USE_SESSION_FOR_NEXT = False
