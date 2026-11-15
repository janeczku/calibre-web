# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2024 OzzieIsaacs
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
from uuid import uuid4
import os
import time

from .file_helper import get_temp_dir
from .subproc_wrapper import process_open
from . import logger, config
from .constants import SUPPORTED_CALIBRE_BINARIES

log = logger.create()

# calibredb refuses to work while any other calibre program of the same user holds calibre's (user-wide, not
# per library) 'db' single-instance lock, e.g. a parallel calibredb call from a conversion, download or e-mail task
CALIBREDB_LOCK_RETRY_TIMEOUT = 30
CALIBREDB_LOCK_RETRY_DELAY = 1


def _calibredb_lock_busy(returncode, err):
    if returncode == 0 or not err:
        return False
    if isinstance(err, bytes):
        err = err.decode('utf-8', errors='ignore')
    # The (translatable) error message always contains the untranslated program name "calibre-server"
    return 'calibre-server' in err and 'Traceback' not in err


def run_calibredb(command, quotes, env, newlines=True):
    """Run calibredb and wait for its result, retry for a limited time while another calibre program holds
    calibre's database lock. Returns returncode, stdout, stderr of the last run"""
    deadline = time.monotonic() + CALIBREDB_LOCK_RETRY_TIMEOUT
    while True:
        # process_open modifies the command on Windows (quoting), so always hand over a copy
        p = process_open(list(command), quotes, env, newlines=newlines)
        out, err = p.communicate()
        if not _calibredb_lock_busy(p.returncode, err) or time.monotonic() >= deadline:
            return p.returncode, out, err
        log.debug("calibredb is blocked by another running calibre program, retrying")
        time.sleep(CALIBREDB_LOCK_RETRY_DELAY)


def do_calibre_export(book_id, book_format):
    try:
        quotes = [5, 7]
        tmp_dir = get_temp_dir()
        calibredb_binarypath = get_calibre_binarypath("calibredb")
        temp_file_name = str(uuid4())
        my_env = os.environ.copy()
        if config.config_calibre_split:
            my_env['CALIBRE_OVERRIDE_DATABASE_PATH'] = os.path.join(config.config_calibre_dir, "metadata.db")
        library_path = config.get_book_path()
        opf_command = [calibredb_binarypath, 'export', '--dont-write-opf', '--dont-save-cover',
                       '--with-library', library_path,
                       '--to-dir', tmp_dir, '--formats', book_format, "--template", "{}".format(temp_file_name),
                       str(book_id)]
        returncode, _, err = run_calibredb(opf_command, quotes, my_env)
        if returncode != 0:
            if isinstance(err, str):
                error_message = err.strip()
            elif err is not None:
                error_message = err.decode('utf-8', errors='replace').strip()
            else:
                error_message = ''
            if not error_message:
                error_message = 'calibredb export failed with return code %s' % returncode
            log.error('Metadata embedder encountered an error: %s', error_message)
            return None, error_message
        if err:
            if isinstance(err, str):
                error_message = err.strip()
            else:
                error_message = err.decode('utf-8', errors='replace').strip()
            log.error('Metadata embedder encountered an error: %s', error_message)
            return None, error_message
        return tmp_dir, temp_file_name
    except OSError as ex:
        log.error_or_exception(ex)
        return None, str(ex)


def get_calibre_binarypath(binary):
    binariesdir = config.config_binariesdir
    if binariesdir:
        try:
            return os.path.join(binariesdir, SUPPORTED_CALIBRE_BINARIES[binary])
        except KeyError as ex:
            log.error("Binary not supported by Calibre-Web: %s", SUPPORTED_CALIBRE_BINARIES[binary])
            log.error_or_exception(ex)
    return ""
