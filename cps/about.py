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

import sys
import platform
import sqlite3
from collections import OrderedDict

import babel, pytz, requests, sqlalchemy
import werkzeug, flask, flask_login, flask_principal, jinja2
from flask_babel import gettext as _
try:
    from flask_wtf import __version__ as flaskwtf_version
except ImportError:
    flaskwtf_version = _(u'not installed')

from . import db, calibre_db, converter, uploader, server, isoLanguages, constants, gdriveutils, dep_check
from .render_template import render_title_template

try:
    from flask_login import __version__ as flask_loginVersion
except ImportError:
    from flask_login.__about__ import __version__ as flask_loginVersion
try:
    # pylint: disable=unused-import
    import unidecode
    # _() necessary to make babel aware of string for translation
    unidecode_version = _(u'installed')
except ImportError:
    unidecode_version = _(u'not installed')

try:
    from flask_dance import __version__ as flask_danceVersion
except ImportError:
    flask_danceVersion = None

try:
    from greenlet import __version__ as greenlet_Version
except ImportError:
    greenlet_Version = None

try:
    from scholarly import scholarly
    scholarly_version = _(u'installed')
except ImportError:
    scholarly_version = _(u'not installed')

from . import services

about = flask.Blueprint('about', __name__)

ret = dict()
req = dep_check.load_dependencys(False)
opt = dep_check.load_dependencys(True)
for i in (req + opt):
    ret[i[1]] = i[0]

if constants.NIGHTLY_VERSION[0] == "$Format:%H$":
    calibre_web_version = constants.STABLE_VERSION['version']
else:
    calibre_web_version = (constants.STABLE_VERSION['version'] + ' - '
                    + constants.NIGHTLY_VERSION[0].replace('%','%%') + ' - '
                    + constants.NIGHTLY_VERSION[1].replace('%','%%'))
if getattr(sys, 'frozen', False):
    calibre_web_version += " - Exe-Version"
elif constants.HOME_CONFIG:
    calibre_web_version += " - pyPi"

if not ret:
    _VERSIONS = OrderedDict(
        Platform = '{0[0]} {0[2]} {0[3]} {0[4]} {0[5]}'.format(platform.uname()),
        Python=sys.version,
        Calibre_Web=calibre_web_version,
        WebServer=server.VERSION,
        Flask=flask.__version__,
        Flask_Login=flask_loginVersion,
        Flask_Principal=flask_principal.__version__,
        Flask_WTF=flaskwtf_version,
        Werkzeug=werkzeug.__version__,
        Babel=babel.__version__,
        Jinja2=jinja2.__version__,
        Requests=requests.__version__,
        SqlAlchemy=sqlalchemy.__version__,
        pySqlite=sqlite3.version,
        SQLite=sqlite3.sqlite_version,
        iso639=isoLanguages.__version__,
        pytz=pytz.__version__,
        Unidecode=unidecode_version,
        Scholarly=scholarly_version,
        Flask_SimpleLDAP=u'installed' if bool(services.ldap) else None,
        python_LDAP=services.ldapVersion if bool(services.ldapVersion) else None,
        Goodreads=u'installed' if bool(services.goodreads_support) else None,
        jsonschema=services.SyncToken.__version__ if bool(services.SyncToken) else None,
        flask_dance=flask_danceVersion,
        greenlet=greenlet_Version
    )
    _VERSIONS.update(gdriveutils.get_versions())
    _VERSIONS.update(uploader.get_versions(True))
else:
    _VERSIONS = OrderedDict(
        Platform = '{0[0]} {0[2]} {0[3]} {0[4]} {0[5]}'.format(platform.uname()),
        Python = sys.version,
        Calibre_Web=calibre_web_version,
        Werkzeug = werkzeug.__version__,
        Jinja2=jinja2.__version__,
        pySqlite = sqlite3.version,
        SQLite = sqlite3.sqlite_version,
    )
    _VERSIONS.update(ret)
    _VERSIONS.update(uploader.get_versions(False))

def collect_stats():
    _VERSIONS['ebook converter'] = _(converter.get_calibre_version())
    _VERSIONS['unrar'] = _(converter.get_unrar_version())
    _VERSIONS['kepubify'] = _(converter.get_kepubify_version())
    return _VERSIONS

@about.route("/stats")
@flask_login.login_required
def stats():
    counter = calibre_db.session.query(db.Books).count()
    authors = calibre_db.session.query(db.Authors).count()
    categorys = calibre_db.session.query(db.Tags).count()
    series = calibre_db.session.query(db.Series).count()
    return render_title_template('stats.html', bookcounter=counter, authorcounter=authors, versions=collect_stats(),
                                 categorycounter=categorys, seriecounter=series, title=_(u"Statistics"), page="stat")
