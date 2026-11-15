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
               options={"repository": "https://github.com/o/liquid"}, info_overrides={"version": "1.1"})
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    themes.init_app_themes(bare_app, str(cfg / "app.db"))
    with bare_app.app_context():
        rows = {r["identifier"]: r for r in ti.installed_themes()}
        assert ti.bundled_identifiers() == {"standard", "caliblur"}
    assert rows["standard"]["bundled"] and rows["standard"]["version"] is None
    assert rows["liquid"] == {"identifier": "liquid", "name": "liquid", "version": "1.1",
                              "bundled": False, "repository": "https://github.com/o/liquid"}


@pytest.mark.parametrize("raw", ["1.2\n", "١.٢", "1" * 40])
def test_parse_version_rejects_hostile(raw):
    assert ti.parse_version(raw) is None


@pytest.mark.parametrize("raw,expected", [
    ("https://github.com/o/r\n", None),
    ("https://github.com/o/..", None),
    ("https://github.com/o/.", None),
    ("https://github.com/o/.git", None),
    ("https://github.com/o/x.git.git", ("o", "x.git")),
])
def test_parse_repository_hardening(raw, expected):
    assert ti.parse_repository(raw) == expected


def test_is_newer_non_string():
    assert ti.is_newer(123, "1") is False


def test_installed_themes_invalid_repository_and_numeric_version(bare_app, tmp_path, monkeypatch):
    cfg = tmp_path / "cfg"
    make_theme(cfg / "themes", "bad_repo_theme",
               options={"repository": "https://gitlab.com/o/r"}, info_overrides={"version": 1.5})
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    themes.init_app_themes(bare_app, str(cfg / "app.db"))
    ti._warned_repository.clear()
    warnings = []
    monkeypatch.setattr(ti.log, "warning", lambda *a, **k: warnings.append(a))
    with bare_app.app_context():
        ti.installed_themes()
        rows = {r["identifier"]: r for r in ti.installed_themes()}
    assert rows["bad_repo_theme"]["repository"] is None
    assert rows["bad_repo_theme"]["version"] == "1.5"
    assert len(warnings) == 1


def test_check_content_length():
    for bad, code in ((None, "no_length"), (ti.MAX_ZIP_BYTES + 64 * 1024 + 1, "too_large")):
        with pytest.raises(ti.ThemeInstallError) as e:
            ti.check_content_length(bad)
        assert e.value.code == code
    ti.check_content_length(1000)


def test_installed_themes_ignores_top_level_repository(bare_app, tmp_path, monkeypatch):
    # Flask-Themes2 keeps application-specific keys in "options"; a top-level "repository" is not ours.
    cfg = tmp_path / "cfg"
    make_theme(cfg / "themes", "toplevel", info_overrides={"repository": "https://github.com/o/r"})
    monkeypatch.delenv("CALIBRE_THEMES_DIR", raising=False)
    themes.init_app_themes(bare_app, str(cfg / "app.db"))
    with bare_app.app_context():
        rows = {r["identifier"]: r for r in ti.installed_themes()}
    assert rows["toplevel"]["repository"] is None
