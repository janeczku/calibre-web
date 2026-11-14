import pytest
import requests

from cps import theme_install as ti


class Resp:
    pass


@pytest.mark.parametrize("url,api", [
    ("https://api.github.com/repos/o/r/releases/latest", True),
    ("https://github.com/o/r/releases/download/v1/t.zip", False),
    ("https://codeload.github.com/o/r/zip/refs/tags/v1", False),
])
def test_github_api_headers_only_for_api_host(monkeypatch, url, api):
    seen = {}
    monkeypatch.setattr(requests, "get", lambda u, **kw: seen.update(kw) or Resp())
    ti._http_get(url)
    headers = seen["headers"]
    assert headers["User-Agent"] == "Calibre-Web"
    assert ("Accept" in headers) is api
    assert ("X-GitHub-Api-Version" in headers) is api


def test_theme_static_csp():
    assert ti.theme_static_csp("_themes.static") == (
        "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; sandbox")
    assert ti.theme_static_csp("web.index") is None
