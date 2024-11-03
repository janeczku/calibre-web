# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2024 quantum5
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

import signal

from . import calibre_db, config, logger, ub

log = logger.create()


def sighup_handler(_signum, _frame):
    log.warning('received SIGHUP; reconnecting to calibre database')
    calibre_db.reconnect_db(config, ub.app_DB_path)


def register_signals():
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, sighup_handler)
