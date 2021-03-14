from __future__ import division, print_function, unicode_literals

from datetime import datetime
from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS

class TaskUpload(CalibreTask):
    def __init__(self, taskMessage):
        super(TaskUpload, self).__init__(taskMessage)
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_FINISH_SUCCESS
        self.progress = 1

    def run(self, worker_thread):
        """Upload task doesn't have anything to do, it's simply a way to add information to the task list"""

    @property
    def name(self):
        return "Upload"
