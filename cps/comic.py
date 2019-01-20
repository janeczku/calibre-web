#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2018 OzzieIsaacs
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

import zipfile
import tarfile
import os
import uploader


def extractCover(tmp_file_name, original_file_extension):
    if original_file_extension.upper() == '.CBZ':
        cf = zipfile.ZipFile(tmp_file_name)
        compressed_name = cf.namelist()[0]
        cover_data = cf.read(compressed_name)
    elif original_file_extension.upper() == '.CBT':
        cf = tarfile.TarFile(tmp_file_name)
        compressed_name = cf.getnames()[0]
        cover_data = cf.extractfile(compressed_name).read()

    prefix = os.path.dirname(tmp_file_name)

    tmp_cover_name = prefix + '/cover' + os.path.splitext(compressed_name)[1]
    image = open(tmp_cover_name, 'wb')
    image.write(cover_data)
    image.close()
    return tmp_cover_name


def get_comic_info(tmp_file_path, original_file_name, original_file_extension):

    coverfile = extractCover(tmp_file_path, original_file_extension)

    return uploader.BookMeta(
            file_path=tmp_file_path,
            extension=original_file_extension,
            title=original_file_name,
            author=u"Unknown",
            cover=coverfile,
            description="",
            tags="",
            series="",
            series_id="",
            languages="")
