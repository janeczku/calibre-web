# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019 cervinko, idalin, SiphonSquirrel, ouzklcn, akushsky,
#                            OzzieIsaacs, bodybybuddha, jkrehm, matthazinski, janeczku
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

import shutil
import glob
import zipfile
import json
from io import BytesIO

import os

from flask import send_file, __version__

from . import logger, config
from .about import collect_stats

log = logger.create()

def assemble_logfiles(file_name):
    log_list = sorted(glob.glob(file_name + '*'), reverse=True)
    wfd = BytesIO()
    for f in log_list:
        with open(f, 'rb') as fd:
            shutil.copyfileobj(fd, wfd)
    wfd.seek(0)
    if int(__version__.split('.')[0]) < 2:
        return send_file(wfd,
                         as_attachment=True,
                         attachment_filename=os.path.basename(file_name))
    else:
        return send_file(wfd,
                         as_attachment=True,
                         download_name=os.path.basename(file_name))


def send_debug():
    file_list = glob.glob(logger.get_logfile(config.config_logfile) + '*')
    file_list.extend(glob.glob(logger.get_accesslogfile(config.config_access_logfile) + '*'))
    for element in [logger.LOG_TO_STDOUT, logger.LOG_TO_STDERR]:
        if element in file_list:
            file_list.remove(element)
    memory_zip = BytesIO()
    with zipfile.ZipFile(memory_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('settings.txt', json.dumps(config.toDict()))
        zf.writestr('libs.txt', json.dumps(collect_stats()))
        for fp in file_list:
            zf.write(fp, os.path.basename(fp))
    memory_zip.seek(0)
    if int(__version__.split('.')[0]) < 2:
        return send_file(memory_zip,
                         as_attachment=True,
                         attachment_filename="Calibre-Web-debug-pack.zip")
    else:
        return send_file(memory_zip,
                         as_attachment=True,
                         download_name="Calibre-Web-debug-pack.zip")
