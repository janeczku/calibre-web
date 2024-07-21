# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2023 OzzieIsaacs
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

from tempfile import gettempdir
import os
import shutil
import zipfile
import mimetypes
from io import BytesIO

from . import logger

log = logger.create()

try:
    import magic
    error = None
except ImportError as e:
    error = "Cannot import python-magic, checking uploaded file metadata will not work: {}".format(e)


def get_temp_dir():
    tmp_dir = os.path.join(gettempdir(), 'calibre_web')
    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)
    return tmp_dir


def del_temp_dir():
    tmp_dir = os.path.join(gettempdir(), 'calibre_web')
    shutil.rmtree(tmp_dir)


def validate_mime_type(file_buffer, allowed_extensions):
    if error:
        log.error(error)
        return False
    mime = magic.Magic(mime=True)
    allowed_mimetypes = list()
    for x in allowed_extensions:
        try:
            allowed_mimetypes.append(mimetypes.types_map["." + x])
        except KeyError:
            log.error("Unkown mimetype for Extension: {}".format(x))
    tmp_mime_type = mime.from_buffer(file_buffer.read())
    file_buffer.seek(0)
    if any(mime_type in tmp_mime_type for mime_type in allowed_mimetypes):
        return True
    # Some epubs show up as zip mimetypes
    elif "zip" in tmp_mime_type:
        try:
            with zipfile.ZipFile(BytesIO(file_buffer.read()), 'r') as epub:
                file_buffer.seek(0)
                if "mimetype" in epub.namelist():
                    return True
        except:
            file_buffer.seek(0)
    log.error("Mimetype '{}' not found in allowed types".format(tmp_mime_type))
    return False
