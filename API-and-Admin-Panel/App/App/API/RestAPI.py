import datetime
import json
import os
import calendar
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, make_response, request
from flask import current_app as app
from flask_cors import CORS
from werkzeug.utils import secure_filename

from extensions import mysql

rest_api = Blueprint("rest_api", __name__)
# Keep CORS permissive for compatibility with the Android app; allow overriding via env.
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()
_allowed_origins = "*" if _allowed_origins_env == "*" else [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
CORS(rest_api, resources={r"/*": {"origins": _allowed_origins}})

# Whitelist tables to prevent SQL injection via table name.
_ALLOWED_TABLES: Dict[str, str] = {
    "Jobs": "JobID",
    "Drivers": "DriverID",
    "Vehicles": "VehicleID",
    "Customers": "CustomerID",
    "Locations": "LocationID",
    "Receipts": "ReceiptID",
    "Admins": "AdminID",
}


def _json_response(payload: Any, status: int = 200):
    """Return a JSON response with the same behavior as legacy endpoints (arrays/dicts)."""
    resp = make_response(jsonify(payload), status)
    resp.headers["Content-Type"] = "application/json"
    return resp


def _fetchall_dict(cur) -> List[Dict[str, Any]]:
    """Fetch all rows from cursor as list of dicts."""
    row_headers = [x[0] for x in cur.description]
    return [dict(zip(row_headers, row)) for row in cur.fetchall()]


def _get_payload() -> Dict[str, Any]:
    """Merge query params and JSON body (JSON overrides query args)."""
    payload: Dict[str, Any] = dict(request.args) if request.args else {}
    body = request.get_json(silent=True) or {}
    if isinstance(body, dict):
        payload.update(body)
    return payload


def _normalize_value(val: Any) -> Any:
    """Convert legacy 'None' string / blanks into Python None."""
    if val is None:
        return None
    if isinstance(val, str):
        v = val.strip()
        if v == "" or v.lower() == "none" or v.lower() == "null":
            return None
        return val
    return val


def _get_columns(table: str) -> List[str]:
    """Get column names for a whitelisted table."""
    if table not in _ALLOWED_TABLES:
        raise ValueError("Invalid table")
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute(f"SHOW COLUMNS FROM {table}")  # table is whitelisted
    return [row[0] for row in cur.fetchall()]


def _get_int_arg(name: str, default: Optional[int] = None) -> Optional[int]:
    v = request.args.get(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


@rest_api.route("/", methods=["GET"])
def apiDefault():
    return _json_response([{"Name": "Aquarian REST API", "Version": "0.2", "Created": "08/02/2020", "LastModified": "2026/04/09"}])


# Jobs
@rest_api.route("/jobs/", methods=["GET"])
@rest_api.route("/jobs", methods=["GET", "POST"])
def returnJobs():
    if request.method == "GET":
        limit1 = request.args.get("limit1")
        limit2 = request.args.get("limit2")
        if limit1 is not None and limit2 is not None:
            return getTable("Jobs", limit1, limit2)
        return getAllTable("Jobs")
    return createRecord("Jobs")


@rest_api.route("/jobs/<int:id>/", methods=["GET"])
@rest_api.route("/jobs/<int:id>", methods=["GET", "PUT", "DELETE"])
def get_job(id: int):
    if request.method == "GET":
        return getRecord("Jobs", "JobID", id)
    if request.method == "PUT":
        return updateTable("Jobs", "JobID", id)
    return deleteRecord("Jobs", "JobID", id)


@rest_api.route("/jobs/pending", methods=["GET"])
def returnPendingJobs():
    return _get_jobs_by_status("Pending")


@rest_api.route("/jobs/delivered", methods=["GET"])
def returnDoneJobs():
    return _get_jobs_by_status("Delivered")


def _get_jobs_by_status(status: str):
    limit1 = _get_int_arg("limit1")
    limit2 = _get_int_arg("limit2")
    conn = mysql.connection
    cur = conn.cursor()

    if limit1 is not None and limit2 is not None:
        cur.execute("SELECT * FROM Jobs WHERE Status=%s LIMIT %s OFFSET %s", (status, limit1, limit2))
    else:
        cur.execute("SELECT * FROM Jobs WHERE Status=%s", (status,))
    return _json_response(_fetchall_dict(cur))


@rest_api.route("/jobs/<string:id>/location", methods=["GET", "PUT"])
def getParcelLocation(id: str):
    if request.method == "PUT":
        # Legacy behavior: allow update Job location-related fields via updateTable.
        # Kept for compatibility even if clients don't use it.
        return updateTable("Jobs", "TrackingID", id)

    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT DriverID FROM Jobs WHERE TrackingID=%s", (id,))
    if cur.rowcount == 0:
        return _json_response([{"Error": "No matching ID found in database."}], 404)

    driver_id = cur.fetchone()[0]
    cur.execute("SELECT DriverID, FirstName, Location FROM Drivers WHERE DriverID=%s", (driver_id,))
    if cur.rowcount == 0:
        return _json_response([{"Error": "No matching ID found in database."}], 404)
    return _json_response(_fetchall_dict(cur))


# Drivers
@rest_api.route("/drivers/", methods=["GET"])
@rest_api.route("/drivers", methods=["GET", "POST"])
def returnDrivers():
    if request.method == "GET":
        limit1 = _get_int_arg("limit1")
        limit2 = _get_int_arg("limit2")
        conn = mysql.connection
        cur = conn.cursor()

        # Keep original field subset for GET
        base_sql = """
            SELECT DriverID, VehicleID, Username, LastName, FirstName, DOB, NINo, DrivingLicenseNo,
                   DrivingLicensePic, Address1, Address2, City, PostCode, Country, Location,
                   DateCreated, LastConnected
            FROM Drivers
        """
        if limit1 is not None and limit2 is not None:
            cur.execute(base_sql + " LIMIT %s OFFSET %s", (limit1, limit2))
        else:
            cur.execute(base_sql)
        return _json_response(_fetchall_dict(cur))

    # POST: preserve legacy behavior (auto-username + default password), but parameterize.
    try:
        payload = _get_payload()
        first = payload.get("FirstName", "") or ""
        last = payload.get("LastName", "") or ""
        conn = mysql.connection
        cur = conn.cursor()

        # Generate unique username
        uname_base = f"{first}{last}".replace(" ", "")
        uname = uname_base if uname_base else "driver"
        suffix = 1
        while True:
            cur.execute("SELECT 1 FROM Drivers WHERE Username=%s", (uname,))
            if cur.rowcount == 0:
                break
            uname = f"{uname_base}{suffix}" if uname_base else f"driver{suffix}"
            suffix += 1

        cols = _get_columns("Drivers")
        id_col = _ALLOWED_TABLES["Drivers"]
        insert_cols = [c for c in cols if c != id_col]

        values: List[Any] = []
        for c in insert_cols:
            if c == "DateCreated":
                # Use NOW() in SQL
                values.append("__NOW__")
            elif c == "Username":
                values.append(uname)
            elif c == "Password":
                values.append(payload.get("Password") or "Aquarian")
            else:
                values.append(_normalize_value(payload.get(c)))

        # Build SQL with NOW() literals where needed.
        placeholders: List[str] = []
        params: List[Any] = []
        for v in values:
            if v == "__NOW__":
                placeholders.append("NOW()")
            else:
                placeholders.append("%s")
                params.append(v)

        sql = f"INSERT INTO Drivers ({','.join(insert_cols)}) VALUES ({','.join(placeholders)})"
        cur.execute(sql, tuple(params))
        conn.commit()
        return _json_response([{"Success": "Record added to table Drivers successfully!"}], 200)
    except Exception as e:
        return _json_response({"Error": str(e)}, 500)


@rest_api.route("/drivers/<int:id>/", methods=["GET"])
@rest_api.route("/drivers/<int:id>", methods=["GET", "PUT", "DELETE"])
def get_driver(id: int):
    if request.method == "GET":
        conn = mysql.connection
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DriverID, VehicleID, LastName, FirstName, DOB, NINo, DrivingLicenseNo, DrivingLicensePic,
                   Address1, Address2, City, PostCode, Country, Location, DateCreated, LastConnected
            FROM Drivers WHERE DriverID=%s
            """,
            (id,),
        )
        if cur.rowcount == 0:
            return _json_response([{"Error": "No matching ID found in database."}], 404)
        return _json_response(_fetchall_dict(cur))
    if request.method == "PUT":
        return updateTable("Drivers", "DriverID", id)
    return deleteRecord("Drivers", "DriverID", id)


@rest_api.route("/drivers/<int:id>/location", methods=["GET", "PUT"])
def getLocation(id: int):
    if request.method == "GET":
        conn = mysql.connection
        cur = conn.cursor()
        cur.execute("SELECT DriverID, FirstName, Location FROM Drivers WHERE DriverID=%s", (id,))
        if cur.rowcount == 0:
            return _json_response([{"Error": "No matching ID found in database."}], 404)
        return _json_response(_fetchall_dict(cur))
    return updateTable("Drivers", "DriverID", id)


# Driver Login (Android App)
@rest_api.route("/drivers/login", methods=["POST"])
def driver_login():
    payload = _get_payload()
    username = payload.get("Username")
    password = payload.get("Password")
    if not username or not password:
        return _json_response([{"Status": "Error", "Message": "Login failed: Missing credentials"}], 200)

    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT DriverID, FirstName, Password, LastConnected, VehicleID FROM Drivers WHERE Username=%s", (username,))
    if cur.rowcount == 0:
        return _json_response([{"Status": "Error", "Message": "Login failed: Wrong Username"}], 200)

    row = cur.fetchone()
    if password != row[2]:
        return _json_response([{"Status": "Error", "Message": "Login failed: Wrong Password"}], 200)

    cur.execute("UPDATE Drivers SET LastConnected=NOW() WHERE Username=%s", (username,))
    conn.commit()
    return _json_response(
        [
            {
                "Status": "Success",
                "Message": "Login Succesful",
                "DriverID": row[0],
                "FirstName": row[1],
                "LastConnected": row[3],
                "VehicleID": row[4],
            }
        ],
        200,
    )


# Vehicles
@rest_api.route("/vehicles/", methods=["GET"])
@rest_api.route("/vehicles", methods=["GET", "POST"])
def returnVehicles():
    if request.method == "GET":
        limit1 = request.args.get("limit1")
        limit2 = request.args.get("limit2")
        if limit1 is not None and limit2 is not None:
            return getTable("Vehicles", limit1, limit2)
        return getAllTable("Vehicles")
    return createRecord("Vehicles")


@rest_api.route("/vehicles/<int:id>/", methods=["GET"])
@rest_api.route("/vehicles/<int:id>", methods=["GET", "PUT", "DELETE"])
def get_vehicle(id: int):
    if request.method == "GET":
        return getRecord("Vehicles", "VehicleID", id)
    if request.method == "PUT":
        return updateTable("Vehicles", "VehicleID", id)
    return deleteRecord("Vehicles", "VehicleID", id)


# Customers
@rest_api.route("/customers/", methods=["GET"])
@rest_api.route("/customers", methods=["GET", "POST"])
def returnCustomers():
    if request.method == "GET":
        limit1 = request.args.get("limit1")
        limit2 = request.args.get("limit2")
        if limit1 is not None and limit2 is not None:
            return getTable("Customers", limit1, limit2)
        return getAllTable("Customers")
    return createRecord("Customers")


@rest_api.route("/customers/<int:id>/", methods=["GET"])
@rest_api.route("/customers/<int:id>", methods=["GET", "PUT", "DELETE"])
def get_customer(id: int):
    if request.method == "GET":
        return getRecord("Customers", "CustomerID", id)
    if request.method == "PUT":
        return updateTable("Customers", "CustomerID", id)
    return deleteRecord("Customers", "CustomerID", id)


# Pick-Up and Drop-Off Locations
@rest_api.route("/locations/", methods=["GET"])
@rest_api.route("/locations", methods=["GET", "POST"])
def returnLocations():
    if request.method == "GET":
        limit1 = request.args.get("limit1")
        limit2 = request.args.get("limit2")
        if limit1 is not None and limit2 is not None:
            return getTable("Locations", limit1, limit2)
        return getAllTable("Locations")
    # NOTE: legacy code used wrong idname; fixed to LocationID.
    return createRecord("Locations")


@rest_api.route("/locations/<int:id>/", methods=["GET"])
@rest_api.route("/locations/<int:id>", methods=["GET", "PUT", "DELETE"])
def get_location(id: int):
    if request.method == "GET":
        return getRecord("Locations", "LocationID", id)
    if request.method == "PUT":
        return updateTable("Locations", "LocationID", id)
    return deleteRecord("Locations", "LocationID", id)


# Receipts
@rest_api.route("/receipts/", methods=["GET"])
@rest_api.route("/receipts", methods=["GET", "POST"])
def returnReceipts():
    if request.method == "GET":
        limit1 = request.args.get("limit1")
        limit2 = request.args.get("limit2")
        if limit1 is not None and limit2 is not None:
            return getTable("Receipts", limit1, limit2)
        return getAllTable("Receipts")
    return createRecord("Receipts")


@rest_api.route("/receipts/<int:id>/", methods=["GET"])
@rest_api.route("/receipts/<int:id>", methods=["GET", "PUT", "DELETE"])
def get_receipt(id: int):
    if request.method == "GET":
        return getRecord("Receipts", "ReceiptID", id)
    if request.method == "PUT":
        return updateTable("Receipts", "ReceiptID", id)
    return deleteRecord("Receipts", "ReceiptID", id)


@rest_api.route("/receipts/driver/<int:id>/", methods=["GET"])
@rest_api.route("/receipts/driver/<int:id>", methods=["GET"])
def get_receipt_by_driver(id: int):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT * FROM Receipts WHERE DriverID=%s AND DATE(DateCreated)=DATE(NOW())", (id,))
    return _json_response(_fetchall_dict(cur))


# FULL JOB
def _full_job_data(job_id: int) -> Dict[str, Any]:
    """Build the legacy 'full job' response object without making HTTP calls."""
    conn = mysql.connection
    cur = conn.cursor()

    cur.execute(
        """
        SELECT JobID, TrackingID, Status, ParcelType, ParcelSize, ParcelWeight, DateCreated, DateDue,
               DateDelivered, DistanceTravelled, Picture1, Picture2, Comments
        FROM Jobs WHERE JobID=%s
        """,
        (job_id,),
    )
    job_rows = _fetchall_dict(cur)
    if not job_rows:
        return {"Error": "No matching ID was found in the database."}

    # IDs required for linked records
    cur.execute("SELECT CustomerID, PickupID, DropOffID FROM Jobs WHERE JobID=%s", (job_id,))
    ids = cur.fetchone()
    customer_id, pickup_id, dropoff_id = ids[0], ids[1], ids[2]

    customer_rows: List[Dict[str, Any]] = []
    pickup_rows: List[Dict[str, Any]] = []
    dropoff_rows: List[Dict[str, Any]] = []

    if customer_id is not None:
        cur.execute("SELECT * FROM Customers WHERE CustomerID=%s", (customer_id,))
        customer_rows = _fetchall_dict(cur)

    if pickup_id is not None:
        cur.execute("SELECT * FROM Locations WHERE LocationID=%s", (pickup_id,))
        pickup_rows = _fetchall_dict(cur)

    if dropoff_id is not None:
        cur.execute("SELECT * FROM Locations WHERE LocationID=%s", (dropoff_id,))
        dropoff_rows = _fetchall_dict(cur)

    return {"Job": job_rows, "Customer": customer_rows, "Pickup": pickup_rows, "Dropoff": dropoff_rows}


@rest_api.route("/jobs/full/<int:id>/", methods=["GET"])
@rest_api.route("/jobs/full/<int:id>", methods=["GET"])
def get_full_job(id: int):
    data = _full_job_data(id)
    if "Error" in data:
        return _json_response(data, 404)
    return _json_response(data)


@rest_api.route("/drivers/assigned/<int:id>/", methods=["GET"])
@rest_api.route("/drivers/assigned/<int:id>", methods=["GET"])
def getAssignedJobs(id: int):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT JobID FROM Jobs WHERE Status=%s AND DriverID=%s", ("Pending", id))
    job_ids = [row[0] for row in cur.fetchall()]
    if not job_ids:
        return _json_response({"Error": "No jobs found."}, 200)

    full_array: List[Dict[str, Any]] = []
    for job_id in job_ids:
        full_array.append(_full_job_data(int(job_id)))
    return _json_response(full_array)


# Admin Login (API)
@rest_api.route("/admin", methods=["POST"])
def admin_login():
    return login("Admins")


# GET helpers
def getAllTable(table: str):
    if table not in _ALLOWED_TABLES:
        return _json_response([{"Error": "Invalid table."}], 400)

    conn = mysql.connection
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table}")  # table is whitelisted
    return _json_response(_fetchall_dict(cur))


def getTable(table: str, limit1: str, limit2: str):
    if table not in _ALLOWED_TABLES:
        return _json_response([{"Error": "Invalid table."}], 400)

    try:
        l1 = int(limit1)
        l2 = int(limit2)
    except ValueError:
        return _json_response([{"Error": "Invalid pagination parameters."}], 400)

    conn = mysql.connection
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} LIMIT %s OFFSET %s", (l1, l2))  # table is whitelisted
    return _json_response(_fetchall_dict(cur))


def getRecord(table: str, idname: str, id_value: Any):
    if table not in _ALLOWED_TABLES:
        return _json_response([{"Error": "Invalid table."}], 400)

    conn = mysql.connection
    cur = conn.cursor()
    # idname is controlled by server code per route
    cur.execute(f"SELECT * FROM {table} WHERE {idname}=%s", (id_value,))
    if cur.rowcount == 0:
        return _json_response([{"Error": "No matching ID found in database."}], 404)
    return _json_response(_fetchall_dict(cur))


def deleteRecord(table: str, idname: str, id_value: Any):
    if table not in _ALLOWED_TABLES:
        return _json_response([{"Error": "Invalid table."}], 400)

    conn = mysql.connection
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE {idname}=%s", (id_value,))
    conn.commit()
    return _json_response([{"Status": f"One row with id {id_value} deleted from {table}"}], 200)


def createRecord(table: str):
    if table not in _ALLOWED_TABLES:
        return _json_response([{"Error": "Invalid table."}], 400)

    try:
        payload = _get_payload()
        conn = mysql.connection
        cur = conn.cursor()

        cols = _get_columns(table)
        id_col = _ALLOWED_TABLES[table]
        insert_cols = [c for c in cols if c != id_col]

        values: List[Any] = []
        for c in insert_cols:
            if c == "DateCreated":
                values.append("__NOW__")
            else:
                values.append(_normalize_value(payload.get(c)))

        placeholders: List[str] = []
        params: List[Any] = []
        for v in values:
            if v == "__NOW__":
                placeholders.append("NOW()")
            else:
                placeholders.append("%s")
                params.append(v)

        sql = f"INSERT INTO {table} ({','.join(insert_cols)}) VALUES ({','.join(placeholders)})"
        cur.execute(sql, tuple(params))
        conn.commit()

        # Preserve legacy tracking ID generation for Jobs.
        if table == "Jobs":
            current_date = datetime.date.today()
            trackid = "AQ" + current_date.strftime("%m%y") + str(cur.lastrowid)
            cur.execute("UPDATE Jobs SET TrackingID=%s WHERE JobID=%s", (trackid, cur.lastrowid))
            conn.commit()

        return _json_response([{"Success": f"Record added to table {table} successfully!"}], 200)
    except Exception as e:
        return _json_response({"Error": str(e)}, 500)


def updateTable(table: str, idname: str, id_value: Any):
    if table not in _ALLOWED_TABLES:
        return _json_response([{"Error": "Invalid table."}], 400)

    try:
        payload = _get_payload()
        conn = mysql.connection
        cur = conn.cursor()

        # Fetch current row to preserve legacy behavior (missing fields keep existing values).
        cur.execute(f"SELECT * FROM {table} WHERE {idname}=%s", (id_value,))
        if cur.rowcount == 0:
            return _json_response([{"Error": "No matching ID found in database."}], 404)

        row_headers = [x[0] for x in cur.description]
        current_row = dict(zip(row_headers, cur.fetchone()))

        cols = _get_columns(table)
        id_col = _ALLOWED_TABLES[table]
        update_cols = [c for c in cols if c != id_col]

        set_parts: List[str] = []
        params: List[Any] = []

        for c in update_cols:
            new_val = payload.get(c, current_row.get(c))
            new_val = _normalize_value(new_val)
            set_parts.append(f"{c}=%s")
            params.append(new_val)

        params.append(id_value)
        sql = f"UPDATE {table} SET {','.join(set_parts)} WHERE {idname}=%s"
        cur.execute(sql, tuple(params))
        conn.commit()
        return _json_response([{"Success": f"Table {table} edited successfully!"}], 200)
    except Exception as e:
        return _json_response({"Error": str(e)}, 500)


def login(table: str):
    if table not in _ALLOWED_TABLES:
        return _json_response([{"Status": "Error", "Message": "Invalid table"}], 400)

    payload = _get_payload()
    username = payload.get("Username")
    password = payload.get("Password")
    if not username or not password:
        return _json_response([{"Status": "Error", "Message": "Login failed: Missing credentials"}], 200)

    conn = mysql.connection
    cur = conn.cursor()
    cur.execute(f"SELECT Password FROM {table} WHERE Username=%s", (username,))
    if cur.rowcount == 0:
        return _json_response([{"Status": "Error", "Message": "Login failed: Wrong Username"}], 200)

    stored_password = cur.fetchone()[0]
    if password != stored_password:
        return _json_response([{"Status": "Error", "Message": "Login failed: Wrong Password"}], 200)

    cur.execute(f"UPDATE {table} SET LastConnected=NOW() WHERE Username=%s", (username,))
    conn.commit()
    return _json_response([{"Status": "Success", "Message": "Login Succesful", "Username": username}], 200)


# Dashboard: monthly revenue and receipts
@rest_api.route("/money", methods=["GET"])
def getMoney():
    current_date = datetime.date.today()
    current_month = current_date.month + 1

    out: List[Dict[str, Any]] = []
    for month in range(1, current_month):
        amount = monthRevenue(month)
        receipt = monthReceipts(month)
        out.append(
            {
                "Month": calendar.month_name[month],
                "Amount": round(float(amount), 2) if amount is not None else None,
                "Receipts": round(float(receipt), 2) if receipt is not None else None,
            }
        )
    return _json_response(out, 200)


def monthRevenue(month: int) -> Optional[float]:
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT SUM(PricePaid) FROM Jobs WHERE MONTH(DateDelivered)=%s", (month,))
    result = cur.fetchone()
    return result[0] if result else None


def monthReceipts(month: int) -> Optional[float]:
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("SELECT SUM(Amount) FROM Receipts WHERE MONTH(DateCreated)=%s", (month,))
    result = cur.fetchone()
    return result[0] if result else None


# File uploads (receipts and parcel pictures)
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _unique_filename(folder: str, filename: str) -> str:
    """Avoid overwriting existing files by adding a numeric suffix."""
    base, ext = os.path.splitext(filename)
    candidate = filename
    i = 1
    while os.path.exists(os.path.join(folder, candidate)):
        candidate = f"{base}-{i}{ext}"
        i += 1
    return candidate


@rest_api.route("/receipts/uploads/", methods=["POST"])
@rest_api.route("/receipts/uploads", methods=["POST"])
def upload_file():
    # Android app expects: JSON array with object containing Message.
    if "file" not in request.files:
        return _json_response([{"Message": "ERROR - No file present."}], 200)

    file = request.files["file"]
    if not file or file.filename == "":
        return _json_response([{"Message": "ERROR - No filename"}], 200)

    if not allowed_file(file.filename):
        return _json_response([{"Message": "ERROR - File type not allowed."}], 200)

    upload_folder = app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        return _json_response([{"Message": "ERROR - Upload folder not configured."}], 500)

    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    filename = _unique_filename(upload_folder, filename)
    abs_path = os.path.join(upload_folder, filename)
    file.save(abs_path)

    # Predictable URL (keeps existing android/admin convention)
    file_url = f"/admin/static/images/receipts/{filename}"
    return _json_response([{"Message": "File uploaded successfully.", "FileURL": file_url, "Filename": filename}], 200)


# 404 Error Handler inside /api blueprint
@rest_api.route("/<path:invalid_path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def missing_resource(invalid_path: str):
    return _json_response([{"Error": "Not Found"}], 404)
