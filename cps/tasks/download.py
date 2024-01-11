import os
import re
import requests
import sqlite3
from datetime import datetime
from flask import flash
from flask_babel import lazy_gettext as N_, gettext as _

from cps.constants import SURVEY_DB_FILE
from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS, STAT_FAIL, STAT_STARTED, STAT_WAITING
from cps.subproc_wrapper import process_open
from .. import logger

log = logger.create()

class TaskDownload(CalibreTask):
    def __init__(self, task_message, media_url, original_url, current_user_name):
        super(TaskDownload, self).__init__(task_message)
        self.message = task_message
        self.media_url = media_url
        self.original_url = original_url
        self.current_user_name = current_user_name
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0

    def run(self, worker_thread):
        """Run the download task"""
        self.worker_thread = worker_thread
        log.info("Starting download task for URL: %s", self.media_url)
        self.start_time  = self.end_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = self.get_lb_executable()

        if self.media_url:
            subprocess_args = [lb_executable, self.media_url]
            log.info("Subprocess args: %s", subprocess_args)

            # Execute the download process using process_open
            try:
                p = process_open(subprocess_args, newlines=True)

                # Define the pattern for the subprocess output
                # Equivalent Regex: https://github.com/iiab/calibre-web/blob/3c3c77f4dbf54ff093c3e3a68ac9b93a522c4070/scripts/lb-wrapper#L26
                pattern_progress = r"^downloading"

                while p.poll() is None:
                    line = p.stdout.readline()
                    if line:
                        if pattern_progress in line:
                            percentage = int(re.search(r'\d+', line).group())
                            # 2024-01-10: 99% (a bit arbitrary) is explained here...
                            # https://github.com/iiab/calibre-web/pull/88#issuecomment-1885916421
                            if percentage < 100:
                                self.message = f"Downloading learning media from {self.media_url}"
                                self.progress = percentage / 100
                            else:
                                self.message = f"Processing learning media from {self.media_url}"
                                self.progress = 0.99

                p.wait()
                self.progress = 1.0
                self.message = f"Downloaded learning media from {self.media_url}"


                # Database operations
                requested_files = []
                conn = sqlite3.connect(SURVEY_DB_FILE)
                c = conn.cursor()
                c.execute("SELECT path FROM media")
                for row in c.fetchall():
                    requested_files.append(row[0])

                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playlists'")
                if c.fetchone():
                    c.execute("SELECT title FROM playlists")
                    shelf_title = c.fetchone()[0]
                else:
                    shelf_title = None
                conn.close()

                if self.original_url:
                    response = requests.get(self.original_url, params={"requested_files": requested_files, "current_user_name": self.current_user_name, "shelf_title": shelf_title})
                    if response.status_code == 200:
                        log.info("Successfully sent the list of requested files to %s", self.original_url)
                    else:
                        log.error("Failed to send the list of requested files to %s", self.original_url)

                # Set the progress to 100% and the end time to the current time
                self.progress = 1
                self.end_time = datetime.now()
                self.stat = STAT_FINISH_SUCCESS

            except Exception as e:
                log.error("An error occurred during the subprocess execution: %s", e)
                # Handling subprocess failure or errors
                flash("Failed to complete the download process", category="error")
                self.stat = STAT_FAIL

        else:
            log.info("No media URL provided")

    def get_lb_executable(self):
        lb_executable = os.getenv("LB_WRAPPER", "lb-wrapper")
        return lb_executable

    @property
    def name(self):
        return N_("Download")

    def __str__(self):
        return "Download %s" % self.media_url

    @property
    def is_cancellable(self):
        return True  # Change to True if the download task should be cancellable
