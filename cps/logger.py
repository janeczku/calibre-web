# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2019 pwr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division, print_function, unicode_literals
import os
import inspect
import logging
from logging import Formatter, StreamHandler
from logging.handlers import RotatingFileHandler

from .constants import BASE_DIR as _BASE_DIR


# FORMATTER           = Formatter("[%(asctime)s] %(levelname)5s {%(name)s:%(lineno)d %(funcName)s} %(message)s")
FORMATTER           = Formatter("[%(asctime)s] %(levelname)5s {%(name)s:%(lineno)d} %(message)s")
DEFAULT_LOG_LEVEL   = logging.INFO
DEFAULT_LOG_FILE    = os.path.join(_BASE_DIR, "calibre-web.log")
LOG_TO_STDERR       = '/dev/stderr'


logging.addLevelName(logging.WARNING, "WARN")
logging.addLevelName(logging.CRITICAL, "CRIT")


def get(name=None):
    return logging.getLogger(name)


def create():
    parent_frame = inspect.stack(0)[1]
    if hasattr(parent_frame, 'frame'):
        parent_frame = parent_frame.frame
    else:
        parent_frame = parent_frame[0]
    parent_module = inspect.getmodule(parent_frame)
    return get(parent_module.__name__)


def is_debug_enabled():
    return logging.root.level <= logging.DEBUG


def get_level_name(level):
    return logging.getLevelName(level)


def is_valid_logfile(file_path):
    if not file_path:
        return True
    if os.path.isdir(file_path):
        return False
    log_dir = os.path.dirname(file_path)
    return (not log_dir) or os.path.isdir(log_dir)


def setup(log_file, log_level=None):
    if log_file:
        if not os.path.dirname(log_file):
            log_file = os.path.join(_BASE_DIR, log_file)
        log_file = os.path.abspath(log_file)
    else:
        # log_file = LOG_TO_STDERR
        log_file = DEFAULT_LOG_FILE

    # print ('%r -- %r' % (log_level, log_file))
    r = logging.root
    r.setLevel(log_level or DEFAULT_LOG_LEVEL)

    previous_handler = r.handlers[0] if r.handlers else None
    # print ('previous %r' % previous_handler)

    if previous_handler:
        # if the log_file has not changed, don't create a new handler
        if getattr(previous_handler, 'baseFilename', None) == log_file:
            return
        r.debug("logging to %s level %s", log_file, r.level)

    if log_file == LOG_TO_STDERR:
        file_handler = StreamHandler()
        file_handler.baseFilename = LOG_TO_STDERR
    else:
        try:
            file_handler = RotatingFileHandler(log_file, maxBytes=50000, backupCount=2)
        except IOError:
            if log_file == DEFAULT_LOG_FILE:
                raise
            file_handler = RotatingFileHandler(DEFAULT_LOG_FILE, maxBytes=50000, backupCount=2)
    file_handler.setFormatter(FORMATTER)

    for h in r.handlers:
        r.removeHandler(h)
        h.close()
    r.addHandler(file_handler)
    # print ('new handler %r' % file_handler)


# Enable logging of smtp lib debug output
class StderrLogger(object):
    def __init__(self, name=None):
        self.log = get(name or self.__class__.__name__)
        self.buffer = ''

    def write(self, message):
        try:
            if message == '\n':
                self.log.debug(self.buffer.replace('\n', '\\n'))
                self.buffer = ''
            else:
                self.buffer += message
        except:
            self.logger.debug("Logging Error")
