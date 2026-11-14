import hashlib
import json
import os
import sys

import pytest

from cps import theme_install as ti
from conftest import info, install, stage


def code_of(fn, *args):
    with pytest.raises(ti.ThemeInstallError) as e:
        fn(*args)
    return e.value.code


def test_first_install_creates_themes_dir_and_loads(env):
    app, cfg = env
    assert not (cfg / "themes").exists()
    s = stage({"info.json": info(version="1.0"), "static/css/a.css": "x"})
    assert s["installed"] is False and s["installed_version"] is None
    assert ti.commit(s["token"], 1, None, False)["version"] == "1.0"
    assert "demo" in app.theme_manager.themes
    assert not os.listdir(app.config["CW_THEME_STAGING_DIR"])


def test_reinstall_requires_matching_version(env):
    install(version="1.0")
    s = stage({"info.json": info(version="1.1")})
    assert s["installed"] and s["installed_version"] == "1.0"
    assert code_of(ti.commit, s["token"], 1, None, False) == "needs_version_confirm"
    assert code_of(ti.commit, s["token"], 1, "1.1", False) == "bad_token"


def test_missing_versions_confirm_with_empty_string(env):
    install(version=None)
    s = stage({"info.json": info(version=None)})
    assert s["installed_version"] is None
    ti.commit(s["token"], 1, "", False)


def test_code_requires_trust(env):
    for entries in ({"templates/layout.html": "x"}, {"static/js/a.js": "x"}):
        s = stage({"info.json": info(), **entries})
        assert code_of(ti.commit, s["token"], 1, None, False) == "needs_trust"
    s = stage({"info.json": info(), "static/js/a.js": "x"})
    ti.commit(s["token"], 1, None, True)


def test_token_is_single_use_user_bound_and_expires(env, monkeypatch):
    app, cfg = env
    s = stage({"info.json": info()})
    assert code_of(ti.commit, s["token"], 2, None, False) == "bad_token"
    ti.commit(s["token"], 1, None, False)
    assert code_of(ti.commit, s["token"], 1, None, False) == "bad_token"
    s = stage({"info.json": info(version="2")})
    assert os.listdir(app.config["CW_THEME_STAGING_DIR"])
    real = ti.time.time
    monkeypatch.setattr(ti.time, "time", lambda: real() + ti.STAGE_TTL + 1)
    assert code_of(ti.commit, s["token"], 1, "1", False) == "bad_token"
    assert not os.listdir(app.config["CW_THEME_STAGING_DIR"])


def test_update_replaces_old_files_and_active_templates(env):
    app, cfg = env
    install(version="1.0", extra={"templates/layout.html": "OLD", "static/old.css": "x"}, trust=True)
    app.jinja_env.cache[("dummy", "x")] = object()
    install(version="1.1", extra={"templates/layout.html": "NEW"}, trust=True, confirm="1.1")
    root = cfg / "themes" / "demo"
    assert (root / "templates/layout.html").read_text() == "NEW"
    assert not (root / "static/old.css").exists()
    assert len(app.jinja_env.cache) == 0
    assert [p.name for p in (cfg / "themes").iterdir()] == ["demo"]


def test_failed_swap_keeps_original(env, monkeypatch):
    app, cfg = env
    install(version="1.0")
    s = stage({"info.json": info(version="1.1")})
    real = os.replace

    def flaky(src, dst):
        if ".incoming-" in str(src):
            raise OSError("boom")
        return real(src, dst)
    monkeypatch.setattr(ti.os, "replace", flaky)
    assert code_of(ti.commit, s["token"], 1, "1.1", False) == "install_failed"
    assert json.loads((cfg / "themes/demo/info.json").read_text())["version"] == "1.0"
    assert [p.name for p in (cfg / "themes").iterdir()] == ["demo"]


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), reason="needs non-root posix")
def test_read_only_themes_dir(env):
    app, cfg = env
    (cfg / "themes").mkdir()
    (cfg / "themes").chmod(0o555)
    try:
        assert ti.themes_dir_writable() is False
        s = stage({"info.json": info()})
        assert code_of(ti.commit, s["token"], 1, None, False) == "read_only"
    finally:
        (cfg / "themes").chmod(0o755)


def test_wrong_theme_on_update(env):
    assert code_of(lambda: stage({"info.json": info()}, expected_identifier="other")) == "wrong_theme"


def test_discard_removes_staging(env):
    app, cfg = env
    s = stage({"info.json": info()})
    assert os.listdir(app.config["CW_THEME_STAGING_DIR"])
    ti.discard(s["token"], 1)
    assert not os.listdir(app.config["CW_THEME_STAGING_DIR"])
    ti.discard("unknown", 1)


def test_write_capped(tmp_path):
    dest = tmp_path / "f"
    assert ti.write_capped([b"abc", b"def"], str(dest), 10) == hashlib.sha256(b"abcdef").hexdigest()
    assert code_of(ti.write_capped, [b"abcdef", b"ghijk"], str(dest), 10) == "too_large"
    assert not dest.exists()


def test_init_app_empties_staging_and_leftovers(env):
    app, cfg = env
    install()
    staging = app.config["CW_THEME_STAGING_DIR"]
    open(os.path.join(staging, "junk.zip"), "w").close()
    os.mkdir(os.path.join(staging, "dir"))
    (cfg / "themes" / ".demo.old-x").mkdir()
    (cfg / "themes" / ".demo.incoming-y").mkdir()
    ti.init_app(app, str(cfg / "app.db"))
    assert not os.listdir(staging)
    assert [p.name for p in (cfg / "themes").iterdir()] == ["demo"]


def test_prepare_staging_root_refuses_unsafe(tmp_path):
    fresh = tmp_path / "fresh"
    ti.prepare_staging_root(str(fresh))
    assert fresh.is_dir()
    if os.name == "nt":
        return
    assert fresh.stat().st_mode & 0o777 == 0o700
    ti.prepare_staging_root(str(fresh))
    link = tmp_path / "link"
    link.symlink_to(tmp_path)
    assert code_of(ti.prepare_staging_root, str(link)) == "unsafe_staging"
    loose = tmp_path / "loose"
    loose.mkdir()
    loose.chmod(0o777)
    assert code_of(ti.prepare_staging_root, str(loose)) == "unsafe_staging"
