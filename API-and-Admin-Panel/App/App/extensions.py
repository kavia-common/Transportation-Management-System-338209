"""
Database extension module providing a MySQL interface for the Flask app.

Uses PyMySQL (pure-Python MySQL driver) instead of flask_mysqldb to avoid
C library dependencies (mysqlclient/libmysqlclient-dev).

Provides a drop-in replacement that exposes the same ``mysql.connection``
interface used throughout the codebase.
"""

from __future__ import annotations

import logging

import pymysql
import pymysql.cursors

logger = logging.getLogger(__name__)


class MySQL:
    """
    Lightweight MySQL extension for Flask using PyMySQL.

    Mimics the flask_mysqldb.MySQL interface so existing code that uses
    ``mysql.connection.cursor()`` continues to work unchanged.

    If the database is unreachable the app will still *start*; connection
    errors surface only when a route actually tries to use the database.
    """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    # PUBLIC_INTERFACE
    def init_app(self, app):
        """
        Bind this extension to the Flask application.

        Reads MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB from
        ``app.config`` (set by config.py / load_config).
        """
        self.app = app
        # Register teardown to close per-request connections.
        app.teardown_appcontext(self._teardown)

    def _teardown(self, exception=None):
        """Close the per-request MySQL connection if one was opened."""
        from flask import g
        conn = g.pop("_mysql_conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    @property
    def connection(self):
        """
        Return a PyMySQL connection, creating one per-request if needed.

        The connection is cached on Flask's ``g`` object so it is reused
        within the same request and closed at teardown.
        """
        from flask import g, has_app_context

        if not has_app_context():
            raise RuntimeError("Working outside of application context.")

        if not hasattr(g, "_mysql_conn") or g._mysql_conn is None:
            app = self.app
            try:
                g._mysql_conn = pymysql.connect(
                    host=app.config.get("MYSQL_HOST", "localhost"),
                    user=app.config.get("MYSQL_USER", "root"),
                    password=app.config.get("MYSQL_PASSWORD", ""),
                    database=app.config.get("MYSQL_DB", ""),
                    port=int(app.config.get("MYSQL_PORT", 3306)),
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.Cursor,
                    autocommit=False,
                )
            except Exception as exc:
                logger.error("MySQL connection failed: %s", exc)
                raise

        return g._mysql_conn


# Module-level singleton used across blueprints.
mysql = MySQL()
