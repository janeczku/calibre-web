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

import os
import sys

base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local directories into path
sys.path.append(base_path)
sys.path.append(os.path.join(base_path, 'cps'))
sys.path.append(os.path.join(base_path, 'vendor'))

from cps import create_app
from cps.opds import opds
from cps import Server
from cps.web import web
from cps.jinjia import jinjia
from cps.about import about
from cps.shelf import shelf
from cps.admin import admi
from cps.gdrive import gdrive
from cps.editbooks import editbook
try:
    from cps.oauth_bb import oauth
    oauth_available = True
except ImportError:
    oauth_available = False


if __name__ == '__main__':
    app = create_app()
    app.register_blueprint(web)
    app.register_blueprint(opds)
    app.register_blueprint(jinjia)
    app.register_blueprint(about)
    app.register_blueprint(shelf)
    app.register_blueprint(admi)
    app.register_blueprint(gdrive)
    app.register_blueprint(editbook)
    if oauth_available:
        app.register_blueprint(oauth)
    Server.startServer()




