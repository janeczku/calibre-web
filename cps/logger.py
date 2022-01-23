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

import os
import sys
import inspect
import logging
from logging import Formatter, StreamHandler
from logging.handlers import RotatingFileHandler

from .constants import CONFIG_DIR as _CONFIG_DIR


ACCESS_FORMATTER_GEVENT  = Formatter("%(message)s")
ACCESS_FORMATTER_TORNADO = Formatter("[%(asctime)s] %(message)s")

FORMATTER           = Formatter("[%(asctime)s] %(levelname)5s {%(name)s:%(lineno)d} %(message)s")
DEFAULT_LOG_LEVEL   = logging.INFO
DEFAULT_LOG_FILE    = os.path.join(_CONFIG_DIR, "calibre-web.log")
DEFAULT_ACCESS_LOG  = os.path.join(_CONFIG_DIR, "access.log")
LOG_TO_STDERR       = '/dev/stderr'
LOG_TO_STDOUT       = '/dev/stdout'

logging.addLevelName(logging.WARNING, "WARN")
logging.addLevelName(logging.CRITICAL, "CRIT")


class _Logger(logging.Logger):

    def debug_or_exception(self, message, stacklevel=2, *args, **kwargs):
        if sys.version_info > (3, 7):
            if is_debug_enabled():
                self.exception(message, stacklevel=stacklevel, *args, **kwargs)
            else:
                self.error(message, stacklevel=stacklevel, *args, **kwargs)
        else:
            if is_debug_enabled():
                self.exception(message, stack_info=True, *args, **kwargs)
            else:
                self.error(message, *args, **kwargs)


    def debug_no_auth(self, message, *args, **kwargs):
        message = message.strip("\r\n")
        if message.startswith("send: AUTH"):
            self.debug(message[:16], *args, **kwargs)
        else:
            self.debug(message, *args, **kwargs)


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

def is_info_enabled(logger):
    return logging.getLogger(logger).level <= logging.INFO


def get_level_name(level):
    return logging.getLevelName(level)


def is_valid_logfile(file_path):
    if file_path == LOG_TO_STDERR or file_path == LOG_TO_STDOUT:
        return True
    if not file_path:
        return True
    if os.path.isdir(file_path):
        return False
    log_dir = os.path.dirname(file_path)
    return (not log_dir) or os.path.isdir(log_dir)


def _absolute_log_file(log_file, default_log_file):
    if log_file:
        if not os.path.dirname(log_file):
            log_file = os.path.join(_CONFIG_DIR, log_file)
        return os.path.abspath(log_file)
    return default_log_file


def get_logfile(log_file):
    return _absolute_log_file(log_file, DEFAULT_LOG_FILE)


def get_accesslogfile(log_file):
    return _absolute_log_file(log_file, DEFAULT_ACCESS_LOG)


def setup(log_file, log_level=None):
    '''
    Configure the logging output.
    May be called multiple times.
    '''
    log_level = log_level or DEFAULT_LOG_LEVEL
    logging.setLoggerClass(_Logger)
    logging.getLogger(__package__).setLevel(log_level)

    r = logging.root
    if log_level >= logging.INFO or os.environ.get('FLASK_DEBUG'):
        # avoid spamming the log with debug messages from libraries
        r.setLevel(log_level)

    # Otherwise name get's destroyed on windows
    if log_file != LOG_TO_STDERR and log_file != LOG_TO_STDOUT:
        log_file = _absolute_log_file(log_file, DEFAULT_LOG_FILE)

    previous_handler = r.handlers[0] if r.handlers else None
    if previous_handler:
        # if the log_file has not changed, don't create a new handler
        if getattr(previous_handler, 'baseFilename', None) == log_file:
            return "" if log_file == DEFAULT_LOG_FILE else log_file
        logging.debug("logging to %s level %s", log_file, r.level)

    if log_file == LOG_TO_STDERR or log_file == LOG_TO_STDOUT:
        if log_file == LOG_TO_STDOUT:
            file_handler = StreamHandler(sys.stdout)
            file_handler.baseFilename = log_file
        else:
            file_handler = StreamHandler(sys.stderr)
            file_handler.baseFilename = log_file
    else:
        try:
            file_handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=2, encoding='utf-8')
        except IOError:
            if log_file == DEFAULT_LOG_FILE:
                raise
            file_handler = RotatingFileHandler(DEFAULT_LOG_FILE, maxBytes=100000, backupCount=2, encoding='utf-8')
            log_file = ""
    file_handler.setFormatter(FORMATTER)

    for h in r.handlers:
        r.removeHandler(h)
        h.close()
    r.addHandler(file_handler)
    return "" if log_file == DEFAULT_LOG_FILE else log_file


def create_access_log(log_file, log_name, formatter):
    '''
    One-time configuration for the web server's access log.
    '''
    log_file = _absolute_log_file(log_file, DEFAULT_ACCESS_LOG)
    logging.debug("access log: %s", log_file)

    access_log = logging.getLogger(log_name)
    access_log.propagate = False
    access_log.setLevel(logging.INFO)
    try:
        file_handler = RotatingFileHandler(log_file, maxBytes=50000, backupCount=2, encoding='utf-8')
    except IOError:
        if log_file == DEFAULT_ACCESS_LOG:
            raise
        file_handler = RotatingFileHandler(DEFAULT_ACCESS_LOG, maxBytes=50000, backupCount=2, encoding='utf-8')
        log_file = ""

    file_handler.setFormatter(formatter)
    access_log.addHandler(file_handler)
    return access_log, \
           "" if _absolute_log_file(log_file, DEFAULT_ACCESS_LOG) == DEFAULT_ACCESS_LOG else log_file


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
        except Exception:
            self.log.debug("Logging Error")


# default configuration, before application settings are applied
setup(LOG_TO_STDERR, logging.DEBUG if os.environ.get('FLASK_DEBUG') else DEFAULT_LOG_LEVEL)
