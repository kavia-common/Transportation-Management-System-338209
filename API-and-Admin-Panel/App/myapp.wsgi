#!/usr/bin/python
"""WSGI entry point for the Transportation Management System."""
import sys
import os
import logging

logging.basicConfig(stream=sys.stderr)

# Add the App directory to the Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from App.App import app as application  # noqa: E402
