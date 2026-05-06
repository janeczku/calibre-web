# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2023 OzzieIsaacs
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

import datetime

from flask_babel import lazy_gettext as N_
from sqlalchemy.sql.expression import or_

from cps import logger, file_helper, ub
from cps.services.worker import CalibreTask


class TaskClean(CalibreTask):
    def __init__(self, task_message=N_('Delete temp folder contents')):
        super(TaskClean, self).__init__(task_message)
        self.log = logger.create()
        self.app_db_session = ub.get_new_session_instance()

    def run(self, worker_thread):
        # delete temp folder
        try:
            file_helper.del_temp_dir()
        except FileNotFoundError:
            pass
        except (PermissionError, OSError) as e:
            self.log.error("Error deleting temp folder: {}".format(e))
        # delete expired session keys
        self.log.debug("Deleted expired session_keys" )
        expiry = int(datetime.datetime.now().timestamp())
        try:
            self.app_db_session.query(ub.User_Sessions).filter(or_(ub.User_Sessions.expiry < expiry,
                                                               ub.User_Sessions.expiry == None)).delete()
            self.app_db_session.commit()
        except Exception as ex:
            self.log.debug('Error deleting expired session keys: ' + str(ex))
            self._handleError('Error deleting expired session keys: ' + str(ex))
            self.app_db_session.rollback()
            return

        self._handleSuccess()
        self.app_db_session.remove()

    @property
    def name(self):
        return "Clean up"

    @property
    def is_cancellable(self):
        return False
