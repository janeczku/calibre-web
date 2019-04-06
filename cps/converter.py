#!/usr/bin/env python
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
import subprocess
import ub
import re
from flask_babel import gettext as _


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
            p = subprocess.Popen([ub.config.config_converterpath, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.wait()
            for lines in p.stdout.readlines():
                if isinstance(lines, bytes):
                    lines = lines.decode('utf-8')
                if re.search('ebook-convert.*\(calibre', lines):
                    versions = lines
        except Exception:
            versions = _(u'Excecution permissions missing')
    return {'Calibre converter' : versions}


def versioncheck():
    if ub.config.config_ebookconverter == 1:
        return versionKindle()
    elif ub.config.config_ebookconverter == 2:
        return versionCalibre()
    else:
        return {'ebook_converter':_(u'not configured')}

