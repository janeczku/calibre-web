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
import os
import json
import importlib
import sys
import inspect

from flask import Blueprint, request, Response
from flask_login import current_user
from flask_login import login_required

from . import constants, logger
from cps.services.Metadata import Metadata

meta = Blueprint('metadata', __name__)

log = logger.create()

new_list = list()
meta_dir = os.path.join(constants.BASE_DIR, "cps", "metadata_provider")
modules = os.listdir(os.path.join(constants.BASE_DIR, "cps", "metadata_provider")) #glob.glob(join(dirname(__file__), "*.py"))
for f in modules:
    if os.path.isfile(os.path.join(meta_dir, f)) and not f.endswith('__init__.py'):
        a = os.path.basename(f)[:-3]
        try:
            importlib.import_module("cps.metadata_provider." + a)
            new_list.append(a)
        except ImportError:
            log.error("Import error for metadata source: {}".format(a))
            pass

def list_classes(provider_list):
    classes = list()
    for element in provider_list:
        for name, obj in inspect.getmembers(sys.modules["cps.metadata_provider." + element]):
            if inspect.isclass(obj) and name != "Metadata" and issubclass(obj, Metadata):
                classes.append(obj())
    return classes

cl = list_classes(new_list)

@meta.route("/metadata/provider")
@login_required
def metadata_provider():
    active = current_user.view_settings.get('metadata', {})
    provider = list()
    for c in cl:
        provider.append({"name": c.__name__, "active": active.get(c.__name__, True), "id": c.__id__})
    return Response(json.dumps(provider), mimetype='application/json')

@meta.route("/metadata/provider", methods=['POST'])
@login_required
def metadata_change_active_provider():
    active = current_user.view_settings.get('metadata', {})
    provider = list()
    for c in cl:
        provider.append({"name": c.__name__, "active": active.get(c.__name__, True), "id": c.__id__})
    return Response(json.dumps(provider), mimetype='application/json')

@meta.route("/metadata/search", methods=['POST'])
@login_required
def metadata_search():
    query = request.form.to_dict().get('query')
    data = list()
    active = current_user.view_settings.get('metadata', {})
    if query:
        for c in cl:
            if active.get(c.__name__, True):
                data.extend(c.search(query))
    return Response(json.dumps(data), mimetype='application/json')
