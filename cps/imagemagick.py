# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2026 IgorKurkov
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

# Wand (ImageMagick binding) is probed once here and shared by all modules.
# Python does not cache a failed import, and every attempt makes Wand search
# all PATH directories for the ImageMagick library, which takes seconds per
# attempt on Windows when ImageMagick is not installed.
try:
    from wand.image import Image, Color
    from wand import version as ImageVersion
    from wand.exceptions import MissingDelegateError, BlobError, PolicyError
    use_IM = True
    import_error = None
except (ImportError, RuntimeError) as e:
    Image = Color = ImageVersion = None
    MissingDelegateError = BlobError = PolicyError = BaseException
    use_IM = False
    import_error = e
