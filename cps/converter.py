# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2016-2019 Ben Bennett, OzzieIsaacs
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
import re
from flask_babel import gettext as _

from . import config, logger
from .subproc_wrapper import process_wait


log = logger.create()

# _() necessary to make babel aware of string for translation
_NOT_CONFIGURED = _('not configured')
_NOT_INSTALLED = _('not installed')
_EXECUTION_ERROR = _('Execution permissions missing')


def _get_command_version(path, pattern, argument=None):
    if os.path.exists(path):
        command = [path]
        if argument:
            command.append(argument)
        try:
            match = process_wait(command, pattern=pattern)
            if isinstance(match, re.Match):
                return match.string
        except Exception as ex:
            log.warning("%s: %s", path, ex)
            return _EXECUTION_ERROR
    return _NOT_INSTALLED


def get_calibre_version():
    return _get_command_version(config.config_converterpath, r'ebook-convert.*\(calibre', '--version') \
           or _NOT_CONFIGURED


def get_unrar_version():
    return _get_command_version(config.config_rarfile_location, r'UNRAR.*\d') or _NOT_CONFIGURED

def get_kepubify_version():
    return _get_command_version(config.config_kepubifypath, r'kepubify\s','--version') or _NOT_CONFIGURED


