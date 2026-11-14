import pytest

from cps import theme_install as ti
from cps import themes
from conftest import make_theme


@pytest.mark.parametrize("raw,expected", [
    ("1.2", (1, 2)), ("v1.2.0", (1, 2)), ("V10", (10,)), ("1.10", (1, 10)),
    ("1.2-beta", None), ("", None), (None, None), ("vv1", None),
])
def test_parse_version(raw, expected):
    assert ti.parse_version(raw) == expected


def test_is_newer():
    assert ti.is_newer("v1.10", "1.9")
    assert not ti.is_newer("1.2.0", "1.2")
    assert not ti.is_newer("1.1", "1.2")
    assert not ti.is_newer("1.3-rc", "1.2")
    assert not ti.is_newer("1.3", None)


def test_display_version():
    assert ti.display_version("1.2") == "1.2"
    assert ti.display_version(1.5) == "1.5"
    assert ti.display_version(True) is None
    assert ti.display_version(["1"]) is None
    assert ti.display_version("x" * 40) == "x" * 32


@pytest.mark.parametrize("raw,expected", [
    ("https://github.com/owner/repo", ("owner", "repo")),
    ("https://github.com/owner/repo/", ("owner", "repo")),
    ("https://github.com/owner/repo.git", ("owner", "repo")),
    ("http://github.com/owner/repo", None),
    ("https://gitlab.com/owner/repo", None),
    ("https://github.com/owner/repo/extra", None),
    ("https://github.com.evil.com/owner/repo", None),
    ("https://github.com/owner", None),
    (42, None),
])
def test_parse_repository(raw, expected):
    assert ti.parse_repository(raw) == expected


def test_installed_themes(bare_app, tmp_path, monkeypatch):
    cfg = tmp_path / "cfg"
    make_theme(cfg / "themes", "liquid",
               info_overrides={"version": "1.1", "repository": "https://github.com/o/liquid"})
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    themes.init_app_themes(bare_app, str(cfg / "app.db"))
    with bare_app.app_context():
        rows = {r["identifier"]: r for r in ti.installed_themes()}
        assert ti.bundled_identifiers() == {"standard", "caliblur"}
    assert rows["standard"]["bundled"] and rows["standard"]["version"] is None
    assert rows["liquid"] == {"identifier": "liquid", "name": "liquid", "version": "1.1",
                              "bundled": False, "repository": "https://github.com/o/liquid"}
