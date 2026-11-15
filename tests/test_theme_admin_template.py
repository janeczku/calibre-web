"""Theme names from info.json must be escaped on the UI configuration page, never run through gettext."""
import glob
import os
import re
from types import SimpleNamespace

from flask import Flask, g, render_template_string
from flask_babel import Babel

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TEMPLATE = os.path.join(ROOT, "cps", "themes", "standard", "templates", "config_view_edit.html")
HOSTILE = '<img src=x onerror=alert(1)> 50% off %(x)s'


def _snippets():
    """The theme select and the theme table rows, exactly as they are in the real template."""
    with open(TEMPLATE, encoding="utf-8") as f:
        source = f.read()
    select = re.search(r"\{% set bundled_themes.*?</select>", source, re.S).group(0)
    rows = re.search(r"\{% for row in theme_rows %\}.*?\{% endfor %\}", source, re.S).group(0)
    return select, rows


def _render(snippet):
    app = Flask("cps")
    Babel(app)
    theme_rows = [
        {"identifier": "standard", "name": "Standard Theme", "version": None, "bundled": True, "repository": None},
        {"identifier": "evil", "name": HOSTILE, "version": "1.0", "bundled": False, "repository": None},
    ]
    with app.test_request_context():
        g.themes = [SimpleNamespace(identifier=r["identifier"], name=r["name"]) for r in theme_rows]
        return render_template_string(snippet, theme_rows=theme_rows,
                                      conf=SimpleNamespace(config_theme_identifier="standard"))


def test_user_theme_name_is_escaped_in_select():
    html = _render(_snippets()[0])
    assert "<img" not in html
    assert "&lt;img src=x onerror=alert(1)&gt; 50% off %(x)s" in html
    assert ">Standard Theme</option>" in html


def test_user_theme_name_is_escaped_in_table():
    html = _render(_snippets()[1])
    assert "<img" not in html
    assert '<td class="theme-name">&lt;img src=x onerror=alert(1)&gt; 50% off %(x)s</td>' in html
    assert '<td class="theme-name">Standard Theme</td>' in html


def test_theme_names_are_only_translated_for_bundled_themes():
    for path in glob.glob(os.path.join(ROOT, "cps", "themes", "*", "templates", "*.html")):
        with open(path, encoding="utf-8") as f:
            source = f.read()
        for match in re.finditer(r"_\(\s*\w+\.name\s*\)", source):
            guard = source[max(0, match.start() - 80):match.start()]
            assert "bundled" in guard, "%s: %s outside a bundled-theme check" % (path, match.group(0))
