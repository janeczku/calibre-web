import os
from datetime import datetime
from flask_babel import lazy_gettext as N_, gettext as _
from cps import logger


from cps.services.worker import CalibreTask
from cps.subproc_wrapper import process_open, process_wait

STAT_FINISH_SUCCESS = "finish_success"
STAT_RUNNING = "running"

class TaskDownload(CalibreTask):
    def __init__(self, task_message, media_url):
        super(TaskDownload, self).__init__(task_message)
        self.media_url = media_url
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_FINISH_SUCCESS
        self.progress = 1

    def get_yb_executable():
        yb_executable = os.getenv("YB_EXECUTABLE", "yb")
        return yb_executable
    
    def run(self, worker_thread):
        """Run the download task"""
        self.start_time = datetime.now()
        self.stat = STAT_RUNNING
        self.progress = 0

        yb_executable = self.get_yb_executable()

        if self.media_url:
            subprocess_args = [
                yb_executable,
                self.media_url,
            ]

            # Execute the download process using process_open
            p = process_open(subprocess_args)
            p.wait()

            # Define the pattern for the subprocess output
            pattern_analyze = r"Running ANALYZE"
            pattern_download = r"'action': 'download'"

            # Wait for the process to terminate and search for patterns in the output
            ret_val_analyze = process_wait(subprocess_args, pattern=pattern_analyze)
            if ret_val_analyze:
                matched_output_analyze = ret_val_analyze.group(0)
                logger.info("Matched output (ANALYZE): {}".format(matched_output_analyze))

            ret_val_download = process_wait(subprocess_args, pattern=pattern_download)
            if ret_val_download:
                matched_output_download = ret_val_download.group(0)
                logger.info("Matched output (download): {}".format(matched_output_download))


    @property
    def name(self):
        return N_("Download Media")

    def __str__(self):
        return "Download {}".format(self.media_url)

    @property
    def is_cancellable(self):
        return False
