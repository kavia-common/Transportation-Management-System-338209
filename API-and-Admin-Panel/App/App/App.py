"""
Main Flask application entry point for the Transportation Management System.

This module initializes the Flask app, configures MySQL database connection
using environment variables, and registers all blueprints for:
- Landing page (public website)
- REST API
- Admin panel
- Driver portal
- Customer portal
"""
import sys
import os

from flask import Flask, redirect

# Ensure the package parent directory is in the path for imports.
# When App.py is run as a script, adding the package directory itself would
# shadow the App package with this module (App.py). The parent directory
# makes App/ a proper importable package.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PARENT = os.path.dirname(APP_DIR)
if APP_PARENT not in sys.path:
    sys.path.insert(0, APP_PARENT)

from dotenv import load_dotenv
load_dotenv()

from App.Website.LandingPage import landing
from App.API.RestAPI import rest_api
from App.AdminPanel.AdminPanel import admin_panel
from App.DriverPortal.DriverPortal import driver_portal
from App.CustomerPortal.CustomerPortal import customer_portal
from App.api_docs import init_api_docs

app = Flask(__name__)

# Secret key for session management - use env variable or fallback
app.secret_key = os.environ.get('SECRET_KEY', 'tms-secret-key-change-in-production')

from App.extensions import mysql

# Database configuration from environment variables
# NOTE: These environment variables need to be set in the .env file
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'aquarian')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'Aquarian123*')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'aquarian')
# Optional; used by the PyMySQL connector in App.extensions
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', '3306'))

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'AdminPanel/static/images/receipts')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initializing the Flask-MySQL extension should not hard-fail app startup.
# This allows non-DB routes (redirects/landing) to work even if MySQL is down.
try:
    mysql.init_app(app)
except Exception as e:
    # Keep behavior minimal: log and continue. Routes that require DB will still
    # fail at request-time when they attempt to use the connection.
    print(f"[WARN] MySQL init failed; continuing without DB connectivity: {e}")

# Register blueprints for each portal
app.register_blueprint(landing, url_prefix='/home')
app.register_blueprint(rest_api, url_prefix='/api')
app.register_blueprint(admin_panel, url_prefix='/admin')
app.register_blueprint(driver_portal, url_prefix='/driver')
app.register_blueprint(customer_portal, url_prefix='/customer')

# Register Swagger/OpenAPI documentation endpoints after blueprints.
init_api_docs(app)


# PUBLIC_INTERFACE
@app.route('/')
def hello():
    """Root route that redirects to the landing page."""
    return redirect("/home", code=301)


if __name__ == '__main__':
    # Respect platform-provided host/port so preview can bind correctly.
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "3001"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
