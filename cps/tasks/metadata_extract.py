import os
import requests
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

class TaskMetadataExtract(CalibreTask):
    def __init__(self, task_message, media_url, original_url, current_user_name):
        super(TaskMetadataExtract, self).__init__(task_message)
        self.message = task_message
        self.media_url = media_url
        self.media_url_link = f'<a href="{media_url}" target="_blank">{media_url}</a>'
        self.original_url = original_url
        self.current_user_name = current_user_name
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0
        self.shelf_title = None
        self.shelf_id = None
        self.playlist_id = None

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
                self.message = f"Successfuly fetched metadata for {self.media_url_link}"

                # Database operations
                requested_urls = []
                with sqlite3.connect(XKLB_DB_FILE) as conn:
                    try:
                        cursor = conn.execute("PRAGMA table_info(media)")
                        columns = [column[1] for column in cursor.fetchall()]
                        if "error" in columns:
                            requested_urls = [row[0] for row in conn.execute("SELECT path FROM media WHERE error IS NULL AND path LIKE 'http%'").fetchall()]
                        else:
                            requested_urls = [row[0] for row in conn.execute("SELECT path FROM media WHERE path LIKE 'http%'").fetchall()]

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
                        self.message = f"{self.media_url_link} failed: {db_error}"

                    # get the shelf title
                    try:
                        self.playlist_id = self.media_url.split("/")[-1]
                        if "list=" in self.playlist_id:
                            self.playlist_id = self.playlist_id.split("list=")[-1]
                            self.shelf_title = conn.execute("SELECT title FROM playlists WHERE extractor_playlist_id = ?", (self.playlist_id,)).fetchone()[0]                
                    except sqlite3.Error as db_error:
                        if "no such table: playlists" in str(db_error):
                            log.info("No playlists table found in the database")
                            self.playlist_id = None
                        else:
                            log.error("An error occurred while trying to connect to the database: %s", db_error)
                            self.message = f"{self.media_url_link} failed to download: {db_error}"
                            self.progress = 0
                    finally:
                        log.info("Shelf title: %s", self.shelf_title)

                conn.close()

                if self.shelf_title:
                    response = requests.get(self.original_url, params={"current_user_name": self.current_user_name, "shelf_title": self.shelf_title})
                    if response.status_code == 200:
                        self.shelf_id = response.json()["shelf_id"]
                    else:
                        log.error("An error occurred while trying to send the shelf title to %s", self.original_url)

                num_requested_urls = len(requested_urls)

                # Add tasks for each requested URL
                for requested_url in requested_urls:
                    task_download = TaskDownload(_("Downloading %(url)s...", url=requested_url),
                                                 requested_url, self.original_url,
                                                 self.current_user_name, self.shelf_id
                                                    )
                    # Add the task to the worker thread
                    WorkerThread.add(self.current_user_name, task_download)

                    # Update progress incrementally after all tasks have been added
                    self.progress += 1 / num_requested_urls

            except Exception as e:
                log.error("An error occurred during the subprocess execution: %s", e)
                self.message = f"{self.media_url_link} failed: {e}"

            finally:
                if p.returncode == 0 or self.progress == 1.0:
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
