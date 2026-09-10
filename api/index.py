"""Vercel serverless entry point.

Everything of substance lives in the package. The path repair for the host's URL
rewrite is registered on the app itself in app/main.py, so it applies however the
platform chooses to discover the ASGI callable.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402,F401  (path must be set before this import)

__all__ = ["app"]
