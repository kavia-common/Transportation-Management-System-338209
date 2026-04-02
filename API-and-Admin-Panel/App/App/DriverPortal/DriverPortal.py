"""
Driver Portal Blueprint for the Transportation Management System.

Provides driver-facing views including:
- Driver login/logout
- Dashboard with assigned jobs overview
- Job detail view and status updates

Flow name: DriverPortalFlow
Entrypoint: driver_portal blueprint registered in App.py
Contract:
  - Inputs: HTTP requests with session-based driver authentication
  - Outputs: Rendered HTML templates or redirects
  - Errors: Redirects to login on missing session; flash messages on failures
  - Side effects: MySQL reads/writes for job status updates, session management
"""

import logging
from flask import (
    Blueprint, render_template, request, redirect,
    session, make_response, jsonify, url_for
)
from App.extensions import mysql

logger = logging.getLogger(__name__)

driver_portal = Blueprint(
    'driver_portal', __name__,
    template_folder='templates',
    static_folder='static'
)


def _require_driver_session():
    """Check if driver is logged in via session.

    Returns:
        dict or None: Driver session info if logged in, None otherwise.
    """
    if 'driver_id' in session and 'driver_name' in session:
        return {
            'driver_id': session['driver_id'],
            'driver_name': session['driver_name'],
            'vehicle_id': session.get('vehicle_id')
        }
    return None


# PUBLIC_INTERFACE
@driver_portal.route("/", methods=['GET', 'POST'])
def login_page():
    """Driver login page.

    GET: Renders the login form. If already logged in, redirects to dashboard.
    POST: Authenticates driver credentials against the Drivers table.

    Returns:
        Rendered login template or redirect to dashboard.
    """
    if request.method == 'GET':
        driver = _require_driver_session()
        if driver:
            return redirect(url_for('driver_portal.dashboard'))
        return render_template('driver_login.html', error_message='')

    # POST: authenticate
    username = request.form.get('username', '')
    password = request.form.get('password', '')

    try:
        conn = mysql.connection
        cur = conn.cursor()
        cur.execute(
            "SELECT DriverID, FirstName, VehicleID, Password FROM Drivers WHERE Username=%s",
            (username,)
        )
        if cur.rowcount == 0:
            logger.info("Driver login failed: unknown username=%s", username)
            return render_template('driver_login.html', error_message='Invalid username or password')

        row = cur.fetchone()
        driver_id, first_name, vehicle_id, stored_password = row

        if password != stored_password:
            logger.info("Driver login failed: wrong password for username=%s", username)
            return render_template('driver_login.html', error_message='Invalid username or password')

        # Update last connected timestamp
        cur.execute("UPDATE Drivers SET LastConnected=NOW() WHERE DriverID=%s", (driver_id,))
        conn.commit()

        # Store session
        session['driver_id'] = driver_id
        session['driver_name'] = first_name
        session['vehicle_id'] = vehicle_id
        logger.info("Driver login successful: driver_id=%s, name=%s", driver_id, first_name)

        return redirect(url_for('driver_portal.dashboard'))

    except Exception as e:
        logger.error("Driver login error: %s", str(e))
        return render_template('driver_login.html', error_message='An error occurred. Please try again.')


# PUBLIC_INTERFACE
@driver_portal.route("/dashboard")
def dashboard():
    """Driver dashboard showing assigned pending jobs and summary KPIs.

    Requires active driver session. Shows count of pending jobs,
    delivered jobs today, and a list of assigned pending jobs.

    Returns:
        Rendered dashboard template or redirect to login.
    """
    driver = _require_driver_session()
    if not driver:
        return redirect(url_for('driver_portal.login_page'))

    driver_id = driver['driver_id']
    try:
        cur = mysql.connection.cursor()

        # Count pending jobs for this driver
        cur.execute(
            "SELECT COUNT(*) FROM Jobs WHERE DriverID=%s AND Status='Pending'",
            (driver_id,)
        )
        pending_count = cur.fetchone()[0] or 0

        # Count delivered jobs today for this driver
        cur.execute(
            "SELECT COUNT(*) FROM Jobs WHERE DriverID=%s AND Status='Delivered' AND DATE(DateDelivered)=DATE(NOW())",
            (driver_id,)
        )
        delivered_today = cur.fetchone()[0] or 0

        # Get pending jobs list
        cur.execute(
            "SELECT JobID, TrackingID, Status, ParcelType, ParcelSize, DateDue "
            "FROM Jobs WHERE DriverID=%s AND Status='Pending' ORDER BY DateDue ASC",
            (driver_id,)
        )
        columns = [desc[0] for desc in cur.description]
        pending_jobs = [dict(zip(columns, row)) for row in cur.fetchall()]

        return render_template(
            'driver_dashboard.html',
            driver_name=driver['driver_name'],
            pending_count=pending_count,
            delivered_today=delivered_today,
            pending_jobs=pending_jobs
        )
    except Exception as e:
        logger.error("Driver dashboard error: driver_id=%s, error=%s", driver_id, str(e))
        return render_template(
            'driver_dashboard.html',
            driver_name=driver['driver_name'],
            pending_count=0,
            delivered_today=0,
            pending_jobs=[]
        )


# PUBLIC_INTERFACE
@driver_portal.route("/job/<int:job_id>")
def job_detail(job_id):
    """View details of a specific job assigned to the current driver.

    Args:
        job_id: The job ID to view.

    Returns:
        Rendered job detail template or redirect to login/dashboard.
    """
    driver = _require_driver_session()
    if not driver:
        return redirect(url_for('driver_portal.login_page'))

    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT j.*, c.FirstName AS CustFirstName, c.LastName AS CustLastName "
            "FROM Jobs j LEFT JOIN Customers c ON j.CustomerID=c.CustomerID "
            "WHERE j.JobID=%s AND j.DriverID=%s",
            (job_id, driver['driver_id'])
        )
        if cur.rowcount == 0:
            return redirect(url_for('driver_portal.dashboard'))

        columns = [desc[0] for desc in cur.description]
        job = dict(zip(columns, cur.fetchone()))

        return render_template(
            'driver_job_detail.html',
            driver_name=driver['driver_name'],
            job=job
        )
    except Exception as e:
        logger.error("Driver job detail error: job_id=%s, error=%s", job_id, str(e))
        return redirect(url_for('driver_portal.dashboard'))


# PUBLIC_INTERFACE
@driver_portal.route("/job/<int:job_id>/update", methods=['POST'])
def update_job_status(job_id):
    """Update the status of a job assigned to the current driver.

    Accepts form field 'status' to update the job. Only allows
    updates on jobs assigned to the logged-in driver.

    Args:
        job_id: The job ID to update.

    Returns:
        Redirect to job detail or dashboard.
    """
    driver = _require_driver_session()
    if not driver:
        return redirect(url_for('driver_portal.login_page'))

    new_status = request.form.get('status', '')
    allowed_statuses = ['Pending', 'In Transit', 'Delivered']

    if new_status not in allowed_statuses:
        logger.warning("Driver attempted invalid status update: %s", new_status)
        return redirect(url_for('driver_portal.job_detail', job_id=job_id))

    try:
        conn = mysql.connection
        cur = conn.cursor()

        # Verify job belongs to this driver
        cur.execute(
            "SELECT JobID FROM Jobs WHERE JobID=%s AND DriverID=%s",
            (job_id, driver['driver_id'])
        )
        if cur.rowcount == 0:
            return redirect(url_for('driver_portal.dashboard'))

        update_sql = "UPDATE Jobs SET Status=%s"
        params = [new_status]
        if new_status == 'Delivered':
            update_sql += ", DateDelivered=NOW()"
        update_sql += " WHERE JobID=%s AND DriverID=%s"
        params.extend([job_id, driver['driver_id']])

        cur.execute(update_sql, tuple(params))
        conn.commit()
        logger.info("Job %s status updated to %s by driver %s", job_id, new_status, driver['driver_id'])

        return redirect(url_for('driver_portal.job_detail', job_id=job_id))
    except Exception as e:
        logger.error("Job status update error: job_id=%s, error=%s", job_id, str(e))
        return redirect(url_for('driver_portal.dashboard'))


# PUBLIC_INTERFACE
@driver_portal.route("/logout")
def logout():
    """Log out the current driver and clear session.

    Returns:
        Redirect to driver login page.
    """
    driver_id = session.get('driver_id', 'unknown')
    session.pop('driver_id', None)
    session.pop('driver_name', None)
    session.pop('vehicle_id', None)
    logger.info("Driver logged out: driver_id=%s", driver_id)
    return redirect(url_for('driver_portal.login_page'))
