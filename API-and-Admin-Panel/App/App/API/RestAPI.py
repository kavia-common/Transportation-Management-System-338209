import sys
import os

[sys.path.append('/var/www/html/env/App/App')]

import calendar
import datetime
import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Blueprint, jsonify, make_response, request
from flask import current_app as app
from flask_cors import CORS
from werkzeug.utils import secure_filename

from extensions import mysql

from .api_utils import (
    ApiError,
    ValidationError,
    fetch_all_as_dicts,
    json_response,
    legacy_list_error,
    legacy_list_status,
    log_exception,
    make_select_all_sql,
    optional_int_arg,
    require_int_arg,
    validate_sql_identifier,
)

rest_api = Blueprint('rest_api', __name__)
CORS(rest_api)


@rest_api.route("/")
def apiDefault():
    return make_response(
        jsonify([{"Name": "Aquarian REST API", "Version": "0.1", "Created": "08/02/2020", "LastModified": "29/02/2020"}])
    )


# -------------------------------------------------------------------
# Jobs
# -------------------------------------------------------------------


@rest_api.route('/jobs/')
@rest_api.route('/jobs', methods=['GET', 'POST'])
def returnJobs():
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return getTable("Jobs", request.args["limit1"], request.args["limit2"])
        else:
            return getAllTable("Jobs")
    elif request.method == 'POST':
        return createRecord(request, "Jobs", "JobID")


@rest_api.route('/jobs/<int:id>/')
@rest_api.route('/jobs/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_job(id):
    if request.method == 'GET':
        return getRecord("Jobs", "JobID", id)
    elif request.method == 'PUT':
        return updateTable(request, 'Jobs', 'JobID', id)
    elif request.method == 'DELETE':
        return deleteRecord("Jobs", "JobID", id)


@rest_api.route('/jobs/pending', methods=['GET'])
def returnPendingJobs():
    """
    Return jobs with Status='Pending'.

    Preserves existing behavior including optional `limit1`/`limit2` query args.
    """
    try:
        cur = mysql.connection.cursor()
        limit = optional_int_arg(request.args, "limit1", minimum=0)
        offset = optional_int_arg(request.args, "limit2", minimum=0)

        if limit is not None and offset is not None:
            cur.execute("SELECT * FROM Jobs WHERE Status=%s LIMIT %s OFFSET %s", ("Pending", limit, offset))
        else:
            cur.execute("SELECT * FROM Jobs WHERE Status=%s", ("Pending",))

        json_data = fetch_all_as_dicts(cur, "SELECT * FROM Jobs WHERE Status=%s" + (" LIMIT %s OFFSET %s" if (limit is not None and offset is not None) else ""),
                                      (("Pending", limit, offset) if (limit is not None and offset is not None) else ("Pending",)))
        # Preserve original response style: json.dumps + make_response
        resp = make_response(json.dumps(json_data, default=str))
        resp.headers['Content-Type'] = 'application/json'
        return resp
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("returnPendingJobs", e, extra={"limit1": request.args.get("limit1"), "limit2": request.args.get("limit2")})
        return legacy_list_error("Internal Server Error", 500)


@rest_api.route('/jobs/delivered', methods=['GET'])
def returnDoneJobs():
    """
    Return jobs with Status='Delivered'.

    Preserves existing behavior including optional `limit1`/`limit2` query args.
    """
    try:
        cur = mysql.connection.cursor()
        limit = optional_int_arg(request.args, "limit1", minimum=0)
        offset = optional_int_arg(request.args, "limit2", minimum=0)

        if limit is not None and offset is not None:
            cur.execute("SELECT * FROM Jobs WHERE Status=%s LIMIT %s OFFSET %s", ("Delivered", limit, offset))
            json_data = fetch_all_as_dicts(cur, "SELECT * FROM Jobs WHERE Status=%s LIMIT %s OFFSET %s", ("Delivered", limit, offset))
        else:
            cur.execute("SELECT * FROM Jobs WHERE Status=%s", ("Delivered",))
            json_data = fetch_all_as_dicts(cur, "SELECT * FROM Jobs WHERE Status=%s", ("Delivered",))

        resp = make_response(json.dumps(json_data, default=str))
        resp.headers['Content-Type'] = 'application/json'
        return resp
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("returnDoneJobs", e, extra={"limit1": request.args.get("limit1"), "limit2": request.args.get("limit2")})
        return legacy_list_error("Internal Server Error", 500)


@rest_api.route('/jobs/<string:id>/location', methods=['GET', 'PUT'])
def getParcelLocation(id):
    if request.method == 'GET':
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT DriverID FROM Jobs WHERE TrackingID=%s", (id,))
            if cur.rowcount == 0:
                return legacy_list_error("No matching ID found in database.", 404)
            result = cur.fetchone()

            cur.execute("SELECT DriverID, FirstName, Location FROM Drivers WHERE DriverID=%s", (result[0],))
            if cur.rowcount == 0:
                return legacy_list_error("No matching ID found in database.", 404)

            row_headers = [x[0] for x in cur.description]
            rv = cur.fetchall()
            json_data = [dict(zip(row_headers, r)) for r in rv]
            resp = make_response(json.dumps(json_data, default=str))
            resp.headers['Content-Type'] = 'application/json'
            return resp
        except Exception as e:
            log_exception("getParcelLocation", e, extra={"tracking_id": id})
            return legacy_list_error("Internal Server Error", 500)


# -------------------------------------------------------------------
# Drivers
# -------------------------------------------------------------------


@rest_api.route('/drivers/')
@rest_api.route('/drivers', methods=['GET', 'POST'])
def returnDrivers():
    if request.method == 'GET':
        try:
            limit = optional_int_arg(request.args, "limit1", minimum=0)
            offset = optional_int_arg(request.args, "limit2", minimum=0)

            base_sql = (
                "SELECT DriverID, VehicleID, Username, LastName, FirstName, DOB, NINo, DrivingLicenseNo, "
                "DrivingLicensePic, Address1, Address2, City, PostCode, Country, Location, DateCreated, LastConnected "
                "FROM Drivers"
            )

            cur = mysql.connection.cursor()
            if limit is not None and offset is not None:
                cur.execute(base_sql + " LIMIT %s OFFSET %s", (limit, offset))
            else:
                cur.execute(base_sql)

            row_headers = [x[0] for x in cur.description]
            rv = cur.fetchall()
            json_data = [dict(zip(row_headers, r)) for r in rv]
            resp = make_response(json.dumps(json_data, default=str))
            resp.headers['Content-Type'] = 'application/json'
            return resp
        except ValidationError as e:
            return legacy_list_error(e.message, 400)
        except Exception as e:
            log_exception("returnDrivers[GET]", e, extra={"limit1": request.args.get("limit1"), "limit2": request.args.get("limit2")})
            return legacy_list_error("Internal Server Error", 500)

    elif request.method == 'POST':
        # This endpoint historically had custom behavior (username generation and default password).
        # We preserve that behavior but remove string-built SQL for safety.
        try:
            _json = request.args
            conn = mysql.connection
            cur = conn.cursor()

            # Ensure table exists / fetch columns
            cur.execute("SELECT * FROM Drivers")
            if cur.rowcount == 0:
                # Keep the original style (even though the old code had a bug referencing `table`).
                return legacy_list_error("No table Drivers found in database.", 404)

            params: List[Any] = []
            headers: List[str] = []
            row_headers = [x[0] for x in cur.description]

            for header in row_headers:
                if header == 'DriverID':
                    continue
                if header in _json:
                    headers.append(header)
                    params.append(_json[header])
                else:
                    headers.append(header)
                    params.append(None)

            # Generate driver username (preserve old approach: FirstName+LastName plus increment suffix)
            if 'FirstName' not in _json or 'LastName' not in _json:
                return legacy_list_error("Missing required parameters: FirstName, LastName", 400)
            uname = f"{_json['FirstName']}{_json['LastName']}"
            x = 1
            while True:
                cur.execute("SELECT 1 FROM Drivers WHERE Username=%s", (uname,))
                if cur.rowcount != 0:
                    if x == 1:
                        uname = f"{uname}{x}"
                    else:
                        # Replace the last character (old code assumed single-digit; keep same behavior but more robust)
                        uname = f"{uname[:-len(str(x - 1))]}{x}"
                    x += 1
                    continue
                break

            # Apply special defaults (preserve original behavior)
            for i, col in enumerate(headers):
                if col == 'DateCreated':
                    params[i] = datetime.datetime.now()
                elif col == 'Username':
                    params[i] = uname
                elif col == 'Password':
                    params[i] = 'Aquarian'

            # Build parameterized INSERT
            safe_cols = [validate_sql_identifier(c, kind="column") for c in headers]
            placeholders = ",".join(["%s"] * len(safe_cols))
            sql = f"INSERT INTO Drivers ({','.join(safe_cols)}) VALUES ({placeholders})"
            cur.execute(sql, tuple(params))
            conn.commit()

            resp = make_response(jsonify([{'Success': 'Record added to table Drivers successfully!'}]))
            resp.status_code = 200
            return resp
        except ApiError as e:
            return legacy_list_error(e.message, e.status_code)
        except Exception as e:
            log_exception("returnDrivers[POST]", e, extra={"args": dict(request.args)})
            return legacy_list_error("Internal Server Error", 500)


@rest_api.route('/drivers/<int:id>/')
@rest_api.route('/drivers/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_driver(id):
    if request.method == 'GET':
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT DriverID, VehicleID, LastName, FirstName, DOB, NINo, DrivingLicenseNo, DrivingLicensePic, "
            "Address1, Address2, City, PostCode, Country, Location, DateCreated, LastConnected "
            "FROM Drivers WHERE DriverID = %s",
            (id,),
        )
        if cur.rowcount == 0:
            return legacy_list_error("No matching ID found in database.", 404)
        row_headers = [x[0] for x in cur.description]
        rv = cur.fetchall()
        json_data = [dict(zip(row_headers, r)) for r in rv]
        resp = make_response(json.dumps(json_data, default=str))
        resp.headers['Content-Type'] = 'application/json'
        return resp
    elif request.method == 'PUT':
        return updateTable(request, 'Drivers', 'DriverID', id)
    elif request.method == 'DELETE':
        return deleteRecord("Drivers", "DriverID", id)


@rest_api.route('/drivers/<int:id>/location', methods=['GET', 'PUT'])
def getLocation(id):
    if request.method == 'GET':
        cur = mysql.connection.cursor()
        cur.execute("SELECT DriverID, FirstName, Location FROM Drivers WHERE DriverID=%s", (id,))
        if cur.rowcount == 0:
            return legacy_list_error("No matching ID found in database.", 404)
        row_headers = [x[0] for x in cur.description]
        rv = cur.fetchall()
        json_data = [dict(zip(row_headers, r)) for r in rv]
        resp = make_response(json.dumps(json_data, default=str))
        resp.headers['Content-Type'] = 'application/json'
        return resp
    elif request.method == 'PUT':
        return updateTable(request, 'Drivers', 'DriverID', id)


# Driver Login (Android App)
@rest_api.route('/drivers/login', methods=['POST'])
def driver_login():
    try:
        _json = request.args
        if "Username" not in _json or "Password" not in _json:
            return legacy_list_status("Error", "Login failed: Missing Username/Password", 200)

        conn = mysql.connection
        cur = conn.cursor()

        cur.execute("SELECT Password FROM Drivers WHERE Username=%s", (_json['Username'],))
        if cur.rowcount == 0:
            return legacy_list_status("Error", "Login failed: Wrong Username", 200)

        result = cur.fetchone()
        if _json['Password'] == result[0]:
            cur.execute("UPDATE Drivers SET LastConnected = NOW() WHERE Username=%s", (_json['Username'],))
            conn.commit()
            cur.execute("SELECT DriverID, FirstName, LastConnected, VehicleID FROM Drivers WHERE Username=%s", (_json['Username'],))
            result = cur.fetchone()
            return legacy_list_status(
                "Success",
                "Login Succesful",
                200,
                DriverID=result[0],
                FirstName=result[1],
                LastConnected=result[2],
                VehicleID=result[3],
            )

        return legacy_list_status("Error", "Login failed: Wrong Password", 200)
    except Exception as e:
        log_exception("driver_login", e, extra={"username": request.args.get("Username")})
        return legacy_list_error("Internal Server Error", 500)


# -------------------------------------------------------------------
# Vehicles
# -------------------------------------------------------------------


@rest_api.route('/vehicles/')
@rest_api.route('/vehicles', methods=['GET', 'POST'])
def returnVehicles():
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return getTable("Vehicles", request.args["limit1"], request.args["limit2"])
        else:
            return getAllTable("Vehicles")
    elif request.method == 'POST':
        return createRecord(request, "Vehicles", "VehicleID")


@rest_api.route('/vehicles/<int:id>/')
@rest_api.route('/vehicles/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_vehicle(id):
    if request.method == 'GET':
        return getRecord("Vehicles", "VehicleID", id)
    elif request.method == 'PUT':
        return updateTable(request, 'Vehicles', 'VehicleID', id)
    elif request.method == 'DELETE':
        return deleteRecord("Vehicles", "VehicleID", id)


# -------------------------------------------------------------------
# Customers
# -------------------------------------------------------------------


@rest_api.route('/customers/')
@rest_api.route('/customers', methods=['GET', 'POST'])
def returnCustomers():
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return getTable("Customers", request.args["limit1"], request.args["limit2"])
        else:
            return getAllTable("Customers")
    elif request.method == 'POST':
        return createRecord(request, "Customers", "CustomerID")


@rest_api.route('/customers/<int:id>/')
@rest_api.route('/customers/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_customer(id):
    if request.method == 'GET':
        return getRecord("Customers", "CustomerID", id)
    elif request.method == 'PUT':
        return updateTable(request, 'Customers', 'CustomerID', id)
    elif request.method == 'DELETE':
        return deleteRecord("Customers", "CustomerID", id)


# -------------------------------------------------------------------
# Pick-Up and Drop-Off Locations
# -------------------------------------------------------------------


@rest_api.route('/locations/')
@rest_api.route('/locations', methods=['GET', 'POST'])
def returnLocations():
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return getTable("Locations", request.args["limit1"], request.args["limit2"])
        else:
            return getAllTable("Locations")
    elif request.method == 'POST':
        return createRecord(request, "Locations", "CustomerID")


@rest_api.route('/locations/<int:id>/')
@rest_api.route('/locations/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_location(id):
    if request.method == 'GET':
        return getRecord("Locations", "LocationID", id)
    elif request.method == 'PUT':
        return updateTable(request, 'Locations', 'LocationID', id)
    elif request.method == 'DELETE':
        return deleteRecord("Locations", "LocationID", id)


# -------------------------------------------------------------------
# Receipts
# -------------------------------------------------------------------


@rest_api.route('/receipts/')
@rest_api.route('/receipts', methods=['GET', 'POST'])
def returnReceipts():
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return getTable("Receipts", request.args["limit1"], request.args["limit2"])
        else:
            return getAllTable("Receipts")
    elif request.method == 'POST':
        return createRecord(request, "Receipts", "ReceiptID")


@rest_api.route('/receipts/<int:id>/')
@rest_api.route('/receipts/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_receipt(id):
    if request.method == 'GET':
        return getRecord("Receipts", "ReceiptID", id)
    elif request.method == 'PUT':
        return updateTable(request, 'Receipts', 'ReceiptID', id)
    elif request.method == 'DELETE':
        return deleteRecord("Receipts", "ReceiptID", id)


@rest_api.route('/receipts/driver/<int:id>/')
@rest_api.route('/receipts/driver/<int:id>', methods=['GET'])
def get_receipt_by_driver(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Receipts WHERE DriverID=%s AND DATE(DateCreated)=DATE(NOW())", (id,))
    row_headers = [x[0] for x in cur.description]
    rv = cur.fetchall()
    json_data = [dict(zip(row_headers, r)) for r in rv]
    resp = make_response(json.dumps(json_data, default=str))
    resp.headers['Content-Type'] = 'application/json'
    return resp


# -------------------------------------------------------------------
# FULL JOB
# -------------------------------------------------------------------


@rest_api.route('/jobs/full/<int:id>/')
@rest_api.route('/jobs/full/<int:id>', methods=['GET'])
def get_full_job(id):
    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT JobId, TrackingID, Status, ParcelType, ParcelSize, ParcelWeight, DateCreated, DateDue, DateDelivered, "
        "DistanceTravelled, Picture1, Picture2, Comments FROM Jobs WHERE JobID = %s",
        (id,),
    )
    if cur.rowcount == 0:
        return '{"Error":"No matching ID was found in the database."}'
    row_headers = [x[0] for x in cur.description]
    rv = cur.fetchall()
    job_data = [dict(zip(row_headers, r)) for r in rv]
    job_data = json.dumps(job_data, default=str)

    cur.execute("SELECT CustomerID FROM Jobs WHERE JobID = %s", (id,))
    rv = cur.fetchall()
    for row in rv:
        cid = row[0]

    cur.execute("SELECT * FROM Customers WHERE CustomerID = %s", (cid,))
    row_headers = [x[0] for x in cur.description]
    rv = cur.fetchall()
    customer_data = [dict(zip(row_headers, r)) for r in rv]
    customer_data = json.dumps(customer_data, default=str)

    cur.execute("SELECT PickupID FROM Jobs WHERE JobID = %s", (id,))
    rv = cur.fetchall()
    for row in rv:
        cid = row[0]

    cur.execute("SELECT * FROM Locations WHERE LocationID = %s", (cid,))
    row_headers = [x[0] for x in cur.description]
    rv = cur.fetchall()
    pickup_data = [dict(zip(row_headers, r)) for r in rv]
    pickup_data = json.dumps(pickup_data, default=str)

    cur.execute("SELECT DropOffID FROM Jobs WHERE JobID = %s", (id,))
    rv = cur.fetchall()
    for row in rv:
        cid = row[0]

    cur.execute("SELECT * FROM Locations WHERE LocationID = %s", (cid,))
    row_headers = [x[0] for x in cur.description]
    rv = cur.fetchall()
    dropoff_data = [dict(zip(row_headers, r)) for r in rv]
    dropoff_data = json.dumps(dropoff_data, default=str)

    resp = make_response(str('{"Job":%s,"Customer":%s,"Pickup":%s,"Dropoff":%s}' % (job_data, customer_data, pickup_data, dropoff_data)))
    resp.headers['Content-Type'] = 'application/json'
    return resp


@rest_api.route('/drivers/assigned/<int:id>/')
@rest_api.route('/drivers/assigned/<int:id>', methods=['GET'])
def getAssignedJobs(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT JobID FROM Jobs WHERE Status=%s AND DriverID=%s", ("Pending", id))
    if cur.rowcount == 0:
        return '{"Error":"No jobs found."}'
    row_headers = [x[0] for x in cur.description]
    rv = cur.fetchall()
    json_data = [dict(zip(row_headers, r)) for r in rv]

    full_array = []
    url = "http://soc-web-liv-82.napier.ac.uk/api/jobs/full/"
    for data in json_data:
        myResponse = requests.get(url + str(data['JobID']))
        if myResponse.ok:
            full_array.append(json.loads(myResponse.content))
    resp = make_response(json.dumps(full_array, default=str))
    resp.headers['Content-Type'] = 'application/json'
    return resp


# 404 Error Handler
@rest_api.route("<path:invalid_path>")
def missing_resource(invalid_path):
    return make_response(jsonify([{"Error": "Not Found"}]), 404)


# -------------------------------------------------------------------
# Admin Login
# -------------------------------------------------------------------


@rest_api.route('/admin', methods=['POST'])
def admin_login():
    return login(request, "Admins")


# -------------------------------------------------------------------
# Shared CRUD helpers (refactored to parameterized queries)
# -------------------------------------------------------------------


def getAllTable(table):
    try:
        table = validate_sql_identifier(table, kind="table")
        cur = mysql.connection.cursor()
        sql, params = make_select_all_sql(table)
        cur.execute(sql, params)
        row_headers = [x[0] for x in cur.description]
        rv = cur.fetchall()
        json_data = [dict(zip(row_headers, r)) for r in rv]
        resp = make_response(json.dumps(json_data, default=str))
        resp.headers['Content-Type'] = 'application/json'
        return resp
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("getAllTable", e, extra={"table": table})
        return legacy_list_error("Internal Server Error", 500)


def getTable(table, limit1, limit2):
    try:
        table = validate_sql_identifier(table, kind="table")
        limit = int(limit1)
        offset = int(limit2)
        if limit < 0 or offset < 0:
            raise ValidationError("limit1/limit2 must be non-negative integers")

        cur = mysql.connection.cursor()
        sql, params = make_select_all_sql(table, limit=limit, offset=offset)
        cur.execute(sql, params)
        row_headers = [x[0] for x in cur.description]
        rv = cur.fetchall()
        json_data = [dict(zip(row_headers, r)) for r in rv]
        resp = make_response(json.dumps(json_data, default=str))
        resp.headers['Content-Type'] = 'application/json'
        return resp
    except (ValueError, TypeError):
        return legacy_list_error("limit1/limit2 must be integers", 400)
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("getTable", e, extra={"table": table, "limit1": limit1, "limit2": limit2})
        return legacy_list_error("Internal Server Error", 500)


def getRecord(table, idname, id):
    try:
        table = validate_sql_identifier(table, kind="table")
        idname = validate_sql_identifier(idname, kind="column")
        cur = mysql.connection.cursor()
        cur.execute(f"SELECT * FROM {table} WHERE {idname} = %s", (id,))
        if cur.rowcount == 0:
            return legacy_list_error("No matching ID found in database.", 404)
        row_headers = [x[0] for x in cur.description]
        rv = cur.fetchall()
        json_data = [dict(zip(row_headers, r)) for r in rv]
        resp = make_response(json.dumps(json_data, default=str))
        resp.headers['Content-Type'] = 'application/json'
        return resp
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("getRecord", e, extra={"table": table, "idname": idname, "id": id})
        return legacy_list_error("Internal Server Error", 500)


def deleteRecord(table, idname, id):
    try:
        table = validate_sql_identifier(table, kind="table")
        idname = validate_sql_identifier(idname, kind="column")
        conn = mysql.connection
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE {idname} = %s", (id,))
        conn.commit()
        resp = make_response(jsonify([{"Status": "One row with id " + str(id) + " deleted from " + table}]))
        return resp
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("deleteRecord", e, extra={"table": table, "idname": idname, "id": id})
        return legacy_list_error("Internal Server Error", 500)


def createRecord(request, table, idname):
    """
    Generic create record using request.args.

    Preserves legacy behavior:
      - Missing fields become NULL
      - 'DateCreated' is set to NOW() (handled here as datetime.now())
      - For Jobs: TrackingID updated after insert (AQ<mmYY><id>)
    """
    try:
        table = validate_sql_identifier(table, kind="table")
        idname = validate_sql_identifier(idname, kind="column")

        _json = request.args
        conn = mysql.connection
        cur = conn.cursor()

        # Fetch columns (and detect table presence)
        cur.execute(f"SELECT * FROM {table} LIMIT 0")
        row_headers = [x[0] for x in cur.description]

        params: List[Any] = []
        headers: List[str] = []

        for header in row_headers:
            if header == idname:
                continue
            if header in _json:
                headers.append(header)
                params.append(_json[header])
            else:
                headers.append(header)
                params.append(None)

        for i, col in enumerate(headers):
            if col == 'DateCreated':
                params[i] = datetime.datetime.now()

        safe_cols = [validate_sql_identifier(c, kind="column") for c in headers]
        placeholders = ",".join(["%s"] * len(safe_cols))
        sql = f"INSERT INTO {table} ({','.join(safe_cols)}) VALUES ({placeholders})"
        cur.execute(sql, tuple(params))
        conn.commit()

        if table == 'Jobs':
            current_date = datetime.date.today()
            trackid = 'AQ' + current_date.strftime("%m%y") + str(cur.lastrowid)
            # Parameterized UPDATE
            cur.execute("UPDATE Jobs SET TrackingID=%s WHERE JobID=%s", (trackid, cur.lastrowid))
            conn.commit()

        resp = make_response(jsonify([{'Success': 'Record added to table ' + table + ' successfully!'}]))
        resp.status_code = 200
        return resp
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("createRecord", e, extra={"table": table, "idname": idname, "args": dict(request.args)})
        return legacy_list_error("Internal Server Error", 500)


def updateTable(request, table, idname, id):
    """
    Generic update record using request.args.

    Preserves legacy behavior:
      - If a field is not provided, it is left unchanged
      - Provided value 'None' becomes SQL NULL
    """
    try:
        table = validate_sql_identifier(table, kind="table")
        idname = validate_sql_identifier(idname, kind="column")

        _json = request.args
        conn = mysql.connection
        cur = conn.cursor()

        # Check existing
        cur.execute(f"SELECT * FROM {table} WHERE {idname}=%s", (id,))
        if cur.rowcount == 0:
            return legacy_list_error("No matching ID found in database.", 404)

        row_headers = [x[0] for x in cur.description]

        # Build update columns (skip id column)
        set_cols: List[str] = []
        values: List[Any] = []
        for header in row_headers:
            if header == idname:
                continue
            if header in _json:
                set_cols.append(validate_sql_identifier(header, kind="column"))
                values.append(None if _json[header] == "None" else _json[header])

        if not set_cols:
            # Nothing to update; preserve success response semantics.
            resp = make_response(jsonify([{'Success': 'Table ' + table + ' edited successfully!'}]))
            resp.status_code = 200
            return resp

        set_clause = ", ".join([f"{col}=%s" for col in set_cols])
        sql = f"UPDATE {table} SET {set_clause} WHERE {idname}=%s"
        values.append(id)

        cur.execute(sql, tuple(values))
        conn.commit()
        resp = make_response(jsonify([{'Success': 'Table ' + table + ' edited successfully!'}]))
        resp.status_code = 200
        return resp
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("updateTable", e, extra={"table": table, "idname": idname, "id": id, "args": dict(request.args)})
        return legacy_list_error("Internal Server Error", 500)


def login(request, table):
    try:
        table = validate_sql_identifier(table, kind="table")
        _json = request.args
        if "Username" not in _json or "Password" not in _json:
            return legacy_list_status("Error", "Login failed: Missing Username/Password", 200)

        conn = mysql.connection
        cur = conn.cursor()
        cur.execute(f"SELECT Password FROM {table} WHERE Username=%s", (_json['Username'],))
        if cur.rowcount == 0:
            return legacy_list_status("Error", "Login failed: Wrong Username", 200)

        result = cur.fetchone()
        if _json['Password'] == result[0]:
            cur.execute(f"UPDATE {table} SET LastConnected = NOW() WHERE Username=%s", (_json['Username'],))
            conn.commit()
            return legacy_list_status("Success", "Login Succesful", 200, Username=_json['Username'])

        return legacy_list_status("Error", "Login failed: Wrong Password", 200)
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("login", e, extra={"table": table, "username": request.args.get("Username")})
        return legacy_list_error("Internal Server Error", 500)


# -------------------------------------------------------------------
# Money endpoints
# -------------------------------------------------------------------


@rest_api.route('/money', methods=['GET'])
def getMoney():
    current_date = datetime.date.today()
    current_month = current_date.month + 1
    json_str = '['
    for month in range(1, current_month):
        json_str += '{"Month":"' + calendar.month_name[month] + '",'
        amount = monthRevenue(month)
        receipt = monthReceipts(month)
        if amount is not None:
            json_str += '"Amount":"' + str(round(amount, 2)) + '",'
        else:
            json_str += '"Amount":null,'
        if receipt is not None:
            json_str += '"Receipts":"' + str(round(receipt, 2)) + '"},'
        else:
            json_str += '"Receipts":null},'
    json_str = json_str[:-1] + ']'
    return json_str


def monthRevenue(month):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT SUM(PricePaid) FROM Jobs WHERE MONTH(DateDelivered)=%s", (int(month),))
    if cur.rowcount == 0:
        return "No data for this month"
    result = cur.fetchone()
    return result[0]


def monthReceipts(month):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT SUM(Amount) FROM Receipts WHERE MONTH(DateCreated)=%s", (int(month),))
    if cur.rowcount == 0:
        return "No data for this month"
    result = cur.fetchone()
    return result[0]


# -------------------------------------------------------------------
# Admin panel helper endpoints (used by AdminPanel/static/scripts/panel.js)
# -------------------------------------------------------------------

_ALLOWED_JOB_STATUSES: Tuple[str, ...] = (
    "Pending",
    "Assigned",
    "PickedUp",
    "InTransit",
    "Delivered",
    "Cancelled",
)


def _coerce_none(value: Optional[str]) -> Optional[str]:
    """Convert legacy 'None' string from the UI into real None."""
    if value is None:
        return None
    return None if value == "None" else value


def _today_range() -> Tuple[datetime.datetime, datetime.datetime]:
    """Return (start,end) datetimes for today in server local time."""
    now = datetime.datetime.now()
    start = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    end = start + datetime.timedelta(days=1)
    return start, end


# PUBLIC_INTERFACE
def assign_job_flow(*, job_id: int, driver_id: Optional[int], vehicle_id: Optional[int]) -> Dict[str, Any]:
    """
    Assign a job to a driver/vehicle in a single canonical flow.

    Contract:
      - Inputs:
          - job_id: existing JobID
          - driver_id: DriverID or None (unassign)
          - vehicle_id: VehicleID or None (unassign)
      - Output:
          - dict with keys: JobID, DriverID, VehicleID, Status
      - Errors:
          - ValidationError on invalid IDs
          - ApiError(404) if job not found
      - Side effects:
          - Updates Jobs table (DriverID/VehicleID and potentially Status)
    """
    conn = mysql.connection
    cur = conn.cursor()

    cur.execute("SELECT JobID, Status FROM Jobs WHERE JobID=%s", (job_id,))
    if cur.rowcount == 0:
        raise ApiError("No matching ID found in database.", status_code=404)
    current_status = cur.fetchone()[1]

    if driver_id is not None:
        cur.execute("SELECT 1 FROM Drivers WHERE DriverID=%s", (driver_id,))
        if cur.rowcount == 0:
            raise ValidationError("Invalid DriverID: no matching driver")
    if vehicle_id is not None:
        cur.execute("SELECT 1 FROM Vehicles WHERE VehicleID=%s", (vehicle_id,))
        if cur.rowcount == 0:
            raise ValidationError("Invalid VehicleID: no matching vehicle")

    # Status adjustment rules (kept minimal to avoid breaking legacy behavior)
    next_status = current_status
    if current_status not in ("Delivered", "Cancelled"):
        if driver_id is not None or vehicle_id is not None:
            if current_status == "Pending":
                next_status = "Assigned"
        else:
            if current_status == "Assigned":
                next_status = "Pending"

    cur.execute(
        "UPDATE Jobs SET DriverID=%s, VehicleID=%s, Status=%s WHERE JobID=%s",
        (driver_id, vehicle_id, next_status, job_id),
    )
    conn.commit()

    return {"JobID": job_id, "DriverID": driver_id, "VehicleID": vehicle_id, "Status": next_status}


# PUBLIC_INTERFACE
def update_job_status_flow(*, job_id: int, status: str) -> Dict[str, Any]:
    """
    Update a job status with validation and automatic timestamp updates.

    Contract:
      - Inputs:
          - job_id: existing JobID
          - status: one of _ALLOWED_JOB_STATUSES
      - Output:
          - dict with keys: JobID, Status, DateDelivered (optional)
      - Errors:
          - ValidationError for invalid status
          - ApiError(404) if job not found
      - Side effects:
          - Updates Jobs.Status and sets DateDelivered when Delivered
    """
    if status not in _ALLOWED_JOB_STATUSES:
        raise ValidationError(f"Invalid Status. Allowed: {', '.join(_ALLOWED_JOB_STATUSES)}")

    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT JobID FROM Jobs WHERE JobID=%s", (job_id,))
    if cur.rowcount == 0:
        raise ApiError("No matching ID found in database.", status_code=404)

    if status == "Delivered":
        cur.execute("UPDATE Jobs SET Status=%s, DateDelivered=NOW() WHERE JobID=%s", (status, job_id))
    else:
        cur.execute("UPDATE Jobs SET Status=%s WHERE JobID=%s", (status, job_id))
    conn.commit()

    payload: Dict[str, Any] = {"JobID": job_id, "Status": status}
    if status == "Delivered":
        payload["DateDelivered"] = str(datetime.datetime.now())
    return payload


# PUBLIC_INTERFACE
def dashboard_kpis_flow() -> Dict[str, Any]:
    """
    Compute dashboard KPIs and chart datasets for the admin panel.

    Contract:
      - Inputs: none
      - Output:
          - kpis: parcels_today, drivers_connected_today, jobs_completed_today, jobs_total_today, completed_percent
          - work_share: list of driver workload entries
      - Errors: DB errors propagate to route handler
      - Side effects: none
    """
    conn = mysql.connection
    cur = conn.cursor()

    start, end = _today_range()

    cur.execute("SELECT COUNT(*) FROM Jobs WHERE DateCreated >= %s AND DateCreated < %s", (start, end))
    parcels_today = int(cur.fetchone()[0] or 0)

    cur.execute("SELECT COUNT(*) FROM Jobs WHERE DateDelivered IS NOT NULL AND DateDelivered >= %s AND DateDelivered < %s", (start, end))
    jobs_completed_today = int(cur.fetchone()[0] or 0)

    jobs_total_today = parcels_today
    completed_percent = int(round((jobs_completed_today / jobs_total_today) * 100)) if jobs_total_today > 0 else 0

    cur.execute("SELECT COUNT(*) FROM Drivers WHERE LastConnected IS NOT NULL AND LastConnected >= %s AND LastConnected < %s", (start, end))
    drivers_connected_today = int(cur.fetchone()[0] or 0)

    cur.execute(
        "SELECT d.DriverID, d.FirstName, d.LastName, COUNT(j.JobID) "
        "FROM Drivers d "
        "LEFT JOIN Jobs j ON j.DriverID = d.DriverID AND j.Status IN ('Pending','Assigned','PickedUp','InTransit') "
        "GROUP BY d.DriverID, d.FirstName, d.LastName "
        "ORDER BY COUNT(j.JobID) DESC"
    )
    share_rows = cur.fetchall()
    work_share: List[Dict[str, Any]] = []
    for row in share_rows:
        driver_id, first_name, last_name, count_jobs = row
        driver_name = (first_name or "").strip()
        if last_name:
            driver_name = (driver_name + " " + last_name).strip()
        if not driver_name:
            driver_name = f"Driver {driver_id}"
        work_share.append({"DriverID": driver_id, "DriverName": driver_name, "Jobs": int(count_jobs or 0)})

    return {
        "kpis": {
            "parcels_today": parcels_today,
            "drivers_connected_today": drivers_connected_today,
            "jobs_completed_today": jobs_completed_today,
            "jobs_total_today": jobs_total_today,
            "completed_percent": completed_percent,
        },
        "work_share": work_share,
    }


@rest_api.route("/jobs/<int:id>/assign", methods=["PUT"])
def assign_job(id: int):
    """
    Assign/unassign a driver and/or vehicle to a job.

    Query args:
      - DriverID: integer or 'None'
      - VehicleID: integer or 'None'
    """
    try:
        driver_raw = _coerce_none(request.args.get("DriverID"))
        vehicle_raw = _coerce_none(request.args.get("VehicleID"))

        driver_id: Optional[int] = int(driver_raw) if driver_raw is not None else None
        vehicle_id: Optional[int] = int(vehicle_raw) if vehicle_raw is not None else None

        job = assign_job_flow(job_id=id, driver_id=driver_id, vehicle_id=vehicle_id)
        return json_response([{"Success": "Job assignment updated successfully!", "Job": job}], status_code=200)
    except (ValueError, TypeError):
        return legacy_list_error("DriverID/VehicleID must be integers or None", 400)
    except ValidationError as e:
        return legacy_list_error(e.message, 400)
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("assign_job", e, extra={"JobID": id, "args": dict(request.args)})
        return legacy_list_error("Internal Server Error", 500)


@rest_api.route("/jobs/<int:id>/status", methods=["PUT"])
def update_job_status(id: int):
    """
    Update job lifecycle status.

    Query args:
      - Status: one of Pending/Assigned/PickedUp/InTransit/Delivered/Cancelled
    """
    try:
        status = request.args.get("Status", "")
        result = update_job_status_flow(job_id=id, status=status)
        return json_response([{"Success": "Job status updated successfully!", "Job": result}], status_code=200)
    except ValidationError as e:
        return legacy_list_error(e.message, 400)
    except ApiError as e:
        return legacy_list_error(e.message, e.status_code)
    except Exception as e:
        log_exception("update_job_status", e, extra={"JobID": id, "args": dict(request.args)})
        return legacy_list_error("Internal Server Error", 500)


@rest_api.route("/dashboard/kpis", methods=["GET"])
def dashboard_kpis():
    """Return KPI + chart datasets for the admin dashboard."""
    try:
        payload = dashboard_kpis_flow()
        return json_response(payload, status_code=200)
    except Exception as e:
        log_exception("dashboard_kpis", e)
        return legacy_list_error("Internal Server Error", 500)


# -------------------------------------------------------------------
# Upload endpoint
# -------------------------------------------------------------------

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@rest_api.route('/receipts/uploads/')
@rest_api.route('/receipts/uploads', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return make_response(jsonify([{"Message": "ERROR - No file present."}]), 200)
        file = request.files['file']
        # if user does not select file, browser also submit an empty part without filename
        if file.filename == '':
            return make_response(jsonify([{"Message": "ERROR - No filename"}]), 200)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return make_response(jsonify([{"Message": "File uploaded successfully."}]), 200)
        return make_response(jsonify([{"Message": "ERROR - File type not allowed."}]), 200)
