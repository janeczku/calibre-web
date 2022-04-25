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

from urllib.request import urlopen

from flask_babel import lazy_gettext as N_

from cps import config, logger
from cps.services.worker import CalibreTask


class TaskReconnectDatabase(CalibreTask):
    def __init__(self, task_message=N_('Reconnecting Calibre database')):
        super(TaskReconnectDatabase, self).__init__(task_message)
        self.log = logger.create()
        self.listen_address = config.get_config_ipaddress()
        self.listen_port = config.config_port


    def run(self, worker_thread):
        address = self.listen_address if self.listen_address else 'localhost'
        port = self.listen_port if self.listen_port else 8083

        try:
            urlopen('http://' + address + ':' + str(port) + '/reconnect')
            self._handleSuccess()
        except Exception as ex:
            self._handleError('Unable to reconnect Calibre database: ' + str(ex))

    @property
    def name(self):
        return "Reconnect Database"

    @property
    def is_cancellable(self):
        return False
