#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019  OzzieIsaacs
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

from __future__ import absolute_import, division, print_function, unicode_literals
import sys
import os


# Insert local directories into path
if sys.version_info < (3, 0):
    sys.path.append(os.path.dirname(os.path.abspath(__file__.decode('utf-8'))))
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__.decode('utf-8'))), 'vendor'))
else:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor'))


from cps import create_app
from cps import web_server
from cps.opds import opds
from cps.web import web
from cps.jinjia import jinjia
from cps.about import about
from cps.shelf import shelf
from cps.admin import admi
from cps.gdrive import gdrive
from cps.editbooks import editbook

try:
    from cps.kobo import kobo, get_kobo_activated
    from cps.kobo_auth import kobo_auth
    kobo_available = get_kobo_activated()
except ImportError:
    kobo_available = False

try:
    from cps.oauth_bb import oauth
    oauth_available = True
except ImportError:
    oauth_available = False


def main():
    app = create_app()
    app.register_blueprint(web)
    app.register_blueprint(opds)
    app.register_blueprint(jinjia)
    app.register_blueprint(about)
    app.register_blueprint(shelf)
    app.register_blueprint(admi)
    app.register_blueprint(gdrive)
    app.register_blueprint(editbook)
    if kobo_available:
        app.register_blueprint(kobo)
        app.register_blueprint(kobo_auth)
    if oauth_available:
        app.register_blueprint(oauth)
    success = web_server.start()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
