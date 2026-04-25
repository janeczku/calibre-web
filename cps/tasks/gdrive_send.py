# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#  License: GPLv3

import os

from flask_babel import lazy_gettext as N_

from cps.services.worker import CalibreTask
from cps.embed_helper import do_calibre_export
from cps import logger, config
from cps import gdriveutils

log = logger.create()


class TaskGdriveSend(CalibreTask):
    """Background task to upload a book file to a user's personal Google Drive."""

    def __init__(self, book_path, filename, book_title, user_gdrive_token, gdrive_folder, book_id=0):
        super().__init__(N_("Send to Google Drive"))
        self.book_path = book_path
        self.filename = filename
        self.book_title = book_title
        self.user_gdrive_token = user_gdrive_token
        self.gdrive_folder = gdrive_folder
        self.book_id = book_id

    def run(self, worker_thread):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            token = self.user_gdrive_token
            creds = Credentials(
                token=token['token'],
                refresh_token=token['refresh_token'],
                token_uri=token['token_uri'],
                client_id=token['client_id'],
                client_secret=token['client_secret'],
                scopes=token.get('scopes', ['https://www.googleapis.com/auth/drive.file']),
            )
            if token.get('expiry'):
                from datetime import datetime
                creds.expiry = datetime.fromisoformat(token['expiry'])

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

            # Read the book file
            file_data = self._get_file(self.book_path, self.filename)
            if not file_data:
                return

            # Write to temp file for upload
            from cps.file_helper import get_temp_dir
            tmp_dir = get_temp_dir()
            tmp_file = os.path.join(tmp_dir, self.filename)
            with open(tmp_file, 'wb') as f:
                f.write(file_data)

            self.progress = 0.3

            service = build('drive', 'v3', credentials=creds)

            # Find or create target folder
            parent_id = None
            if self.gdrive_folder:
                parent_id = self._find_or_create_folder(service, self.gdrive_folder)

            self.progress = 0.5

            # Upload file
            file_metadata = {'name': self.filename}
            if parent_id:
                file_metadata['parents'] = [parent_id]

            media = MediaFileUpload(tmp_file, resumable=True)
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            self.progress = 0.9

            # Cleanup
            try:
                os.remove(tmp_file)
            except OSError:
                pass

            self._handleSuccess()
            log.info("Book '%s' uploaded to Google Drive successfully", self.book_title)

        except Exception as ex:
            log.error_or_exception(ex)
            self._handleError("Error uploading to Google Drive: {}".format(ex))

    def _find_or_create_folder(self, service, folder_name):
        """Find existing folder or create it in the user's Drive root."""
        query = ("mimeType='application/vnd.google-apps.folder' "
                 "and name='{}' and trashed=false").format(folder_name.replace("'", "\\'"))
        results = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
        # Create folder
        meta = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = service.files().create(body=meta, fields='id').execute()
        return folder['id']

    def _get_file(self, book_path, filename):
        """Read book file from local storage or library GDrive."""
        calibre_path = config.get_book_path()
        extension = os.path.splitext(filename)[1][1:]

        if config.config_use_google_drive:
            df = gdriveutils.getFileFromEbooksFolder(book_path, filename)
            if df:
                datafile = os.path.join(calibre_path, book_path, filename)
                if not os.path.exists(os.path.join(calibre_path, book_path)):
                    os.makedirs(os.path.join(calibre_path, book_path))
                df.GetContentFile(datafile)
            else:
                self._handleError("File not found on Google Drive")
                return None
            if config.config_binariesdir and config.config_embed_metadata:
                data_path, data_file = do_calibre_export(self.book_id, extension)
                datafile = os.path.join(data_path, data_file + "." + extension)
            with open(datafile, 'rb') as f:
                data = f.read()
            os.remove(datafile)
        else:
            datafile = os.path.join(calibre_path, book_path, filename)
            try:
                if config.config_binariesdir and config.config_embed_metadata:
                    data_path, data_file = do_calibre_export(self.book_id, extension)
                    datafile = os.path.join(data_path, data_file + "." + extension)
                with open(datafile, 'rb') as f:
                    data = f.read()
                if config.config_binariesdir and config.config_embed_metadata:
                    os.remove(datafile)
            except IOError as e:
                log.error_or_exception(e)
                self._handleError("The requested file could not be read.")
                return None
        return data

    @property
    def name(self):
        return "Google Drive Upload"

    @property
    def is_cancellable(self):
        return False
