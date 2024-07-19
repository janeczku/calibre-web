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

import os
import hashlib
import json
from uuid import uuid4
from time import time
from shutil import move, copyfile

from flask import Blueprint, flash, request, redirect, url_for, abort
from flask_babel import gettext as _

from . import logger, gdriveutils, config, ub, calibre_db, csrf
from .admin import admin_required
from .file_helper import get_temp_dir
from .usermanagement import user_login_required

gdrive = Blueprint('gdrive', __name__, url_prefix='/gdrive')
log = logger.create()

try:
    from googleapiclient.errors import HttpError
except ImportError as err:
    log.debug("Cannot import googleapiclient, using GDrive will not work: %s", err)

current_milli_time = lambda: int(round(time() * 1000))

gdrive_watch_callback_token = 'target=calibreweb-watch_files'  # nosec


@gdrive.route("/authenticate")
@user_login_required
@admin_required
def authenticate_google_drive():
    try:
        authUrl = gdriveutils.Gauth.Instance().auth.GetAuthUrl()
    except gdriveutils.InvalidConfigError:
        flash(_('Google Drive setup not completed, try to deactivate and activate Google Drive again'),
              category="error")
        return redirect(url_for('web.index'))
    return redirect(authUrl)


@gdrive.route("/callback")
def google_drive_callback():
    auth_code = request.args.get('code')
    if not auth_code:
        abort(403)
    try:
        credentials = gdriveutils.Gauth.Instance().auth.flow.step2_exchange(auth_code)
        with open(gdriveutils.CREDENTIALS, 'w') as f:
            f.write(credentials.to_json())
    except (ValueError, AttributeError) as error:
        log.error(error)
    return redirect(url_for('admin.db_configuration'))


@gdrive.route("/watch/subscribe")
@user_login_required
@admin_required
def watch_gdrive():
    if not config.config_google_drive_watch_changes_response:
        with open(gdriveutils.CLIENT_SECRETS, 'r') as settings:
            filedata = json.load(settings)
        address = filedata['web']['redirect_uris'][0].rstrip('/').replace('/gdrive/callback', '/gdrive/watch/callback')
        notification_id = str(uuid4())
        try:
            result = gdriveutils.watchChange(gdriveutils.Gdrive.Instance().drive, notification_id,
                                 'web_hook', address, gdrive_watch_callback_token, current_milli_time() + 604800*1000)

            config.config_google_drive_watch_changes_response = result
            config.save()
        except HttpError as e:
            reason = json.loads(e.content)['error']['errors'][0]
            if reason['reason'] == 'push.webhookUrlUnauthorized':
                flash(_('Callback domain is not verified, '
                        'please follow steps to verify domain in google developer console'), category="error")
            else:
                flash(reason['message'], category="error")

    return redirect(url_for('admin.db_configuration'))


@gdrive.route("/watch/revoke")
@user_login_required
@admin_required
def revoke_watch_gdrive():
    last_watch_response = config.config_google_drive_watch_changes_response
    if last_watch_response:
        try:
            gdriveutils.stopChannel(gdriveutils.Gdrive.Instance().drive, last_watch_response['id'],
                                    last_watch_response['resourceId'])
        except (HttpError, AttributeError):
            pass
        config.config_google_drive_watch_changes_response = {}
        config.save()
    return redirect(url_for('admin.db_configuration'))


try:
    @csrf.exempt
    @gdrive.route("/watch/callback", methods=['GET', 'POST'])
    def on_received_watch_confirmation():
        if not config.config_google_drive_watch_changes_response:
            return ''
        if request.headers.get('X-Goog-Channel-Token') != gdrive_watch_callback_token \
                or request.headers.get('X-Goog-Resource-State') != 'change' \
                or not request.data:
            return ''

        log.debug('%r', request.headers)
        log.debug('%r', request.data)
        log.info('Change received from gdrive')

        try:
            j = json.loads(request.data)
            log.info('Getting change details')
            response = gdriveutils.getChangeById(gdriveutils.Gdrive.Instance().drive, j['id'])
            log.debug('%r', response)
            if response:
                dbpath = os.path.join(config.config_calibre_dir, "metadata.db").encode()
                if not response['deleted'] and response['file']['title'] == 'metadata.db' \
                  and response['file']['md5Checksum'] != hashlib.md5(dbpath):  # nosec
                    tmp_dir = get_temp_dir()

                    log.info('Database file updated')
                    copyfile(dbpath, os.path.join(tmp_dir, "metadata.db_" + str(current_milli_time())))
                    log.info('Backing up existing and downloading updated metadata.db')
                    gdriveutils.downloadFile(None, "metadata.db", os.path.join(tmp_dir, "tmp_metadata.db"))
                    log.info('Setting up new DB')
                    # prevent error on windows, as os.rename does on existing files, also allow cross hdd move
                    move(os.path.join(tmp_dir, "tmp_metadata.db"), dbpath)
                    calibre_db.reconnect_db(config, ub.app_DB_path)
        except Exception as ex:
            log.error_or_exception(ex)
        return ''
except AttributeError:
    pass
