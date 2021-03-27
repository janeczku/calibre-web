from __future__ import print_function
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from .constants import BASE_DIR
import json
from datetime import datetime

subject = "Test"
msg = "Testnachricht"
sender = "matthias1.knopp@googlemail.com"
receiver = "matthias.knopp@web.de"

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def setup_gmail(config):
    token = config.mail_gmail_token
    # if config.mail_gmail_token != "{}":
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
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(BASE_DIR, 'gmail.json'), SCOPES)
            creds = flow.run_local_server(port=0)

        return {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'expiry': creds.expiry.isoformat(),
        }

# implement your storage logic here, e.g. just good old json.dump() / json.load()

# service = build('gmail', 'v1', credentials=creds)
# message = MIMEText(msg)
# message['to'] = receiver
# message['from'] = sender
# message['subject'] = subject
# raw = base64.urlsafe_b64encode(message.as_bytes())
# raw = raw.decode()
# body = {'raw' : raw}
# message = (service.users().messages().send(userId='me', body=body).execute())
