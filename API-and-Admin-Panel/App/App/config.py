"""
Centralized environment-based configuration for the Flask app.

This module intentionally keeps *sensible local defaults* to preserve existing
preview/start behavior, while allowing production deployments to override
settings via environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """
    Typed configuration values for the Flask application.

    Contract:
      - Inputs: environment variables (optional)
      - Outputs: concrete config values suitable for app.config
      - Side effects: none
      - Errors: none (falls back to defaults)
    """

    secret_key: str
    mysql_host: str
    mysql_user: str
    mysql_password: str
    mysql_db: str
    upload_folder: str


def _default_upload_folder() -> str:
    """
    Compute the default upload folder in a way that is stable regardless of CWD.

    Default matches historical behavior:
      App/App/AdminPanel/static/images/receipts (relative to this file).
    """
    app_pkg_root = Path(__file__).resolve().parent  # .../App/App
    return str(app_pkg_root / "AdminPanel" / "static" / "images" / "receipts")


# PUBLIC_INTERFACE
def load_config() -> AppConfig:
    """
    Load application configuration from environment variables with safe defaults.

    Environment variables supported:
      - FLASK_SECRET_KEY
      - MYSQL_HOST
      - MYSQL_USER
      - MYSQL_PASSWORD
      - MYSQL_DB
      - UPLOAD_FOLDER

    Returns:
      AppConfig: normalized configuration object.

    Notes:
      - Defaults are intentionally set to preserve current local behavior.
      - In production, ALWAYS set FLASK_SECRET_KEY and DB credentials via env.
    """
    return AppConfig(
        secret_key=os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me"),
        mysql_host=os.getenv("MYSQL_HOST", "localhost"),
        mysql_user=os.getenv("MYSQL_USER", "aquarian"),
        mysql_password=os.getenv("MYSQL_PASSWORD", "Aquarian123*"),
        mysql_db=os.getenv("MYSQL_DB", "aquarian"),
        upload_folder=os.getenv("UPLOAD_FOLDER", _default_upload_folder()),
    )
