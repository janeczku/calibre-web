import os
import re
import requests
import select
import sqlite3
from datetime import datetime
from flask_babel import lazy_gettext as N_, gettext as _

from cps.constants import XKLB_DB_FILE
from cps.services.worker import CalibreTask, STAT_FINISH_SUCCESS, STAT_FAIL, STAT_STARTED, STAT_WAITING
from cps.subproc_wrapper import process_open
from .. import logger
from time import sleep

log = logger.create()

class TaskDownload(CalibreTask):
    def __init__(self, task_message, media_url, original_url, current_user_name, shelf_id):
        super(TaskDownload, self).__init__(task_message)
        self.message = task_message
        self.media_url = media_url
        self.media_url_link = f'<a href="{media_url}" target="_blank">{media_url}</a>'
        self.original_url = original_url
        self.current_user_name = current_user_name
        self.shelf_id = shelf_id
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0

    def run(self, worker_thread):
        """Run the download task"""
        self.worker_thread = worker_thread
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = os.getenv("LB_WRAPPER", "lb-wrapper")

        if self.media_url:
            subprocess_args = [lb_executable, "dl", self.media_url]
            log.info("Subprocess args: %s", subprocess_args)

            # Execute the download process using process_open
            try:
                p = process_open(subprocess_args, newlines=True)

                # Define the patterns for the subprocess output
                # Equivalent Regex's: https://github.com/iiab/calibre-web/blob/8684ffb491244e15ab927dfb390114240e483eb3/scripts/lb-wrapper#L59-L60
                pattern_progress = r"^downloading"
                pattern_success = r"\[{}\]:".format(self.media_url)

                complete_progress_cycle = 0

                fragment_stuck_timeout = 10  # seconds
                fragment_stuck_time = 0

                while p.poll() is None:
                    # Check if there's data available to read
                    rlist, _, _ = select.select([p.stdout], [], [], 0.1)
                    if rlist:
                        line = p.stdout.readline()
                        if line:
                            if re.search(pattern_success, line):
                                # 2024-01-10: 99% (a bit arbitrary) is explained here...
                                # https://github.com/iiab/calibre-web/pull/88#issuecomment-1885916421
                                self.progress = 0.99
                                break
                            elif re.search(pattern_progress, line):
                                percentage = int(re.search(r'\d+', line).group())
                                if percentage < 100:
                                    self.message = f"Downloading {self.media_url_link}..."
                                    self.end_time = datetime.now()
                                    self.progress = min(0.99, (complete_progress_cycle + (percentage / 100)) / 4)
                                if percentage == 100:
                                    complete_progress_cycle += 1
                                    if complete_progress_cycle == 4:
                                        break
                    else:
                        fragment_stuck_time += 0.1
                        if fragment_stuck_time >= fragment_stuck_timeout:
                            log.error("Download appears to be stuck.")
                            self.record_error_in_database("Download appears to be stuck.")
                            raise ValueError("Download appears to be stuck.")

                    sleep(0.1)
                
                p.wait()

                # Database operations
                with sqlite3.connect(XKLB_DB_FILE) as conn:
                    try:
                        requested_file = conn.execute("SELECT path FROM media WHERE webpath = ? AND path NOT LIKE 'http%'", (self.media_url,)).fetchone()[0]

                        # Abort if there is not a path
                        if not requested_file:
                            log.info("No path found in the database")
                            error = conn.execute("SELECT error, webpath FROM media WHERE error IS NOT NULL").fetchone()
                            if error:
                                log.error("[xklb] An error occurred while trying to download %s: %s", error[1], error[0])
                                self.message = f"{error[1]} failed to download: {error[0]}"
                            return
                    except sqlite3.Error as db_error:
                        log.error("An error occurred while trying to connect to the database: %s", db_error)
                        self.message = f"{self.media_url_link} failed to download: {db_error}"

                    self.message = self.message + "\n" + f"Almost done..."
                    response = requests.get(self.original_url, params={"requested_file": requested_file, "current_user_name": self.current_user_name, "shelf_id": self.shelf_id})
                    if response.status_code == 200:
                        log.info("Successfully sent the requested file to %s", self.original_url)
                        file_downloaded = response.json()["file_downloaded"]
                        self.message = f"Successfully downloaded {self.media_url_link} to <br><br>{file_downloaded}"
                        new_video_path = response.json()["new_book_path"]
                        new_video_path = next((os.path.join(new_video_path, file) for file in os.listdir(new_video_path) if file.endswith((".webm", ".mp4"))), None)
                        # 2024-02-17: Dedup Design Evolving... https://github.com/iiab/calibre-web/pull/125
                        conn.execute("UPDATE media SET path = ? WHERE webpath = ?", (new_video_path, self.media_url))
                        conn.execute("UPDATE media SET webpath = ? WHERE path = ?", (f"{self.media_url}&timestamp={int(datetime.now().timestamp())}", new_video_path))
                        self.progress = 1.0
                    else:
                        log.error("Failed to send the requested file to %s", self.original_url)
                        self.message = f"{self.media_url_link} failed to download: {response.status_code} {response.reason}"
                
                conn.close()

            except Exception as e:
                log.error("An error occurred during the subprocess execution: %s", e)
                self.message = f"{self.media_url_link} failed to download: {e}"
                self.record_error_in_database(str(e))

            finally:
                if p.returncode == 0 or self.progress == 1.0:
                    self.end_time = datetime.now()
                    self.stat = STAT_FINISH_SUCCESS
                    log.info("Download task for %s completed successfully", self.media_url)
                else:
                    self.end_time = datetime.now()                    
                    self.stat = STAT_FAIL

        else:
            log.info("No media URL provided - skipping download task")

    def record_error_in_database(self, error_message):
        """Record the error in the database"""
        with sqlite3.connect(XKLB_DB_FILE) as conn:
            # Check if the error column exists, if not, create it at the rightmost position
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(media)")
            columns = [column[1] for column in cursor.fetchall()]
            if "error" not in columns:
                conn.execute("ALTER TABLE media ADD COLUMN error TEXT")
            conn.execute("UPDATE media SET error = ? WHERE webpath = ?", (error_message, self.media_url))
            conn.commit()
        conn.close()

    @property
    def name(self):
        return N_("Download")

    def __str__(self):
        return f"Download task for {self.media_url}"

    @property
    def is_cancellable(self):
        return True
