import json
import os
import sys

import flask_themes2
import pytest
from flask import Flask
from flask_themes2 import Themes

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))


def make_theme(base_dir, identifier, templates=None, static=None, options=None, info_overrides=None):
    """Write a valid theme folder <base_dir>/<identifier> and return its path."""
    path = base_dir / identifier
    path.mkdir(parents=True, exist_ok=True)
    info = {"name": identifier, "identifier": identifier, "application": "cps", "author": "test"}
    if options:
        info["options"] = options
    info.update(info_overrides or {})
    (path / "info.json").write_text(json.dumps(info))
    for folder, files in (("templates", templates or {}), ("static", static or {})):
        for name, content in files.items():
            target = path / folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
    return path


@pytest.fixture(autouse=True)
def reusable_themes_blueprint():
    # Flask-Themes2 uses one module-level blueprint and adds its URL rule on every
    # init_themes() call; Flask refuses that once the blueprint was registered.
    # The app does this once per process, the tests once per test app.
    flask_themes2.themes_blueprint._got_registered_once = False


@pytest.fixture
def bundled_dir(tmp_path):
    """Directory holding the bundled themes of the test app (app.root_path/themes)."""
    path = tmp_path / "themes"
    path.mkdir()
    make_theme(path, "standard", info_overrides={"name": "Standard Theme"})
    make_theme(path, "caliblur", info_overrides={"name": "caliBlur! Dark Theme"})
    return path


@pytest.fixture
def theme_app(tmp_path, bundled_dir):
    app = Flask("cps", root_path=str(tmp_path))
    Themes().init_themes(app, app_identifier="cps")
    return app
