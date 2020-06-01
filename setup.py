#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2019 decentral1se
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
#
#  """Calibre-web distribution package setuptools installer."""

from setuptools import setup
from setuptools import find_packages
import re
import ast

STABLE_VERSION = ast.literal_eval(
    re.findall(
        "{.*}",
        re.findall("^STABLE_VERSION.*",
                   open("cps/constants.py").read(), re.MULTILINE)[0])[0])

setup(
    description="Web app for calibre",
    version=STABLE_VERSION['version'],
    author="Jan B",
    url="https://github.com/janeczku/calibre-web",
    packages=find_packages(),
    py_modules=[ 'cps' ],
)
