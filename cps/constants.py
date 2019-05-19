# -*- python-mode -*-
# -*- coding: utf-8 -*-

import sys
import os
import logging


BASE_DIR = sys.path[0]
STATIC_DIR = os.path.join(BASE_DIR, 'cps', 'static')


ROLE_USER               = 0
ROLE_ADMIN              = 1 << 0
ROLE_DOWNLOAD           = 1 << 1
ROLE_UPLOAD             = 1 << 2
ROLE_EDIT               = 1 << 3
ROLE_PASSWD             = 1 << 4
ROLE_ANONYMOUS          = 1 << 5
ROLE_EDIT_SHELFS        = 1 << 6
ROLE_DELETE_BOOKS       = 1 << 7

DETAIL_RANDOM           = 1 <<  0
SIDEBAR_LANGUAGE        = 1 <<  1
SIDEBAR_SERIES          = 1 <<  2
SIDEBAR_CATEGORY        = 1 <<  3
SIDEBAR_HOT             = 1 <<  4
SIDEBAR_RANDOM          = 1 <<  5
SIDEBAR_AUTHOR          = 1 <<  6
SIDEBAR_BEST_RATED      = 1 <<  7
SIDEBAR_READ_AND_UNREAD = 1 <<  8
SIDEBAR_RECENT          = 1 <<  9
SIDEBAR_SORTED          = 1 << 10
MATURE_CONTENT          = 1 << 11
SIDEBAR_PUBLISHER       = 1 << 12


def has_flag(value, bit_flag):
    return bit_flag == (bit_flag & (value or 0))


ADMIN_USER_ROLES   = ROLE_USER | ROLE_ADMIN | ROLE_DOWNLOAD | ROLE_UPLOAD | ROLE_EDIT | ROLE_DELETE_BOOKS | ROLE_PASSWD
ADMIN_USER_SIDEBAR = (SIDEBAR_PUBLISHER << 1) - 1


DEFAULT_LOG_LEVEL  = logging.INFO
DEFAULT_PASSWORD   = "admin123"
try:
    DEFAULT_PORT = os.environ.get("CALIBRE_PORT", 8083)
    DEFAULT_PORT = int(DEFAULT_PORT)
except ValueError:
    print ('Environment variable CALIBRE_PORT is set to an invalid value (%s), faling back to default (8083)' % DEFAULT_PORT)
    DEFAULT_PORT = 8083


EXTENSIONS_UPLOAD  = {'txt', 'pdf', 'epub', 'mobi', 'azw', 'azw3', 'cbr', 'cbz', 'cbt', 'djvu', 'prc', 'doc', 'docx',
                      'fb2', 'html', 'rtf', 'odt'}
EXTENSIONS_CONVERT = {'pdf', 'epub', 'mobi', 'azw3', 'docx', 'rtf', 'fb2', 'lit', 'lrf', 'txt', 'htmlz'}


UPDATE_STABLE = 0
AUTO_UPDATE_STABLE = 1
UPDATE_NIGHTLY = 2
AUTO_UPDATE_NIGHTLY = 4
