# -*- coding: utf-8 -*-

import threading

import jwt

from .. import logger

log = logger.create()

ACCESS_JWT_HEADER = "Cf-Access-Jwt-Assertion"
CERTS_PATH = "/cdn-cgi/access/certs"
KEY_CACHE_SECONDS = 3600
# Cloudflare and this server keep their own clocks, allow normal NTP-level skew on
# iat/nbf/exp so a fresh token isn't refused for being a second "in the future"
LEEWAY_SECONDS = 60

_clients = {}
_clients_lock = threading.Lock()


def normalize_team_domain(value):
    """Return the team domain as an https origin without a trailing slash, or ''."""
    value = (value or "").strip().rstrip("/")
    if value and "://" not in value:
        value = "https://" + value
    return value


def _jwk_client(team_domain):
    with _clients_lock:
        client = _clients.get(team_domain)
        if client is None:
            client = jwt.PyJWKClient(team_domain + CERTS_PATH,
                                     cache_keys=True,
                                     lifespan=KEY_CACHE_SECONDS,
                                     timeout=10)
            _clients[team_domain] = client
        return client


def team_domain_problem(team_domain):
    """Fetch the signing keys once. Return None if that works, else the reason.

    Used when the settings are saved, so a mistyped team domain shows up there instead
    of refusing every header login afterwards. A wrong AUD tag can't be checked this
    way, that needs a real token.
    """
    team_domain = normalize_team_domain(team_domain)
    if not team_domain:
        return None
    try:
        jwt.PyJWKClient(team_domain + CERTS_PATH, cache_keys=False, timeout=10).get_signing_keys()
    except jwt.PyJWTError as e:
        return str(e)
    return None


def verified_email(req, team_domain, audience):
    """Return the email a valid Access token in req vouches for, or None."""
    token = req.headers.get(ACCESS_JWT_HEADER)
    if not token:
        log.warning("Cloudflare Access check: no %s header on the request", ACCESS_JWT_HEADER)
        return None
    try:
        signing_key = _jwk_client(team_domain).get_signing_key_from_jwt(token)
        claims = jwt.decode(token,
                            signing_key.key,
                            algorithms=["RS256"],
                            audience=audience,
                            issuer=team_domain,
                            options={"require": ["exp", "iat", "iss", "aud"]},
                            leeway=LEEWAY_SECONDS)
    except jwt.PyJWTError as e:
        log.warning("Cloudflare Access check: token rejected: %s", e)
        return None
    email = (claims.get("email") or "").strip()
    if not email:
        log.warning("Cloudflare Access check: token has no email claim")
        return None
    return email


def header_login_permitted(req, header_value, config):
    """Decide whether a reverse proxy header value may be used to log in.

    With no Access settings the header is trusted as before. With both set, the token
    must verify and its email must match the header. With only one set the login is
    refused, so a missing field can't quietly fall back to trusting the bare header.
    """
    team_domain = normalize_team_domain(getattr(config, "config_reverse_proxy_access_team_domain", None))
    audience = (getattr(config, "config_reverse_proxy_access_aud", None) or "").strip()
    if not team_domain and not audience:
        return True
    if not (team_domain and audience):
        log.error("Cloudflare Access check needs both a team domain and an AUD tag, rejecting reverse proxy login")
        return False
    email = verified_email(req, team_domain, audience)
    if email is None:
        return False
    if email.lower() != header_value.lower():
        log.warning("Cloudflare Access check: header names '%s' but the token is for '%s'", header_value, email)
        return False
    return True
