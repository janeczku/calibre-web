# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2026 OzzieIsaacs
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
import subprocess
import sys

from . import config, constants, logger

log = logger.create()

_process = None


def start():
    global _process
    stop()
    if not config.config_calibre_server_enabled or not config.config_calibre_dir:
        return
    binary = os.path.join(config.config_binariesdir or "",
                          "calibre-server.exe" if sys.platform == "win32" else "calibre-server")
    if not os.path.isfile(binary):
        log.error("calibre-server binary not found: %s", binary)
        return
    args = [binary, "--port", str(config.config_calibre_server_port)]
    if config.config_calibre_server_username and config.config_calibre_server_password_e:
        userdb = os.path.join(constants.CONFIG_DIR, "content_server_users.sqlite")
        try:
            os.remove(userdb)
        except OSError:
            pass
        result = subprocess.run([binary, "--userdb", userdb, "--manage-users", "--", "add",
                                 config.config_calibre_server_username,
                                 config.config_calibre_server_password_e],
                                capture_output=True, text=True)
        if result.returncode != 0:
            log.error("Failed to create calibre content server user: %s", result.stderr)
            return
        args += ["--enable-auth", "--userdb", userdb]
    args.append(config.config_calibre_dir)
    try:
        _process = subprocess.Popen(args)
    except OSError as ex:
        log.error("Failed to start calibre content server: %s", ex)
        _process = None
        return
    log.info("Calibre content server started on port %s", config.config_calibre_server_port)


def stop():
    global _process
    if _process is not None and _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(10)
        except subprocess.TimeoutExpired:
            _process.kill()
        log.info("Calibre content server stopped")
    _process = None
