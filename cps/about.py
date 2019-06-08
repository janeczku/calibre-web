#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, cervinko, jkrehm, bodybybuddha, ok11,
#                            andy29485, idalin, Kyosfonica, wuqi, Kennyl, lemmsh,
#                            falgh1, grunjol, csitko, ytils, xybydy, trasba, vrabe,
#                            ruben-herold, marblepebble, JackED42, SiphonSquirrel,
#                            apetresc, nanu-c, mutschler
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

from __future__ import division, print_function, unicode_literals
import sys
import requests

from flask import Blueprint
from flask import __version__ as flaskVersion
from flask_babel import gettext as _
from flask_principal import __version__ as flask_principalVersion
from flask_login import login_required
try:
    from flask_login import __version__ as flask_loginVersion
except ImportError:
    from flask_login.__about__ import __version__ as flask_loginVersion
from werkzeug import __version__ as werkzeugVersion

from babel import __version__ as babelVersion
from jinja2 import __version__  as jinja2Version
from pytz import __version__ as pytzVersion
from sqlalchemy import __version__ as sqlalchemyVersion

from . import db, converter, Server, uploader
from .isoLanguages import __version__ as iso639Version
from .web import render_title_template


about = Blueprint('about', __name__)


@about.route("/stats")
@login_required
def stats():
    counter = db.session.query(db.Books).count()
    authors = db.session.query(db.Authors).count()
    categorys = db.session.query(db.Tags).count()
    series = db.session.query(db.Series).count()
    versions = uploader.get_versions()
    versions['Babel'] = 'v' + babelVersion
    versions['Sqlalchemy'] = 'v' + sqlalchemyVersion
    versions['Werkzeug'] = 'v' + werkzeugVersion
    versions['Jinja2'] = 'v' + jinja2Version
    versions['Flask'] = 'v' + flaskVersion
    versions['Flask Login'] = 'v' + flask_loginVersion
    versions['Flask Principal'] = 'v' + flask_principalVersion
    versions['Iso 639'] = 'v' + iso639Version
    versions['pytz'] = 'v' + pytzVersion

    versions['Requests'] = 'v' + requests.__version__
    versions['pySqlite'] = 'v' + db.engine.dialect.dbapi.version
    versions['Sqlite'] = 'v' + db.engine.dialect.dbapi.sqlite_version
    versions.update(converter.versioncheck())
    versions.update(Server.getNameVersion())
    versions['Python'] = sys.version
    return render_title_template('stats.html', bookcounter=counter, authorcounter=authors, versions=versions,
                                 categorycounter=categorys, seriecounter=series, title=_(u"Statistics"), page="stat")
