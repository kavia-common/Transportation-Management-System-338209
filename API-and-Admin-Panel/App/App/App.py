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

# Ensure the app directory is in the path for imports
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv()

from App.Website.LandingPage import landing
from App.API.RestAPI import rest_api
from App.AdminPanel.AdminPanel import admin_panel
from App.DriverPortal.DriverPortal import driver_portal
from App.CustomerPortal.CustomerPortal import customer_portal

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

mysql.init_app(app)

# Register blueprints for each portal
app.register_blueprint(landing, url_prefix='/home')
app.register_blueprint(rest_api, url_prefix='/api')
app.register_blueprint(admin_panel, url_prefix='/admin')
app.register_blueprint(driver_portal, url_prefix='/driver')
app.register_blueprint(customer_portal, url_prefix='/customer')


# PUBLIC_INTERFACE
@app.route('/')
def hello():
    """Root route that redirects to the landing page."""
    return redirect("/home", code=301)


if __name__ == '__main__':
    app.run(debug=True)
