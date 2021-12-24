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

import os
import json
import importlib
import sys
import inspect
import datetime
import concurrent.futures

from flask import Blueprint, request, Response, url_for
from flask_login import current_user
from flask_login import login_required
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import OperationalError, InvalidRequestError

from . import constants, logger, ub
from cps.services.Metadata import Metadata


meta = Blueprint('metadata', __name__)

log = logger.create()

new_list = list()
meta_dir = os.path.join(constants.BASE_DIR, "cps", "metadata_provider")
modules = os.listdir(os.path.join(constants.BASE_DIR, "cps", "metadata_provider"))
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
        ac = active.get(c.__id__, True)
        provider.append({"name": c.__name__, "active": ac, "initial": ac, "id": c.__id__})
    return Response(json.dumps(provider), mimetype='application/json')

@meta.route("/metadata/provider", methods=['POST'])
@meta.route("/metadata/provider/<prov_name>", methods=['POST'])
@login_required
def metadata_change_active_provider(prov_name):
    new_state = request.get_json()
    active = current_user.view_settings.get('metadata', {})
    active[new_state['id']] = new_state['value']
    current_user.view_settings['metadata'] = active
    try:
        try:
            flag_modified(current_user, "view_settings")
        except AttributeError:
            pass
        ub.session.commit()
    except (InvalidRequestError, OperationalError):
        log.error("Invalid request received: {}".format(request))
        return "Invalid request", 400
    if "initial" in new_state and prov_name:
        for c in cl:
            if c.__id__ == prov_name:
                data = c.search(new_state.get('query', ""))
                break
        return Response(json.dumps(data), mimetype='application/json')
    return ""

@meta.route("/metadata/search", methods=['POST'])
@login_required
def metadata_search():
    query = request.form.to_dict().get('query')
    data = list()
    active = current_user.view_settings.get('metadata', {})
    if query:
        generic_cover = ""
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            meta = {executor.submit(c.search, query, generic_cover): c for c in cl if active.get(c.__id__, True)}
            for future in concurrent.futures.as_completed(meta):
                data.extend(future.result())
    return Response(json.dumps(data), mimetype='application/json')






