#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cps import db, ub
from cps import config

import smtplib
import sys
import os
import traceback
from StringIO import StringIO
from email import encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.generator import Generator
import subprocess

def update_download(book_id, user_id):
    check = ub.session.query(ub.Downloads).filter(ub.Downloads.user_id == user_id).filter(ub.Downloads.book_id == book_id).first()

    if not check:
        new_download = ub.Downloads(user_id=user_id, book_id=book_id)
        ub.session.add(new_download)
        ub.session.commit()

def make_mobi(book_id):
    kindlegen = os.path.join(config.MAIN_DIR, "kindlegen")
    if not os.path.exists(kindlegen):
        return False
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()

    file_path = os.path.join(config.DB_ROOT, book.path, book.data[0].name)
    # print os.path.getsize(file_path + ".epub")
    if os.path.exists(file_path + ".epub") and not os.path.exists(file_path + ".mobi"):
        # print u"conversion started for %s" % book.title
        check = subprocess.call([kindlegen, file_path + ".epub"], stdout=subprocess.PIPE)
        if not check or check < 2:
            book.data.append(db.Data(
                    name=book.data[0].name,
                    format="MOBI",
                    book=book.id,
                    uncompressed_size=os.path.getsize(file_path + ".mobi")
                ))
            db.session.commit()
            return file_path + ".mobi"
        else:
            return False
    else:
        return file_path + ".mobi"

def send_mail(book_id, kindle_mail):
    '''Send email with attachments'''

    is_mobi = False
    is_epub = False
    # create MIME message
    msg = MIMEMultipart()
    msg['From'] = config.MAIL_FROM
    msg['To'] = kindle_mail
    msg['Subject'] = 'Sent to Kindle'
    text = 'This email has been automatically sent by library.'
    msg.attach(MIMEText(text))

    # attach files
        #msg.attach(self.get_attachment(file_path))

    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    for format in book.data:
        if format.format == "MOBI":
            is_mobi == True
        if format.format == "EPUB":
            is_epub = True


    if is_mobi:
        file_path = os.path.join(config.DB_ROOT, book.path, format.name + ".mobi")

    if is_epub and not is_mobi:
        file_path = make_mobi(book.id)

    if file_path:
        msg.attach(get_attachment(file_path))
    else:
        return False

    #sys.exit()
    # convert MIME message to string
    fp = StringIO()
    gen = Generator(fp, mangle_from_=False)
    gen.flatten(msg)
    msg = fp.getvalue()

    # send email
    try:
        mail_server = smtplib.SMTP(host=config.MAIL_SERVER,
                                      port=config.MAIL_PORT)
        mail_server.login(config.MAIL_LOGIN, config.MAIL_PASSWORD)
        mail_server.sendmail(config.MAIL_LOGIN, kindle_mail, msg)
        mail_server.close()
    except smtplib.SMTPException:
        traceback.print_exc()
        return False
        #sys.exit(7)

    return True


def get_attachment(file_path):
    '''Get file as MIMEBase message'''

    try:
        file_ = open(file_path, 'rb')
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(file_.read())
        file_.close()
        encoders.encode_base64(attachment)

        attachment.add_header('Content-Disposition', 'attachment',
                              filename=os.path.basename(file_path))
        return attachment
    except IOError:
        traceback.print_exc()
        message = ('The requested file could not be read. Maybe wrong '
                   'permissions?')
        return None
