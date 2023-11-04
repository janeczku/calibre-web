import os
import sqlite3
from datetime import datetime
from flask import flash
from flask_babel import lazy_gettext as N_, gettext as _
from flask_login import current_user
from cps import logger

from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS
from cps.subproc_wrapper import process_open, process_wait
from sqlalchemy.exc import OperationalError, InvalidRequestError
from .. import shelf, ub

log = logger.create()

class TaskDownload(CalibreTask):
    def __init__(self, task_message, media_url):
        super(TaskDownload, self).__init__(task_message)
        self.media_url = media_url
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_FINISH_SUCCESS
        self.progress = 1

    def run(self, worker_thread):
        """Run the download task"""
        log.info("Starting download task for URL: %s", self.media_url)
        shelf_id = None
        self.start_time  = self.end_time = datetime.now()
        self.stat = STAT_RUNNING
        self.progress = 0

        yb_executable = self.get_yb_executable()

        if self.media_url:
            subprocess_args = [yb_executable, self.media_url]

            # Execute the download process using process_open
            try:
                p = process_open(subprocess_args)
                p.wait()

                # Define the pattern for the subprocess output
                pattern_analyze = r"Running ANALYZE"
                pattern_download = r"'action': 'download'"

                # Wait for the process to terminate and search for patterns in the output
                ret_val_analyze = process_wait(subprocess_args, pattern=pattern_analyze)
                if ret_val_analyze:
                    matched_output_analyze = ret_val_analyze.group(0)
                    log.info("Matched output (ANALYZE): %s", matched_output_analyze)

                ret_val_download = process_wait(subprocess_args, pattern=pattern_download)
                if ret_val_download:
                    matched_output_download = ret_val_download.group(0)
                    log.info("Matched output (download): %s", matched_output_download)

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
                    # Return the list of requested files and the shelf ID
                    return requested_files, shelf_id

                # Set the progress to 100% and the end time to the current time
                self.progress = 100
                self.end_time = datetime.now()
                self.stat = STAT_FINISH_SUCCESS

            except Exception as e:
                log.error("An error occurred during the subprocess execution: %s", e)
                # Handling subprocess failure or errors
                flash("Failed to complete the download process", category="error")

        else:
            log.info("No media URL provided")

    def get_yb_executable(self):
        yb_executable = os.getenv("YB_EXECUTABLE", "yb")
        return yb_executable

    @property
    def name(self):
        return N_("Download Media")

    def __str__(self):
        return "Download %s" % self.media_url

    @property
    def is_cancellable(self):
        return True  # Change to True if the download task should be cancellable
