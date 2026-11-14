import hashlib
import os

import pytest
import requests
from flask_babel import Babel

from cps import theme_install as ti
from cps.theme_install import ThemeInstallError
from conftest import info, make_zip

API = "https://api.github.com/repos/o/demo/releases/latest"
ZIPBALL = "https://api.github.com/repos/o/demo/zipball/v1.2"
ASSET = "https://github.com/o/demo/releases/download/v1.2/demo.zip"


class FakeResp:
    def __init__(self, status=200, json=None, headers=None, body=b"", text=""):
        self.status_code = status
        self._json = json
        self.headers = headers or {}
        self.body = body
        self.text = text
        self.closed = False

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json

    def iter_content(self, size):
        for i in range(0, len(self.body), size):
            yield self.body[i:i + size]

    def close(self):
        self.closed = True


def route(monkeypatch, routes):
    calls = []

    def fake(url, stream=False, timeout=(5, 15)):
        calls.append(url)
        if url not in routes:
            pytest.fail("unexpected request: %s" % url)
        res = routes[url]
        if isinstance(res, Exception):
            raise res
        return res
    monkeypatch.setattr(ti, "_http_get", fake)
    return calls


def release(tag="v1.2", assets=None, zipball=ZIPBALL):
    data = {"tag_name": tag, "assets": assets or []}
    if zipball is not None:
        data["zipball_url"] = zipball
    return FakeResp(200, json=data)


def code_of(fn, *args):
    with pytest.raises(ThemeInstallError) as exc:
        fn(*args)
    return exc.value.code


def test_latest_release_prefers_zip_asset(monkeypatch):
    route(monkeypatch, {API: release(assets=[
        {"name": "notes.txt", "browser_download_url": "https://github.com/n"},
        {"name": "demo.zip", "browser_download_url": ASSET}])})
    assert ti.latest_release("o", "demo") == {"tag": "v1.2", "version": "1.2", "download_url": ASSET}


def test_latest_release_falls_back_to_zipball(monkeypatch):
    route(monkeypatch, {API: release(assets=[{"name": "notes.txt", "browser_download_url": "x"}])})
    assert ti.latest_release("o", "demo")["download_url"] == ZIPBALL


@pytest.mark.parametrize("status,code", [(404, "no_release"), (403, "rate_limited"), (429, "rate_limited"),
                                         (500, "github_error")])
def test_latest_release_errors(monkeypatch, status, code):
    resp = FakeResp(status)
    route(monkeypatch, {API: resp})
    assert code_of(ti.latest_release, "o", "demo") == code
    assert resp.closed


def test_api_version_error(monkeypatch):
    route(monkeypatch, {API: FakeResp(400, text="Unsupported X-GitHub-Api-Version")})
    assert code_of(ti.latest_release, "o", "demo") == "api_version"
    route(monkeypatch, {API: FakeResp(400, text="other")})
    assert code_of(ti.latest_release, "o", "demo") == "github_error"


@pytest.mark.parametrize("data", [
    {"assets": [], "zipball_url": ZIPBALL},
    {"tag_name": 5, "assets": [], "zipball_url": ZIPBALL},
    {"tag_name": "v1", "assets": "x", "zipball_url": ZIPBALL},
    {"tag_name": "v1", "assets": ["x"], "zipball_url": ZIPBALL},
    {"tag_name": "v1", "assets": [{"name": 1, "browser_download_url": "x"}], "zipball_url": ZIPBALL},
    {"tag_name": "v1", "assets": [{"name": "a.zip", "browser_download_url": 1}], "zipball_url": ZIPBALL},
    {"tag_name": "v1", "assets": [], "zipball_url": 3},
    {"tag_name": "v1", "assets": []},
    [1],
])
def test_latest_release_malformed(monkeypatch, data):
    route(monkeypatch, {API: FakeResp(200, json=data)})
    assert code_of(ti.latest_release, "o", "demo") == "github_error"


def test_malformed_json(monkeypatch):
    route(monkeypatch, {API: FakeResp(200)})
    assert code_of(ti.latest_release, "o", "demo") == "github_error"


def test_network_error(monkeypatch):
    route(monkeypatch, {API: requests.ConnectionError("boom /secret/path")})
    with pytest.raises(ThemeInstallError) as exc:
        ti.latest_release("o", "demo")
    assert exc.value.code == "github_error"


def test_long_tag_is_capped(monkeypatch):
    route(monkeypatch, {API: release(tag="x" * 100)})
    assert len(ti.latest_release("o", "demo")["version"]) <= ti.MAX_VERSION_LEN


@pytest.mark.parametrize("url", [
    "https://github.com/x", "http://github.com/x", "https://evil.example/x", "https://github.com@evil.example/x",
    "https://user@github.com/x", "https://github.com:8443/x", "https://github.com.evil.example/x",
    "ftp://github.com/x", "https://GITHUB.com.evil/x", "//github.com/x", "", "https:///x"])
def test_check_host(url):
    if url == "https://github.com/x":
        ti.check_host(url)
        ti.check_host("https://GitHub.com:443/x")
    else:
        assert code_of(ti.check_host, url) == "bad_host"


def test_download_follows_allowlisted_redirects(tmp_path, monkeypatch):
    final = "https://objects.githubusercontent.com/x"
    hop = FakeResp(302, headers={"Location": final})
    route(monkeypatch, {ASSET: hop, final: FakeResp(200, body=b"hello")})
    dest = str(tmp_path / "a.zip")
    assert ti.download(ASSET, dest) == hashlib.sha256(b"hello").hexdigest()
    assert open(dest, "rb").read() == b"hello"
    assert hop.closed


def test_download_relative_redirect_stays_on_host(tmp_path, monkeypatch):
    route(monkeypatch, {ASSET: FakeResp(302, headers={"Location": "/y"}),
                        "https://github.com/y": FakeResp(200, body=b"z")})
    ti.download(ASSET, str(tmp_path / "a.zip"))


def test_download_refuses_foreign_redirect(tmp_path, monkeypatch):
    calls = route(monkeypatch, {ASSET: FakeResp(302, headers={"Location": "https://evil.example/x"})})
    assert code_of(ti.download, ASSET, str(tmp_path / "a.zip")) == "bad_host"
    assert calls == [ASSET]


def test_download_refuses_http(tmp_path, monkeypatch):
    route(monkeypatch, {ASSET: FakeResp(302, headers={"Location": "http://github.com/x"})})
    assert code_of(ti.download, ASSET, str(tmp_path / "a.zip")) == "bad_host"


def test_download_refuses_bad_start_url(tmp_path, monkeypatch):
    calls = route(monkeypatch, {})
    assert code_of(ti.download, "https://evil.example/a.zip", str(tmp_path / "a.zip")) == "bad_host"
    assert calls == []


def test_download_too_many_redirects(tmp_path, monkeypatch):
    urls = ["https://github.com/h%d" % i for i in range(8)]
    route(monkeypatch, {urls[i]: FakeResp(302, headers={"Location": urls[i + 1]}) for i in range(7)})
    assert code_of(ti.download, urls[0], str(tmp_path / "a.zip")) == "too_many_redirects"


def test_download_redirect_without_location_and_bad_status(tmp_path, monkeypatch):
    route(monkeypatch, {ASSET: FakeResp(302)})
    assert code_of(ti.download, ASSET, str(tmp_path / "a.zip")) == "github_error"
    route(monkeypatch, {ASSET: FakeResp(404)})
    assert code_of(ti.download, ASSET, str(tmp_path / "a.zip")) == "github_error"


def test_download_network_error(tmp_path, monkeypatch):
    route(monkeypatch, {ASSET: requests.Timeout("t")})
    assert code_of(ti.download, ASSET, str(tmp_path / "a.zip")) == "github_error"


def test_download_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(ti, "MAX_ZIP_BYTES", 10)
    route(monkeypatch, {ASSET: FakeResp(200, body=b"x" * 11)})
    dest = tmp_path / "a.zip"
    assert code_of(ti.download, ASSET, str(dest)) == "too_large"
    assert not dest.exists()


@pytest.fixture
def genv(env):
    app, cfg = env
    Babel(app)
    return env


def add_theme(cfg, ident, version="1.0", repo=None):
    from conftest import make_theme
    extra = {"version": version}
    if repo:
        extra["repository"] = repo
    make_theme(cfg / "themes", ident, info_overrides=extra)


def reload(app):
    from cps import theme_install
    theme_install.reload_themes(app)


def test_check_updates_mixed(genv, monkeypatch):
    app, cfg = genv
    for ident in "abcd":
        add_theme(cfg, ident, repo=None if ident == "c" else "https://github.com/o/" + ident)
    reload(app)
    api = "https://api.github.com/repos/o/%s/releases/latest"
    route(monkeypatch, {
        api % "a": release("v1.1"), api % "b": release("v1.0"), api % "d": release("nightly")})
    result = ti.check_updates()
    assert set(result) == {"a", "b", "d"}
    assert result["a"] == {"latest": "1.1", "update_available": True, "error": None}
    assert result["b"]["update_available"] is False and result["b"]["latest"] == "1.0"
    assert result["d"] == {"latest": "nightly", "update_available": False, "error": None}


def test_check_updates_stops_after_rate_limit(genv, monkeypatch):
    app, cfg = genv
    for ident in "ab":
        add_theme(cfg, ident, repo="https://github.com/o/" + ident)
    reload(app)
    calls = route(monkeypatch, {"https://api.github.com/repos/o/a/releases/latest": FakeResp(403),
                                "https://api.github.com/repos/o/b/releases/latest": FakeResp(403)})
    result = ti.check_updates()
    assert len(calls) == 1
    assert result["a"]["error"] and result["a"]["error"] == result["b"]["error"]
    assert result["a"]["latest"] is None and result["b"]["update_available"] is False


def test_check_updates_other_error_continues(genv, monkeypatch):
    app, cfg = genv
    for ident in "ab":
        add_theme(cfg, ident, repo="https://github.com/o/" + ident)
    reload(app)
    route(monkeypatch, {"https://api.github.com/repos/o/a/releases/latest": FakeResp(404),
                        "https://api.github.com/repos/o/b/releases/latest": release("v2")})
    result = ti.check_updates()
    assert result["a"]["error"] and result["b"]["update_available"] is True


def installed_demo(env, version="1.0"):
    app, cfg = env
    add_theme(cfg, "demo", version=version, repo="https://github.com/o/demo")
    reload(app)


def zip_bytes(tmp_path, entries):
    p = make_zip(str(tmp_path / "src.zip"), entries)
    return open(p, "rb").read()


def test_stage_update_end_to_end(env, monkeypatch, tmp_path):
    installed_demo(env)
    body = zip_bytes(tmp_path, {"info.json": info(version="1.1")})
    route(monkeypatch, {API: release("v1.1", assets=[{"name": "demo.zip", "browser_download_url": ASSET}]),
                        ASSET: FakeResp(200, body=body)})
    summary = ti.stage_update("demo", 1)
    assert summary["identifier"] == "demo" and summary["version"] == "1.1"
    assert summary["installed_version"] == "1.0"
    root = env[0].config["CW_THEME_STAGING_DIR"]
    assert not [n for n in os.listdir(root) if n.endswith(".zip")]


def test_stage_update_wrong_identifier(env, monkeypatch, tmp_path):
    installed_demo(env)
    body = zip_bytes(tmp_path, {"info.json": info(version="1.1", identifier="other")})
    route(monkeypatch, {API: release("v1.1", assets=[{"name": "demo.zip", "browser_download_url": ASSET}]),
                        ASSET: FakeResp(200, body=body)})
    assert code_of(ti.stage_update, "demo", 1) == "wrong_theme"


def test_stage_update_no_repository(env, monkeypatch):
    add_theme(env[1], "norepo")
    reload(env[0])
    route(monkeypatch, {})
    for ident in ("standard", "unknown", "norepo"):
        assert code_of(ti.stage_update, ident, 1) == "no_repository"
