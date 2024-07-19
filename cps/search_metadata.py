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

import concurrent.futures
import importlib
import inspect
import json
import os
import sys

from flask import Blueprint, Response, request, url_for
from .cw_login import current_user
from flask_babel import get_locale
from sqlalchemy.exc import InvalidRequestError, OperationalError
from sqlalchemy.orm.attributes import flag_modified

from cps.services.Metadata import Metadata
from . import constants, logger, ub, web_server
from .usermanagement import user_login_required

# current_milli_time = lambda: int(round(time() * 1000))

meta = Blueprint("metadata", __name__)

log = logger.create()

try:
    from dataclasses import asdict
except ImportError:
    log.info('*** "dataclasses" is needed for calibre-web to run. Please install it using pip: "pip install dataclasses" ***')
    print('*** "dataclasses" is needed for calibre-web to run. Please install it using pip: "pip install dataclasses" ***')
    web_server.stop(True)
    sys.exit(6)

new_list = list()
meta_dir = os.path.join(constants.BASE_DIR, "cps", "metadata_provider")
modules = os.listdir(os.path.join(constants.BASE_DIR, "cps", "metadata_provider"))
for f in modules:
    if os.path.isfile(os.path.join(meta_dir, f)) and not f.endswith("__init__.py"):
        a = os.path.basename(f)[:-3]
        try:
            importlib.import_module("cps.metadata_provider." + a)
            new_list.append(a)
        except (IndentationError, SyntaxError) as e:
            log.error("Syntax error for metadata source: {} - {}".format(a, e))
        except ImportError as e:
            log.debug("Import error for metadata source: {} - {}".format(a, e))


def list_classes(provider_list):
    classes = list()
    for element in provider_list:
        for name, obj in inspect.getmembers(
            sys.modules["cps.metadata_provider." + element]
        ):
            if (
                inspect.isclass(obj)
                and name != "Metadata"
                and issubclass(obj, Metadata)
            ):
                classes.append(obj())
    return classes


cl = list_classes(new_list)


@meta.route("/metadata/provider")
@user_login_required
def metadata_provider():
    active = current_user.view_settings.get("metadata", {})
    provider = list()
    for c in cl:
        ac = active.get(c.__id__, True)
        provider.append(
            {"name": c.__name__, "active": ac, "initial": ac, "id": c.__id__}
        )
    return Response(json.dumps(provider), mimetype="application/json")


@meta.route("/metadata/provider", methods=["POST"])
@meta.route("/metadata/provider/<prov_name>", methods=["POST"])
@user_login_required
def metadata_change_active_provider(prov_name):
    new_state = request.get_json()
    active = current_user.view_settings.get("metadata", {})
    active[new_state["id"]] = new_state["value"]
    current_user.view_settings["metadata"] = active
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
        data = []
        provider = next((c for c in cl if c.__id__ == prov_name), None)
        if provider is not None:
            data = provider.search(new_state.get("query", ""))
        return Response(
            json.dumps([asdict(x) for x in data]), mimetype="application/json"
        )
    return ""


@meta.route("/metadata/search", methods=["POST"])
@user_login_required
def metadata_search():
    query = request.form.to_dict().get("query")
    data = list()
    active = current_user.view_settings.get("metadata", {})
    locale = get_locale()
    if query:
        static_cover = url_for("static", filename="generic_cover.jpg")
        # start = current_milli_time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            meta = {
                executor.submit(c.search, query, static_cover, locale): c
                for c in cl
                if active.get(c.__id__, True)
            }
            for future in concurrent.futures.as_completed(meta):
                data.extend([asdict(x) for x in future.result() if x])
    # log.info({'Time elapsed {}'.format(current_milli_time()-start)})
    return Response(json.dumps(data), mimetype="application/json")
