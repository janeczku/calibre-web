# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2020 mmonkey
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

from flask_babel import lazy_gettext as N_

from cps import config, logger, db, ub
from cps.services.worker import CalibreTask


class TaskReconnectDatabase(CalibreTask):
    def __init__(self, task_message=N_('Reconnecting Calibre database')):
        super(TaskReconnectDatabase, self).__init__(task_message)
        self.log = logger.create()
        self.calibre_db = db.CalibreDB(expire_on_commit=False, init=True)

    def run(self, worker_thread):
        self.calibre_db.reconnect_db(config, ub.app_DB_path)
        self.calibre_db.session.close()
        self._handleSuccess()

    @property
    def name(self):
        return "Reconnect Database"

    @property
    def is_cancellable(self):
        return False
