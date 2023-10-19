import os
import flask
import markdown
from flask import abort
from pathlib import Path
from flask_babel import gettext as _
from werkzeug.exceptions import NotFound

from . import logger, config, ub
from .render_template import render_title_template
from .constants import CONFIG_DIR as _CONFIG_DIR

page = flask.Blueprint('page', __name__)

log = logger.create()

@page.route('/page/<string:file>', methods=['GET'])
def get_page(file):
    page = ub.session.query(ub.Page)\
        .filter(ub.Page.name == file)\
        .filter(ub.Page.is_enabled)\
        .first()

    if not page:
        log.error(f"'{file}' was accessed but is not enabled or it's not in database.")
        abort(404)

    try:
        dir_config_path = Path(_CONFIG_DIR) / 'pages'
        file_path = dir_config_path / f"{file}.md"
        with open(file_path, 'r') as f:
            temp_md = f.read()
        body = markdown.markdown(temp_md)

        return render_title_template('page.html', body=body, title=page.title, page=page.name)
    except NotFound:
        log.error("'%s' was accessed but file doesn't exists." % file)
        abort(404)
