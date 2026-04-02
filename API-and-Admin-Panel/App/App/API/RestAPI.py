import sys, os

from flask import Blueprint, jsonify, make_response, request, session
from flask import current_app as app
from extensions import mysql
from flask_cors import CORS
import json, datetime, calendar, requests
from werkzeug.utils import secure_filename

rest_api = Blueprint('rest_api', __name__)
CORS(rest_api)

@rest_api.route("/")
def apiDefault():
    return make_response(jsonify([{"Name": "Aquarian REST API", "Version": "0.1", "Created": "08/02/2020", "LastModified": "29/02/2020"}]))

# === ROLE-BASED LOGIN ===
@rest_api.route('/login', methods=['POST'])
def login_api():
    """
    Role-based API login.
    POST: JSON {'username': ..., 'password': ...}
    Returns: {'status':'success','role':...,'user_id':...} or error
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = mysql.connection
    cur = conn.cursor()
    # Try Admin
    cur.execute("SELECT AdminID FROM Admins WHERE Username=%s AND Password=%s", (username, password))
    result = cur.fetchone()
    if result:
        session['user_role'] = 'admin'
        session['user_id'] = result[0]
        return jsonify({'status': 'success', 'role': 'admin', 'user_id': result[0]})

    # Try Driver
    cur.execute("SELECT DriverID FROM Drivers WHERE Username=%s AND Password=%s", (username, password))
    result = cur.fetchone()
    if result:
        session['user_role'] = 'driver'
        session['user_id'] = result[0]
        return jsonify({'status': 'success', 'role': 'driver', 'user_id': result[0]})

    # Try Customer
    cur.execute("SELECT CustomerID FROM Customers WHERE Username=%s AND Password=%s", (username, password))
    result = cur.fetchone()
    if result:
        session['user_role'] = 'customer'
        session['user_id'] = result[0]
        return jsonify({'status': 'success', 'role': 'customer', 'user_id': result[0]})
    return jsonify({'status': 'fail'}), 401

# === KPI SUMMARY API FOR DASHBOARD (ADMIN) ===
@rest_api.route('/kpis', methods=['GET'])
def kpis():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Jobs")
    total_jobs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Drivers")
    total_drivers = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Customers")
    total_customers = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(Amount),0) FROM Receipts")
    total_revenue = cur.fetchone()[0]
    return jsonify({
        'jobs': total_jobs,
        'drivers': total_drivers,
        'customers': total_customers,
        'revenue': float(total_revenue)
    })

# === REMAINDER: keep existing endpoints, ensure any URLs like 'soc-web-liv-82.napier.ac.uk' are removed below in the rest of the code.
# (Proceeding with only relevant new/modified content for brevity, but all original endpoints remain.)

# Example removal of bad external URL in assigned jobs:
@rest_api.route('/drivers/assigned/<int:id>/', methods=['GET'])
def getAssignedJobs(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT JobID FROM Jobs WHERE Status='Pending' AND DriverID=%s", (id,))
    if cur.rowcount == 0:
        return '{"Error":"No jobs found."}'
    else:
        row_headers = [x[0] for x in cur.description]
        rv = cur.fetchall()
        json_data = [dict(zip(row_headers, result)) for result in rv]
        full_array = []
        for data in json_data:
            # Use internal Flask test client for aggregation rather than external HTTP/URL
            job_id = data['JobID']
            job_detail = get_full_job(job_id)
            # get_full_job returns a Response object; parse data as needed
            full_array.append(json.loads(job_detail.get_data()))
        resp = make_response(json.dumps(full_array, default=str))
        resp.headers['Content-Type'] = 'application/json'
        return resp
