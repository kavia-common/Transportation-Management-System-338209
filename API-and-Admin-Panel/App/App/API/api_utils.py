"""
Shared utilities for the REST API blueprint.

This module centralizes:
  - request validation/parsing helpers
  - consistent JSON responses
  - safe/parameterized DB query helpers
  - error handling + logging

It is intentionally lightweight and Flask-native to preserve existing endpoint
behavior while improving safety and maintainability.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from flask import Response, jsonify, make_response

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Base class for API errors that should become JSON responses."""

    def __init__(self, message: str, status_code: int = 400, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}


class NotFoundError(ApiError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Not Found", payload: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=404, payload=payload)


class ValidationError(ApiError):
    """Raised when request input validation fails."""

    def __init__(self, message: str = "Invalid request", payload: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=400, payload=payload)


# PUBLIC_INTERFACE
def json_response(payload: Any, status_code: int = 200) -> Response:
    """
    Return a consistent JSON response.

    Contract:
      - Inputs:
          - payload: any JSON-serializable object (dict/list/primitive)
          - status_code: HTTP status code
      - Output: Flask Response with application/json
      - Errors: none (serialization errors propagate to Flask error handling)
    """
    resp = make_response(jsonify(payload), status_code)
    resp.headers["Content-Type"] = "application/json"
    return resp


# PUBLIC_INTERFACE
def legacy_list_error(message: str, status_code: int = 400) -> Response:
    """
    Preserve historical error shape used across this API: a JSON list with one object.

    Example: [{"Error": "No matching ID found in database."}]

    Contract:
      - Inputs: message, status_code
      - Output: Flask JSON response with list-of-one error object
    """
    return json_response([{"Error": message}], status_code=status_code)


# PUBLIC_INTERFACE
def legacy_list_status(status: str, message: str, status_code: int = 200, **extra_fields: Any) -> Response:
    """
    Preserve historical login/status shape used across this API.

    Example: [{"Status":"Success","Message":"Login Succesful", ...}]

    Contract:
      - Inputs: status, message, optional extra fields
      - Output: Flask JSON response with list-of-one status object
    """
    payload: Dict[str, Any] = {"Status": status, "Message": message}
    payload.update(extra_fields)
    return json_response([payload], status_code=status_code)


def _rows_to_dicts(cursor) -> List[Dict[str, Any]]:
    """Convert cursor results to list of dicts based on cursor.description."""
    row_headers = [x[0] for x in cursor.description]
    rv = cursor.fetchall()
    return [dict(zip(row_headers, row)) for row in rv]


# PUBLIC_INTERFACE
def fetch_all_as_dicts(cursor, sql: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT and return results as list of dicts.

    Contract:
      - Inputs: DB cursor, SQL with %s placeholders, optional params
      - Outputs: list[dict] of rows
      - Errors: DB driver errors propagate (boundary should handle)
    """
    cursor.execute(sql, params or ())
    if cursor.description is None:
        return []
    return _rows_to_dicts(cursor)


# PUBLIC_INTERFACE
def require_int_arg(args, name: str, *, minimum: int = 0) -> int:
    """
    Read a required integer query arg from request.args.

    Contract:
      - Inputs: args mapping (typically request.args), name, minimum
      - Output: int
      - Errors: ValidationError if missing or invalid
    """
    if name not in args:
        raise ValidationError(f"Missing required parameter: {name}")
    try:
        value = int(args[name])
    except (TypeError, ValueError) as e:
        raise ValidationError(f"Invalid integer parameter: {name}") from e
    if value < minimum:
        raise ValidationError(f"Parameter {name} must be >= {minimum}")
    return value


# PUBLIC_INTERFACE
def optional_int_arg(args, name: str, *, minimum: int = 0) -> Optional[int]:
    """
    Read an optional integer query arg from request.args.

    Returns None if not present.

    Contract:
      - Inputs: args mapping, name, minimum
      - Output: Optional[int]
      - Errors: ValidationError if present but invalid
    """
    if name not in args:
        return None
    try:
        value = int(args[name])
    except (TypeError, ValueError) as e:
        raise ValidationError(f"Invalid integer parameter: {name}") from e
    if value < minimum:
        raise ValidationError(f"Parameter {name} must be >= {minimum}")
    return value


# ---- SQL identifier validation (prevents injection when identifiers are dynamic) ----

_SAFE_IDENTIFIER_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


# PUBLIC_INTERFACE
def validate_sql_identifier(identifier: str, *, kind: str = "identifier") -> str:
    """
    Validate a SQL identifier (table or column name) used for dynamic SQL construction.

    IMPORTANT:
      - Parameterization cannot be used for identifiers; only for values.
      - This function enforces an allowlist-style validation to prevent SQL injection.

    Contract:
      - Inputs: identifier (string), kind (for error messages)
      - Output: the same identifier if safe
      - Errors: ValidationError if unsafe/empty
    """
    if not identifier or not isinstance(identifier, str):
        raise ValidationError(f"Invalid {kind}: empty")
    if any(ch not in _SAFE_IDENTIFIER_CHARS for ch in identifier):
        raise ValidationError(f"Invalid {kind}: {identifier}")
    return identifier


# PUBLIC_INTERFACE
def make_select_all_sql(table: str, *, limit: Optional[int] = None, offset: Optional[int] = None) -> Tuple[str, Tuple[Any, ...]]:
    """
    Build a safe SELECT * statement with optional LIMIT/OFFSET parameterization.

    Contract:
      - Inputs: validated table name, optional limit/offset
      - Output: (sql, params) ready for cursor.execute
      - Errors: ValidationError if identifiers invalid or limit/offset invalid
    """
    table = validate_sql_identifier(table, kind="table")

    sql = f"SELECT * FROM {table}"
    params: List[Any] = []
    if limit is not None and offset is not None:
        if limit < 0 or offset < 0:
            raise ValidationError("limit1/limit2 must be non-negative integers")
        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
    return sql, tuple(params)


# PUBLIC_INTERFACE
def log_exception(operation: str, exc: Exception, *, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an exception with operation context (best-effort structured context).

    Contract:
      - Inputs: operation name, exception, optional extra context
      - Output: None
      - Side effects: logs to Python logging system
    """
    context = extra or {}
    logger.exception("REST API error in %s | context=%s | error=%s", operation, context, str(exc))
