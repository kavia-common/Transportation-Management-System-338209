"""
Main Flask application entry point for the Transportation Management System.

This module provides the application factory (create_app) and a module-level
``app`` instance for backward compatibility with WSGI and direct execution.
"""

import os
import sys

from flask import Flask, redirect

# Use relative imports within the App package so the module resolves
# correctly regardless of how the app is launched.
from .Website.LandingPage import landing
from .API.RestAPI import rest_api
from .AdminPanel.AdminPanel import admin_panel
from .extensions import mysql
from .config import load_config


# PUBLIC_INTERFACE
def create_app() -> Flask:
    """
    Application factory for the Transportation Management System Flask app.

    Contract:
      - Inputs: environment variables (see App.config.load_config)
      - Outputs: a fully configured Flask app with registered blueprints
      - Side effects:
          - Initializes MySQL extension binding to the app
          - Ensures upload directory exists (creates it if missing)
      - Errors:
          - Any unexpected runtime error will propagate to the caller (boundary),
            but configuration itself has defaults and should not raise.
    """
    cfg = load_config()

    application = Flask(__name__)
    application.secret_key = cfg.secret_key

    # MySQL configuration (env-based; defaults preserved for local/dev).
    application.config["MYSQL_HOST"] = cfg.mysql_host
    application.config["MYSQL_USER"] = cfg.mysql_user
    application.config["MYSQL_PASSWORD"] = cfg.mysql_password
    application.config["MYSQL_DB"] = cfg.mysql_db

    # Upload folder configuration (env-based; defaults preserved).
    application.config["UPLOAD_FOLDER"] = cfg.upload_folder

    # Ensure the upload directory exists to prevent runtime failures on save().
    os.makedirs(application.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize MySQL extension (lazy connection - does NOT connect yet).
    mysql.init_app(application)

    # Preserve existing blueprint structure and URL prefixes.
    application.register_blueprint(landing, url_prefix="/home")
    application.register_blueprint(rest_api, url_prefix="/api")
    application.register_blueprint(admin_panel, url_prefix="/admin")

    @application.route("/")
    def hello():
        """Redirect root to the landing page."""
        return redirect("/home", code=301)

    @application.route("/health")
    def health():
        """Health-check endpoint for the preview system."""
        return {"status": "ok"}, 200

    return application


# Keep backward compatibility: existing imports expect ``app`` at module level.
app = create_app()

if __name__ == "__main__":
    # Read port from environment (preview system sets PORT=3001).
    port = int(os.environ.get("PORT", 3001))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=False)
