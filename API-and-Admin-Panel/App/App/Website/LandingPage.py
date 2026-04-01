from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import requests
from flask import Blueprint, render_template, request, url_for

landing = Blueprint("landing", __name__, template_folder="templates", static_folder="static")


@landing.route("/")
def landingPage():
    return render_template("index.html")


def _tracking_api_url(tracking_id: str) -> str:
    """
    Build an absolute URL to the tracking API endpoint.

    We intentionally call into the existing /api route (same service), but keep
    the *public* routes under the Website blueprint only (no overlap with /api).
    """
    # url_for builds "/api/jobs/<id>/location" because RestAPI blueprint is mounted at /api
    # and its route is "/jobs/<string:id>/location".
    return url_for("rest_api.getParcelLocation", id=tracking_id, _external=True)


def _fetch_tracking_result(tracking_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Call the existing tracking API and normalize the response for the UI.

    Returns:
        (result, error)
        - result: dict with DriverID, FirstName, Location, plus derived lat/lng when available
        - error: user-facing error string, if any
    """
    tracking_id = (tracking_id or "").strip()
    if not tracking_id:
        return None, "Please enter a tracking number."

    try:
        resp = requests.get(_tracking_api_url(tracking_id), timeout=8)
    except Exception:
        # Keep error generic (avoid leaking internal network details).
        return None, "Tracking service is currently unavailable. Please try again."

    if resp.status_code == 404:
        return None, "Tracking number not found."
    if not resp.ok:
        return None, "Unable to retrieve tracking details right now. Please try again."

    try:
        payload = resp.json()
    except Exception:
        return None, "Unexpected tracking response format."

    if not isinstance(payload, list) or not payload:
        return None, "No tracking details available yet."

    item = payload[0] if isinstance(payload[0], dict) else None
    if not item:
        return None, "Unexpected tracking response format."

    location_raw = (item.get("Location") or "").strip()
    lat = lng = None
    if location_raw and "," in location_raw:
        parts = [p.strip() for p in location_raw.split(",")]
        if len(parts) >= 2:
            try:
                lat = float(parts[0])
                lng = float(parts[1])
            except Exception:
                lat = lng = None

    normalized: Dict[str, Any] = {
        "tracking_id": tracking_id,
        "DriverID": item.get("DriverID"),
        "FirstName": item.get("FirstName"),
        "Location": location_raw or None,
        "lat": lat,
        "lng": lng,
    }
    return normalized, None


@landing.route("/track", methods=["GET"])
def tracking_form():
    """Public parcel tracking form page (GET)."""
    # If user comes in with /home/track?id=AQ..., prefill and optionally auto-load.
    tracking_id = (request.args.get("id") or "").strip()
    return render_template("track.html", tracking_id=tracking_id)


@landing.route("/track/result", methods=["GET", "POST"])
def tracking_result():
    """
    Public parcel tracking result page.

    Accepts:
      - POST form field: tracking_id
      - or GET query param: id
    """
    tracking_id = ""
    if request.method == "POST":
        tracking_id = (request.form.get("tracking_id") or "").strip()
    else:
        tracking_id = (request.args.get("id") or "").strip()

    result, error = _fetch_tracking_result(tracking_id)
    return render_template(
        "track_result.html",
        tracking_id=tracking_id,
        result=result,
        error=error,
    )

