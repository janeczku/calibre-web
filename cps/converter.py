#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import ub
import db
import re
import web
from flask_babel import gettext as _


RET_FAIL = 0
RET_SUCCESS = 1


def versionKindle():
    versions = _(u'not installed')
    if os.path.exists(ub.config.config_converterpath):
        try:
            p = subprocess.Popen(ub.config.config_converterpath, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.wait()
            for lines in p.stdout.readlines():
                if isinstance(lines, bytes):
                    lines = lines.decode('utf-8')
                if re.search('Amazon kindlegen\(', lines):
                    versions = lines
        except Exception:
            versions = _(u'Excecution permissions missing')
    return {'kindlegen' : versions}


def versionCalibre():
    versions = _(u'not installed')
    if os.path.exists(ub.config.config_converterpath):
        try:
            p = subprocess.Popen(ub.config.config_converterpath + ' --version', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.wait()
            for lines in p.stdout.readlines():
                if isinstance(lines, bytes):
                    lines = lines.decode('utf-8')
                if re.search('.*\(calibre', lines):
                    versions = lines
        except Exception:
            versions = _(u'Excecution permissions missing')
    return {'Calibre converter' : versions}


def convert_kindlegen(file_path, book):
    error_message = None
    # vendorpath = os.path.join(os.path.normpath(os.path.dirname(os.path.realpath(__file__)) +
    #                                           os.sep + "../vendor" + os.sep))
    #if sys.platform == "win32":
    #    kindlegen = (os.path.join(vendorpath, u"kindlegen.exe")).encode(sys.getfilesystemencoding())
    #else:
    #    kindlegen = (os.path.join(vendorpath, u"kindlegen")).encode(sys.getfilesystemencoding())
    if not os.path.exists(ub.config.config_converterpath):
        error_message = _(u"kindlegen binary %(kindlepath)s not found", kindlepath=ub.config.config_converterpath)
        web.app.logger.error("convert_kindlegen: " + error_message)
        return error_message, RET_FAIL
    try:
        p = subprocess.Popen((ub.config.config_converterpath + " \"" + file_path + u".epub\"").encode(sys.getfilesystemencoding()),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    except Exception as e:
        error_message = _(u"kindlegen failed, no execution permissions")
        web.app.logger.error("convert_kindlegen: " + error_message)
        return error_message, RET_FAIL
    # Poll process for new output until finished
    while True:
        nextline = p.stdout.readline()
        if nextline == '' and p.poll() is not None:
            break
        if nextline != "\r\n":
            # Format of error message (kindlegen translates its output texts):
            # Error(prcgen):E23006: Language not recognized in metadata.The dc:Language field is mandatory.Aborting.
            conv_error = re.search(".*\(.*\):(E\d+):\s(.*)", nextline)
            # If error occoures, log in every case
            if conv_error:
                error_message = _(u"Kindlegen failed with Error %(error)s. Message: %(message)s",
                                  error=conv_error.group(1), message=conv_error.group(2).decode('utf-8'))
                web.app.logger.info("convert_kindlegen: " + error_message)
                web.app.logger.info(nextline.strip('\r\n'))
            else:
                web.app.logger.debug(nextline.strip('\r\n'))

    check = p.returncode
    if not check or check < 2:
        book.data.append(db.Data(
            name=book.data[0].name,
            book_format="MOBI",
            book=book.id,
            uncompressed_size=os.path.getsize(file_path + ".mobi")
        ))
        db.session.commit()
        return file_path + ".mobi", RET_SUCCESS
    else:
        web.app.logger.info("convert_kindlegen: kindlegen failed with error while converting book")
        if not error_message:
            error_message = 'kindlegen failed, no excecution permissions'
        return error_message, RET_FAIL


def convert_calibre(file_path, book):
    error_message = None
    if not os.path.exists(ub.config.config_converterpath):
        error_message = _(u"Ebook-convert binary %(converterpath)s not found", converterpath=ub.config.config_converterpath)
        web.app.logger.error("convert_calibre: " + error_message)
        return error_message, RET_FAIL
    try:
        command = ("\""+ub.config.config_converterpath + "\" " + ub.config.config_calibre +
                  " \"" + file_path + u".epub\" \"" + file_path + u".mobi\"").encode(sys.getfilesystemencoding())
        p = subprocess.Popen(command,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    except Exception as e:
        error_message = _(u"Ebook-convert failed, no execution permissions")
        web.app.logger.error("convert_calibre: " + error_message)
        return error_message, RET_FAIL
    # Poll process for new output until finished
    while True:
        nextline = p.stdout.readline()
        if nextline == '' and p.poll() is not None:
            break
        web.app.logger.debug(nextline.strip('\r\n').decode(sys.getfilesystemencoding()))

    check = p.returncode
    if check == 0 :
        book.data.append(db.Data(
            name=book.data[0].name,
            book_format="MOBI",
            book=book.id,
            uncompressed_size=os.path.getsize(file_path + ".mobi")
        ))
        db.session.commit()
        return file_path + ".mobi", RET_SUCCESS
    else:
        web.app.logger.info("convert_calibre: Ebook-convert failed with error while converting book")
        if not error_message:
            error_message = 'Ebook-convert failed, no excecution permissions'
        return error_message, RET_FAIL


def versioncheck():
    if ub.config.config_ebookconverter == 1:
        return versionKindle()
    elif ub.config.config_ebookconverter == 2:
        return versionCalibre()
    else:
        return {'ebook_converter':''}


def convert_mobi(file_path, book):
    if ub.config.config_ebookconverter == 2:
        return convert_calibre(file_path, book)
    else:
        return convert_kindlegen(file_path, book)
