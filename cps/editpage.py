import os
import flask
from flask import Blueprint, Flask, abort, request
from functools import wraps
from pathlib import Path
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound

from .render_template import render_title_template
from . import logger, config, ub
from .constants import CONFIG_DIR as _CONFIG_DIR

log = logger.create()

editpage = Blueprint('editpage', __name__)

def edit_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_edit() or current_user.role_admin():
            return f(*args, **kwargs)
        abort(403)

    return inner

def _get_checkbox(dictionary, field, default):
    new_value = dictionary.get(field, default)
    convertor = lambda y: y == "on"
    new_value = convertor(new_value)

    return new_value

@editpage.route("/admin/page/<string:file>", methods=["GET", "POST"])
@login_required
@edit_required
def edit_page(file):
    doc = ""
    title = ""
    name = ""
    icon = "file"
    is_enabled = True
    order = 0
    position = "0"

    page = ub.session.query(ub.Page).filter(ub.Page.id == file).first()

    try:
        title = page.title
        name = page.name
        icon = page.icon
        is_enabled = page.is_enabled
        order = page.order
        position = page.position
    except AttributeError:
        if file != "new":
            abort(404)

    if request.method == "POST":
        to_save = request.form.to_dict()
        title = to_save.get("title", "").strip()
        name = to_save.get("name", "").strip()
        icon = to_save.get("icon", "").strip()
        position = to_save.get("position", "").strip()
        order = int(to_save.get("order", 0))
        content = to_save.get("content", "").strip()
        is_enabled = _get_checkbox(to_save, "is_enabled", True)

        if page:
            page.title = title
            page.name = name
            page.icon = icon
            page.is_enabled = is_enabled
            page.order = order
            page.position = position
            ub.session_commit("Page edited {}".format(file))
        else:
            new_page = ub.Page(title=title, name=name, icon=icon, is_enabled=is_enabled, order=order, position=position)
            ub.session.add(new_page)
            ub.session_commit("Page added {}".format(file))

        if (file == "new"):
            file = str(new_page.id)
        dir_config_path = os.path.join(_CONFIG_DIR, 'pages')
        file_name = Path(name + '.md')
        file_path = dir_config_path / file_name
        os.makedirs(dir_config_path, exist_ok=True)

        try:
            with open(file_path, 'w') as f:
                f.write(content)
                f.close()
        except Exception as ex:
            log.error(ex)

    if file != "new":
        try:
            dir_config_path = Path(_CONFIG_DIR) / 'pages'
            file_path = dir_config_path / f"{name}.md"

            with open(file_path, 'r') as f:
                doc = f.read()
        except NotFound:
            log.error("'%s' was accessed but file doesn't exists." % file)

    else:
        doc = "## New file\n\nInformation"

    return render_title_template("edit_page.html", title=title, name=name, icon=icon, is_enabled=is_enabled, order=order, position=position, content=doc, file=file)
