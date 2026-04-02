"""
Shared Flask extensions for the TMS application.

This module provides the MySQL database connection instance
that is shared across all blueprints.
"""
from flask_mysqldb import MySQL

# Shared MySQL instance initialized in App.py
mysql = MySQL()
