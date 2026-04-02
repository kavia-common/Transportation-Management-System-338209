"""
WSGI entrypoint for running the Flask app without Apache/mod_wsgi.

This is intended for environments where Apache build tooling (apxs) isn't
available. Use gunicorn, for example:

    gunicorn -w 2 -b 0.0.0.0:8000 wsgi:application

It can also be used by any WSGI server expecting an `application` callable.
"""

from App.App import app as application
