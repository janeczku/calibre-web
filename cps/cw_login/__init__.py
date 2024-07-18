# from .__about__ import __version__
from .config import AUTH_HEADER_NAME
from .config import COOKIE_DURATION
from .config import COOKIE_HTTPONLY
from .config import COOKIE_NAME
from .config import COOKIE_SECURE
from .config import ID_ATTRIBUTE
from .config import LOGIN_MESSAGE
from .config import LOGIN_MESSAGE_CATEGORY
from .config import REFRESH_MESSAGE
from .config import REFRESH_MESSAGE_CATEGORY
from .login_manager import LoginManager
from .mixins import AnonymousUserMixin
from .mixins import UserMixin
from .signals import session_protected
from .signals import user_accessed
from .signals import user_loaded_from_cookie
from .signals import user_loaded_from_request
from .signals import user_logged_in
from .signals import user_logged_out
from .signals import user_login_confirmed
from .signals import user_needs_refresh
from .signals import user_unauthorized
# from .test_client import FlaskLoginClient
from .utils import confirm_login
from .utils import current_user
from .utils import decode_cookie
from .utils import encode_cookie
from .utils import fresh_login_required
from .utils import login_fresh
from .utils import login_remembered
from .utils import login_required
from .utils import login_url
from .utils import login_user
from .utils import logout_user
from .utils import make_next_param
from .utils import set_login_view

__version_info__ = ("0", "6", "3")
__version__ = ".".join(__version_info__)


__all__ = [
    "__version__",
    "AUTH_HEADER_NAME",
    "COOKIE_DURATION",
    "COOKIE_HTTPONLY",
    "COOKIE_NAME",
    "COOKIE_SECURE",
    "ID_ATTRIBUTE",
    "LOGIN_MESSAGE",
    "LOGIN_MESSAGE_CATEGORY",
    "REFRESH_MESSAGE",
    "REFRESH_MESSAGE_CATEGORY",
    "LoginManager",
    "AnonymousUserMixin",
    "UserMixin",
    "session_protected",
    "user_accessed",
    "user_loaded_from_cookie",
    "user_loaded_from_request",
    "user_logged_in",
    "user_logged_out",
    "user_login_confirmed",
    "user_needs_refresh",
    "user_unauthorized",
    # "FlaskLoginClient",
    "confirm_login",
    "current_user",
    "decode_cookie",
    "encode_cookie",
    "fresh_login_required",
    "login_fresh",
    "login_remembered",
    "login_required",
    "login_url",
    "login_user",
    "logout_user",
    "make_next_param",
    "set_login_view",
]


def __getattr__(name):
    if name == "user_loaded_from_header":
        import warnings
        from .signals import _user_loaded_from_header

        warnings.warn(
            "'user_loaded_from_header' is deprecated and will be"
            " removed in Flask-Login 0.7. Use"
            " 'user_loaded_from_request' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _user_loaded_from_header

    raise AttributeError(name)
