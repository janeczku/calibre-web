# Calibre-Web (cps) AI coding guide

## Big picture architecture
- Entry point is `cps.py` which calls `cps.main.main()`; app setup lives in `cps/__init__.py:create_app()`.
- `create_app()` wires configuration (`cps/config_sql.py`), initializes user DB (`cps/ub.py`), and the Calibre library DB via `db.CalibreDB` (`cps/db.py`). It also initializes updater, scheduler, CSRF, and rate limiter.
- The web API/UI is organized as Flask blueprints registered in `cps/main.py` (e.g., `web`, `basic`, `opds`, `admin`, `search`, `gdrive`, `editbooks`). Large UI/route logic lives in `cps/web.py`.
- Server runtime uses Gevent if available, otherwise Tornado (`cps/server.py`). It supports systemd socket activation and Unix sockets (`LISTEN_FDS`, `CALIBRE_UNIX_SOCKET`).

## Key workflows
- Run locally via the console script `cps` (defined in `pyproject.toml`) or `python cps.py`.
- Dependencies are in `requirements.txt`; optional features (gdrive/ldap/oauth/etc.) are listed in `optional-requirements.txt` and `pyproject.toml` optional-dependencies.

## Project-specific conventions/patterns
- Central app globals: `cps/__init__.py` defines `app`, `config`, `cli_param`, `calibre_db`, `limiter`, `csrf`, `web_server` — most modules import from there instead of instantiating their own Flask app.
- Rate limiting is configured in `cps/__init__.py` and applied per-blueprint in `cps/main.py` (e.g., OPDS and Kobo limits).
- Security headers are enforced in `cps/web.py` via `@app.after_request` and depend on runtime config (e.g., trusted hosts, Google Drive).

## Integration points
- Calibre DB path and settings come from the admin-configured config SQL DB (`cps/config_sql.py` + `cps/ub.py`).
- Optional services are toggled by availability: LDAP, OAuth, Goodreads, Google Drive (`cps/services/*`, `optional-requirements.txt`).
- External binaries for conversions (Calibre `ebook-convert`) and other integrations are configured at runtime, not hardcoded.

## Where to look first
- App bootstrapping: `cps/__init__.py`, `cps/main.py`, `cps/server.py`.
- Main web/UI logic: `cps/web.py`.
- Dependency lists and packaging: `requirements.txt`, `optional-requirements.txt`, `pyproject.toml`.
