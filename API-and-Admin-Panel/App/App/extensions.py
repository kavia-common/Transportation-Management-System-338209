"""
Shared Flask extensions for the TMS application.

This project originally used `flask_mysqldb`, which depends on `mysqlclient`
(a native extension requiring system MySQL/MariaDB development headers).
That dependency can fail to install in minimal CI/preview environments.

To keep `pip install -r requirements.txt` working everywhere, we provide a
small PyMySQL-based connector that preserves the `mysql.connection` access
pattern used throughout the codebase.

The rest of the app expects:
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute(...)
    conn.commit()

Environment variables (loaded in App.py via python-dotenv):
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

Note: PyMySQL is pure-Python and does not require system build tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pymysql


@dataclass
class _MySQLConfig:
    host: str
    user: str
    password: str
    db: str
    port: int = 3306
    charset: str = "utf8mb4"
    cursorclass: object = pymysql.cursors.Cursor


class _PyMySQLConnector:
    """Minimal connector providing a `.connection` property similar to flask_mysqldb."""

    def __init__(self) -> None:
        self._config: Optional[_MySQLConfig] = None
        self._connection: Optional[pymysql.connections.Connection] = None

    def init_app(self, app) -> None:
        """Bind configuration from a Flask app config dict."""
        self._config = _MySQLConfig(
            host=app.config.get("MYSQL_HOST", "localhost"),
            user=app.config.get("MYSQL_USER", ""),
            password=app.config.get("MYSQL_PASSWORD", ""),
            db=app.config.get("MYSQL_DB", ""),
            port=int(app.config.get("MYSQL_PORT", 3306)),
        )

    @property
    def connection(self) -> pymysql.connections.Connection:
        """Get a live connection, reconnecting if needed."""
        if self._config is None:
            raise RuntimeError("MySQL connector not initialized. Call mysql.init_app(app) first.")

        if self._connection is None or not getattr(self._connection, "open", False):
            # autocommit=False matches typical MySQLdb behavior used by the app (explicit conn.commit()).
            self._connection = pymysql.connect(
                host=self._config.host,
                user=self._config.user,
                password=self._config.password,
                database=self._config.db,
                port=self._config.port,
                charset=self._config.charset,
                cursorclass=self._config.cursorclass,
                autocommit=False,
            )
        return self._connection


# Shared MySQL connector initialized in App.py
mysql = _PyMySQLConnector()
