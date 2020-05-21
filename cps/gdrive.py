# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, cervinko, jkrehm, bodybybuddha, ok11,
#                            andy29485, idalin, Kyosfonica, wuqi, Kennyl, lemmsh,
#                            falgh1, grunjol, csitko, ytils, xybydy, trasba, vrabe,
#                            ruben-herold, marblepebble, JackED42, SiphonSquirrel,
#                            apetresc, nanu-c, mutschler
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division, print_function, unicode_literals
import os
import sys
import hashlib
import json
import tempfile
from uuid import uuid4
from time import time
from shutil import move, copyfile

from flask import Blueprint, flash, request, redirect, url_for, abort
from flask_babel import gettext as _
from flask_login import login_required

try:
    from googleapiclient.errors import HttpError
except ImportError:
    pass

from . import logger, gdriveutils, config, ub, calibre_db
from .web import admin_required


gdrive = Blueprint('gdrive', __name__)
log = logger.create()

current_milli_time = lambda: int(round(time() * 1000))

gdrive_watch_callback_token = 'target=calibreweb-watch_files'


@gdrive.route("/gdrive/authenticate")
@login_required
@admin_required
def authenticate_google_drive():
    try:
        authUrl = gdriveutils.Gauth.Instance().auth.GetAuthUrl()
    except gdriveutils.InvalidConfigError:
        flash(_(u'Google Drive setup not completed, try to deactivate and activate Google Drive again'),
              category="error")
        return redirect(url_for('web.index'))
    return redirect(authUrl)


@gdrive.route("/gdrive/callback")
def google_drive_callback():
    auth_code = request.args.get('code')
    if not auth_code:
        abort(403)
    try:
        credentials = gdriveutils.Gauth.Instance().auth.flow.step2_exchange(auth_code)
        with open(gdriveutils.CREDENTIALS, 'w') as f:
            f.write(credentials.to_json())
    except ValueError as error:
        log.error(error)
    return redirect(url_for('admin.configuration'))


@gdrive.route("/gdrive/watch/subscribe")
@login_required
@admin_required
def watch_gdrive():
    if not config.config_google_drive_watch_changes_response:
        with open(gdriveutils.CLIENT_SECRETS, 'r') as settings:
            filedata = json.load(settings)
        if filedata['web']['redirect_uris'][0].endswith('/'):
            filedata['web']['redirect_uris'][0] = filedata['web']['redirect_uris'][0][:-((len('/gdrive/callback')+1))]
        else:
            filedata['web']['redirect_uris'][0] = filedata['web']['redirect_uris'][0][:-(len('/gdrive/callback'))]
        address = '%s/gdrive/watch/callback' % filedata['web']['redirect_uris'][0]
        notification_id = str(uuid4())
        try:
            result = gdriveutils.watchChange(gdriveutils.Gdrive.Instance().drive, notification_id,
                               'web_hook', address, gdrive_watch_callback_token, current_milli_time() + 604800*1000)
            config.config_google_drive_watch_changes_response = json.dumps(result)
            # after save(), config_google_drive_watch_changes_response will be a json object, not string
            config.save()
        except HttpError as e:
            reason=json.loads(e.content)['error']['errors'][0]
            if reason['reason'] == u'push.webhookUrlUnauthorized':
                flash(_(u'Callback domain is not verified, please follow steps to verify domain in google developer console'), category="error")
            else:
                flash(reason['message'], category="error")

    return redirect(url_for('admin.configuration'))


@gdrive.route("/gdrive/watch/revoke")
@login_required
@admin_required
def revoke_watch_gdrive():
    last_watch_response = config.config_google_drive_watch_changes_response
    if last_watch_response:
        try:
            gdriveutils.stopChannel(gdriveutils.Gdrive.Instance().drive, last_watch_response['id'],
                                    last_watch_response['resourceId'])
        except HttpError:
            pass
        config.config_google_drive_watch_changes_response = None
        config.save()
    return redirect(url_for('admin.configuration'))


@gdrive.route("/gdrive/watch/callback", methods=['GET', 'POST'])
def on_received_watch_confirmation():
    log.debug('%r', request.headers)
    if request.headers.get('X-Goog-Channel-Token') == gdrive_watch_callback_token \
            and request.headers.get('X-Goog-Resource-State') == 'change' \
            and request.data:

        data = request.data

        def updateMetaData():
            log.info('Change received from gdrive')
            log.debug('%r', data)
            try:
                j = json.loads(data)
                log.info('Getting change details')
                response = gdriveutils.getChangeById(gdriveutils.Gdrive.Instance().drive, j['id'])
                log.debug('%r', response)
                if response:
                    if sys.version_info < (3, 0):
                        dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
                    else:
                        dbpath = os.path.join(config.config_calibre_dir, "metadata.db").encode()
                    if not response['deleted'] and response['file']['title'] == 'metadata.db' \
                       and response['file']['md5Checksum'] != hashlib.md5(dbpath):
                        tmpDir = tempfile.gettempdir()
                        log.info('Database file updated')
                        copyfile(dbpath, os.path.join(tmpDir, "metadata.db_" + str(current_milli_time())))
                        log.info('Backing up existing and downloading updated metadata.db')
                        gdriveutils.downloadFile(None, "metadata.db", os.path.join(tmpDir, "tmp_metadata.db"))
                        log.info('Setting up new DB')
                        # prevent error on windows, as os.rename does on exisiting files
                        move(os.path.join(tmpDir, "tmp_metadata.db"), dbpath)
                        calibre_db.setup_db(config, ub.app_DB_path)
            except Exception as e:
                log.exception(e)
        updateMetaData()
    return ''
