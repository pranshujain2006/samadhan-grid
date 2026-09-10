"""Vercel serverless entry point.

Vercel looks for an ASGI app called `app` in this module. Everything else lives
in the package exactly as it does when running locally with `python run.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402  (path must be set before this import)

__all__ = ["app"]
