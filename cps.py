#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019  OzzieIsaacs
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

from __future__ import absolute_import, division, print_function, unicode_literals
import sys
import os


# Insert local directories into path
_SELF = os.path.abspath(__file__.decode('utf-8') if sys.version_info < (3, 0) else __file__)
_BASE = os.path.dirname(_SELF)
sys.path.append(_BASE)
sys.path.append(os.path.join(_BASE, 'vendor'))


if __name__ == '__main__':
    from cps import main as _cps_main
    _cps_main()
