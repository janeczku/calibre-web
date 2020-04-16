# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2019 pwr
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division, print_function, unicode_literals

from .. import logger


log = logger.create()


try: from . import goodreads_support
except ImportError as err:
    log.debug("Cannot import goodreads, showing authors-metadata will not work: %s", err)
    goodreads_support = None


try:
    from . import simpleldap as ldap
    from .simpleldap import ldapVersion
except ImportError as err:
    log.debug("Cannot import simpleldap, logging in with ldap will not work: %s", err)
    ldap = None
    ldapVersion = None

try:
    from . import SyncToken as SyncToken
    kobo = True
except ImportError as err:
    log.debug("Cannot import SyncToken, syncing books with Kobo Devices will not work: %s", err)
    kobo = None
    SyncToken = None
