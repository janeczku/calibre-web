import flask
import json
from flask import make_response,abort
from flask_login import current_user, login_required
from functools import wraps
from flask_babel import gettext as _

from .render_template import render_title_template
from . import ub, db

listpages = flask.Blueprint('listpages', __name__)

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

@listpages.route("/ajax/listpages")
@login_required
@edit_required
def list_pages():
    pages = ub.session.query(ub.Page).order_by(ub.Page.position).order_by(ub.Page.order).all()
    table_entries = {'totalNotFiltered': len(pages), 'total': len(pages), "rows": pages}
    js_list = json.dumps(table_entries, cls=db.AlchemyEncoder)
    response = make_response(js_list)
    response.headers["Content-Type"] = "application/json; charset=utf-8"

    return response
