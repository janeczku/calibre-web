import json
import warnings
import zipfile

import pytest

from cps import theme_install as ti
from conftest import make_zip

ok_info = json.dumps({"name": "Demo", "identifier": "demo", "application": "cps", "author": "t"})


def extract(tmp_path, entries, **kw):
    z = make_zip(tmp_path / "t.zip", entries, **kw)
    dest = tmp_path / "out"
    dest.mkdir()
    return ti.extract_theme_zip(str(z), str(dest), {"standard", "caliblur"}), dest


def code_of(tmp_path, entries, **kw):
    with pytest.raises(ti.ThemeInstallError) as e:
        extract(tmp_path, entries, **kw)
    return e.value.code


def test_theme_at_root(tmp_path):
    r, dest = extract(tmp_path, {"info.json": ok_info, "static/css/a.css": "x"})
    assert r["info"]["identifier"] == "demo" and not r["has_templates"] and not r["has_js"]
    assert (dest / "static/css/a.css").read_text() == "x"


def test_single_top_folder_and_repo_noise_skipped(tmp_path):
    r, dest = extract(tmp_path, {
        "o-demo-abc/info.json": ok_info, "o-demo-abc/static/js/a.js": "x",
        "o-demo-abc/templates/layout.html": "x", "o-demo-abc/LICENSE": "MIT",
        "o-demo-abc/.github/workflows/ci.yml": "x", "o-demo-abc/package.json": "{}",
        "o-demo-abc/screenshot.png": "x", "__MACOSX/._info.json": "x"})
    assert r["has_templates"] and r["has_js"]
    assert sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()) == \
        ["LICENSE", "info.json", "static/js/a.js", "templates/layout.html"]


def test_directory_entries_allowed(tmp_path):
    r, dest = extract(tmp_path, {"info.json": ok_info, "static/": "", "static/css/": "", "static/css/a.css": "x"})
    assert (dest / "static/css/a.css").is_file()


@pytest.mark.parametrize("name", ["../evil.css", "/abs/static/a.css", "C:/x/static/a.css",
                                  "static\\a.css", "static//a.css", "static/./a.css",
                                  "o/.github/../../evil", "static/x.html:.css", "static:x/a.css", "static/" + "a" * 256 + ".css",
                                  "static/" + "/".join(["abcdefgh"] * 130) + ".css"])
def test_bad_paths_rejected_even_when_skipped(tmp_path, name):
    assert code_of(tmp_path, {"info.json": ok_info, name: "x"}) == "bad_path"


def test_symlink_rejected(tmp_path):
    assert code_of(tmp_path, {"info.json": ok_info}, symlinks={"static/a.css": "/etc/passwd"}) == "bad_type"


def test_skipped_symlink_rejected(tmp_path):
    assert code_of(tmp_path, {"info.json": ok_info}, symlinks={"docs/a": "/etc/passwd"}) == "bad_type"


@pytest.mark.parametrize("name", ["static/page.html", "static/x.htm", "static/x.xhtml", "static/run.py",
                                  "templates/x.js", "evil.sh", "static/PAGE.HTML", "README.html"])
def test_extension_allowlist(tmp_path, name):
    entries = {"info.json": ok_info, name: "x"}
    if name == "evil.sh":   # root-level non-kept file is skipped, not rejected
        extract(tmp_path, entries)
    else:
        assert code_of(tmp_path, entries) == "bad_extension"


def test_duplicate_entry(tmp_path):
    z = tmp_path / "t.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("info.json", ok_info)
            zf.writestr("static/a.css", "1")
            zf.writestr("static/a.css", "2")
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ti.ThemeInstallError) as e:
        ti.extract_theme_zip(str(z), str(dest), set())
    assert e.value.code == "duplicate"


def test_too_many_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(ti, "MAX_ENTRIES", 3)
    assert code_of(tmp_path, {"info.json": ok_info, "static/a.css": "x", "static/b.css": "x",
                              "static/c.css": "x"}) == "too_many_entries"


def test_zip_bomb_total(tmp_path, monkeypatch):
    monkeypatch.setattr(ti, "MAX_TOTAL_BYTES", 1000)
    assert code_of(tmp_path, {"info.json": ok_info, "static/a.css": b"\0" * 1000,
                              "static/b.css": b"\0" * 1000}) == "too_large"


def test_lying_file_size_header(tmp_path, monkeypatch):
    monkeypatch.setattr(ti, "MAX_FILE_BYTES", 100)
    z = make_zip(tmp_path / "t.zip", {"info.json": ok_info, "static/a.css": b"a" * 5000})
    real_infolist = zipfile.ZipFile.infolist

    def lying(self):
        infos = real_infolist(self)
        for i in infos:
            if i.filename == "static/a.css":
                i.file_size = 1
        return infos
    monkeypatch.setattr(zipfile.ZipFile, "infolist", lying)
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ti.ThemeInstallError) as e:
        ti.extract_theme_zip(str(z), str(dest), set())
    # zipfile stops reading at the declared size and fails the CRC check, so the real bytes never exceed it
    assert e.value.code in ("too_large", "not_zip")


def test_not_a_zip(tmp_path):
    p = tmp_path / "t.zip"
    p.write_text("hello")
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ti.ThemeInstallError) as e:
        ti.extract_theme_zip(str(p), str(dest), set())
    assert e.value.code == "not_zip"


def test_encrypted(tmp_path, monkeypatch):
    z = make_zip(tmp_path / "t.zip", {"info.json": ok_info, "static/a.css": "x"})
    real_infolist = zipfile.ZipFile.infolist

    def enc(self):
        infos = real_infolist(self)
        infos[-1].flag_bits |= 0x1
        return infos
    monkeypatch.setattr(zipfile.ZipFile, "infolist", enc)
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ti.ThemeInstallError) as e:
        ti.extract_theme_zip(str(z), str(dest), set())
    assert e.value.code == "encrypted"


@pytest.mark.parametrize("info,code", [
    (None, "no_info"),
    ("not json", "bad_info"),
    ("[]", "bad_info"),
    (json.dumps({"name": 1, "identifier": "demo", "application": "cps", "author": "t"}), "bad_info"),
    (json.dumps({"name": "x", "identifier": "my-theme", "application": "cps", "author": "t"}), "bad_info"),
    (json.dumps({"name": "x", "identifier": 5, "application": "cps", "author": "t"}), "bad_info"),
    (json.dumps({"name": "x", "identifier": "demo", "application": "other", "author": "t"}), "bad_info"),
    (json.dumps({"name": "x", "identifier": "standard", "application": "cps", "author": "t"}), "bundled"),
])
def test_info_validation(tmp_path, info, code):
    entries = {"static/a.css": "x"}
    if info is not None:
        entries["info.json"] = info
    assert code_of(tmp_path, entries) == code


def test_oversized_info_json(tmp_path):
    big = json.dumps({"name": "x", "identifier": "demo", "application": "cps", "author": "t",
                      "description": "d" * 70000})
    assert code_of(tmp_path, {"info.json": big}) == "bad_info"


def test_two_top_folders_no_root_info(tmp_path):
    assert code_of(tmp_path, {"a/info.json": ok_info, "b/x": "x"}) == "no_info"


def test_uppercase_js_sets_has_js(tmp_path):
    r, _ = extract(tmp_path, {"info.json": ok_info, "static/x.JS": "alert(1)"})
    assert r["has_js"]


def test_invalid_utf8_name_is_not_zip(tmp_path):
    z = tmp_path / "t.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("info.json", ok_info)
        zf.writestr("static/\u00e9.css", "x")  # non-ASCII name sets the UTF-8 flag
    z.write_bytes(z.read_bytes().replace("\u00e9".encode(), b"\xff\xfe"))
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ti.ThemeInstallError) as e:
        ti.extract_theme_zip(str(z), str(dest), set())
    assert e.value.code == "not_zip"


def test_os_error_while_writing_is_write_failed(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise OSError(36, "File name too long")
    monkeypatch.setattr(ti.os, "makedirs", boom)
    assert code_of(tmp_path, {"info.json": ok_info}) == "write_failed"
