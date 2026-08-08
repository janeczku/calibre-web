# -*- coding: utf-8 -*-

import hmac
import ipaddress
import re
from functools import lru_cache

from . import logger

log = logger.create()

HEADER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


def to_wsgi_header_key(header_name):
    return "HTTP_{}".format(header_name.strip().upper().replace("-", "_"))


def is_valid_header_name(header_name):
    return bool(header_name and HEADER_NAME_PATTERN.fullmatch(header_name.strip()))


@lru_cache(maxsize=32)
def parse_trusted_proxy_networks(trusted_proxy_config):
    networks = []
    for entry in trusted_proxy_config.split(","):
        value = entry.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            log.warning("Ignoring invalid reverse proxy trusted network entry in config: %s", value)
    return tuple(networks)


def is_trusted_proxy_source(remote_addr, trusted_proxy_config):
    if not remote_addr or not trusted_proxy_config:
        return False

    try:
        remote_ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        log.warning("Unable to parse remote address '%s' for reverse proxy trust check", remote_addr)
        return False

    for network in parse_trusted_proxy_networks(trusted_proxy_config):
        if remote_ip in network:
            return True
    return False


def is_shared_secret_valid(provided_secret, expected_secret):
    if provided_secret is None or expected_secret is None:
        return False
    return hmac.compare_digest(str(provided_secret), str(expected_secret))
