#!/usr/bin/env python
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

from subproc_wrapper import process_open, cmdlineCall
import os
import sys
import re
import time

def main():
    quotes = [1, 2]
    format_new_ext = '.mobi'
    format_old_ext = '.epub'
    file_path = '/home/matthias/Dokumente/bücher/Bettina Szramah/Die Giftmischerin TCP_IP (10)/Die Giftmischerin TCP_IP - Bettina, Szrama'
    command = ['/opt/calibre/ebook-convert', (file_path + format_old_ext),
               (file_path + format_new_ext)]

    #print(command)
    #p1 = cmdlineCall(command[0],command[1:])
    #time.sleep(10)
    #print(p1)

    p = process_open(command, quotes)
    while p.poll() is None:
        nextline = p.stdout.readline()
        if os.name == 'nt' and sys.version_info < (3, 0):
            nextline = nextline.decode('windows-1252')
        elif os.name == 'posix' and sys.version_info < (3, 0):
            nextline = nextline.decode('utf-8')
        # log.debug(nextline.strip('\r\n'))
        # parse progress string from calibre-converter
        progress = re.search(r"(\d+)%\s.*", nextline)
        if progress:
            print('Progress:' + str(progress))
            # self.UIqueue[index]['progress'] = progress.group(1) + ' %

    # process returncode
    check = p.returncode
    calibre_traceback = p.stderr.readlines()
    for ele in calibre_traceback:
        if sys.version_info < (3, 0):
            ele = ele.decode('utf-8')
        print(ele.strip('\n'))
        if not ele.startswith('Traceback') and not ele.startswith('  File'):
            print( "Calibre failed with error: %s" % ele.strip('\n'))
    print(str(check))

if __name__ == '__main__':
    main()
