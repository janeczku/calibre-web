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

import functools
import fnmatch
import ipaddress
import re

try:
    import netifaces
    HAVE_NETIFACES = True
except ImportError:
    netifaces = None
    HAVE_NETIFACES = False

from .exceptions import NameserverException, ConfigException


def canonicalize_hostname(hostname):
    """Lowercase and punycodify a hostname"""
    # We do the lowercasing after IDNA encoding because we only want to
    # lowercase the *ASCII* chars.
    # TODO: The differences between IDNA2003 and IDNA2008 might be relevant
    # to us, but both specs are damn confusing.
    return str(hostname.encode("idna").lower(), 'utf-8')


def determine_local_addresses():
    """Get all IPs that refer to this machine according to netifaces"""
    if not HAVE_NETIFACES:
        raise ConfigException("Tried to determine local addresses, "
                              "but netifaces module was not importable")
    ips = []
    for interface in netifaces.interfaces():
        if_families = netifaces.ifaddresses(interface)
        for family_kind in {netifaces.AF_INET, netifaces.AF_INET6}:
            addrs = if_families.get(family_kind, [])
            for addr in (x.get("addr", "") for x in addrs):
                if family_kind == netifaces.AF_INET6:
                    # We can't do anything sensible with the scope here
                    addr = addr.split("%")[0]
                ips.append(ipaddress.ip_network(addr))
    return ips


def add_local_address_arg(func):
    """Add the "_local_addresses" kwarg if it's missing

    IMO this information shouldn't be cached between calls (what if one of the
    adapters got a new IP at runtime?,) and we don't want each function to
    recalculate it. Just recalculate it if the caller didn't provide it for us.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if "_local_addresses" not in kwargs:
            if self.autodetect_local_addresses:
                kwargs["_local_addresses"] = determine_local_addresses()
            else:
                kwargs["_local_addresses"] = []
        return func(self, *args, **kwargs)
    return wrapper


class AddrValidator:
    _6TO4_RELAY_NET = ipaddress.ip_network("192.88.99.0/24")
    # Just the well known prefix, DNS64 servers can set their own
    # prefix, but in practice most probably don't.
    _DNS64_WK_PREFIX = ipaddress.ip_network("64:ff9b::/96")
    DEFAULT_PORT_WHITELIST = {80, 8080, 443, 8443, 8000}

    def __init__(
            self,
            ip_blacklist=None,
            ip_whitelist=None,
            port_whitelist=None,
            port_blacklist=None,
            hostname_blacklist=None,
            allow_ipv6=False,
            allow_teredo=False,
            allow_6to4=False,
            allow_dns64=False,
            # Must be explicitly set to "False" if you don't want to try
            # detecting local interface addresses with netifaces.
            autodetect_local_addresses=True,
    ):
        if not port_blacklist and not port_whitelist:
            # An assortment of common HTTPS? ports.
            port_whitelist = self.DEFAULT_PORT_WHITELIST.copy()
        self.ip_blacklist = ip_blacklist or set()
        self.ip_whitelist = ip_whitelist or set()
        self.port_blacklist = port_blacklist or set()
        self.port_whitelist = port_whitelist or set()
        # TODO: ATM this can contain either regexes or globs that are converted
        # to regexes upon every check. Create a collection that automagically
        # converts them to regexes on insert?
        self.hostname_blacklist = hostname_blacklist or set()
        self.allow_ipv6 = allow_ipv6
        self.allow_teredo = allow_teredo
        self.allow_6to4 = allow_6to4
        self.allow_dns64 = allow_dns64
        self.autodetect_local_addresses = autodetect_local_addresses

    @add_local_address_arg
    def is_ip_allowed(self, addr_ip, _local_addresses=None):
        if not isinstance(addr_ip,
                          (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            addr_ip = ipaddress.ip_address(addr_ip)

        # The whitelist should take precedence over the blacklist so we can
        # punch holes in blacklisted ranges
        if any(addr_ip in net for net in self.ip_whitelist):
            return True

        if any(addr_ip in net for net in self.ip_blacklist):
            return False

        if any(addr_ip in net for net in _local_addresses):
            return False

        if addr_ip.version == 4:
            if not addr_ip.is_private:
                # IPs for carrier-grade NAT. Seems weird that it doesn't set
                # `is_private`, but we need to check `not is_global`
                if not ipaddress.ip_network(addr_ip).is_global:
                    return False
        elif addr_ip.version == 6:
            # You'd better have a good reason for enabling IPv6
            # because Advocate's techniques don't work well without NAT.
            if not self.allow_ipv6:
                return False

            # v6 addresses can also map to IPv4 addresses! Tricky!
            v4_nested = []
            if addr_ip.ipv4_mapped:
                v4_nested.append(addr_ip.ipv4_mapped)
            # WTF IPv6? Why you gotta have a billion tunneling mechanisms?
            # XXX: Do we even really care about these? If we're tunneling
            # through public servers we shouldn't be able to access
            # addresses on our private network, right?
            if addr_ip.sixtofour:
                if not self.allow_6to4:
                    return False
                v4_nested.append(addr_ip.sixtofour)
            if addr_ip.teredo:
                if not self.allow_teredo:
                    return False
                # Check both the client *and* server IPs
                v4_nested.extend(addr_ip.teredo)
            if addr_ip in self._DNS64_WK_PREFIX:
                if not self.allow_dns64:
                    return False
                # When using the well-known prefix the last 4 bytes
                # are the IPv4 addr
                v4_nested.append(ipaddress.ip_address(addr_ip.packed[-4:]))

            if not all(self.is_ip_allowed(addr_v4) for addr_v4 in v4_nested):
                return False

            # fec0::*, apparently deprecated?
            if addr_ip.is_site_local:
                return False
        else:
            raise ValueError("Unsupported IP version(?): %r" % addr_ip)

        # 169.254.XXX.XXX, AWS uses these for autoconfiguration
        if addr_ip.is_link_local:
            return False
        # 127.0.0.1, ::1, etc.
        if addr_ip.is_loopback:
            return False
        if addr_ip.is_multicast:
            return False
        # 192.168.XXX.XXX, 10.XXX.XXX.XXX
        if addr_ip.is_private:
            return False
        # 255.255.255.255, ::ffff:XXXX:XXXX (v6->v4) mapping
        if addr_ip.is_reserved:
            return False
        # There's no reason to connect directly to a 6to4 relay
        if addr_ip in self._6TO4_RELAY_NET:
            return False
        # 0.0.0.0
        if addr_ip.is_unspecified:
            return False

        # It doesn't look bad, so... it's must be ok!
        return True

    def _hostname_matches_pattern(self, hostname, pattern):
        # If they specified a string, just assume they only want basic globbing.
        # This stops people from not realizing they're dealing in REs and
        # not escaping their periods unless they specifically pass in an RE.
        # This has the added benefit of letting us sanely handle globbed
        # IDNs by default.
        if isinstance(pattern, str):
            # convert the glob to a punycode glob, then a regex
            pattern = fnmatch.translate(canonicalize_hostname(pattern))

        hostname = canonicalize_hostname(hostname)
        # Down the line the hostname may get treated as a null-terminated string
        # (as with `socket.getaddrinfo`.) Try to account for that.
        #
        #    >>> socket.getaddrinfo("example.com\x00aaaa", 80)
        #    [(2, 1, 6, '', ('93.184.216.34', 80)), [...]
        no_null_hostname = hostname.split("\x00")[0]

        return any(re.match(pattern, x.strip(".")) for x
                   in (no_null_hostname, hostname))

    def is_hostname_allowed(self, hostname):
        # Sometimes (like with "external" services that your IP has privileged
        # access to) you might not always know the IP range to blacklist access
        # to, or the `A` record might change without you noticing.
        # For e.x.: `foocorp.external.org`.
        #
        # Another option is doing something like:
        #
        #     for addrinfo in socket.getaddrinfo("foocorp.external.org", 80):
        #         global_validator.ip_blacklist.add(ip_address(addrinfo[4][0]))
        #
        # but that's not always a good idea if they're behind a third-party lb.
        for pattern in self.hostname_blacklist:
            if self._hostname_matches_pattern(hostname, pattern):
                return False
        return True

    @add_local_address_arg
    def is_addrinfo_allowed(self, addrinfo, _local_addresses=None):
        assert(len(addrinfo) == 5)
        # XXX: Do we care about any of the other elements? Guessing not.
        family, socktype, proto, canonname, sockaddr = addrinfo

        # The 4th elem inaddrinfo may either be a touple of two or four items,
        # depending on whether we're dealing with IPv4 or v6
        if len(sockaddr) == 2:
            # v4
            ip, port = sockaddr
        elif len(sockaddr) == 4:
            # v6
            # XXX: what *are* `flow_info` and `scope_id`? Anything useful?
            # Seems like we can figure out all we need about the scope from
            # the `is_<x>` properties.
            ip, port, flow_info, scope_id = sockaddr
        else:
            raise ValueError("Unexpected addrinfo format %r" % sockaddr)

        # Probably won't help protect against SSRF, but might prevent our being
        # used to attack others' non-HTTP services. See
        # http://www.remote.org/jochen/sec/hfpa/
        if self.port_whitelist and port not in self.port_whitelist:
            return False
        if port in self.port_blacklist:
            return False

        if self.hostname_blacklist:
            if not canonname:
                raise NameserverException(
                    "addrinfo must contain the canon name to do blacklisting "
                    "based on hostname. Make sure you use the "
                    "`socket.AI_CANONNAME` flag, and that each record contains "
                    "the canon name. Your DNS server might also be garbage."
                )

            if not self.is_hostname_allowed(canonname):
                return False

        return self.is_ip_allowed(ip, _local_addresses=_local_addresses)
