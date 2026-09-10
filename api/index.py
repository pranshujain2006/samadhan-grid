"""Vercel serverless entry point.

Vercel rewrites every incoming URL to this file. That rewrite REPLACES the path,
so the ASGI app would otherwise be handed ``/api/index`` for every request and
FastAPI would answer 404 for the whole site.

``vercel.json`` therefore smuggles the real path through as a query parameter
(``__vpath``), which is deterministic and does not rely on any undocumented
header. This wrapper reads it back, restores the path, and strips the parameter
so the application never sees it. Running locally none of this triggers.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app as fastapi_app  # noqa: E402  (path set above first)

_ENTRY_PREFIXES = ("/api/index.py", "/api/index")
_PATH_PARAM = "__vpath"
_HEADER_KEYS = (b"x-vercel-original-path", b"x-forwarded-uri", b"x-original-uri")


def _clean(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return path or "/"


class RestoreOriginalPath:
    """Undo Vercel's rewrite so FastAPI sees the URL the visitor asked for."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.inner(scope, receive, send)
            return

        path = scope.get("path", "")
        query = scope.get("query_string", b"").decode("latin-1")
        params = parse_qsl(query, keep_blank_values=True)

        restored = None

        # 1. the path we passed through the rewrite ourselves
        for key, value in params:
            if key == _PATH_PARAM:
                restored = _clean(value)
                break

        # 2. a header, if this platform provides one
        if restored is None and path.startswith(_ENTRY_PREFIXES):
            for key, value in scope.get("headers", []):
                if key.lower() in _HEADER_KEYS:
                    candidate = urlsplit(value.decode("latin-1")).path
                    if candidate.startswith("/") and not candidate.startswith(_ENTRY_PREFIXES):
                        restored = candidate
                        break

        # 3. the entry prefix with the real path appended after it
        if restored is None and path.startswith(_ENTRY_PREFIXES):
            for prefix in _ENTRY_PREFIXES:
                if path.startswith(prefix):
                    restored = _clean(path[len(prefix):] or "/")
                    break

        if restored is not None:
            remaining = [(k, v) for k, v in params if k != _PATH_PARAM]
            scope = dict(scope)
            scope["path"] = restored
            scope["raw_path"] = restored.encode("utf-8")
            scope["query_string"] = urlencode(remaining).encode("latin-1")

        await self.inner(scope, receive, send)


app = RestoreOriginalPath(fastapi_app)

__all__ = ["app"]
