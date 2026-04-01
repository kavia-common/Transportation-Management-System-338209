-- Transportation Management System - MySQL Schema (Reproducible DDL)
--
-- Purpose:
--   Provide a reproducible schema that matches the expectations of the existing Flask REST API
--   (API/RestAPI.py) and Admin Panel (AdminPanel/AdminPanel.py).
--
-- How to apply:
--   mysql -h <host> -u <user> -p <database> < schema.mysql.sql
--
-- Notes:
--   - Uses InnoDB for FK support.
--   - Uses utf8mb4 for full Unicode support.
--   - Keeps column names aligned with code expectations (case-sensitive in MySQL on some systems).
--   - Defaults allow existing INSERT logic to omit some fields (API builds SQL dynamically).
--
-- Entities covered:
--   Admins, Drivers, Vehicles, Customers, Locations, Jobs, Receipts

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- Recommended to keep strict mode enabled in production; schema is compatible.
-- SET sql_mode = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -------------------------
-- Admins
-- -------------------------
CREATE TABLE IF NOT EXISTS Admins (
  AdminID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  Username VARCHAR(100) NOT NULL,
  Password VARCHAR(255) NOT NULL,
  DateCreated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  LastConnected DATETIME NULL,
  PRIMARY KEY (AdminID),
  UNIQUE KEY uq_admins_username (Username),
  KEY idx_admins_lastconnected (LastConnected)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- Vehicles
-- -------------------------
CREATE TABLE IF NOT EXISTS Vehicles (
  VehicleID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  VehicleReg VARCHAR(32) NULL,
  Make VARCHAR(64) NULL,
  Model VARCHAR(64) NULL,
  Colour VARCHAR(32) NULL,
  FuelType VARCHAR(32) NULL,
  MOTDate DATE NULL,
  InsuranceDate DATE NULL,
  TaxDate DATE NULL,
  Notes TEXT NULL,
  DateCreated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (VehicleID),
  UNIQUE KEY uq_vehicles_reg (VehicleReg),
  KEY idx_vehicles_datecreated (DateCreated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- Drivers
-- -------------------------
CREATE TABLE IF NOT EXISTS Drivers (
  DriverID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  VehicleID INT UNSIGNED NULL,
  Username VARCHAR(100) NOT NULL,
  Password VARCHAR(255) NOT NULL,
  LastName VARCHAR(100) NULL,
  FirstName VARCHAR(100) NULL,
  DOB DATE NULL,
  NINo VARCHAR(32) NULL,
  DrivingLicenseNo VARCHAR(64) NULL,
  DrivingLicensePic VARCHAR(255) NULL,
  Address1 VARCHAR(255) NULL,
  Address2 VARCHAR(255) NULL,
  City VARCHAR(100) NULL,
  PostCode VARCHAR(32) NULL,
  Country VARCHAR(100) NULL,
  Location VARCHAR(255) NULL,
  DateCreated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  LastConnected DATETIME NULL,
  PRIMARY KEY (DriverID),
  UNIQUE KEY uq_drivers_username (Username),
  KEY idx_drivers_vehicleid (VehicleID),
  KEY idx_drivers_lastconnected (LastConnected),
  CONSTRAINT fk_drivers_vehicle
    FOREIGN KEY (VehicleID) REFERENCES Vehicles(VehicleID)
    ON UPDATE CASCADE
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- Customers
-- -------------------------
CREATE TABLE IF NOT EXISTS Customers (
  CustomerID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  FirstName VARCHAR(100) NULL,
  LastName VARCHAR(100) NULL,
  Email VARCHAR(255) NULL,
  Phone VARCHAR(50) NULL,
  Company VARCHAR(255) NULL,
  Address1 VARCHAR(255) NULL,
  Address2 VARCHAR(255) NULL,
  City VARCHAR(100) NULL,
  PostCode VARCHAR(32) NULL,
  Country VARCHAR(100) NULL,
  DateCreated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (CustomerID),
  KEY idx_customers_email (Email),
  KEY idx_customers_datecreated (DateCreated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- Locations
-- -------------------------
CREATE TABLE IF NOT EXISTS Locations (
  LocationID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  CustomerID INT UNSIGNED NULL,
  LocationName VARCHAR(255) NULL,
  Address1 VARCHAR(255) NULL,
  Address2 VARCHAR(255) NULL,
  City VARCHAR(100) NULL,
  PostCode VARCHAR(32) NULL,
  Country VARCHAR(100) NULL,
  Latitude DECIMAL(10,7) NULL,
  Longitude DECIMAL(10,7) NULL,
  Notes TEXT NULL,
  DateCreated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (LocationID),
  KEY idx_locations_customerid (CustomerID),
  KEY idx_locations_city (City),
  CONSTRAINT fk_locations_customer
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
    ON UPDATE CASCADE
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- Jobs
-- -------------------------
CREATE TABLE IF NOT EXISTS Jobs (
  JobID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  CustomerID INT UNSIGNED NULL,
  DriverID INT UNSIGNED NULL,
  PickupID INT UNSIGNED NULL,
  DropOffID INT UNSIGNED NULL,

  TrackingID VARCHAR(64) NULL,
  Status VARCHAR(32) NOT NULL DEFAULT 'Pending',

  ParcelType VARCHAR(64) NULL,
  ParcelSize VARCHAR(64) NULL,
  ParcelWeight VARCHAR(64) NULL,

  -- Financials
  PricePaid DECIMAL(10,2) NULL,

  -- Dates
  DateCreated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  DateDue DATETIME NULL,
  DateDelivered DATETIME NULL,

  -- Delivery evidence / metadata
  DistanceTravelled DECIMAL(10,2) NULL,
  Picture1 VARCHAR(255) NULL,
  Picture2 VARCHAR(255) NULL,
  Comments TEXT NULL,

  PRIMARY KEY (JobID),
  UNIQUE KEY uq_jobs_trackingid (TrackingID),

  KEY idx_jobs_status (Status),
  KEY idx_jobs_driver_status (DriverID, Status),
  KEY idx_jobs_customerid (CustomerID),
  KEY idx_jobs_dates (DateCreated, DateDue, DateDelivered),

  CONSTRAINT fk_jobs_customer
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT fk_jobs_driver
    FOREIGN KEY (DriverID) REFERENCES Drivers(DriverID)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT fk_jobs_pickup
    FOREIGN KEY (PickupID) REFERENCES Locations(LocationID)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT fk_jobs_dropoff
    FOREIGN KEY (DropOffID) REFERENCES Locations(LocationID)
    ON UPDATE CASCADE
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------
-- Receipts
-- -------------------------
CREATE TABLE IF NOT EXISTS Receipts (
  ReceiptID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  DriverID INT UNSIGNED NULL,

  -- Business info
  Type VARCHAR(64) NULL,
  Amount DECIMAL(10,2) NULL,

  -- Optional link to a job (not currently required by API, but useful)
  JobID INT UNSIGNED NULL,

  -- Stored filename for uploaded receipt image/pdf
  FileName VARCHAR(255) NULL,

  DateCreated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (ReceiptID),
  KEY idx_receipts_driver_date (DriverID, DateCreated),
  KEY idx_receipts_jobid (JobID),

  CONSTRAINT fk_receipts_driver
    FOREIGN KEY (DriverID) REFERENCES Drivers(DriverID)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT fk_receipts_job
    FOREIGN KEY (JobID) REFERENCES Jobs(JobID)
    ON UPDATE CASCADE
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
