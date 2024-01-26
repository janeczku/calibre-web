import os
import sqlite3
from datetime import datetime
from flask_babel import lazy_gettext as N_, gettext as _

from cps.constants import XKLB_DB_FILE
from cps.services.worker import WorkerThread
from cps.tasks.download import TaskDownload
from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS, STAT_FAIL, STAT_STARTED, STAT_WAITING
from cps.subproc_wrapper import process_open
from .. import logger

log = logger.create()

class TaskMediaMeta(CalibreTask):
    def __init__(self, task_message, media_url, original_url, current_user_name):
        super(TaskMediaMeta, self).__init__(task_message)
        self.message = task_message
        self.media_url = media_url
        self.original_url = original_url
        self.current_user_name = current_user_name
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0

    def run(self, worker_thread):
        """Run the metadata fetching task"""
        self.worker_thread = worker_thread
        log.info("Starting to fetch metadata for URL: %s", self.media_url)
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = os.getenv("LB_WRAPPER", "lb-wrapper")

        if self.media_url:
            subprocess_args = [lb_executable, "tubeadd", self.media_url]
            log.info("Subprocess args: %s", subprocess_args)

            # Execute the download process using process_open
            try:
                p = process_open(subprocess_args, newlines=True)

                p.wait()
                self.message = f"Successfuly fetched metadata for {self.media_url}"

                # Database operations
                requested_urls = []
                with sqlite3.connect(XKLB_DB_FILE) as conn:
                    shelf_title = None
                    try:
                        # Get the urls from the database
                        requested_urls = list(set([row[0] for row in conn.execute("SELECT path FROM media").fetchall() if row[0].startswith("http")]))

                        # Abort if there are no urls
                        if not requested_urls:
                            log.info("No urls found in the database")
                            error = conn.execute("SELECT error, webpath FROM media WHERE error IS NOT NULL").fetchone()
                            if error:
                                log.error("[xklb] An error occurred while trying to retrieve the data for %s: %s", error[1], error[0])
                                self.progress = 0
                                self.message = f"{error[1]} gave no data : {error[0]}"
                            return
                    except sqlite3.Error as db_error:
                        log.error("An error occurred while trying to connect to the database: %s", db_error)
                        self.message = f"{self.media_url} failed: {db_error}"

                    # get the shelf title
                    try:
                        shelf_title = conn.execute("SELECT title FROM playlists").fetchone()[0]                               
                    except sqlite3.Error as db_error:
                        if "no such table: playlists" in str(db_error):
                            log.info("No playlists table found in the database")
                        else:
                            log.error("An error occurred while trying to connect to the database: %s", db_error)
                            self.message = f"{self.media_url} failed to download: {db_error}"
                            self.progress = 0
                    finally:
                        log.info("Shelf title: %s", shelf_title)

                conn.close()

                # call the download task for each requested file
                for requested_url in requested_urls:
                    # self.worker_thread.add_task("download", requested_url, self.original_url, self.current_user_name)
                    WorkerThread.add(self.current_user_name, TaskDownload(_("Downloading %(url)s...", url=requested_url), requested_url, self.original_url, self.current_user_name, shelf_title))
                    # based on the number of urls, the progress will be updated
                    self.progress += 1 / len(requested_urls)

            except Exception as e:
                log.error("An error occurred during the subprocess execution: %s", e)
                self.message = f"{self.media_url} failed: {e}"

            finally:
                if p.returncode == 0:
                    self.stat = STAT_FINISH_SUCCESS
                else:
                    self.stat = STAT_FAIL

        else:
            log.info("No media URL provided - skipping download task")

    @property
    def name(self):
        return N_("Metadata Fetch")

    def __str__(self):
        return f"Metadata fetch task for {self.media_url}"

    @property
    def is_cancellable(self):
        return True  # Change to True if the download task should be cancellable
