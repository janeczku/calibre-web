#!/usr/bin/env python
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
from flask import Blueprint
from . import gdriveutils
from flask import flash, request, redirect, url_for, abort
from flask_babel import gettext as _
from . import app, config, ub, db
from flask_login import login_required
import json
from uuid import uuid4
from time import time
import tempfile
from shutil import move, copyfile
from .web import admin_required

try:
    from googleapiclient.errors import HttpError
except ImportError:
    pass

gdrive = Blueprint('gdrive', __name__)

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
        with open(os.path.join(config.get_main_dir,'gdrive_credentials'), 'w') as f:
            f.write(credentials.to_json())
    except ValueError as error:
        app.logger.error(error)
    return redirect(url_for('admin.configuration'))


@gdrive.route("/gdrive/watch/subscribe")
@login_required
@admin_required
def watch_gdrive():
    if not config.config_google_drive_watch_changes_response:
        with open(os.path.join(config.get_main_dir,'client_secrets.json'), 'r') as settings:
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
            settings = ub.session.query(ub.Settings).first()
            settings.config_google_drive_watch_changes_response = json.dumps(result)
            ub.session.merge(settings)
            ub.session.commit()
            settings = ub.session.query(ub.Settings).first()
            config.loadSettings()
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
        settings = ub.session.query(ub.Settings).first()
        settings.config_google_drive_watch_changes_response = None
        ub.session.merge(settings)
        ub.session.commit()
        config.loadSettings()
    return redirect(url_for('admin.configuration'))


@gdrive.route("/gdrive/watch/callback", methods=['GET', 'POST'])
def on_received_watch_confirmation():
    app.logger.debug(request.headers)
    if request.headers.get('X-Goog-Channel-Token') == gdrive_watch_callback_token \
            and request.headers.get('X-Goog-Resource-State') == 'change' \
            and request.data:

        data = request.data

        def updateMetaData():
            app.logger.info('Change received from gdrive')
            app.logger.debug(data)
            try:
                j = json.loads(data)
                app.logger.info('Getting change details')
                response = gdriveutils.getChangeById(gdriveutils.Gdrive.Instance().drive, j['id'])
                app.logger.debug(response)
                if response:
                    dbpath = os.path.join(config.config_calibre_dir, "metadata.db")
                    if not response['deleted'] and response['file']['title'] == 'metadata.db' and response['file']['md5Checksum'] != hashlib.md5(dbpath):
                        tmpDir = tempfile.gettempdir()
                        app.logger.info('Database file updated')
                        copyfile(dbpath, os.path.join(tmpDir, "metadata.db_" + str(current_milli_time())))
                        app.logger.info('Backing up existing and downloading updated metadata.db')
                        gdriveutils.downloadFile(None, "metadata.db", os.path.join(tmpDir, "tmp_metadata.db"))
                        app.logger.info('Setting up new DB')
                        # prevent error on windows, as os.rename does on exisiting files
                        move(os.path.join(tmpDir, "tmp_metadata.db"), dbpath)
                        db.setup_db()
            except Exception as e:
                app.logger.info(e.message)
                app.logger.exception(e)
        updateMetaData()
    return ''
