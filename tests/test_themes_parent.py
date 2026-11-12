import pytest

from cps import themes
from conftest import make_theme


@pytest.fixture
def family_app(bare_app, bundled_dir):
    make_theme(bundled_dir, "standard", templates={"page.html": "S", "other.html": "S2"})
    make_theme(bundled_dir, "base", templates={"page.html": "B"},
               options={"css_files": ["css/b.css"], "body_class": "b"})
    make_theme(bundled_dir, "child", options={"parent": "base", "css_files": ["css/c.css"], "body_class": "c"})
    make_theme(bundled_dir, "lonely", options={"parent": "nope"})
    make_theme(bundled_dir, "selfish", options={"parent": "selfish"})
    make_theme(bundled_dir, "a", options={"parent": "b"})
    make_theme(bundled_dir, "b", options={"parent": "a"})
    themes.init_app_themes(bare_app, bare_app.root_path + "/cfg/app.db")
    return bare_app


def chain(identifier):
    return [t.identifier for t in themes.theme_chain(themes.get_theme(identifier))]


def test_child_template_then_parent_then_standard(family_app):
    with family_app.app_context():
        assert themes.resolve_template("child", "page.html") == "_themes/base/page.html"
        assert themes.resolve_template("child", "other.html") == "_themes/standard/other.html"
        assert themes.resolve_template("base", "page.html") == "_themes/base/page.html"


def test_assets_and_body_class_ancestors_first(family_app):
    with family_app.test_request_context():
        child = themes.get_theme("child")
        assert themes.theme_assets(child, "css_files") == ["/_themes/base/css/b.css", "/_themes/child/css/c.css"]
        assert themes.theme_body_class(child) == "b c"


def test_theme_chain_stops_on_unknown_and_cycles(family_app):
    with family_app.app_context():
        assert chain("lonely") == ["lonely"]
        assert chain("selfish") == ["selfish"]
        assert chain("a") == ["a", "b"]
        assert chain("child") == ["child", "base"]


def test_body_class_is_a_jinja_global(family_app):
    assert family_app.jinja_env.globals["theme_body_class"] is themes.theme_body_class
