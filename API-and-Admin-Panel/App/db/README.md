# Database Setup (MySQL)

This folder contains a **reproducible MySQL schema** that matches the current Flask API/Admin Panel expectations.

## What this schema supports

Tables, keys, and indexes for:

- `Admins`
- `Drivers`
- `Vehicles`
- `Customers`
- `Locations`
- `Jobs`
- `Receipts`

It is aligned to the existing code usage in:

- `API-and-Admin-Panel/App/App/API/RestAPI.py`
- `API-and-Admin-Panel/App/App/AdminPanel/AdminPanel.py`

## Prerequisites

- MySQL 8.x (or compatible)
- A database created (example: `aquarian`)
- A user with permissions to create tables / foreign keys

## 1) Create database (example)

Run (adjust database name as needed):

```sql
CREATE DATABASE aquarian CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 2) Apply the schema

From this repo, apply the DDL file:

```bash
mysql -h <MYSQL_HOST> -u <MYSQL_USER> -p <MYSQL_DB> < API-and-Admin-Panel/App/db/schema.mysql.sql
```

## 3) Configure the Flask app DB connection

The Flask app uses environment variables (see `API-and-Admin-Panel/App/.env.example`):

- `MYSQL_HOST`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DB`

## 4) Seed an admin user (required for Admin Panel login)

The Admin Panel authenticates against the `Admins` table.

Example (run in MySQL):

```sql
INSERT INTO Admins (Username, Password) VALUES ('admin', 'admin');
```

Security note: this project currently uses plaintext passwords in code; for any real deployment you should upgrade to password hashing.

## 5) Notes on API expectations / indexes

The API issues queries such as:

- `SELECT * FROM Jobs WHERE Status='Pending'`
- `SELECT JobID FROM Jobs WHERE Status='Pending' AND DriverID=?`
- `SELECT * FROM Receipts WHERE DriverID=? AND DATE(DateCreated)=DATE(NOW())`
- `SELECT DriverID, FirstName, Location FROM Drivers WHERE DriverID=?`
- `SELECT Password FROM Admins WHERE Username=?`

The schema therefore includes indexes on `Jobs(Status)`, `(DriverID, Status)`, and `Receipts(DriverID, DateCreated)`, plus unique usernames for Admins/Drivers.
