#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib
import threading
from datetime import datetime
import logging
import time
import socket
import sys
from email.generator import Generator
import web
from flask_babel import gettext as _
# from babel.dates import format_datetime
import re

try:
    from StringIO import StringIO
except ImportError as e:
    from io import StringIO

chunksize = 8192

STAT_WAITING = 0
STAT_FAIL = 1
STAT_STARTED = 2
STAT_FINISH_SUCCESS = 3


class email(smtplib.SMTP):

    transferSize = 0
    progress = 0

    def __init__(self, *args, **kwargs):
        smtplib.SMTP.__init__(self, *args, **kwargs)

    def data(self, msg):
        self.transferSize = len(msg)
        (code, resp) = smtplib.SMTP.data(self, msg)
        self.progress = 0
        return (code, resp)

    def send(self, str):
        """Send `str' to the server."""
        if self.debuglevel > 0:
            from __future__ import print_function
            print('send:', repr(str), file=sys.stderr)
        if hasattr(self, 'sock') and self.sock:
            try:
                if self.transferSize:
                    lock=threading.Lock()
                    lock.acquire()
                    self.transferSize = len(str)
                    lock.release()
                    for i in range(0, self.transferSize, chunksize):
                        self.sock.send(str[i:i+chunksize])
                        lock.acquire()
                        self.progress = i
                        lock.release()
                else:
                    self.sock.sendall(str)
            except socket.error:
                self.close()
                raise smtplib.SMTPServerDisconnected('Server not connected')
        else:
            raise smtplib.SMTPServerDisconnected('please run connect() first')

    def getTransferStatus(self):
        if self.transferSize:
            lock2 = threading.Lock()
            lock2.acquire()
            value = round(float(self.progress) / float(self.transferSize),2)*100
            lock2.release()
            return str(value) + ' %'
        else:
            return "100 %"

class email_SSL(email):

    def __init__(self, *args, **kwargs):
        smtplib.SMTP_SSL.__init__(self, *args, **kwargs)


class EMailThread(threading.Thread):

    def __init__(self):
        self._stopevent = threading.Event()
        threading.Thread.__init__(self)
        self.status = 0
        self.current = 0
        self.last = 0
        self.queue=list()
        self.UIqueue = list()
        self.asyncSMTP=None

    def run(self):
        while not self._stopevent.isSet():
            doLock = threading.Lock()
            doLock.acquire()
            if self.current != self.last:
                doLock.release()
                self.send_raw_email()
                self.current += 1
            else:
                doLock.release()
            time.sleep(1)

    def stop(self):
        self._stopevent.set()

    def get_send_status(self):
        if self.asyncSMTP:
            return self.asyncSMTP.getTransferStatus()
        else:
            return "0 %"

    def delete_completed_tasks(self):
        # muss gelockt werden
        for index, task in reversed(list(enumerate(self.UIqueue))):
            if task['progress'] == "100 %":
                # delete tasks
                self.queue.pop(index)
                self.UIqueue.pop(index)
                # if we are deleting entries before the current index, adjust the index
                # if self.current >= index:
                self.current -= 1
        self.last = len(self.queue)

    def get_taskstatus(self):
        if self.current  < len(self.queue):
            if self.queue[self.current]['status'] == STAT_STARTED:
                self.UIqueue[self.current]['progress'] = self.get_send_status()
                self.UIqueue[self.current]['runtime'] = self._formatRuntime(
                                                        datetime.now() - self.queue[self.current]['starttime'])

        return self.UIqueue

    def add_email(self, data, settings, recipient, user_name, type):
        # if more than 50 entries in the list, clean the list
        addLock = threading.Lock()
        addLock.acquire()
        if self.last >= 20:
            self.delete_completed_tasks()
        # progress, runtime, and status = 0
        self.queue.append({'data':data, 'settings':settings, 'recipent':recipient, 'starttime': 0,
                           'status': STAT_WAITING})
        self.UIqueue.append({'user': user_name, 'formStarttime': '', 'progress': " 0 %", 'type': type,
                             'runtime': '0 s', 'status': _('Waiting') })
        # access issue
        self.last=len(self.queue)
        addLock.release()

    def send_raw_email(self):
        obj=self.queue[self.current]
        # settings = ub.get_mail_settings()

        obj['data']['From'] = obj['settings']["mail_from"]
        obj['data']['To'] = obj['recipent']

        use_ssl = int(obj['settings'].get('mail_use_ssl', 0))

        # convert MIME message to string
        fp = StringIO()
        gen = Generator(fp, mangle_from_=False)
        gen.flatten(obj['data'])
        obj['data'] = fp.getvalue()

        # send email
        try:
            timeout = 600  # set timeout to 5mins

            org_stderr = sys.stderr
            #org_stderr2 = smtplib.stderr
            sys.stderr = StderrLogger()
            #smtplib.stderr = StderrLogger()

            self.queue[self.current]['status'] = STAT_STARTED
            self.UIqueue[self.current]['status'] = _('Started')
            self.queue[self.current]['starttime'] = datetime.now()
            self.UIqueue[self.current]['formStarttime'] = self.queue[self.current]['starttime']


            if use_ssl == 2:
                self.asyncSMTP = email_SSL(obj['settings']["mail_server"], obj['settings']["mail_port"], timeout)
            else:
                self.asyncSMTP = email(obj['settings']["mail_server"], obj['settings']["mail_port"], timeout)

            # link to logginglevel
            if web.ub.config.config_log_level != logging.DEBUG:
                self.asyncSMTP.set_debuglevel(0)
            else:
                self.asyncSMTP.set_debuglevel(1)
            if use_ssl == 1:
                self.asyncSMTP.starttls()
            if obj['settings']["mail_password"]:
                self.asyncSMTP.login(str(obj['settings']["mail_login"]), str(obj['settings']["mail_password"]))
            self.asyncSMTP.sendmail(obj['settings']["mail_from"], obj['recipent'], obj['data'])
            self.asyncSMTP.quit()
            self.queue[self.current]['status'] = STAT_FINISH_SUCCESS
            self.UIqueue[self.current]['status'] = _('Finished')
            self.UIqueue[self.current]['progress'] = "100 %"
            self.UIqueue[self.current]['runtime'] = self._formatRuntime(
                                                        datetime.now() - self.queue[self.current]['starttime'])

            sys.stderr = org_stderr
            #smtplib.stderr = org_stderr2

        except (socket.error, smtplib.SMTPRecipientsRefused, smtplib.SMTPException) as e:
            self.queue[self.current]['status'] = STAT_FAIL
            self.UIqueue[self.current]['status'] = _('Failed')
            self.UIqueue[self.current]['progress'] = "100 %"
            self.UIqueue[self.current]['runtime'] = self._formatRuntime(
                                                    datetime.now() - self.queue[self.current]['starttime'])
            web.app.logger.error(e)
        return None

    def _formatRuntime(self, runtime):
        val = re.split('\:|\.', str(runtime))[0:3]
        erg = list()
        for v in val:
            if int(v) > 0:
                erg.append(v)
        retVal = (':'.join(erg)).lstrip('0') + ' s'
        if retVal == ' s':
            retVal = '0 s'
        return retVal

class StderrLogger(object):

    buffer = ''

    def __init__(self):
        self.logger = web.app.logger

    def write(self, message):
        if message == '\n':
            self.logger.debug(self.buffer)
            print(self.buffer)
            self.buffer = ''
        else:
            self.buffer += message
