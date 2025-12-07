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

    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')

    SW_HIDE = 0

    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, SW_HIDE)


if __name__ == '__main__':
    # Only hide the console window on Windows when there is no interactive
    # console attached. This preserves the ability to use Ctrl+C from a
    # terminal (stdin is a tty) to stop the server.
    if os.name == "nt" and not sys.stdin.isatty():
        hide_console_windows()

    try:
        main()
    except KeyboardInterrupt:
        # Allow stopping the server with Ctrl+C from an interactive console, after reboot of calibre-web
        # (initally the SIGINT signal CTRL+C is catched in server.py via the signal callback).
        try:
            # Try to perform a graceful stop if web_server is available.
            # Import here to avoid import-time side-effects when not needed.
            from cps import web_server
            web_server.stop()
        except Exception:
            pass
        print('\nCalibre-Web: received interrupt, shutting down')
        sys.exit(0)



