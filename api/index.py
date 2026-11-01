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
app = create_app(settings)
