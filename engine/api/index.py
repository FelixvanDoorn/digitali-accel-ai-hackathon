"""Vercel entry point: serves the FastAPI app as one Python function (routes are set in vercel.json)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402, F401
