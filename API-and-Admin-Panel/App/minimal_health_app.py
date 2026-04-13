"""
Minimal Flask entrypoint for preview/CI readiness.

This file intentionally does NOT import the existing application package, because
the full app initializes blueprints and (best-effort) database schema at startup.
In environments where MySQL isn't available/configured, we still want the server
to boot and expose a simple health endpoint so the platform can mark the port as
ready.

Run:
  python minimal_health_app.py --host 0.0.0.0 --port 3001

Endpoints:
  GET /health   -> {"status":"ok"}
  GET /         -> simple text response (optional convenience)
"""

from __future__ import annotations

import argparse
import os

from flask import Flask, jsonify


def _truthy_env(name: str, default: bool = False) -> bool:
    """Parse a boolean-ish environment variable value."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")


# PUBLIC_INTERFACE
def create_minimal_app() -> Flask:
    """Create a minimal Flask app that does not require MySQL to start.

    Returns:
        Flask: A Flask application with only health endpoints.
    """
    app = Flask(__name__)

    @app.get("/")
    def root() -> str:
        """Optional root endpoint for quick manual verification."""
        return "ok"

    @app.get("/health")
    def health() -> tuple[object, int]:
        """Health check endpoint for readiness/liveness probes."""
        return jsonify({"status": "ok"}), 200

    @app.get("/healthz")
    def healthz() -> tuple[object, int]:
        """Health check endpoint alias used by some platforms/manifests."""
        return jsonify({"status": "ok"}), 200

    return app


app = create_minimal_app()

# Many WSGI/preview runners look for a module-level variable named `application`.
# Export it as an alias to ensure consistent discovery.
application = app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minimal Flask health server (no DB required).")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "3001")))
    parser.add_argument("--debug", action="store_true", default=_truthy_env("FLASK_DEBUG", False))
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
