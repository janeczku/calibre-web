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
from io import BytesIO

try:
    from PIL import Image
    use_pillow = True
except ImportError:
    use_pillow = False


NO_JPEG_EXTENSIONS = ['.png', '.webp', '.bmp']
COVER_EXTENSIONS = ['.png', '.webp', '.bmp', '.jpg', '.jpeg']


def image_to_rgb(img):
    # JPEG has no alpha channel: flatten transparent images onto white instead of black
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img = img.convert('RGBA')
        background = Image.new('RGB', img.size, 'white')
        background.paste(img, mask=img.getchannel('A'))
        return background
    return img.convert('RGB')


def save_image(img, filename, image_format='jpeg'):
    if image_format.lower() in ('jpeg', 'jpg'):
        image_to_rgb(img).save(filename, format='JPEG', quality=90)
    else:
        img.save(filename, format=image_format)


def cover_processing(tmp_file_path, img, extension):
    # tmp_cover_name = os.path.join(os.path.dirname(tmp_file_name), 'cover.jpg')
    tmp_cover_name = tmp_file_path + '.jpg'
    if extension in NO_JPEG_EXTENSIONS:
        if use_pillow:
            with Image.open(BytesIO(img)) as imgc:
                save_image(imgc, tmp_cover_name)
                return tmp_cover_name
        else:
            return None
    if img:
        with open(tmp_cover_name, 'wb') as f:
            f.write(img)
        return tmp_cover_name
    else:
        return None
