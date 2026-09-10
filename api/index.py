"""Vercel serverless entry point.

Vercel rewrites every incoming URL to this file, which means the ASGI app can be
handed a path like ``/api/index.py`` instead of the URL the visitor actually
requested. FastAPI then has no matching route and answers 404 for everything.

The wrapper below restores the real path before the request reaches the app, and
falls back to Vercel's ``x-vercel-original-path`` / ``x-forwarded-uri`` headers
when they are present. Running locally, none of this triggers.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app as fastapi_app  # noqa: E402  (path set above first)

_ENTRY_PREFIXES = ("/api/index.py", "/api/index")


class RestoreOriginalPath:
    """Undo Vercel's rewrite so FastAPI sees the URL the visitor asked for."""

    def __init__(self, inner):
        self.inner = inner

    @staticmethod
    def _from_headers(scope) -> str | None:
        wanted = (b"x-vercel-original-path", b"x-forwarded-uri", b"x-original-uri")
        for key, value in scope.get("headers", []):
            if key.lower() in wanted:
                path = urlsplit(value.decode("latin-1")).path
                if path.startswith("/") and not path.startswith(_ENTRY_PREFIXES):
                    return path
        return None

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if path.startswith(_ENTRY_PREFIXES):
                scope = dict(scope)
                restored = self._from_headers(scope)
                if restored is None:
                    for prefix in _ENTRY_PREFIXES:
                        if path.startswith(prefix):
                            restored = path[len(prefix):] or "/"
                            break
                scope["path"] = restored or "/"
                scope["raw_path"] = scope["path"].encode("utf-8")
        await self.inner(scope, receive, send)


app = RestoreOriginalPath(fastapi_app)

__all__ = ["app"]
