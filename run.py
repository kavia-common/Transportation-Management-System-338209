"""
Repo-root entrypoint for the Transportation Management System Flask app.

This module ensures imports work when the application is launched from the
repository root without requiring PYTHONPATH tweaks.

Usage:
  - Development: python run.py
  - WSGI servers: gunicorn -w 2 -b 0.0.0.0:8000 run:application
"""

from __future__ import annotations

import os
import sys


def _ensure_app_on_path() -> None:
    """Ensure the Flask app package directory is importable from repo root."""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    app_parent = os.path.join(repo_root, "API-and-Admin-Panel", "App")
    if app_parent not in sys.path:
        sys.path.insert(0, app_parent)


_ensure_app_on_path()

# Import after sys.path is corrected.
from App.App import app as application  # noqa: E402


if __name__ == "__main__":
    # Local dev convenience: `python run.py`
    application.run(debug=True)
