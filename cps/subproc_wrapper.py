# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs
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

from __future__ import division, print_function, unicode_literals
import sys
import os
import subprocess


def process_open(command, quotes=(), env=None, sout=subprocess.PIPE, serr=subprocess.PIPE, newlines=True):
    # Linux py2.7 encode as list without quotes no empty element for parameters
    # linux py3.x no encode and as list without quotes no empty element for parameters
    # windows py2.7 encode as string with quotes empty element for parameters is okay
    # windows py 3.x no encode and as string with quotes empty element for parameters is okay
    # separate handling for windows and linux
    if os.name == 'nt':
        for key, element in enumerate(command):
            if key in quotes:
                command[key] = '"' + element + '"'
        exc_command = " ".join(command)
        if sys.version_info < (3, 0):
            exc_command = exc_command.encode(sys.getfilesystemencoding())
    else:
        if sys.version_info < (3, 0):
            exc_command = [x.encode(sys.getfilesystemencoding()) for x in command]
        else:
            exc_command = [x for x in command]

    return subprocess.Popen(exc_command, shell=False, stdout=sout, stderr=serr, universal_newlines=newlines, env=env)


def process_wait(command, serr=subprocess.PIPE):
    # Run command, wait for process to terminate, and return an iterator over lines of its output.
    newlines = os.name != 'nt'
    p = process_open(command, serr=serr, newlines=newlines)
    p.wait()
    for line in p.stdout.readlines():
        if isinstance(line, bytes):
            line = line.decode('utf-8')
        yield line
