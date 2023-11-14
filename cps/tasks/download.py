import os
import requests
import sqlite3
from datetime import datetime
from flask import flash
from flask_babel import lazy_gettext as N_, gettext as _
from flask_login import current_user

from cps import ub
from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS, STAT_FAIL, STAT_STARTED, STAT_WAITING
from cps.subproc_wrapper import process_open
from sqlalchemy.exc import OperationalError, InvalidRequestError
from .. import shelf, ub, logger

log = logger.create()

class TaskDownload(CalibreTask):
    def __init__(self, task_message, media_url, original_url, current_user_name):
        super(TaskDownload, self).__init__(task_message)
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
        shelf_id = None
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
                pattern_analyze = r"Running ANALYZE"
                pattern_download = r"'action': 'download'"

                while p.poll() is None:
                    line = p.stdout.readline()
                    if line:
                        log.info(line)
                        if pattern_analyze in line:
                            log.info("Matched output (ANALYZE): %s", line)
                            self.progress = 0.1
                        if pattern_download in line:
                            log.info("Matched output (download): %s", line)
                            self.progress = 0.5
                            
                        p.wait()


                        # Database operations
                        requested_files = []
                        download_db_path = "/var/tmp/download.db"
                        conn = sqlite3.connect(download_db_path)
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

                        if shelf_title:
                            shelf_object = ub.Shelf()
                            is_public = 1
                            if shelf.check_shelf_is_unique(shelf_title, is_public, shelf_id=None):
                                shelf_object.name = shelf_title
                                shelf_object.is_public = is_public
                                shelf_object.user_id = int(current_user.id)
                                ub.session.add(shelf_object)
                                shelf_action = "created"
                                flash_text = _("Shelf %(title)s created", title=shelf_title)
                                try:
                                    ub.session.commit()
                                    shelf_id = shelf_object.id
                                    log.info("Shelf %s %s", shelf_title, shelf_action)
                                    flash(flash_text, category="success")
                                except (OperationalError, InvalidRequestError) as ex:
                                    ub.session.rollback()
                                    log.error("Settings Database error: %s", ex)
                                    flash(_("Oops! Database Error: %(error)s.", error=ex.orig), category="error")
                                except Exception as ex:
                                    ub.session.rollback()
                                    log.error("Error occurred: %s", ex)
                                    flash(_("There was an error"), category="error")

                        # Log the list of requested files
                        log.info("Requested files: %s", requested_files)
                        requested_files = str(requested_files)
                        if self.original_url:
                            response = requests.get(self.original_url, params={"shelf_id": shelf_id, "requested_files": requested_files, "current_user_name": self.current_user_name})
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
