import sys
import os

[sys.path.append('/var/www/html/env/App/App')]

from flask import Flask, redirect
from App.Website.LandingPage import landing
from App.API.RestAPI import rest_api
from App.AdminPanel.AdminPanel import admin_panel

from extensions import mysql
from App.config import load_config


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

    mysql.init_app(application)

    # Preserve existing blueprint structure and URL prefixes.
    application.register_blueprint(landing, url_prefix="/home")
    application.register_blueprint(rest_api, url_prefix="/api")
    application.register_blueprint(admin_panel, url_prefix="/admin")

    @application.route("/")
    def hello():
        return redirect("/home", code=301)

    return application


# Keep backward compatibility: existing imports expect `app` at module level.
app = create_app()

if __name__ == "__main__":
    # Preserve current behavior when run directly.
    app.run()
