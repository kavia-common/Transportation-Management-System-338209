import argparse
import logging
import os
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, redirect
from werkzeug.middleware.proxy_fix import ProxyFix

from AdminPanel.AdminPanel import admin_panel
from API.RestAPI import rest_api
from Website.LandingPage import landing
from extensions import mysql

logger = logging.getLogger(__name__)


def _truthy_env(name: str, default: bool = False) -> bool:
    """Parse a boolean-ish environment variable value."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")


# PUBLIC_INTERFACE
def create_app() -> Flask:
    """Create and configure the Flask application.

    The app serves:
    - Customer site under /home
    - REST API under /api
    - Admin panel under /admin

    Configuration is environment-driven (no hard-coded secrets/DB creds), and
    the database schema is initialized idempotently at startup when possible.
    """
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

    app = Flask(__name__)

    # Secret key MUST come from environment (or a safe ephemeral default for preview).
    # In production, set FLASK_SECRET_KEY.
    app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

    # Trust proxy headers in the preview environment (optional).
    if _truthy_env("TRUST_PROXY", default=True):
        # x_for=1, x_proto=1 are typical when behind a reverse proxy.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # MySQL config (do not hardcode credentials).
    # Request these env vars from user/orchestrator if not already set:
    # MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT (optional)
    app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "127.0.0.1")
    app.config["MYSQL_USER"] = os.getenv("MYSQL_USER", "")
    app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD", "")
    app.config["MYSQL_DB"] = os.getenv("MYSQL_DB", "")
    if os.getenv("MYSQL_PORT"):
        try:
            app.config["MYSQL_PORT"] = int(os.getenv("MYSQL_PORT", "3306"))
        except ValueError:
            logger.warning("Invalid MYSQL_PORT; ignoring.")

    # Uploads: keep receipts under AdminPanel static so the existing URLs used by Android/admin work:
    # /admin/static/images/receipts/<filename>
    app_root = Path(__file__).resolve().parent
    upload_folder = app_root / "AdminPanel" / "static" / "images" / "receipts"
    upload_folder.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_folder)

    # Optional: cap upload size (defaults to 10MB).
    max_upload_mb = os.getenv("MAX_UPLOAD_MB", "10")
    try:
        app.config["MAX_CONTENT_LENGTH"] = int(max_upload_mb) * 1024 * 1024
    except ValueError:
        app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    mysql.init_app(app)

    # Register blueprints
    app.register_blueprint(landing, url_prefix="/home")
    app.register_blueprint(rest_api, url_prefix="/api")
    app.register_blueprint(admin_panel, url_prefix="/admin")

    @app.get("/")
    def root_redirect():
        """Redirect root to the customer website."""
        return redirect("/home", code=301)

    @app.get("/healthz")
    def healthz():
        """Health check endpoint used by the preview environment."""
        return jsonify({"status": "ok"})

    # Initialize schema at startup (best-effort).
    with app.app_context():
        try:
            _init_schema_and_seed()
        except Exception as e:
            # Do not prevent app start if DB isn't reachable; API will error clearly on use.
            logger.exception("Database schema initialization failed: %s", e)

    return app


def _exec(cur, sql: str, params: Optional[tuple] = None) -> None:
    """Execute SQL with optional parameters."""
    if params is None:
        cur.execute(sql)
    else:
        cur.execute(sql, params)


def _init_schema_and_seed() -> None:
    """Create core tables if missing and insert minimal seed data (idempotent)."""
    conn = mysql.connection
    cur = conn.cursor()

    # Core tables (minimal columns required by the existing API/admin/android clients).
    _exec(
        cur,
        """
        CREATE TABLE IF NOT EXISTS Admins (
            AdminID INT AUTO_INCREMENT PRIMARY KEY,
            Username VARCHAR(64) NOT NULL UNIQUE,
            Password VARCHAR(255) NOT NULL,
            DateCreated DATETIME NULL,
            LastConnected DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _exec(
        cur,
        """
        CREATE TABLE IF NOT EXISTS Vehicles (
            VehicleID INT AUTO_INCREMENT PRIMARY KEY,
            RegNo VARCHAR(32) NULL,
            Make VARCHAR(64) NULL,
            Model VARCHAR(64) NULL,
            MOTDate DATETIME NULL,
            TaxDate DATETIME NULL,
            InsuranceDate DATETIME NULL,
            Mileage INT NULL,
            DateCreated DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _exec(
        cur,
        """
        CREATE TABLE IF NOT EXISTS Drivers (
            DriverID INT AUTO_INCREMENT PRIMARY KEY,
            VehicleID INT NULL,
            Username VARCHAR(128) NULL UNIQUE,
            Password VARCHAR(255) NULL,
            LastName VARCHAR(128) NULL,
            FirstName VARCHAR(128) NULL,
            DOB VARCHAR(32) NULL,
            NINo VARCHAR(64) NULL,
            DrivingLicenseNo VARCHAR(64) NULL,
            DrivingLicensePic VARCHAR(255) NULL,
            Address1 VARCHAR(255) NULL,
            Address2 VARCHAR(255) NULL,
            City VARCHAR(128) NULL,
            PostCode VARCHAR(32) NULL,
            Country VARCHAR(128) NULL,
            Location VARCHAR(64) NULL,
            DateCreated DATETIME NULL,
            LastConnected DATETIME NULL,
            CONSTRAINT fk_drivers_vehicle FOREIGN KEY (VehicleID) REFERENCES Vehicles(VehicleID)
                ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _exec(
        cur,
        """
        CREATE TABLE IF NOT EXISTS Customers (
            CustomerID INT AUTO_INCREMENT PRIMARY KEY,
            LastName VARCHAR(128) NULL,
            FirstName VARCHAR(128) NULL,
            Email VARCHAR(255) NULL,
            Phone VARCHAR(64) NULL,
            Address1 VARCHAR(255) NULL,
            Address2 VARCHAR(255) NULL,
            City VARCHAR(128) NULL,
            PostCode VARCHAR(32) NULL,
            Country VARCHAR(128) NULL,
            DateCreated DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _exec(
        cur,
        """
        CREATE TABLE IF NOT EXISTS Locations (
            LocationID INT AUTO_INCREMENT PRIMARY KEY,
            CustomerID INT NULL,
            Address1 VARCHAR(255) NULL,
            Address2 VARCHAR(255) NULL,
            City VARCHAR(128) NULL,
            PostCode VARCHAR(32) NULL,
            Country VARCHAR(128) NULL,
            Latitude DECIMAL(10,7) NULL,
            Longitude DECIMAL(10,7) NULL,
            DateCreated DATETIME NULL,
            CONSTRAINT fk_locations_customer FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
                ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _exec(
        cur,
        """
        CREATE TABLE IF NOT EXISTS Jobs (
            JobID INT AUTO_INCREMENT PRIMARY KEY,
            CustomerID INT NULL,
            DriverID INT NULL,
            PickupID INT NULL,
            DropOffID INT NULL,
            TrackingID VARCHAR(64) NULL UNIQUE,
            Status VARCHAR(32) NULL,
            ParcelType VARCHAR(64) NULL,
            ParcelSize VARCHAR(64) NULL,
            ParcelWeight VARCHAR(64) NULL,
            PricePaid DECIMAL(10,2) NULL,
            DateCreated DATETIME NULL,
            DateDue DATETIME NULL,
            DateDelivered DATETIME NULL,
            DistanceTravelled DECIMAL(10,2) NULL,
            Picture1 VARCHAR(255) NULL,
            Picture2 VARCHAR(255) NULL,
            Comments TEXT NULL,
            CONSTRAINT fk_jobs_customer FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
                ON DELETE SET NULL ON UPDATE CASCADE,
            CONSTRAINT fk_jobs_driver FOREIGN KEY (DriverID) REFERENCES Drivers(DriverID)
                ON DELETE SET NULL ON UPDATE CASCADE,
            CONSTRAINT fk_jobs_pickup FOREIGN KEY (PickupID) REFERENCES Locations(LocationID)
                ON DELETE SET NULL ON UPDATE CASCADE,
            CONSTRAINT fk_jobs_dropoff FOREIGN KEY (DropOffID) REFERENCES Locations(LocationID)
                ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _exec(
        cur,
        """
        CREATE TABLE IF NOT EXISTS Receipts (
            ReceiptID INT AUTO_INCREMENT PRIMARY KEY,
            DriverID INT NULL,
            Amount DECIMAL(10,2) NULL,
            Type VARCHAR(128) NULL,
            Picture VARCHAR(255) NULL,
            DateCreated DATETIME NULL,
            CONSTRAINT fk_receipts_driver FOREIGN KEY (DriverID) REFERENCES Drivers(DriverID)
                ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    conn.commit()

    # Seed data (idempotent)
    _exec(
        cur,
        """
        INSERT INTO Admins (Username, Password, DateCreated)
        SELECT %s, %s, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM Admins WHERE Username=%s)
        """,
        ("admin", "admin", "admin"),
    )

    _exec(
        cur,
        """
        INSERT INTO Vehicles (RegNo, Make, Model, DateCreated)
        SELECT %s, %s, %s, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM Vehicles WHERE RegNo=%s)
        """,
        ("SEED-TRUCK-1", "Ford", "Transit", "SEED-TRUCK-1"),
    )

    _exec(
        cur,
        """
        INSERT INTO Drivers (VehicleID, Username, Password, FirstName, LastName, Location, DateCreated)
        SELECT v.VehicleID, %s, %s, %s, %s, %s, NOW()
        FROM Vehicles v
        WHERE v.RegNo=%s
          AND NOT EXISTS (SELECT 1 FROM Drivers WHERE Username=%s)
        """,
        ("driver", "Aquarian", "Seed", "Driver", "53.479593,-2.223730", "SEED-TRUCK-1", "driver"),
    )

    _exec(
        cur,
        """
        INSERT INTO Customers (FirstName, LastName, Email, DateCreated)
        SELECT %s, %s, %s, NOW()
        WHERE NOT EXISTS (SELECT 1 FROM Customers WHERE Email=%s)
        """,
        ("Seed", "Customer", "seed.customer@example.com", "seed.customer@example.com"),
    )

    # Insert 2 locations and 1 pending job if none exist.
    _exec(cur, "SELECT CustomerID FROM Customers WHERE Email=%s", ("seed.customer@example.com",))
    customer_row = cur.fetchone()
    if customer_row:
        customer_id = customer_row[0]

        _exec(
            cur,
            """
            INSERT INTO Locations (CustomerID, Address1, City, PostCode, Country, Latitude, Longitude, DateCreated)
            SELECT %s, %s, %s, %s, %s, %s, %s, NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM Locations WHERE CustomerID=%s AND Address1=%s
            )
            """,
            (
                customer_id,
                "Seed Pickup Address",
                "Manchester",
                "M1 1AA",
                "UK",
                53.479593,
                -2.223730,
                customer_id,
                "Seed Pickup Address",
            ),
        )

        _exec(
            cur,
            """
            INSERT INTO Locations (CustomerID, Address1, City, PostCode, Country, Latitude, Longitude, DateCreated)
            SELECT %s, %s, %s, %s, %s, %s, %s, NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM Locations WHERE CustomerID=%s AND Address1=%s
            )
            """,
            (
                customer_id,
                "Seed Dropoff Address",
                "Liverpool",
                "L1 1AA",
                "UK",
                53.408371,
                -2.991573,
                customer_id,
                "Seed Dropoff Address",
            ),
        )

        _exec(cur, "SELECT LocationID FROM Locations WHERE CustomerID=%s AND Address1=%s", (customer_id, "Seed Pickup Address"))
        pickup_id = (cur.fetchone() or [None])[0]
        _exec(cur, "SELECT LocationID FROM Locations WHERE CustomerID=%s AND Address1=%s", (customer_id, "Seed Dropoff Address"))
        dropoff_id = (cur.fetchone() or [None])[0]

        _exec(cur, "SELECT DriverID FROM Drivers WHERE Username=%s", ("driver",))
        driver_id = (cur.fetchone() or [None])[0]

        if pickup_id and dropoff_id and driver_id:
            # Only seed a job if there are no jobs at all.
            _exec(cur, "SELECT 1 FROM Jobs LIMIT 1")
            if cur.fetchone() is None:
                _exec(
                    cur,
                    """
                    INSERT INTO Jobs (
                        CustomerID, DriverID, PickupID, DropOffID,
                        TrackingID, Status, ParcelType, ParcelSize, ParcelWeight,
                        PricePaid, DateCreated, DateDue, Comments
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, NOW(), DATE_ADD(NOW(), INTERVAL 2 DAY), %s
                    )
                    """,
                    (
                        customer_id,
                        driver_id,
                        pickup_id,
                        dropoff_id,
                        "AQ-SEED-TRACK-1",
                        "Pending",
                        "Box",
                        "Medium",
                        "2kg",
                        12.50,
                        "Seed job for preview/testing",
                    ),
                )

    conn.commit()


app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transportation Management System (Flask)")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "3001")))
    parser.add_argument("--debug", action="store_true", default=_truthy_env("FLASK_DEBUG", False))
    args = parser.parse_args()

    # IMPORTANT: Bind to provided host/port for preview environment.
    app.run(host=args.host, port=args.port, debug=args.debug)
