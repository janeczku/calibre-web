# -*- coding: utf-8 -*-
from flask import Blueprint, send_from_directory
import os
from . import constants

spa = Blueprint('spa', __name__)

@spa.route("/spa")
@spa.route("/spa/<path:path>")
def serve_spa(path: str = "index.html"):
    dist = os.path.join(constants.BASE_DIR, "frontend", "dist")
    
    # If path is empty, serve index.html
    if not path:
        return send_from_directory(dist, "index.html")
        
    # Check if the requested file exists in dist
    file_path = os.path.join(dist, path)
    if os.path.isfile(file_path):
        return send_from_directory(dist, path)
    else:
        # Fallback to index.html for React Router routing to take over
        return send_from_directory(dist, "index.html")
