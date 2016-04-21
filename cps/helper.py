#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cps import db, ub
from cps import config
from flask import current_app as app

import smtplib
import sys
import os
import traceback
import re
import unicodedata
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
    kindlegen = os.path.join(config.MAIN_DIR, "vendor", "kindlegen")
    if not os.path.exists(kindlegen):
        app.logger.error("make_mobi: kindlegen binary not found in: %s" % kindlegen)
        return None
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == 'EPUB').first()
    if not data:
        app.logger.error("make_mobi: epub format not found for book id: %d" % book_id)
        return None

    file_path = os.path.join(config.DB_ROOT, book.path, data.name)

    if os.path.exists(file_path + ".epub"):
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
            app.logger.error("make_mobi: kindlegen failed with error while converting book")
            return None
    else:
        app.logger.error("make_mobie: epub not found: %s.epub" % file_path)
        return None

def send_mail(book_id, kindle_mail):
    '''Send email with attachments'''
    is_mobi = False
    is_azw = False
    is_azw3 = False
    is_epub = False
    is_pdf = False
    file_path = None
    settings = ub.get_mail_settings()
    # create MIME message
    msg = MIMEMultipart()
    msg['From'] = settings["mail_from"]
    msg['To'] = kindle_mail
    msg['Subject'] = 'Send to Kindle'
    text = 'This email has been sent via calibre web.'
    msg.attach(MIMEText(text))

    use_ssl = settings.get('mail_use_ssl', 0)

    # attach files
        #msg.attach(self.get_attachment(file_path))

    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id)

    formats = {}

    for entry in data:
        if entry.format == "MOBI":
            formats["mobi"] = os.path.join(config.DB_ROOT, book.path, entry.name + ".mobi")
        if entry.format == "EPUB":
            formats["epub"] = os.path.join(config.DB_ROOT, book.path, entry.name + ".epub")
        if entry.format == "PDF":
            formats["pdf"] = os.path.join(config.DB_ROOT, book.path, entry.name + ".pdf")

    if len(formats) == 0:
        return "Could not find any formats suitable for sending by email"

    if 'mobi' in formats:
        msg.attach(get_attachment(formats['mobi']))
    elif 'epub' in formats:
        filepath = make_mobi(book.id)
        if filepath is not None:
            msg.attach(get_attachment(filepath))
        elif 'pdf' in formats:
            msg.attach(get_attachment(formats['pdf']))
    elif 'pdf' in formats:
        msg.attach(get_attachment(formats['pdf']))
    else:
        return "Could not find any formats suitable for sending by email"

    # convert MIME message to string
    fp = StringIO()
    gen = Generator(fp, mangle_from_=False)
    gen.flatten(msg)
    msg = fp.getvalue()

    # send email
    try:
        mailserver = smtplib.SMTP(settings["mail_server"],settings["mail_port"])
        mailserver.set_debuglevel(0)

        if int(use_ssl) == 1:
            mailserver.ehlo()
            mailserver.starttls()
            mailserver.ehlo()

        mailserver.login(settings["mail_login"], settings["mail_password"])
        mailserver.sendmail(settings["mail_login"], kindle_mail, msg)
        mailserver.quit()
    except (socket.error, smtplib.SMTPRecipientsRefused, smtplib.SMTPException), e:
        app.logger.error(traceback.print_exc())
        return "Failed to send mail: %s" % str(e)

    return None


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

def get_valid_filename(value, replace_whitespace=True):
    """
    Returns the given string converted to a string that can be used for a clean
    filename. Limits num characters to 128 max.
    """
    value = value[:128]
    re_slugify = re.compile('[^\w\s-]', re.UNICODE)
    value = unicodedata.normalize('NFKD', value)
    re_slugify = re.compile('[^\w\s-]', re.UNICODE)
    value = unicode(re_slugify.sub('', value).strip())
    if replace_whitespace:
        value = re.sub('[\s]+', '_', value, flags=re.U)
    value = value.replace(u"\u00DF", "ss")
    return value

def get_normalized_author(value):
    """
    Normalizes sorted author name
    """
    value = unicodedata.normalize('NFKD', value)
    value = re.sub('[^\w,\s]', '', value, flags=re.U)
    value = " ".join(value.split(", ")[::-1])
    return value
    
def update_dir_stucture(book_id):
    db.session.connection().connection.connection.create_function("title_sort",1,db.title_sort)
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    path = os.path.join(config.DB_ROOT, book.path)
    
    authordir = book.path.split("/")[0]
    new_authordir=get_valid_filename(book.authors[0].name, False)
    titledir = book.path.split("/")[1]
    new_titledir = get_valid_filename(book.title, False) + " (" + str(book_id) + ")"
    
    if titledir != new_titledir:
        new_title_path = os.path.join(os.path.dirname(path), new_titledir)
        os.rename(path, new_title_path)
        path = new_title_path
        book.path = book.path.split("/")[0] + "/" + new_titledir
    
    if authordir != new_authordir:
        new_author_path = os.path.join(os.path.join(config.DB_ROOT, new_authordir), os.path.basename(path))
        os.renames(path, new_author_path)
        book.path = new_authordir + "/" + book.path.split("/")[1]
    db.session.commit()
    
