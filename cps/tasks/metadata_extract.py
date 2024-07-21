import os
import re
import requests
import sqlite3
from datetime import datetime
from flask_babel import lazy_gettext as N_, gettext as _

from cps.constants import XKLB_DB_FILE, MAX_VIDEOS_PER_DOWNLOAD
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
        self.media_url = self._format_media_url(media_url)
        self.media_url_link = f'<a href="{self.media_url}" target="_blank">{self.media_url}</a>'
        self.original_url = self._format_original_url(original_url)
        self.is_playlist = None
        self.current_user_name = current_user_name
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_WAITING
        self.progress = 0
        self.columns = None
        self.shelf_title = None
        self.shelf_id = None
        self.unavailable = []

    def _format_media_url(self, media_url):
        return media_url.split("&")[0] if "&" in media_url else media_url

    def _format_original_url(self, original_url):
        # (?=...) is a "lookahead assertion" https://docs.python.org/3/library/re.html#regular-expression-syntax
        return re.sub(r"/media(?=\?|$)", r"/meta", original_url)

    def _execute_subprocess(self, subprocess_args):
        try:
            p = process_open(subprocess_args, newlines=True)
            while p.poll() is None:
                line = p.stdout.readline()
                if "[download] Downloading playlist:" in line:
                    self.is_playlist = True
                    self.shelf_title = line.split("Downloading playlist: ")[1].strip()
                    break
            p.wait()
            self.message = self.media_url_link + "..."
            return p
        except Exception as e:
            log.error("An error occurred during subprocess execution: %s", e)
            self.message = f"{self.media_url_link} failed: {e}"
            return None

    def _remove_shorts_from_db(self, conn):
        conn.execute("DELETE FROM media WHERE path LIKE '%shorts%'")
        conn.commit()

    def _fetch_requested_urls(self, conn):
        try:
            cursor = conn.execute("PRAGMA table_info(media)")
            self.columns = [column[1] for column in cursor.fetchall()]
            if "live_status" not in self.columns:
                conn.execute("ALTER TABLE media ADD COLUMN live_status TEXT")
            if "error" not in self.columns:
                conn.execute("ALTER TABLE media ADD COLUMN error TEXT")
            query = "SELECT path, duration, live_status FROM media WHERE path LIKE 'http%' AND (error IS NULL OR error = '')"
            rows = conn.execute(query).fetchall()
            requested_urls = {}
            for path, duration, live_status in rows:
                if duration is not None and duration > 0:
                    requested_urls[path] = {"duration": duration, "live_status": live_status}
                else:
                    self.unavailable.append(path)
            return requested_urls
        except sqlite3.Error as db_error:
            log.error("An error occurred while trying to connect to the database: %s", db_error)
            self.message = f"{self.media_url_link} failed: An error occurred ({db_error}) while trying to connect to the database."
            return {}

    def _send_shelf_title(self):
        try:
            response = requests.get(self.original_url, params={"current_user_name": self.current_user_name, "shelf_title": self.shelf_title})
            if response.status_code == 200:
                self.shelf_id = response.json()["shelf_id"]
                self.shelf_title = response.json()["shelf_title"]
            else:
                log.error("Received unexpected status code %s while sending the shelf title to %s", response.status_code, self.original_url)
        except Exception as e:
            log.error("An error occurred during the shelf title sending: %s", e)

    def _update_metadata(self, requested_urls):
        failed_urls = []
        subprocess_args_list = [[os.getenv("LB_WRAPPER", "lb-wrapper"), "tubeadd", requested_url] for requested_url in requested_urls.keys()]

        for index, subprocess_args in enumerate(subprocess_args_list):
            try:
                p = self._execute_subprocess(subprocess_args)
                if p is not None:
                    self.progress = (index + 1) / len(subprocess_args_list)
                else:
                    failed_urls.append(subprocess_args[2])
                p.wait()
            except Exception as e:
                log.error("An error occurred during updating the metadata of %s: %s", subprocess_args[2], e)
                self.message = f"{subprocess_args[2]} failed: {e}"
                failed_urls.append(subprocess_args[2])

        requested_urls = {url: requested_urls[url] for url in requested_urls.keys() if "shorts" not in url and url not in failed_urls}

    def _calculate_views_per_day(self, requested_urls, conn):
        now = datetime.now()
        for requested_url in requested_urls.keys():
            try:
                view_count = conn.execute("SELECT view_count FROM media WHERE path = ?", (requested_url,)).fetchone()[0]
                time_uploaded = datetime.utcfromtimestamp(conn.execute("SELECT time_uploaded FROM media WHERE path = ?", (requested_url,)).fetchone()[0])
                days_since_publish = (now - time_uploaded).days or 1
                requested_urls[requested_url]["views_per_day"] = view_count / days_since_publish
            except Exception as e:
                log.error("An error occurred during the calculation of views per day for %s: %s", requested_url, e)
                self.message = f"{requested_url} failed: {e}"

    def _sort_and_limit_requested_urls(self, requested_urls):
        return dict(sorted(requested_urls.items(), key=lambda item: item[1]["views_per_day"], reverse=True)[:min(MAX_VIDEOS_PER_DOWNLOAD, len(requested_urls))])

    def _add_download_tasks_to_worker(self, requested_urls):
        for index, (requested_url, url_data) in enumerate(requested_urls.items()):
            task_download = TaskDownload(_("Downloading %(url)s...", url=requested_url),
                                         requested_url, self.original_url,
                                         self.current_user_name, self.shelf_id, duration=str(url_data["duration"]), live_status=url_data["live_status"])
            WorkerThread.add(self.current_user_name, task_download)
            num_requested_urls = len(requested_urls)
            total_duration = sum(url_data["duration"] for url_data in requested_urls.values())
            self.message = self.media_url_link + f"<br><br>" \
                           f"Number of Videos: {index + 1}/{num_requested_urls}<br>" \
                           f"Total Duration: {datetime.utcfromtimestamp(total_duration).strftime('%H:%M:%S')}"
            if self.shelf_title:
                shelf_url = re.sub(r"/meta(?=\?|$)", r"/shelf", self.original_url) + f"/{self.shelf_id}"
                self.message += f"<br><br>Shelf Title: <a href='{shelf_url}' target='_blank'>{self.shelf_title}</a>"
            if self.unavailable:
                self.message += "<br><br>Unavailable Video(s):<br>" + "<br>".join(f'<a href="{url}" target="_blank">{url}</a>' for url in self.unavailable)
                upcoming_live_urls = [url for url, url_data in requested_urls.items() if url_data["live_status"] == "is_upcoming"]
                live_urls = [url for url, url_data in requested_urls.items() if url_data["live_status"] == "is_live"]
                if upcoming_live_urls:
                    self.message += "<br><br>Upcoming Live Video(s):<br>" + "<br>".join(f'<a href="{url}" target="_blank">{url}</a>' for url in upcoming_live_urls)
                if live_urls:
                    self.message += "<br><br>Live Video(s):<br>" + "<br>".join(f'<a href="{url}" target="_blank">{url}</a>' for url in live_urls)


    def run(self, worker_thread):
        self.worker_thread = worker_thread
        log.info("Starting to fetch metadata for URL: %s", self.media_url)
        self.start_time = self.end_time = datetime.now()
        self.stat = STAT_STARTED
        self.progress = 0

        lb_executable = os.getenv("LB_WRAPPER", "lb-wrapper")
        subprocess_args = [lb_executable, "tubeadd", self.media_url]

        p = self._execute_subprocess(subprocess_args)
        if p is None:
            self.stat = STAT_FAIL
            return

        with sqlite3.connect(XKLB_DB_FILE) as conn:
            self._remove_shorts_from_db(conn)
            requested_urls = self._fetch_requested_urls(conn)
            if not requested_urls:
                if self.unavailable:
                    self.message = f"{self.media_url_link} failed: Video not available."
                elif error_message := conn.execute("SELECT error FROM media WHERE ? LIKE '%' || extractor_id || '%'", (self.media_url,)).fetchone()[0]:
                    self.message = f"{self.media_url_link} failed previously with this error: {error_message}<br><br>To force a retry, submit the URL again."
                    media_id = conn.execute("SELECT id FROM media WHERE webpath = ?", (self.media_url,)).fetchone()[0]
                    conn.execute("DELETE FROM media WHERE webpath = ?", (self.media_url,))
                    conn.execute("DELETE FROM captions WHERE media_id = ?", (media_id,))
                else:
                    self.message = f"{self.media_url_link} failed: An error occurred while trying to fetch the requested URLs."
                self.stat = STAT_FAIL

            elif self.is_playlist:
                self._send_shelf_title()
                self._update_metadata(requested_urls)
                self._calculate_views_per_day(requested_urls, conn)
                requested_urls = self._sort_and_limit_requested_urls(requested_urls)
                conn.execute("UPDATE playlists SET path = ? WHERE path = ?", (f"{self.media_url}&timestamp={int(datetime.now().timestamp())}", self.media_url))
            else:
                try:
                    extractor_id = conn.execute("SELECT extractor_id FROM media WHERE ? LIKE '%' || extractor_id || '%'", (self.media_url,)).fetchone()[0]
                    requested_urls = {url: requested_urls[url] for url in requested_urls.keys() if extractor_id in url}
                except Exception as e:
                    log.error("An error occurred during the selection of the extractor ID: %s", e)
                    self.message = f"{self.media_url_link} failed: {e}"
                    return

            self._add_download_tasks_to_worker(requested_urls)
        conn.close()

        self.progress = 1.0
        self.stat = STAT_FINISH_SUCCESS

    @property
    def name(self):
        return N_("Metadata Fetch")

    def __str__(self):
        return f"Metadata fetch task for {self.media_url}"

    @property
    def is_cancellable(self):
        return True  # Change to True if the download task should be cancellable
