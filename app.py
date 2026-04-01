"""
Alternative root-level entry point for the Transportation Management System.

Some deployment/preview systems look for ``app.py`` rather than ``run.py``.
This module re-exports the Flask ``app`` instance so that both conventions work.

The canonical application factory lives in API-and-Admin-Panel/App/App/App.py.
"""

import os
import sys

# Ensure the nested App package directory is on sys.path.
_app_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "API-and-Admin-Panel",
    "App",
)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from App.App import app  # noqa: E402


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3001))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Transportation Management System on {host}:{port}")
    app.run(host=host, port=port, debug=False)
