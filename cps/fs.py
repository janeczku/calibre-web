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

from __future__ import division, print_function, unicode_literals
from .constants import CACHE_DIR
from os import listdir, makedirs, remove
from os.path import isdir, isfile, join
from shutil import rmtree

CACHE_TYPE_THUMBNAILS = 'thumbnails'


class FileSystem:
    _instance = None
    _cache_dir = CACHE_DIR

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FileSystem, cls).__new__(cls)
        return cls._instance

    def get_cache_dir(self, cache_type=None):
        if not isdir(self._cache_dir):
            makedirs(self._cache_dir)

        if cache_type and not isdir(join(self._cache_dir, cache_type)):
            makedirs(join(self._cache_dir, cache_type))

        return join(self._cache_dir, cache_type) if cache_type else self._cache_dir

    def get_cache_file_path(self, filename, cache_type=None):
        return join(self.get_cache_dir(cache_type), filename) if filename else None

    def list_cache_files(self, cache_type=None):
        path = self.get_cache_dir(cache_type)
        return [file for file in listdir(path) if isfile(join(path, file))]

    def list_existing_cache_files(self, filenames, cache_type=None):
        path = self.get_cache_dir(cache_type)
        return [file for file in listdir(path) if isfile(join(path, file)) and file in filenames]

    def list_missing_cache_files(self, filenames, cache_type=None):
        path = self.get_cache_dir(cache_type)
        return [file for file in listdir(path) if isfile(join(path, file)) and file not in filenames]

    def delete_cache_dir(self, cache_type=None):
        if not cache_type and isdir(self._cache_dir):
            rmtree(self._cache_dir)
        if cache_type and isdir(join(self._cache_dir, cache_type)):
            rmtree(join(self._cache_dir, cache_type))

    def delete_cache_file(self, filename, cache_type=None):
        if isfile(join(self.get_cache_dir(cache_type), filename)):
            remove(join(self.get_cache_dir(cache_type), filename))
