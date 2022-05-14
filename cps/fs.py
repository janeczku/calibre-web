# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2020 mmonkey
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

from . import logger
from .constants import CACHE_DIR
from os import makedirs, remove
from os.path import isdir, isfile, join
from shutil import rmtree


class FileSystem:
    _instance = None
    _cache_dir = CACHE_DIR

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FileSystem, cls).__new__(cls)
            cls.log = logger.create()
        return cls._instance

    def get_cache_dir(self, cache_type=None):
        if not isdir(self._cache_dir):
            try:
                makedirs(self._cache_dir)
            except OSError:
                self.log.info(f'Failed to create path {self._cache_dir} (Permission denied).')
                raise

        path = join(self._cache_dir, cache_type)
        if cache_type and not isdir(path):
            try:
                makedirs(path)
            except OSError:
                self.log.info(f'Failed to create path {path} (Permission denied).')
                raise

        return path if cache_type else self._cache_dir

    def get_cache_file_dir(self, filename, cache_type=None):
        path = join(self.get_cache_dir(cache_type), filename[:2])
        if not isdir(path):
            try:
                makedirs(path)
            except OSError:
                self.log.info(f'Failed to create path {path} (Permission denied).')
                raise

        return path

    def get_cache_file_path(self, filename, cache_type=None):
        return join(self.get_cache_file_dir(filename, cache_type), filename) if filename else None

    def get_cache_file_exists(self, filename, cache_type=None):
        path = self.get_cache_file_path(filename, cache_type)
        return isfile(path)

    def delete_cache_dir(self, cache_type=None):
        if not cache_type and isdir(self._cache_dir):
            try:
                rmtree(self._cache_dir)
            except OSError:
                self.log.info(f'Failed to delete path {self._cache_dir} (Permission denied).')
                raise

        path = join(self._cache_dir, cache_type)
        if cache_type and isdir(path):
            try:
                rmtree(path)
            except OSError:
                self.log.info(f'Failed to delete path {path} (Permission denied).')
                raise

    def delete_cache_file(self, filename, cache_type=None):
        path = self.get_cache_file_path(filename, cache_type)
        if isfile(path):
            try:
                remove(path)
            except OSError:
                self.log.info(f'Failed to delete path {path} (Permission denied).')
                raise
