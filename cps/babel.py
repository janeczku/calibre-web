from babel import Locale as LC
from babel import negotiate_locale
from flask_babel import Babel
from babel.core import UnknownLocaleError
from flask import request, g

from . import logger

log = logger.create()

babel = Babel()
BABEL_TRANSLATIONS = set()

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    user = getattr(g, 'user', None)
    if user is not None and hasattr(user, "locale"):
        if user.name != 'Guest':   # if the account is the guest account bypass the config lang settings
            return user.locale

    preferred = list()
    if request.accept_languages:
        for x in request.accept_languages.values():
            try:
                preferred.append(str(LC.parse(x.replace('-', '_'))))
            except (UnknownLocaleError, ValueError) as e:
                log.debug('Could not parse locale "%s": %s', x, e)

    return negotiate_locale(preferred or ['en'], BABEL_TRANSLATIONS)
