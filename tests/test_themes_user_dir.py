import logging
import os

import pytest

from cps import themes
from conftest import make_theme


@pytest.fixture
def cfg_dir(tmp_path):
    path = tmp_path / "cfg"
    path.mkdir()
    return path


def init(app, cfg_dir):
    themes.init_app_themes(app, str(cfg_dir / "app.db"))


def identifiers(app):
    with app.app_context():
        return [t.identifier for t in themes.get_available_themes()]


def test_user_themes_dir_default_and_env(monkeypatch):
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    assert themes.get_user_themes_dir("/config/app.db") == os.path.join("/config", "themes")
    monkeypatch.setenv("CALIBRE_THEMES_DIR", "/themes")
    assert themes.get_user_themes_dir("/config/app.db") == "/themes"
    monkeypatch.setenv("CALIBRE_THEMES_DIR", "")
    assert themes.get_user_themes_dir("/config/app.db") == os.path.join("/config", "themes")


def test_user_theme_is_loaded(bare_app, cfg_dir, monkeypatch):
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    make_theme(cfg_dir / "themes", "demo")
    init(bare_app, cfg_dir)
    assert identifiers(bare_app) == ["caliblur", "demo", "standard"]


def test_missing_user_dir_is_fine(bare_app, cfg_dir, monkeypatch):
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    init(bare_app, cfg_dir)
    assert identifiers(bare_app) == ["caliblur", "standard"]


def test_user_theme_cannot_shadow_bundled(bare_app, bundled_dir, cfg_dir, monkeypatch, caplog):
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    make_theme(cfg_dir / "themes", "standard", templates={"layout.html": "EVIL"})
    init(bare_app, cfg_dir)
    with bare_app.app_context():
        assert themes.get_theme("standard").path == str(bundled_dir / "standard")
    assert "standard" in caplog.text


def test_user_loader_skips_invalid(bare_app, cfg_dir, monkeypatch, caplog):
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    user = cfg_dir / "themes"
    (user / "bad_json").mkdir(parents=True)
    (user / "bad_json" / "info.json").write_text("{")
    make_theme(user, "noauthor", info_overrides={"author": None})
    (user / "noauthor" / "info.json").write_text('{"name": "x", "identifier": "noauthor", "application": "cps"}')
    make_theme(user, "mismatch", info_overrides={"identifier": "other"})
    make_theme(user, "my-theme")
    caplog.set_level(logging.WARNING)
    init(bare_app, cfg_dir)
    assert identifiers(bare_app) == ["caliblur", "standard"]
    for folder in ("bad_json", "noauthor", "mismatch", "my-theme"):
        assert folder in caplog.text


@pytest.mark.parametrize("bad", [
    {"name": 123},
    {"options": ["not", "a", "dict"]},
    {"options": {"parent": ["standard"]}},
    {"options": {"css_files": "css/a.css"}},
    {"options": {"js_files": [1, 2]}},
    {"options": {"body_class": ["x"]}},
])
def test_user_loader_skips_wrong_value_types(bare_app, cfg_dir, monkeypatch, caplog, bad):
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    make_theme(cfg_dir / "themes", "typed", info_overrides=bad)
    caplog.set_level(logging.WARNING)
    init(bare_app, cfg_dir)
    assert identifiers(bare_app) == ["caliblur", "standard"]
    assert "typed" in caplog.text
