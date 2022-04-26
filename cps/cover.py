# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2022 OzzieIsaacs
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

try:
    from wand.image import Image
    use_IM = True
except (ImportError, RuntimeError) as e:
    use_IM = False


NO_JPEG_EXTENSIONS = ['.png', '.webp', '.bmp']
COVER_EXTENSIONS = ['.png', '.webp', '.bmp', '.jpg', '.jpeg']


def cover_processing(tmp_file_name, img, extension):
    tmp_cover_name = os.path.join(os.path.dirname(tmp_file_name), 'cover.jpg')
    if extension in NO_JPEG_EXTENSIONS:
        if use_IM:
            with Image(blob=img) as imgc:
                imgc.format = 'jpeg'
                imgc.transform_colorspace('rgb')
                imgc.save(filename=tmp_cover_name)
                return tmp_cover_name
        else:
            return None
    if img:
        with open(tmp_cover_name, 'wb') as f:
            f.write(img)
        return tmp_cover_name
    else:
        return None
