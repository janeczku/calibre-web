# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2018 OzzieIsaacs
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import argparse
import socket

from .constants import CONFIG_DIR as _CONFIG_DIR
from .constants import STABLE_VERSION as _STABLE_VERSION
from .constants import NIGHTLY_VERSION as _NIGHTLY_VERSION
from .constants import DEFAULT_SETTINGS_FILE, DEFAULT_GDRIVE_FILE


def version_info():
    if _NIGHTLY_VERSION[1].startswith('$Format'):
        return "Calibre-Web version: %s - unknown git-clone" % _STABLE_VERSION['version'].replace("b", " Beta")
    return "Calibre-Web version: %s -%s" % (_STABLE_VERSION['version'].replace("b", " Beta"), _NIGHTLY_VERSION[1])


class CliParameter(object):

    def __init__(self):
        self.user_credentials = None
        self.ip_address = None
        self.allow_localhost = None
        self.reconnect_enable = None
        self.memory_backend = None
        self.dry_run = None
        self.certfilepath = None
        self.keyfilepath = None
        self.gd_path = None
        self.settings_path = None
        self.logpath = None

    def init(self):
        self.arg_parser()

    def arg_parser(self):
        parser = argparse.ArgumentParser(description='Calibre Web is a web app providing '
                                                     'a interface for browsing, reading and downloading eBooks\n',
                                         prog='cps.py')
        parser.add_argument('-p', metavar='path', help='path and name to settings db, e.g. /opt/cw.db')
        parser.add_argument('-g', metavar='path', help='path and name to gdrive db, e.g. /opt/gd.db')
        parser.add_argument('-c', metavar='path', help='path and name to SSL certfile, '
                                                       'e.g. /opt/test.cert, works only in combination with keyfile')
        parser.add_argument('-k', metavar='path', help='path and name to SSL keyfile, e.g. /opt/test.key, '
                                                       'works only in combination with certfile')
        parser.add_argument('-o', metavar='path', help='path and name Calibre-Web logfile')
        parser.add_argument('-v', '--version', action='version', help='Shows version number '
                                                                      'and exits Calibre-Web',
                            version=version_info())
        parser.add_argument('-i', metavar='ip-address', help='Server IP-Address to listen')
        parser.add_argument('-m', action='store_true',
                            help='Use Memory-backend as limiter backend, use this parameter '
                                 'in case of miss configured backend')
        parser.add_argument('-s', metavar='user:pass',
                            help='Sets specific username to new password and exits Calibre-Web')
        parser.add_argument('-l', action='store_true', help='Allow loading covers from localhost')
        parser.add_argument('-d', action='store_true', help='Dry run of updater to check file permissions '
                                                            'in advance and exits Calibre-Web')
        parser.add_argument('-r', action='store_true', help='Enable public database reconnect '
                                                            'route under /reconnect')
        args = parser.parse_args()

        self.logpath = args.o or ""
        self.settings_path = args.p or os.path.join(_CONFIG_DIR, DEFAULT_SETTINGS_FILE)
        self.gd_path = args.g or os.path.join(_CONFIG_DIR, DEFAULT_GDRIVE_FILE)

        if os.path.isdir(self.settings_path):
            self.settings_path = os.path.join(self.settings_path, DEFAULT_SETTINGS_FILE)

        if os.path.isdir(self.gd_path):
            self.gd_path = os.path.join(self.gd_path, DEFAULT_GDRIVE_FILE)

        # handle and check parameter for ssl encryption
        self.certfilepath = None
        self.keyfilepath = None
        if args.c:
            if os.path.isfile(args.c):
                self.certfilepath = args.c
            else:
                print("Certfile path is invalid. Exiting...")
                sys.exit(1)

        if args.c == "":
            self.certfilepath = ""

        if args.k:
            if os.path.isfile(args.k):
                self.keyfilepath = args.k
            else:
                print("Keyfile path is invalid. Exiting...")
                sys.exit(1)

        if (args.k and not args.c) or (not args.k and args.c):
            print("Certfile and Keyfile have to be used together. Exiting...")
            sys.exit(1)

        if args.k == "":
            self.keyfilepath = ""

        # overwrite limiter backend
        self.memory_backend = args.m or None
        # dry run updater
        self.dry_run = args.d or None
        # enable reconnect endpoint for docker database reconnect
        self.reconnect_enable = args.r or os.environ.get("CALIBRE_RECONNECT", None)
        # load covers from localhost
        self.allow_localhost = args.l or os.environ.get("CALIBRE_LOCALHOST", None)
        # handle and check ip address argument
        self.ip_address = args.i or None
        if self.ip_address:
            try:
                # try to parse the given ip address with socket
                if hasattr(socket, 'inet_pton'):
                    if ':' in self.ip_address:
                        socket.inet_pton(socket.AF_INET6, self.ip_address)
                    else:
                        socket.inet_pton(socket.AF_INET, self.ip_address)
                else:
                    # on Windows python < 3.4, inet_pton is not available
                    # inet_atom only handles IPv4 addresses
                    socket.inet_aton(self.ip_address)
            except socket.error as err:
                print(self.ip_address, ':', err)
                sys.exit(1)

        # handle and check user password argument
        self.user_credentials = args.s or None
        if self.user_credentials and ":" not in self.user_credentials:
            print("No valid 'username:password' format")
            sys.exit(3)
