"""Vercel Serverless Function entry point for EventCraft AI.

This module initializes the FastAPI application using the production factory,
ensuring ./src is present in sys.path so that domain services and modules are
resolvable within the Vercel execution environment.
"""

import sys
from pathlib import Path

# Add project root and ./src to sys.path for serverless runtime
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eventcraft.config import AppSettings  # noqa: E402
from eventcraft.main import create_app  # noqa: E402

# Instantiate settings from environment variables (e.g., GEMINI_API_KEY, ALLOWED_ORIGINS)
settings = AppSettings()

# Expose 'app' as the module-level ASGI variable required by Vercel's Python runtime
from urllib.parse import parse_qsl, urlencode

_inner_app = create_app(settings)


async def app(scope, receive, send):
    """Restore the original request path that Vercel's rewrite replaced."""
    if scope["type"] == "http":
        params = parse_qsl(scope.get("query_string", b"").decode(), keep_blank_values=True)
        original = None
        rest = []
        for key, value in params:
            if key == "__path" and original is None:
                original = value
            else:
                rest.append((key, value))
        if original is not None:
            path = "/" + original.lstrip("/")
            scope = dict(scope)
            scope["path"] = path
            scope["raw_path"] = path.encode()
            scope["query_string"] = urlencode(rest).encode()
    await _inner_app(scope, receive, send)