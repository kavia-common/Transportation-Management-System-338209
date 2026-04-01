"""
Entry point for running the Transportation Management System Flask server.

Usage:
    python run.py

The server binds to HOST:PORT from environment variables (defaults: 0.0.0.0:3001).
"""

import os
import sys

# Ensure the App package directory is on the path so imports resolve.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from App.App import app  # noqa: E402


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3001))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Transportation Management System on {host}:{port}")
    app.run(host=host, port=port, debug=False)
