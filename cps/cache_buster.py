# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2016-2019 jkrehm andy29485 OzzieIsaacs
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

# Inspired by https://github.com/ChrisTM/Flask-CacheBust
# Uses query strings so CSS font files are found without having to resort to absolute URLs

import os
import hashlib

from . import logger


log = logger.create()


def init_cache_busting(app):
    """
    Configure `app` to so that `url_for` adds a unique query string to URLs generated
    for the `'static'` endpoint.

    This allows setting long cache expiration values on static resources
    because whenever the resource changes, so does its URL.
    """

    static_folder = os.path.join(app.static_folder, '')  # path to the static file folder, with trailing slash

    hash_table = {}  # map of file hashes

    log.debug('Computing cache-busting values...')
    # compute file hashes
    for dirpath, __, filenames in os.walk(static_folder):
        for filename in filenames:
            # compute version component
            rooted_filename = os.path.join(dirpath, filename)
            with open(rooted_filename, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:7] # nosec

            # save version to tables
            file_path = rooted_filename.replace(static_folder, "")
            file_path = file_path.replace("\\", "/")  # Convert Windows path to web path
            hash_table[file_path] = file_hash
    log.debug('Finished computing cache-busting values')

    def bust_filename(filename):
        return hash_table.get(filename, "")

    def unbust_filename(filename):
        return filename.split("?", 1)[0]

    @app.url_defaults
    # pylint: disable=unused-variable
    def reverse_to_cache_busted_url(endpoint, values):
        """
        Make `url_for` produce busted filenames when using the 'static' endpoint.
        """
        if endpoint == "static":
            file_hash = bust_filename(values["filename"])
            if file_hash:
                values["q"] = file_hash

    def debusting_static_view(filename):
        """
        Serve a request for a static file having a busted name.
        """
        return original_static_view(filename=unbust_filename(filename))

    # Replace the default static file view with our debusting view.
    original_static_view = app.view_functions["static"]
    app.view_functions["static"] = debusting_static_view
