# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
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

"""FastAPI app mounted under /api.

This module is intentionally minimal: it exposes Swagger UI at /api and
implements only a single GET endpoint for now.

The FastAPI ASGI app is mounted into the existing Flask WSGI app via a
small ASGI->WSGI adapter (see `cps/asgi_wsgi.py`).
"""

from __future__ import annotations

import os
import traceback

from fastapi import FastAPI
from fastapi import Depends
from fastapi import Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def create_api_app() -> FastAPI:
    api = FastAPI(
        title="Calibre-Web API",
        description=(
            "API for Calibre-Web.\n\n"
            "Notes:\n"
            "- Swagger UI is available at `/api/` (mounted under the Flask app).\n"
            "- Most endpoints require `Authorization: Bearer <API_TOKEN>` when `API_TOKEN` is set.\n"
            "- `GET /health` is public and intended for container/orchestrator health checks.\n"
            "- Rate limiting is applied per IP via `API_RATE_LIMIT_PER_MINUTE` (in-memory).\n"
            "\n"
            "This API is intentionally read-only for now."
        ),
        version="0.1.0",
        docs_url="/",  # /api -> Swagger UI
        redoc_url=None,
        openapi_url="/openapi.json",
    )

    # --- Auth (API_TOKEN / Bearer) ---
    # If API_TOKEN is set, every endpoint (except Swagger/OpenAPI) requires:
    #   Authorization: Bearer <API_TOKEN>
    _api_token = os.environ.get("API_TOKEN")
    _bearer = HTTPBearer(auto_error=False)

    def require_api_token(
        creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> None:
        if not _api_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        if not creds or creds.scheme.lower() != "bearer" or creds.credentials != _api_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    def _calibre_session():
        # Lazy import to avoid side-effects at import time
        # Calibre-Web's CalibreDB.session relies on Flask's app/request context (flask.g).
        # FastAPI runs outside that context, so we create one for the duration of the call.
        from . import app as flask_app
        from . import calibre_db
        ctx = flask_app.app_context()
        ctx.push()
        try:
            return calibre_db.session
        finally:
            # Session will be closed by CalibreDB teardown when the context pops.
            ctx.pop()

    # --- Simple per-IP rate limiting (requests per minute) ---
    # Configure with API_RATE_LIMIT_PER_MINUTE (default: 60).
    # This is intentionally lightweight (in-memory) and applies only to /api.
    _rpm = int(os.environ.get("API_RATE_LIMIT_PER_MINUTE", "60"))
    _rate_state: dict[str, tuple[int, int]] = {}  # ip -> (window_start_epoch_minute, count)

    class _RateLimitMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Ignore docs/openapi if you want them always accessible; keep them limited too by default.
            if _rpm > 0:
                ip = request.headers.get("x-forwarded-for")
                if ip:
                    ip = ip.split(",")[0].strip()
                else:
                    ip = request.client.host if request.client else "unknown"

                now_minute = int(__import__("time").time() // 60)
                window_start, count = _rate_state.get(ip, (now_minute, 0))
                if window_start != now_minute:
                    window_start, count = now_minute, 0
                count += 1
                _rate_state[ip] = (window_start, count)
                if count > _rpm:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too Many Requests",
                    )

            return await call_next(request)

    class _SwaggerCSPMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)

            # Only relax CSP for the Swagger UI and its assets.
            # The default FastAPI Swagger UI uses CDN assets (jsdelivr).
            if request.url.path in ("/", "/openapi.json"):
                csp = (
                    "style-src-elem 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
                    "script-src 'self' https://unpkg.com https://cdn.jsdelivr.net; "
                    "img-src 'self' data: https://cdn.jsdelivr.net https://unpkg.com; "
                    "font-src 'self' data: https://cdn.jsdelivr.net https://unpkg.com"
                )

                existing = response.headers.get("Content-Security-Policy")
                if existing:
                    # Don't try to merge directives; just append ours.
                    response.headers["Content-Security-Policy"] = existing + "; " + csp
                else:
                    response.headers["Content-Security-Policy"] = csp

            return response

    api.add_middleware(_SwaggerCSPMiddleware)
    api.add_middleware(_RateLimitMiddleware)

    @api.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        # Print full traceback to stdout/stderr to help debugging in Docker logs.
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error", "traceback": traceback.format_exc()},
        )

    @api.get(
        "/health",
        tags=["system"],
        summary="Health check",
        description=(
            "Checks connectivity to both SQLite databases used by Calibre-Web:\n"
            "- `calibre_db`: the Calibre library database (metadata.db)\n"
            "- `app_db`: the Calibre-Web settings database (app.db)\n\n"
            "Returns only `status` and `message`."
        ),
    )
    def health() -> dict:
        """Health check.

        Returns only:
          - status: ok|error
          - message: human readable

        If any DB connectivity check fails, return status=error and identify which DB failed.
        """
        from sqlalchemy import text
        from . import app as flask_app
        from . import ub

        # Check Calibre library DB (metadata.db)
        try:
            session = _calibre_session()
            session.execute(text("SELECT 1"))
        except Exception as ex:
            return {"status": "error", "message": f"calibre_db connection failed: {ex}"}

        # Check Calibre-Web settings DB (app.db)
        try:
            with flask_app.app_context():
                ub.session.execute(text("SELECT 1"))
        except Exception as ex:
            return {"status": "error", "message": f"app_db connection failed: {ex}"}

        return {"status": "ok", "message": "all databases reachable"}

    @api.get(
        "/books",
        tags=["library"],
        summary="List books",
        description=(
            "Lists books from the Calibre library database.\n\n"
            "This endpoint intentionally returns a small payload and avoids heavy joins. "
            "Use `page`/`per_page` for pagination and `q` to search by title substring."
        ),
        dependencies=[Depends(require_api_token)],
    )
    def list_books(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional title search (substring, case-insensitive)"),
    ) -> dict:
        """List books (basic fields).

        This intentionally returns a small payload and avoids heavy joins.
        """
        from sqlalchemy import func
        from . import db

        session = _calibre_session()
        query = session.query(db.Books)
        if q:
            query = query.filter(func.lower(db.Books.title).contains(q.lower()))

        total = query.count()
        items = (
            query.order_by(db.Books.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": [
                {
                    "id": b.id,
                    "title": b.title,
                    "sort": b.sort,
                    "author_sort": b.author_sort,
                    "timestamp": b.timestamp.isoformat() if b.timestamp else None,
                    "pubdate": b.pubdate.isoformat() if b.pubdate else None,
                    "last_modified": b.last_modified.isoformat() if b.last_modified else None,
                    "path": b.path,
                    "has_cover": bool(b.has_cover),
                    "uuid": b.uuid,
                    "isbn": b.isbn,
                }
                for b in items
            ],
        }

    @api.get(
        "/shelfs",
        tags=["library"],
        summary="List shelves",
        description=(
            "Lists Calibre-Web shelves (stored in the settings database, not in the Calibre library DB).\n\n"
            "Use `public_only=true` to return only public shelves, and `q` to search by shelf name."
        ),
        dependencies=[Depends(require_api_token)],
    )
    def list_shelfs(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional shelf name search (substring, case-insensitive)"),
        public_only: bool = Query(False, description="Only include public shelves"),
    ) -> dict:
        """List shelves (Calibre-Web settings DB)."""
        from sqlalchemy import func
        from . import ub

        # ub.session relies on Flask app context.
        from . import app as flask_app

        with flask_app.app_context():
            query = ub.session.query(ub.Shelf)
            if public_only:
                query = query.filter(ub.Shelf.is_public == 1)
            if q:
                query = query.filter(func.lower(ub.Shelf.name).contains(q.lower()))

            total = query.count()
            rows = (
                query.order_by(ub.Shelf.id.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            items = [
                {
                    "id": s.id,
                    "uuid": s.uuid,
                    "name": s.name,
                    "is_public": bool(s.is_public),
                    "user_id": s.user_id,
                    "kobo_sync": bool(getattr(s, "kobo_sync", False)),
                    "created": s.created.isoformat() if getattr(s, "created", None) else None,
                    "last_modified": s.last_modified.isoformat() if getattr(s, "last_modified", None) else None,
                }
                for s in rows
            ]

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": items,
        }

    @api.get(
        "/series",
        tags=["library"],
        summary="List series",
        description="Lists series from the Calibre library database.",
        dependencies=[Depends(require_api_token)],
    )
    def list_series(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional series name search (substring, case-insensitive)"),
    ) -> dict:
        from sqlalchemy import func
        from . import db

        session = _calibre_session()
        query = session.query(db.Series)
        if q:
            query = query.filter(func.lower(db.Series.name).contains(q.lower()))

        total = query.count()
        rows = (
            query.order_by(db.Series.sort.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": [
                {
                    "id": s.id,
                    "name": s.name,
                    "sort": s.sort,
                }
                for s in rows
            ],
        }

    @api.get(
        "/authors",
        tags=["library"],
        summary="List authors",
        description="Lists authors from the Calibre library database.",
        dependencies=[Depends(require_api_token)],
    )
    def list_authors(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional author name search (substring, case-insensitive)"),
    ) -> dict:
        from sqlalchemy import func
        from . import db

        session = _calibre_session()
        query = session.query(db.Authors)
        if q:
            query = query.filter(func.lower(db.Authors.name).contains(q.lower()))

        total = query.count()
        rows = (
            query.order_by(db.Authors.sort.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": [
                {
                    "id": a.id,
                    "name": a.name,
                    "sort": a.sort,
                    "link": getattr(a, "link", None),
                }
                for a in rows
            ],
        }

    @api.get(
        "/publishers",
        tags=["library"],
        summary="List publishers",
        description="Lists publishers from the Calibre library database.",
        dependencies=[Depends(require_api_token)],
    )
    def list_publishers(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional publisher name search (substring, case-insensitive)"),
    ) -> dict:
        from sqlalchemy import func
        from . import db

        session = _calibre_session()
        query = session.query(db.Publishers)
        if q:
            query = query.filter(func.lower(db.Publishers.name).contains(q.lower()))

        total = query.count()
        rows = (
            query.order_by(db.Publishers.name.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "sort": getattr(p, "sort", None),
                }
                for p in rows
            ],
        }

    @api.get(
        "/languages",
        tags=["library"],
        summary="List languages",
        description="Lists languages (by `lang_code`) from the Calibre library database.",
        dependencies=[Depends(require_api_token)],
    )
    def list_languages(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional language code search (substring, case-insensitive)"),
    ) -> dict:
        from sqlalchemy import func
        from . import db

        session = _calibre_session()
        query = session.query(db.Languages)
        if q:
            query = query.filter(func.lower(db.Languages.lang_code).contains(q.lower()))

        total = query.count()
        rows = (
            query.order_by(db.Languages.lang_code.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": [
                {
                    "id": l.id,
                    "lang_code": l.lang_code,
                }
                for l in rows
            ],
        }

    @api.get(
        "/formats",
        tags=["library"],
        summary="List file formats",
        description=(
            "Lists distinct file formats present in the library.\n\n"
            "Derived from the Calibre `data` table (`db.Data.format`)."
        ),
        dependencies=[Depends(require_api_token)],
    )
    def list_file_formats(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional format search (e.g. epub, pdf)"),
    ) -> dict:
        """List distinct file formats present in the library.

        This is derived from the `data` table (db.Data.format).
        """
        from sqlalchemy import func
        from . import db

        session = _calibre_session()
        query = session.query(func.lower(db.Data.format).label("format"))
        if q:
            query = query.filter(func.lower(db.Data.format).contains(q.lower()))
        query = query.group_by(func.lower(db.Data.format))

        total = query.count()
        rows = (
            query.order_by(func.lower(db.Data.format).asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": [{"format": r.format} for r in rows],
        }

    @api.get(
        "/categories",
        tags=["library"],
        summary="List categories",
        description=(
            "Lists categories as Calibre tags (table `tags`).\n\n"
            "In the Calibre-Web UI these are shown as 'Categories'."
        ),
        dependencies=[Depends(require_api_token)],
    )
    def list_categories(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional category (tag) name search"),
    ) -> dict:
        """List categories (Calibre tags)."""
        from sqlalchemy import func
        from . import db

        session = _calibre_session()
        query = session.query(db.Tags)
        if q:
            query = query.filter(func.lower(db.Tags.name).contains(q.lower()))

        total = query.count()
        rows = (
            query.order_by(db.Tags.name.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": [
                {
                    "id": t.id,
                    "name": t.name,
                }
                for t in rows
            ],
        }

    @api.get(
        "/users",
        tags=["system"],
        summary="List users",
        description=(
            "Lists Calibre-Web users from the settings database.\n\n"
            "Security: this endpoint never returns password hashes."
        ),
        dependencies=[Depends(require_api_token)],
    )
    def list_users(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(25, ge=1, le=200, description="Items per page (max 200)"),
        q: str | None = Query(None, description="Optional username search (substring, case-insensitive)"),
    ) -> dict:
        """List Calibre-Web users (settings DB).

        Note: This intentionally does NOT return password hashes.
        """
        from sqlalchemy import func
        from . import ub

        from . import app as flask_app

        with flask_app.app_context():
            query = ub.session.query(ub.User)
            if q:
                query = query.filter(func.lower(ub.User.name).contains(q.lower()))

            total = query.count()
            rows = (
                query.order_by(ub.User.id.asc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            items = [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "role": int(u.role) if u.role is not None else None,
                    "locale": getattr(u, "locale", None),
                    "default_language": getattr(u, "default_language", None),
                    "sidebar_view": getattr(u, "sidebar_view", None),
                    "kindle_mail": getattr(u, "kindle_mail", None),
                    "roles": {
                        "admin": bool(u.role_admin()),
                        "download": bool(u.role_download()),
                        "upload": bool(u.role_upload()),
                        "edit": bool(u.role_edit()),
                        "passwd": bool(u.role_passwd()),
                        "anonymous": bool(u.role_anonymous()),
                        "edit_shelfs": bool(u.role_edit_shelfs()),
                        "delete_books": bool(u.role_delete_books()),
                        "viewer": bool(u.role_viewer()),
                    },
                }
                for u in rows
            ]

        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": items,
        }

    @api.get(
        "/tasks",
        tags=["system"],
        summary="List background tasks",
        description=(
            "Lists background tasks managed by Calibre-Web's in-process worker thread.\n\n"
            "Note: tasks are stored in-memory per process. If you run multiple processes, each one has its own list."
        ),
        dependencies=[Depends(require_api_token)],
    )
    def list_tasks() -> dict:
        """List background worker tasks.

        This mirrors what the Calibre-Web UI shows on the tasks page, but as JSON.
        """
        from .services.worker import WorkerThread

        # WorkerThread is a singleton; tasks are held in-memory.
        wt = WorkerThread.get_instance()
        tasks = wt.tasks

        def _stat_name(stat: int) -> str:
            from .services import worker as w

            return {
                w.STAT_WAITING: "waiting",
                w.STAT_STARTED: "started",
                w.STAT_FINISH_SUCCESS: "success",
                w.STAT_FAIL: "fail",
                w.STAT_ENDED: "ended",
                w.STAT_CANCELLED: "cancelled",
            }.get(stat, str(stat))

        items = []
        for queued in tasks:
            t = queued.task
            items.append(
                {
                    "num": queued.num,
                    "user": queued.user,
                    "added": queued.added.isoformat() if getattr(queued, "added", None) else None,
                    "hidden": bool(getattr(queued, "hidden", False)),
                    "id": str(getattr(t, "id", "")),
                    "name": str(t),
                    "message": getattr(t, "message", None),
                    "stat": int(getattr(t, "stat", -1)),
                    "stat_name": _stat_name(int(getattr(t, "stat", -1))),
                    "progress": float(getattr(t, "progress", 0.0)),
                    "error": getattr(t, "error", None),
                    "start_time": t.start_time.isoformat() if getattr(t, "start_time", None) else None,
                    "end_time": t.end_time.isoformat() if getattr(t, "end_time", None) else None,
                    "runtime_seconds": getattr(t, "runtime", None).total_seconds()
                    if getattr(t, "start_time", None)
                    else None,
                    "is_cancellable": bool(getattr(t, "is_cancellable", False)),
                    "scheduled": bool(getattr(t, "scheduled", False)),
                    "self_cleanup": bool(getattr(t, "self_cleanup", False)),
                }
            )

        return {"total": len(items), "items": items}

    return api

api_app = create_api_app()
