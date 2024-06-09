#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2022 OzzieIsaacs
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

import os
import sys


# Add local path to sys.path, so we can import cps
path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, path)

from cps.main import main


def hide_console_windows():
    import ctypes
    import os

    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd != 0:
        try:
            import win32process
        except ImportError:
            print("To hide console window install 'pywin32' using 'pip install pywin32'")
            return
        ctypes.windll.user32.ShowWindow(hwnd, 0)
        ctypes.windll.kernel32.CloseHandle(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        os.system('taskkill /PID ' + str(pid) + ' /f')


if __name__ == '__main__':
    if os.name == "nt":
        hide_console_windows()
    main()



