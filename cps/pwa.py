# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2026 OzzieIsaacs
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

from flask import Blueprint, jsonify, make_response, render_template, url_for

from . import config, constants

pwa = Blueprint('pwa', __name__)


@pwa.route("/manifest.json")
def manifest():
    instance = config.config_calibre_web_title or "Calibre-Web"
    response = jsonify({
        "name": instance,
        "short_name": instance,
        "description": "Browse and read the books of your Calibre library, online and offline.",
        "start_url": url_for("web.index"),
        "scope": url_for("web.index"),
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#f8f8f8",
        "icons": [
            {
                "src": url_for("static", filename="icon.png"),
                "sizes": "800x800",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": url_for("static", filename="icon.svg"),
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any"
            }
        ]
    })
    response.headers["Cache-Control"] = "no-cache"
    return response


@pwa.route("/sw.js")
def service_worker():
    # Served from the application root so the service worker can control
    # every page of the (possibly reverse-proxy prefixed) application.
    response = make_response(render_template("sw.js", version=constants.STABLE_VERSION))
    response.headers["Content-Type"] = "application/javascript; charset=utf-8"
    response.headers["Cache-Control"] = "no-cache"
    return response


@pwa.route("/offline")
def offline_library():
    # Deliberately available without login: the page contains no library data,
    # books are listed client-side from the browser's own offline storage.
    # It also acts as the service worker's offline fallback page.
    return render_template("offline.html",
                           instance=config.config_calibre_web_title or "Calibre-Web",
                           title="Offline Books")
