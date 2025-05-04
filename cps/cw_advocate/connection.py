#
# Copyright 2015 Jordan Milne
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Source: https://github.com/JordanMilne/Advocate

import ipaddress
import socket
from socket import timeout as SocketTimeout

from urllib3.connection import HTTPSConnection, HTTPConnection
from urllib3.exceptions import ConnectTimeoutError
from urllib3.util.connection import _set_socket_options
from urllib3.util.connection import create_connection as old_create_connection

from . import addrvalidator
from .exceptions import UnacceptableAddressException


def advocate_getaddrinfo(host, port, get_canonname=False):
    addrinfo = socket.getaddrinfo(
        host,
        port,
        0,
        socket.SOCK_STREAM,
        0,
        # We need what the DNS client sees the hostname as, correctly handles
        # IDNs and tricky things like `private.foocorp.org\x00.google.com`.
        # All IDNs will be converted to punycode.
        socket.AI_CANONNAME if get_canonname else 0,
    )
    return fix_addrinfo(addrinfo)


def fix_addrinfo(records):
    """
    Propagate the canonname across records and parse IPs

    I'm not sure if this is just the behaviour of `getaddrinfo` on Linux, but
    it seems like only the first record in the set has the canonname field
    populated.
    """
    def fix_record(record, canonname):
        sa = record[4]
        sa = (ipaddress.ip_address(sa[0]),) + sa[1:]
        return record[0], record[1], record[2], canonname, sa

    canonname = None
    if records:
        # Apparently the canonical name is only included in the first record?
        # Add it to all of them.
        assert(len(records[0]) == 5)
        canonname = records[0][3]
    return tuple(fix_record(x, canonname) for x in records)


# Lifted from requests' urllib3, which in turn lifted it from `socket.py`. Oy!
def validating_create_connection(address,
                       timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                       source_address=None, socket_options=None,
                       validator=None):
    """Connect to *address* and return the socket object.

    Convenience function.  Connect to *address* (a 2-tuple ``(host,
    port)``) and return the socket object.  Passing the optional
    *timeout* parameter will set the timeout on the socket instance
    before attempting to connect.  If no *timeout* is supplied, the
    global default timeout setting returned by :func:`getdefaulttimeout`
    is used.  If *source_address* is set it must be a tuple of (host, port)
    for the socket to bind as a source address before making the connection.
    An host of '' or port 0 tells the OS to use the default.
    """

    host, port = address
    # We can skip asking for the canon name if we're not doing hostname-based
    # blacklisting.
    need_canonname = False
    if validator.hostname_blacklist:
        need_canonname = True
        # We check both the non-canonical and canonical hostnames so we can
        # catch both of these:
        # CNAME from nonblacklisted.com -> blacklisted.com
        # CNAME from blacklisted.com -> nonblacklisted.com
        if not validator.is_hostname_allowed(host):
            raise UnacceptableAddressException(host)

    err = None
    addrinfo = advocate_getaddrinfo(host, port, get_canonname=need_canonname)
    if addrinfo:
        if validator.autodetect_local_addresses:
            local_addresses = addrvalidator.determine_local_addresses()
        else:
            local_addresses = []
        for res in addrinfo:
            # Are we allowed to connect with this result?
            if not validator.is_addrinfo_allowed(
                res,
                _local_addresses=local_addresses,
            ):
                continue
            af, socktype, proto, canonname, sa = res
            # Unparse the validated IP
            sa = (sa[0].exploded,) + sa[1:]
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)

                # If provided, set socket level options before connecting.
                # This is the only addition urllib3 makes to this function.
                _set_socket_options(sock, socket_options)

                if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                    sock.settimeout(timeout)
                if source_address:
                    sock.bind(source_address)
                sock.connect(sa)
                return sock

            except socket.error as _:
                err = _
                if sock is not None:
                    sock.close()
                    sock = None

        if err is None:
            # If we got here, none of the results were acceptable
            err = UnacceptableAddressException(address)
    if err is not None:
        raise err
    else:
        raise socket.error("getaddrinfo returns an empty list")


# TODO: Is there a better way to add this to multiple classes with different
# base classes? I tried a mixin, but it used the base method instead.
def _validating_new_conn(self):
    """ Establish a socket connection and set nodelay settings on it.

    :return: New socket connection.
    """
    extra_kw = {}
    if self.source_address:
        extra_kw['source_address'] = self.source_address

    if self.socket_options:
        extra_kw['socket_options'] = self.socket_options

    try:
        # Hack around HTTPretty's patched sockets
        # TODO: some better method of hacking around it that checks if we
        # _would have_ connected to a private addr?
        conn_func = validating_create_connection
        if socket.getaddrinfo.__module__.startswith("httpretty"):
            conn_func = old_create_connection
        else:
            extra_kw["validator"] = self._validator

        conn = conn_func(
            (self.host, self.port),
            self.timeout,
            **extra_kw
        )

    except SocketTimeout:
        raise ConnectTimeoutError(
            self, "Connection to %s timed out. (connect timeout=%s)" %
            (self.host, self.timeout))

    return conn


# Don't silently break if the private API changes across urllib3 versions
assert(hasattr(HTTPConnection, '_new_conn'))
assert(hasattr(HTTPSConnection, '_new_conn'))


class ValidatingHTTPConnection(HTTPConnection):
    _new_conn = _validating_new_conn

    def __init__(self, *args, **kwargs):
        self._validator = kwargs.pop("validator")
        HTTPConnection.__init__(self, *args, **kwargs)


class ValidatingHTTPSConnection(HTTPSConnection):
    _new_conn = _validating_new_conn

    def __init__(self, *args, **kwargs):
        self._validator = kwargs.pop("validator")
        HTTPSConnection.__init__(self, *args, **kwargs)
