import pytest

from cps import themes
from conftest import make_theme


@pytest.fixture
def asset_app(bare_app, bundled_dir):
    make_theme(bundled_dir, "demo",
               static={"css/a.css": "body{}"},
               options={"css_files": ["css/a.css"], "js_files": ["js/b.js"]})
    themes.init_app_themes(bare_app, bare_app.root_path + "/cfg/app.db")
    return bare_app


def test_theme_assets_urls(asset_app):
    with asset_app.test_request_context():
        demo = themes.get_theme("demo")
        assert themes.theme_assets(demo, "css_files") == ["/_themes/demo/css/a.css"]
        assert themes.theme_assets(demo, "js_files") == ["/_themes/demo/js/b.js"]
        assert themes.theme_assets(themes.get_theme("standard"), "css_files") == []


def test_theme_assets_respect_script_name(asset_app):
    with asset_app.test_request_context(base_url="http://localhost/books"):
        assert themes.theme_assets(themes.get_theme("demo"), "css_files") == ["/books/_themes/demo/css/a.css"]


def test_theme_static_is_served(asset_app):
    assert asset_app.test_client().get("/_themes/demo/css/a.css").data == b"body{}"


def test_theme_assets_is_a_jinja_global(asset_app):
    assert asset_app.jinja_env.globals["theme_assets"] is themes.theme_assets
