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
import sqlite3
from collections import OrderedDict

import babel, pytz, requests, sqlalchemy
import werkzeug, flask, flask_login, flask_principal, jinja2
from flask_babel import gettext as _

from . import db, converter, uploader, server, isoLanguages
from .web import render_title_template
try:
    from flask_login import __version__ as flask_loginVersion
except ImportError:
    from flask_login.__about__ import __version__ as flask_loginVersion
try:
    import unidecode
    # _() necessary to make babel aware of string for translation
    unidecode_version = _(u'installed')
except ImportError:
    unidecode_version = _(u'not installed')

from . import services

about = flask.Blueprint('about', __name__)


_VERSIONS = OrderedDict(
    Python=sys.version,
    WebServer=server.VERSION,
    Flask=flask.__version__,
    Flask_Login=flask_loginVersion,
    Flask_Principal=flask_principal.__version__,
    Werkzeug=werkzeug.__version__,
    Babel=babel.__version__,
    Jinja2=jinja2.__version__,
    Requests=requests.__version__,
    SqlAlchemy=sqlalchemy.__version__,
    pySqlite=sqlite3.version,
    SQLite=sqlite3.sqlite_version,
    iso639=isoLanguages.__version__,
    pytz=pytz.__version__,
    Unidecode = unidecode_version,
    Flask_SimpleLDAP =  u'installed' if bool(services.ldap) else u'not installed',
    Goodreads = u'installed' if bool(services.goodreads_support) else u'not installed',
)
_VERSIONS.update(uploader.get_versions())


@about.route("/stats")
@flask_login.login_required
def stats():
    counter = db.session.query(db.Books).count()
    authors = db.session.query(db.Authors).count()
    categorys = db.session.query(db.Tags).count()
    series = db.session.query(db.Series).count()
    _VERSIONS['ebook converter'] = _(converter.get_version())
    return render_title_template('stats.html', bookcounter=counter, authorcounter=authors, versions=_VERSIONS,
                                 categorycounter=categorys, seriecounter=series, title=_(u"Statistics"), page="stat")
