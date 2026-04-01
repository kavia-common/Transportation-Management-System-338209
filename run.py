"""
Root-level entry point for the Transportation Management System Flask server.

This file exists at the container workspace root so the Kavia preview system
can discover and launch the Flask application automatically.

It delegates to the actual application factory located in
API-and-Admin-Panel/App/App/App.py.

Usage:
    python run.py

The server binds to HOST:PORT from environment variables (defaults: 0.0.0.0:3001).
"""

import os
import sys

# Ensure the nested App package directory is on sys.path so that
# "from App.App import app" resolves correctly.
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
