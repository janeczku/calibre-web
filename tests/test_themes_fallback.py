import pytest
from flask import render_template

from cps import themes
from conftest import make_theme

LAYOUT = "STD[{% block body %}{% endblock %}]"
PAGE = '{% extends theme("layout.html") %}{% block body %}P{% endblock %}'


@pytest.fixture
def fallback_app(bare_app, bundled_dir):
    make_theme(bundled_dir, "standard", templates={"layout.html": LAYOUT, "page.html": PAGE})
    make_theme(bundled_dir, "demo")
    themes.init_app_themes(bare_app)
    return bare_app


def test_theme_without_layout_uses_standard_layout(fallback_app):
    with fallback_app.test_request_context():
        assert render_template("_themes/standard/page.html", _theme="demo") == "STD[P]"


def test_theme_layout_override_wins(fallback_app, bundled_dir):
    make_theme(bundled_dir, "demo", templates={"layout.html": "DEMO[{% block body %}{% endblock %}]"})
    with fallback_app.test_request_context():
        assert render_template("_themes/standard/page.html", _theme="demo") == "DEMO[P]"
