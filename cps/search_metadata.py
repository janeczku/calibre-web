# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2021 OzzieIsaacs
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
import datetime
from functools import wraps
import os

from flask import Blueprint, request, render_template, Response, g, make_response, abort
from flask_login import login_required
from flask_login import current_user
from sqlalchemy.sql.expression import func, text, or_, and_, true
from werkzeug.security import check_password_hash

from . import constants, logger, config, db, calibre_db, ub, services, get_locale, isoLanguages
# from .metadata_provider

opds = Blueprint('metadata', __name__)

log = logger.create()


#for module in os.listdir(os.join(constants.BASE_DIR, "metadata_provider")):
#    if module == '__init__.py' or module[-3:] != '.py':
#        continue
#    __import__(module[:-3], locals(), globals())
#del module

from os.path import basename, isfile
# import glob
meta_dir = os.path.join(constants.BASE_DIR, "cps", "metadata_provider")
modules = os.listdir(os.path.join(constants.BASE_DIR, "cps", "metadata_provider")) #glob.glob(join(dirname(__file__), "*.py"))
__all__ = [ basename(f)[:-3] for f in modules if isfile(os.path.join(meta_dir, f)) and not f.endswith('__init__.py')]

import importlib
for a in __all__:
    importlib.import_module("cps.metadata_provider." + a)

import sys, inspect
def print_classes():
    for a in __all__:
        for name, obj in inspect.getmembers(sys.modules["cps.metadata_provider." + a]):
            if inspect.isclass(obj):
                print(obj)

print_classes()

@opds.route("/metadata/provider")
@login_required
def metadata_provider():
    return ""

@opds.route("/metadata/search")
@login_required
def metadata_search():
    return ""

@opds.route("/metadata/replace/<id>")
@login_required
def metadata_provider(id):
    return ""
