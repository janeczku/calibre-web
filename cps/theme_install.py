# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2026
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.


import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import tempfile
import threading
import time
import zipfile
import zlib

from flask import current_app
from flask_babel import lazy_gettext as N_
from flask_themes2 import IDENTIFIER, Theme

from . import logger, themes

log = logger.create()

MAX_ZIP_BYTES = 20 * 1024 * 1024
MAX_ENTRIES = 2000
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_INFO_BYTES = 64 * 1024
STAGE_TTL = 30 * 60
MAX_REDIRECTS = 5
MAX_VERSION_LEN = 32

GITHUB_API_VERSION = "2026-03-10"
GITHUB_HOSTS = {"api.github.com", "github.com", "codeload.github.com",
                "objects.githubusercontent.com", "release-assets.githubusercontent.com"}

_REPOSITORY_RE = re.compile(r"https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})/?")
_VERSION_RE = re.compile(r"[0-9]+(\.[0-9]+)*")

_DRIVE_RE = re.compile(r"[A-Za-z]:")
_ROOT_DOC_RE = re.compile(r"(LICENSE|README|COPYING)[^/]*")
_STATIC_EXTENSIONS = {".css", ".js", ".map", ".json", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
                      ".woff", ".woff2", ".ttf", ".otf", ".eot", ".txt"}
_TEMPLATE_EXTENSIONS = {".html", ".xml", ".jinja"}
_ROOT_DOC_EXTENSIONS = {"", ".txt", ".md"}
_CHUNK = 64 * 1024

_warned_repository = set()
_OLD_RE = re.compile(r"\.([A-Za-z0-9_]+)\.old-[0-9a-f]+")
_staged = {}
_lock = threading.Lock()


class ThemeInstallError(Exception):
    def __init__(self, code, message):
        super().__init__(code)
        self.code = code
        self.message = message


def parse_version(value):
    """Numeric tuple of a version like '1.2' or 'v1.2.0' (trailing zeros dropped), else None."""
    if not isinstance(value, str):
        return None
    if value[:1] in ("v", "V"):
        value = value[1:]
    if len(value) > MAX_VERSION_LEN or not _VERSION_RE.fullmatch(value):
        return None
    parts = [int(p) for p in value.split(".")]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def is_newer(latest, installed):
    latest, installed = parse_version(latest), parse_version(installed)
    return latest is not None and installed is not None and latest > installed


def display_version(value):
    if isinstance(value, str):
        return value[:MAX_VERSION_LEN]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def parse_repository(value):
    """(owner, repo) of a https://github.com/owner/repo URL, else None."""
    if not isinstance(value, str):
        return None
    match = _REPOSITORY_RE.fullmatch(value)
    if not match:
        return None
    owner, repo = match.groups()
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not repo or not repo.strip("."):
        return None
    return owner, repo


def bundled_identifiers():
    path = os.path.join(current_app.root_path, "themes")
    if not os.path.isdir(path):
        return set()
    return {n for n in os.listdir(path)
            if not n.startswith((".", "_")) and os.path.isdir(os.path.join(path, n))}


def installed_themes():
    bundled_path = os.path.join(current_app.root_path, "themes")
    rows = []
    for theme in themes.get_available_themes():
        raw = theme.info.get("repository")
        parsed = parse_repository(raw)
        if raw is not None and parsed is None and theme.identifier not in _warned_repository:
            _warned_repository.add(theme.identifier)
            log.warning("Theme '%s': invalid 'repository' in info.json, ignored", theme.identifier)
        rows.append({
            "identifier": theme.identifier,
            "name": theme.name,
            "version": display_version(theme.info.get("version")),
            "bundled": os.path.dirname(os.path.abspath(theme.path)) == bundled_path,
            "repository": "https://github.com/{}/{}".format(*parsed) if parsed else None,
        })
    return rows


def _check_entry(info):
    """Reject encrypted entries, non-regular files and hostile names; return the name without a trailing '/'."""
    if info.flag_bits & 0x1:
        raise ThemeInstallError("encrypted", N_("The archive contains encrypted files."))
    fmt = stat.S_IFMT(info.external_attr >> 16)  # 0 when the zip tool stored permission bits only
    if fmt not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ThemeInstallError("bad_type", N_("The archive contains links or special files."))
    name = info.filename
    bad = (not name or "\x00" in name or "\\" in name or name.startswith("/") or ":" in name or _DRIVE_RE.match(name)
           or len(name.encode("utf-8")) > 1024)
    if not bad:
        name = name[:-1] if name.endswith("/") else name
        bad = any(seg in ("", ".", "..") or len(seg.encode("utf-8")) > 255 for seg in name.split("/"))
    if bad:
        raise ThemeInstallError("bad_path", N_("The archive contains an invalid file name: %(name)s",
                                               name=info.filename[:100]))
    return name


def _is_kept(rel):
    return rel == "info.json" or rel.startswith(("static/", "templates/")) or \
        (_ROOT_DOC_RE.fullmatch(rel) is not None)


def _check_extension(rel):
    ext = os.path.splitext(rel.rsplit("/", 1)[-1])[1].lower()
    if rel == "info.json":
        return
    if rel.startswith("static/"):
        allowed = _STATIC_EXTENSIONS
    elif rel.startswith("templates/"):
        allowed = _TEMPLATE_EXTENSIONS
    else:
        allowed = _ROOT_DOC_EXTENSIONS
    if ext not in allowed:
        raise ThemeInstallError("bad_extension", N_("File type not allowed in a theme: %(name)s", name=rel[:100]))


def _write_member(zf, info, target, rel, limit, limit_code, total):
    """Copy one entry to target counting real bytes; return the new running total."""
    try:
        return _copy_member(zf, info, target, rel, limit, limit_code, total)
    except OSError:
        log.error("Theme install: writing '%s' failed", rel[:100], exc_info=True)
        raise ThemeInstallError("write_failed", N_("The theme could not be written."))


def _copy_member(zf, info, target, rel, limit, limit_code, total):
    """Copy one entry to target counting real bytes; return the new running total."""
    try:
        os.makedirs(os.path.dirname(target), 0o755, exist_ok=True)
        out = open(target, "xb")
    except (FileExistsError, NotADirectoryError):
        raise ThemeInstallError("duplicate", N_("The archive contains conflicting entries: %(name)s", name=rel[:100]))
    with out, zf.open(info) as src:
        size = 0
        while True:
            chunk = src.read(_CHUNK)
            if not chunk:
                break
            size += len(chunk)
            total += len(chunk)
            if size > limit:
                raise ThemeInstallError(limit_code, N_("The archive is too large."))
            if total > MAX_TOTAL_BYTES:
                raise ThemeInstallError("too_large", N_("The archive is too large."))
            out.write(chunk)
    os.chmod(target, 0o644)
    return total


def extract_theme_zip(zip_path, dest, bundled):
    """Validate zip_path and extract the theme into the empty directory dest.

    Returns {"info", "has_templates", "has_js"}; raises ThemeInstallError (caller deletes dest).
    """
    if not zipfile.is_zipfile(zip_path):
        raise ThemeInstallError("not_zip", N_("The file is not a valid zip archive."))
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return _extract(zf, dest, bundled)
    except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError, ValueError):
        raise ThemeInstallError("not_zip", N_("The file is not a valid zip archive."))


def _extract(zf, dest, bundled):
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ThemeInstallError("too_many_entries", N_("The archive contains too many files."))
    entries = []
    for info in infos:
        name = _check_entry(info)
        if name.startswith("__MACOSX/") or name.rsplit("/", 1)[-1] == ".DS_Store":
            continue
        entries.append((name, info))
    files = [(n, i) for n, i in entries if not i.filename.endswith("/")]

    if any(n == "info.json" for n, _ in files):
        prefix = ""
    else:
        top = {n.split("/", 1)[0] for n, _ in entries}
        if len(top) == 1 and any(n == next(iter(top)) + "/info.json" for n, _ in files):
            prefix = next(iter(top)) + "/"
        else:
            raise ThemeInstallError("no_info", N_("The archive has no info.json."))

    kept = []
    for name, info in files:
        rel = name[len(prefix):]
        if _is_kept(rel):
            _check_extension(rel)
            kept.append((rel, info))

    real_dest = os.path.realpath(dest)
    total = 0
    for rel, info in kept:
        target = os.path.join(dest, rel)
        if not os.path.realpath(target).startswith(real_dest + os.sep):
            raise ThemeInstallError("bad_path", N_("The archive contains an invalid file name: %(name)s", name=rel[:100]))
        if rel == "info.json":
            total = _write_member(zf, info, target, rel, MAX_INFO_BYTES, "bad_info", total)
        else:
            total = _write_member(zf, info, target, rel, MAX_FILE_BYTES, "too_large", total)

    try:
        theme = Theme(dest)
    except Exception:
        raise ThemeInstallError("bad_info", N_("info.json is not valid."))
    type_error = themes._info_type_error(theme)
    identifier = theme.identifier
    if type_error or not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier) \
            or theme.application != "cps":
        raise ThemeInstallError("bad_info", N_("info.json is not valid."))
    if identifier in bundled:
        raise ThemeInstallError("bundled", N_("A bundled theme already uses this identifier."))
    return {"info": theme.info,
            "has_templates": any(r.startswith("templates/") for r, _ in kept),
            "has_js": any(r.lower().endswith(".js") for r, _ in kept)}


def staging_root(settings_path):
    digest = hashlib.sha256(os.path.abspath(settings_path).encode("utf-8")).hexdigest()[:12]
    return os.path.join(tempfile.gettempdir(), "calibre-web-theme-staging-" + digest)


def prepare_staging_root(path):
    """Create the private staging folder, or verify an existing one is ours and not accessible by others."""
    try:
        os.mkdir(path, 0o700)
        return
    except FileExistsError:
        pass
    except OSError:
        raise ThemeInstallError("unsafe_staging", N_("The staging folder could not be created."))
    try:
        st = os.lstat(path)
    except OSError:
        raise ThemeInstallError("unsafe_staging", N_("The staging folder is not safe to use."))
    if not stat.S_ISDIR(st.st_mode) or (os.name != "nt" and (st.st_uid != os.getuid() or st.st_mode & 0o077)):
        raise ThemeInstallError("unsafe_staging", N_("The staging folder is not safe to use."))


def themes_dir_writable():
    path = current_app.config["CW_USER_THEMES_DIR"]
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return False
    return os.access(path, os.W_OK)


def _empty_dir(path):
    for name in os.listdir(path):
        full = os.path.join(path, name)
        if os.path.isdir(full) and not os.path.islink(full):
            shutil.rmtree(full, ignore_errors=True)
        else:
            try:
                os.remove(full)
            except OSError:
                pass


def init_app(app, settings_path):
    """Prepare the staging folder and remove leftovers of interrupted installs; never raises."""
    try:
        root = staging_root(settings_path)
        app.config["CW_THEME_STAGING_DIR"] = root
        prepare_staging_root(root)
        _empty_dir(root)
    except Exception:
        log.error("Theme staging folder could not be prepared", exc_info=True)
    try:
        path = app.config.get("CW_USER_THEMES_DIR")
        if path and os.path.isdir(path) and os.access(path, os.W_OK):
            _clean_themes_dir(path)
    except Exception:
        log.error("Leftovers in the themes folder could not be removed", exc_info=True)


def _clean_themes_dir(path):
    """Restore a theme lost in an interrupted swap from its newest '.old' folder; delete other leftovers."""
    olds = {}
    for name in os.listdir(path):
        if not name.startswith("."):
            continue
        match = _OLD_RE.fullmatch(name)
        if match and IDENTIFIER.fullmatch(match.group(1)):
            olds.setdefault(match.group(1), []).append(name)
        elif ".incoming-" in name:
            shutil.rmtree(os.path.join(path, name), ignore_errors=True)
    for identifier, names in olds.items():
        names.sort(key=lambda n: os.lstat(os.path.join(path, n)).st_mtime, reverse=True)
        if not os.path.lexists(os.path.join(path, identifier)):
            try:
                os.replace(os.path.join(path, names[0]), os.path.join(path, identifier))
                log.warning("Theme '%s' restored from '%s' after an interrupted update", identifier, names[0])
                names = names[1:]
            except OSError:
                log.error("Theme '%s' could not be restored from '%s'", identifier, names[0], exc_info=True)
                names = names[1:]
        for name in names:
            shutil.rmtree(os.path.join(path, name), ignore_errors=True)


def write_capped(chunks, dest_path, limit):
    """Write chunks to dest_path and return their SHA-256; too_large (file removed) beyond limit bytes."""
    digest = hashlib.sha256()
    size = 0
    try:
        with open(dest_path, "wb") as out:
            for chunk in chunks:
                size += len(chunk)
                if size > limit:
                    raise ThemeInstallError("too_large", N_("The archive is too large."))
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        try:
            os.remove(dest_path)
        except OSError:
            pass
        raise
    return digest.hexdigest()


def _drop(entry):
    shutil.rmtree(entry["path"], ignore_errors=True)


def _purge_expired():
    """Caller holds _lock."""
    now = time.time()
    for token in [t for t, e in _staged.items() if now - e["created"] > STAGE_TTL]:
        _drop(_staged.pop(token))


def stage_zip(zip_path, user_id, source, sha256, expected_identifier=None):
    """Validate and extract zip_path into a staging folder; the zip is deleted afterwards."""
    try:
        root = current_app.config["CW_THEME_STAGING_DIR"]
        prepare_staging_root(root)
        with _lock:
            _purge_expired()
        try:
            folder = tempfile.mkdtemp(dir=root)
        except OSError:
            log.error("Theme install: staging folder could not be created", exc_info=True)
            raise ThemeInstallError("install_failed", N_("The theme could not be installed."))
        try:
            result = extract_theme_zip(zip_path, folder, bundled_identifiers())
            theme_info = result["info"]
            identifier = theme_info["identifier"]
            if expected_identifier is not None and identifier != expected_identifier:
                raise ThemeInstallError("wrong_theme", N_("The archive contains a different theme."))
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
    finally:
        try:
            os.remove(zip_path)
        except OSError:
            pass
    version = display_version(theme_info.get("version"))
    installed = os.path.lexists(os.path.join(current_app.config["CW_USER_THEMES_DIR"], identifier))
    installed_version = None
    if installed:
        try:
            with open(os.path.join(current_app.config["CW_USER_THEMES_DIR"], identifier, "info.json"),
                      encoding="utf-8") as f:
                installed_version = display_version(json.load(f).get("version"))
        except (OSError, ValueError, AttributeError):
            pass
    token = secrets.token_urlsafe(32)
    name = theme_info.get("name")
    with _lock:
        _staged[token] = {"path": folder, "identifier": identifier, "name": name, "version": version,
                          "has_templates": result["has_templates"], "has_js": result["has_js"],
                          "user_id": user_id, "created": time.time(), "source": source, "sha256": sha256}
    return {"token": token, "identifier": identifier, "name": name, "version": version, "installed": installed,
            "installed_version": installed_version, "has_templates": result["has_templates"],
            "has_js": result["has_js"]}


def discard(token, user_id):
    with _lock:
        _purge_expired()
        entry = _staged.get(token)
        if entry and entry["user_id"] == user_id:
            _drop(_staged.pop(token))


def reload_themes(app):
    """Rescan all theme loaders and drop cached templates so new files are used without a restart."""
    manager = app.theme_manager
    manager._themes = {t.identifier: t for loader in manager.loaders for t in loader(app)
                       if manager.valid_app_id(t.application)}
    if app.jinja_env.cache is not None:
        app.jinja_env.cache.clear()
    themes._warned_missing.clear()


def _admin_name(user_id):
    try:
        from .cw_login import current_user
        if current_user.is_authenticated:
            return current_user.name
    except Exception:
        pass
    return user_id


def commit(token, user_id, confirm_version, trust_code):
    """Install a staged theme (replacing an installed one atomically) and reload the themes."""
    with _lock:
        _purge_expired()
        entry = _staged.get(token)
        if entry is None or entry["user_id"] != user_id:
            raise ThemeInstallError("bad_token", N_("The upload has expired. Please upload the theme again."))
        del _staged[token]
        try:
            return _commit_locked(entry, confirm_version, trust_code)
        finally:
            _drop(entry)


def _commit_locked(entry, confirm_version, trust_code):
    identifier = entry["identifier"]
    base = current_app.config["CW_USER_THEMES_DIR"]
    target = os.path.join(base, identifier)
    old_version = None
    if os.path.lexists(target):
        if confirm_version != (entry["version"] or ""):
            raise ThemeInstallError("needs_version_confirm", N_("Confirm the version to replace the installed theme."))
        old_version = _installed_version(target)
    if (entry["has_templates"] or entry["has_js"]) and not trust_code:
        raise ThemeInstallError("needs_trust", N_("This theme contains code. Confirm that you trust it."))
    if not themes_dir_writable():
        raise ThemeInstallError("read_only", N_("The themes folder is not writable."))
    if identifier in bundled_identifiers():
        raise ThemeInstallError("bundled", N_("A bundled theme already uses this identifier."))

    suffix = secrets.token_hex(4)
    incoming = os.path.join(base, ".{}.incoming-{}".format(identifier, suffix))
    old = os.path.join(base, ".{}.old-{}".format(identifier, suffix))
    had_old = False
    try:
        shutil.copytree(entry["path"], incoming)
        if os.path.exists(target):
            os.replace(target, old)
            had_old = True
        try:
            os.replace(incoming, target)
        except OSError:
            if had_old:
                try:
                    os.replace(old, target)
                except OSError:
                    log.error("Theme '%s' could not be put back; its files are in '%s'", identifier,
                              os.path.basename(old), exc_info=True)
            raise
    except OSError:
        log.error("Theme '%s' could not be installed", identifier, exc_info=True)
        shutil.rmtree(incoming, ignore_errors=True)
        raise ThemeInstallError("install_failed", N_("The theme could not be installed."))
    if had_old:
        shutil.rmtree(old, ignore_errors=True)
    try:
        reload_themes(current_app)
    except Exception:
        log.error("Themes could not be reloaded after installing '%s'; restart to load it", identifier,
                  exc_info=True)
    log.info("Theme '%s' installed by '%s': %s -> %s (%s, sha256 %s)", identifier, _admin_name(entry["user_id"]),
             old_version, entry["version"], entry["source"], entry["sha256"])
    return {"identifier": identifier, "name": entry["name"], "version": entry["version"]}


def _installed_version(path):
    try:
        with open(os.path.join(path, "info.json"), encoding="utf-8") as f:
            return display_version(json.load(f).get("version"))
    except (OSError, ValueError, AttributeError):
        return None
