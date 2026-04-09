"""
Flask MySQL extension compatibility layer.

The original project used Flask-MySQLdb/mysqlclient, which requires native build
dependencies that are often unavailable in preview/CI environments.

This module provides a small adapter that preserves the existing interface used
throughout the codebase:
  - mysql.init_app(app)
  - mysql.connection  (returns a DB-API compatible connection)
"""

from __future__ import annotations

from typing import Optional

from flask import current_app, g

try:
    # Prefer the original implementation if it exists in the environment.
    from flask_mysqldb import MySQL as _FlaskMySQL  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    _FlaskMySQL = None

try:
    import pymysql  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    pymysql = None


class _MySQLCompat:
    """Drop-in replacement providing mysql.init_app() and mysql.connection."""

    def __init__(self) -> None:
        self._impl = _FlaskMySQL() if _FlaskMySQL is not None else None
        self._initialized = False

    def init_app(self, app) -> None:
        """Initialize extension with a Flask app instance."""
        self._initialized = True
        if self._impl is not None:
            self._impl.init_app(app)
            return

        # PyMySQL fallback: register teardown to close per-appcontext connection.
        @app.teardown_appcontext
        def _close_connection(exc: Optional[BaseException]) -> None:
            conn = g.pop("_mysql_conn", None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    # Best-effort cleanup; do not mask original exceptions.
                    pass

    @property
    def connection(self):
        """Return an active DB connection (created lazily per app context)."""
        if self._impl is not None:
            return self._impl.connection

        if not self._initialized:
            raise RuntimeError("MySQL extension not initialized. Call mysql.init_app(app) first.")
        if pymysql is None:
            raise RuntimeError(
                "PyMySQL is not installed. Ensure requirements are installed (pip install -r requirements.txt)."
            )

        conn = getattr(g, "_mysql_conn", None)
        if conn is not None:
            return conn

        cfg = current_app.config
        host = cfg.get("MYSQL_HOST", "127.0.0.1")
        user = cfg.get("MYSQL_USER") or ""
        password = cfg.get("MYSQL_PASSWORD") or ""
        db = cfg.get("MYSQL_DB") or ""
        port = int(cfg.get("MYSQL_PORT", 3306) or 3306)

        # Important: do not crash app startup for missing env vars; callers handle failures.
        if not user or not db:
            raise RuntimeError(
                "MySQL is not configured. Set MYSQL_USER and MYSQL_DB (and MYSQL_PASSWORD) environment variables."
            )

        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db,
            port=port,
            charset="utf8mb4",
        )
        g._mysql_conn = conn
        return conn


mysql = _MySQLCompat()
