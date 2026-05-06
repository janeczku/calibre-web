# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2020 pwr
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

from datetime import datetime

from flask_babel import lazy_gettext as N_

from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS


class TaskUpload(CalibreTask):
    def __init__(self, task_message, book_title):
        super(TaskUpload, self).__init__(task_message)
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_FINISH_SUCCESS
        self.progress = 1
        self.book_title = book_title

    def run(self, worker_thread):
        """Upload task doesn't have anything to do, it's simply a way to add information to the task list"""

    @property
    def name(self):
        return N_("Upload")

    def __str__(self):
        return "Upload {}".format(self.book_title)

    @property
    def is_cancellable(self):
        return False
