# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2021 OzzieIsaacs
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

import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from datetime import datetime
import base64
from flask_babel import gettext as _
from ..constants import BASE_DIR
from .. import logger


log = logger.create()

SCOPES = ['openid', 'https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/userinfo.email']

def setup_gmail(token):
    # If there are no (valid) credentials available, let the user log in.
    creds = None
    if "token" in token:
        creds = Credentials(
            token=token['token'],
            refresh_token=token['refresh_token'],
            token_uri=token['token_uri'],
            client_id=token['client_id'],
            client_secret=token['client_secret'],
            scopes=token['scopes'],
        )
        creds.expiry = datetime.fromisoformat(token['expiry'])

    if not creds or not creds.valid:
        # don't forget to dump one more time after the refresh
        # also, some file-locking routines wouldn't be needless
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            cred_file = os.path.join(BASE_DIR, 'gmail.json')
            if not os.path.exists(cred_file):
                raise Exception(_("Found no valid gmail.json file with OAuth information"))
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(BASE_DIR, 'gmail.json'), SCOPES)
            creds = flow.run_local_server(port=0)
            user_info = get_user_info(creds)
        return {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'expiry': creds.expiry.isoformat(),
            'email': user_info
        }
    return {}

def get_user_info(credentials):
    user_info_service = build(serviceName='oauth2', version='v2',credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    return user_info.get('email', "")

def send_messsage(token, msg):
    log.debug("Start sending e-mail via Gmail")
    creds = Credentials(
        token=token['token'],
        refresh_token=token['refresh_token'],
        token_uri=token['token_uri'],
        client_id=token['client_id'],
        client_secret=token['client_secret'],
        scopes=token['scopes'],
    )
    creds.expiry = datetime.fromisoformat(token['expiry'])
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build('gmail', 'v1', credentials=creds)
    message_as_bytes = msg.as_bytes()  # the message should converted from string to bytes.
    message_as_base64 = base64.urlsafe_b64encode(message_as_bytes)  # encode in base64 (printable letters coding)
    raw = message_as_base64.decode()  # convert to something  JSON serializable
    body = {'raw': raw}

    (service.users().messages().send(userId='me', body=body).execute())
    log.debug("E-mail send successfully via Gmail")
