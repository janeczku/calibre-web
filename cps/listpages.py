import flask
import json
from flask import Blueprint, jsonify, make_response,abort
from flask_login import current_user, login_required
from functools import wraps
from flask_babel import gettext as _

from .render_template import render_title_template
from . import ub, db

listpages = Blueprint('listpages', __name__)

def edit_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if current_user.role_edit() or current_user.role_admin():
            return f(*args, **kwargs)
        abort(403)

    return inner

@listpages.route("/admin/pages/", methods=["GET"])
@login_required
@edit_required
def show_list():
    pages = ub.session.query(ub.Page).order_by(ub.Page.position).order_by(ub.Page.order).all()

    return render_title_template('list_pages.html', title=_("Pages List"), page="book_table", pages=pages)
