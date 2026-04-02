"""
Customer Portal Blueprint for the Transportation Management System.

Provides customer-facing views including:
- Customer login/logout
- Dashboard with order summary
- Order history and tracking
- Parcel tracking by tracking ID

Flow name: CustomerPortalFlow
Entrypoint: customer_portal blueprint registered in App.py
Contract:
  - Inputs: HTTP requests with session-based customer authentication
  - Outputs: Rendered HTML templates or redirects
  - Errors: Redirects to login on missing session; user-friendly error messages
  - Side effects: MySQL reads for order/tracking data, session management
"""

import logging
from flask import (
    Blueprint, render_template, request, redirect,
    session, url_for, jsonify, make_response
)
from App.extensions import mysql

logger = logging.getLogger(__name__)

customer_portal = Blueprint(
    'customer_portal', __name__,
    template_folder='templates',
    static_folder='static'
)


def _require_customer_session():
    """Check if customer is logged in via session.

    Returns:
        dict or None: Customer session info if logged in, None otherwise.
    """
    if 'customer_id' in session and 'customer_name' in session:
        return {
            'customer_id': session['customer_id'],
            'customer_name': session['customer_name']
        }
    return None


# PUBLIC_INTERFACE
@customer_portal.route("/", methods=['GET', 'POST'])
def login_page():
    """Customer login page.

    GET: Renders the login form. If already logged in, redirects to dashboard.
    POST: Authenticates customer credentials against the Customers table.

    Returns:
        Rendered login template or redirect to dashboard.
    """
    if request.method == 'GET':
        customer = _require_customer_session()
        if customer:
            return redirect(url_for('customer_portal.dashboard'))
        return render_template('customer_login.html', error_message='')

    # POST: authenticate
    email = request.form.get('email', '')
    password = request.form.get('password', '')

    try:
        conn = mysql.connection
        cur = conn.cursor()
        cur.execute(
            "SELECT CustomerID, FirstName, LastName, Password FROM Customers WHERE Email=%s",
            (email,)
        )
        if cur.rowcount == 0:
            logger.info("Customer login failed: unknown email=%s", email)
            return render_template('customer_login.html', error_message='Invalid email or password')

        row = cur.fetchone()
        customer_id, first_name, last_name, stored_password = row

        if password != stored_password:
            logger.info("Customer login failed: wrong password for email=%s", email)
            return render_template('customer_login.html', error_message='Invalid email or password')

        # Store session
        session['customer_id'] = customer_id
        session['customer_name'] = first_name
        session['customer_last_name'] = last_name or ''
        logger.info("Customer login successful: customer_id=%s, name=%s", customer_id, first_name)

        return redirect(url_for('customer_portal.dashboard'))

    except Exception as e:
        logger.error("Customer login error: %s", str(e))
        return render_template('customer_login.html', error_message='An error occurred. Please try again.')


# PUBLIC_INTERFACE
@customer_portal.route("/dashboard")
def dashboard():
    """Customer dashboard showing order summary and recent orders.

    Requires active customer session. Shows total orders, pending orders,
    delivered orders, and a list of recent orders.

    Returns:
        Rendered dashboard template or redirect to login.
    """
    customer = _require_customer_session()
    if not customer:
        return redirect(url_for('customer_portal.login_page'))

    customer_id = customer['customer_id']
    try:
        cur = mysql.connection.cursor()

        # Count total orders
        cur.execute("SELECT COUNT(*) FROM Jobs WHERE CustomerID=%s", (customer_id,))
        total_orders = cur.fetchone()[0] or 0

        # Count pending orders
        cur.execute(
            "SELECT COUNT(*) FROM Jobs WHERE CustomerID=%s AND Status='Pending'",
            (customer_id,)
        )
        pending_orders = cur.fetchone()[0] or 0

        # Count delivered orders
        cur.execute(
            "SELECT COUNT(*) FROM Jobs WHERE CustomerID=%s AND Status='Delivered'",
            (customer_id,)
        )
        delivered_orders = cur.fetchone()[0] or 0

        # Recent orders (last 20)
        cur.execute(
            "SELECT JobID, TrackingID, Status, ParcelType, DateCreated, DateDue, DateDelivered "
            "FROM Jobs WHERE CustomerID=%s ORDER BY DateCreated DESC LIMIT 20",
            (customer_id,)
        )
        columns = [desc[0] for desc in cur.description]
        orders = [dict(zip(columns, row)) for row in cur.fetchall()]

        return render_template(
            'customer_dashboard.html',
            customer_name=customer['customer_name'],
            total_orders=total_orders,
            pending_orders=pending_orders,
            delivered_orders=delivered_orders,
            orders=orders
        )
    except Exception as e:
        logger.error("Customer dashboard error: customer_id=%s, error=%s", customer_id, str(e))
        return render_template(
            'customer_dashboard.html',
            customer_name=customer['customer_name'],
            total_orders=0,
            pending_orders=0,
            delivered_orders=0,
            orders=[]
        )


# PUBLIC_INTERFACE
@customer_portal.route("/track", methods=['GET', 'POST'])
def track_parcel():
    """Track a parcel by tracking ID.

    GET: Shows the tracking form.
    POST: Looks up the tracking ID and displays driver location info.

    Returns:
        Rendered tracking template with results or empty form.
    """
    customer = _require_customer_session()
    if not customer:
        return redirect(url_for('customer_portal.login_page'))

    tracking_result = None
    error_message = ''
    tracking_id = ''

    if request.method == 'POST':
        tracking_id = request.form.get('tracking_id', '').strip()
        if not tracking_id:
            error_message = 'Please enter a tracking ID.'
        else:
            try:
                cur = mysql.connection.cursor()
                cur.execute(
                    "SELECT j.JobID, j.TrackingID, j.Status, j.ParcelType, j.DateCreated, "
                    "j.DateDue, j.DateDelivered, d.FirstName AS DriverName, d.Location "
                    "FROM Jobs j LEFT JOIN Drivers d ON j.DriverID=d.DriverID "
                    "WHERE j.TrackingID=%s",
                    (tracking_id,)
                )
                if cur.rowcount == 0:
                    error_message = 'No parcel found with that tracking ID.'
                else:
                    columns = [desc[0] for desc in cur.description]
                    tracking_result = dict(zip(columns, cur.fetchone()))
            except Exception as e:
                logger.error("Track parcel error: tracking_id=%s, error=%s", tracking_id, str(e))
                error_message = 'An error occurred while looking up the tracking ID.'

    return render_template(
        'customer_track.html',
        customer_name=customer['customer_name'],
        tracking_result=tracking_result,
        error_message=error_message,
        tracking_id=tracking_id
    )


# PUBLIC_INTERFACE
@customer_portal.route("/logout")
def logout():
    """Log out the current customer and clear session.

    Returns:
        Redirect to customer login page.
    """
    customer_id = session.get('customer_id', 'unknown')
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    session.pop('customer_last_name', None)
    logger.info("Customer logged out: customer_id=%s", customer_id)
    return redirect(url_for('customer_portal.login_page'))
