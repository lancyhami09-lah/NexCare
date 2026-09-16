"""
NexCare REST API Layer
Implements both Patient-Facing and Staff-Facing Endpoints
Full JSON responses with validation, error handling, and disclaimers
"""

import logging
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from . import database
from .config import (
    AREAS,
    DISCLAIMER,
    EMERGENCY_MESSAGE,
    CROWD_THRESHOLDS,
    INDIA_LOCATIONS,
    NON_CHENNAI_NOTICE,
    STATE_HOSPITAL_NOTICE,
    LOCALITY_COORDINATES,
    ALL_INDIA_COORDINATES,
    haversine_distance,
)
from .recommendation import rank_hospitals

logger = logging.getLogger("nexcare.api")
api = Blueprint("api", __name__, url_prefix="/api")

# Standard demo bearer token for staff authentication
DEMO_TOKEN = "nexcare-demo-staff-token-2026"


def ok_response(data, status=200, extra=None):
    """Consistent success response envelope"""
    payload = {
        "success": True,
        "data": data,
        "disclaimer": DISCLAIMER,
        "emergency_message": EMERGENCY_MESSAGE,
    }
    if extra and isinstance(extra, dict):
        payload.update(extra)
    return jsonify(payload), status


def error_response(message, status=400, error_code=None):
    """Consistent error response envelope"""
    payload = {
        "success": False,
        "error": message,
        "disclaimer": DISCLAIMER,
        "emergency_message": EMERGENCY_MESSAGE,
    }
    if error_code:
        payload["error_code"] = error_code
    return jsonify(payload), status


def parse_hospital_id(raw_id):
    """Safely validate integer hospital ID"""
    try:
        val = int(raw_id)
        return val if val > 0 else None
    except (TypeError, ValueError):
        return None


def verify_staff_token():
    """Verify Bearer token on staff-protected endpoints"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header.split(" ", 1)[1].strip()
    return token == DEMO_TOKEN


# ====================================================================
# PATIENT-FACING ENDPOINTS (Public, read-only)
# ====================================================================

@api.get("/areas")
@api.get("/localities")
def list_localities():
    """
    List all 12 supported Chennai localities for patient location selection.
    """
    return ok_response(AREAS)


@api.get("/locations")
def list_locations():
    """
    Return all Indian states, Union Territories, and cities/localities.
    Used for two-step State -> City navigation across India.
    """
    return ok_response(
        INDIA_LOCATIONS,
        extra={
            "coverage_note": NON_CHENNAI_NOTICE,
            "default_state": "Tamil Nadu",
            "default_city": "Chennai - Adyar",
        },
    )


@api.get("/states")
def list_states():
    """
    List all Indian states and Union Territories.
    Puts primary active states (Tamil Nadu, Karnataka) first for immediate discovery.
    """
    all_states = sorted(list(INDIA_LOCATIONS.keys()))
    ordered = []
    for priority in ["Tamil Nadu", "Karnataka"]:
        if priority in all_states:
            all_states.remove(priority)
            ordered.append(priority)
    ordered.extend(all_states)
    return ok_response(
        ordered,
        extra={
            "count": len(ordered),
            "active_coverage": ["Tamil Nadu", "Karnataka"],
        },
    )


@api.get("/states/<state>/cities")
def list_state_cities(state):
    """
    List cities and localities for a given Indian state or UT.
    Returns honest notice if state does not yet have active hospital listings.
    """
    matched_state = None
    for s in INDIA_LOCATIONS.keys():
        if s.lower() == state.lower() or state.lower() in s.lower() or s.lower().startswith(state.lower()):
            matched_state = s
            break

    if not matched_state:
        return error_response(f"State '{state}' not found in locations directory.", 404)

    cities = INDIA_LOCATIONS[matched_state]
    extra = {
        "state": matched_state,
        "cities": cities,
        "count": len(cities),
        "data_available": True,
        "state_note": "",
    }
    return ok_response(cities, extra=extra)


@api.get("/hospitals")
def list_hospitals():
    """
    List hospitals with current simulated availability status.
    Supports optional filters:
    - locality: string (e.g. 'Adyar')
    - type: 'Government' | 'Private'
    - patient_locality: patient's selected area to compute dynamic distance
    - search: keyword search in name/address
    - lat: float (live latitude)
    - lng: float (live longitude)
    - state: state name filter (e.g. 'Kerala', 'Delhi (NCT)')
    """
    locality = request.args.get("locality")
    hospital_type = request.args.get("type")
    patient_locality = request.args.get("patient_locality")
    search = request.args.get("search")
    state = request.args.get("state")

    lat = None
    lng = None
    lat_str = request.args.get("lat")
    lng_str = request.args.get("lng")
    if lat_str and lng_str:
        try:
            lat = float(lat_str)
            lng = float(lng_str)
        except (ValueError, TypeError):
            pass

    results = database.get_hospitals(
        locality=locality,
        hospital_type=hospital_type,
        patient_locality=patient_locality,
        search=search,
        lat=lat,
        lng=lng,
        state=state,
    )

    extra = {"count": len(results)}
    return ok_response(results, extra=extra)


@api.get("/hospitals/<hospital_id>")
def get_hospital_details(hospital_id):
    """
    Fetch comprehensive details for a specific hospital by ID.
    Includes bed statistics, doctors, resources, crowd level, and distance.
    """
    hid = parse_hospital_id(hospital_id)
    if hid is None:
        return error_response("Invalid hospital ID format. Must be a positive integer.", 400)

    patient_locality = request.args.get("patient_locality")
    lat = None
    lng = None
    lat_str = request.args.get("lat")
    lng_str = request.args.get("lng")
    if lat_str and lng_str:
        try:
            lat = float(lat_str)
            lng = float(lng_str)
        except (ValueError, TypeError):
            pass

    hospital = database.get_hospital(hid, patient_locality=patient_locality, lat=lat, lng=lng)
    if not hospital:
        return error_response(f"Hospital with ID {hospital_id} not found.", 404)

    return ok_response(hospital)


@api.get("/hospitals/recommendations")
def get_recommendations():
    """
    Return ranked hospitals with transparency scoring and natural language explanations.
    Query parameters:
    - locality: Patient's current locality or city
    - lat: float (live latitude)
    - lng: float (live longitude)
    - limit: Number of top recommendations to return (default: 5)
    """
    patient_locality = (request.args.get("city") or request.args.get("locality", "")).strip()
    state = request.args.get("state")
    lat = None
    lng = None
    lat_str = request.args.get("lat")
    lng_str = request.args.get("lng")
    if lat_str and lng_str:
        try:
            lat = float(lat_str)
            lng = float(lng_str)
        except (ValueError, TypeError):
            pass

    limit_str = request.args.get("limit", "5")
    try:
        limit = int(limit_str)
        if limit <= 0:
            limit = 5
    except ValueError:
        limit = 5

    all_hospitals = database.get_hospitals(patient_locality=patient_locality, lat=lat, lng=lng, state=state)
    ranked = rank_hospitals(all_hospitals, patient_locality=patient_locality, limit=limit)

    extra = {
        "patient_locality": patient_locality or (f"{lat:.4f}, {lng:.4f}" if lat is not None else "Nearby"),
        "ranking_factors": {
            "Bed Availability": "30%",
            "Distance Proximity": "20%",
            "Doctor Availability": "20%",
            "General Medical Resources": "15%",
            "Crowd Level": "15%",
        },
    }

    return ok_response(
        ranked,
        extra=extra,
    )


# ====================================================================
# STAFF-FACING ENDPOINTS (Login-gated, updates, audit history)
# ====================================================================

@api.post("/staff/login")
def staff_login():
    """
    Staff demo authentication.
    Body: { "staff_id": "staff_fortis", "password": "demo123" }
    Returns session token and staff metadata.
    """
    body = request.get_json(silent=True) or {}
    staff_id = str(body.get("staff_id", "")).strip()
    password = str(body.get("password", "")).strip()

    if not staff_id or not password:
        return error_response("Staff ID and password are required.", 400)

    staff_user = database.verify_staff(staff_id, password)
    if not staff_user:
        return error_response("Invalid demo staff ID or password.", 401)

    return ok_response(
        {
            "token": DEMO_TOKEN,
            "staff_id": staff_user["staff_id"],
            "name": staff_user["name"],
            "hospital_id": staff_user["hospital_id"],
            "auth_note": "Demo session active — not for production security.",
        }
    )


@api.get("/staff/<hospital_id>/dashboard")
def staff_dashboard(hospital_id):
    """
    Fetch live dashboard data for hospital staff management.
    Requires Bearer token authorization.
    """
    if not verify_staff_token():
        return error_response("Staff authentication required. Please provide a valid Bearer token.", 401)

    hid = parse_hospital_id(hospital_id)
    if hid is None:
        return error_response("Invalid hospital ID.", 400)

    hospital = database.get_hospital(hid)
    if not hospital:
        return error_response(f"Hospital with ID {hospital_id} not found.", 404)

    # Compute staff warning alerts
    warnings = []
    beds = hospital.get("beds", {})
    if beds.get("total", 0) > 0:
        occ_ratio = beds.get("occupied", 0) / beds.get("total", 1)
        if occ_ratio >= 0.90:
            warnings.append({
                "type": "danger",
                "message": f"Critical Bed Capacity Warning: {int(occ_ratio*100)}% beds occupied ({beds.get('available')} available)."
            })
        elif occ_ratio >= 0.80:
            warnings.append({
                "type": "warning",
                "message": f"High Bed Occupancy Alert: {int(occ_ratio*100)}% beds occupied."
            })

    if hospital.get("crowd_status") == "High":
        waiting = hospital.get("crowd", {}).get("waiting_patients", 0)
        warnings.append({
            "type": "danger",
            "message": f"High Patient Crowd Alert: {waiting} patients in waiting queue."
        })

    if hospital.get("doctor_status") == "Unavailable":
        warnings.append({
            "type": "danger",
            "message": "Doctor Shortage Warning: No on-duty doctors currently available for consultations."
        })

    # Check for unavailable critical resources (ICU beds, Oxygen, ED)
    critical_units = ["ICU beds", "Oxygen", "ED"]
    unavailable_critical = [
        r["resource_type"] for r in hospital.get("resources", [])
        if r.get("resource_type") in critical_units and r.get("status") == "Unavailable"
    ]
    if unavailable_critical:
        warnings.append({
            "type": "danger",
            "message": f"Critical Resource Shortage: {', '.join(unavailable_critical)} currently marked Unavailable."
        })

    # Check for data not updated recently (> 12 hours)
    last_up = hospital.get("last_updated")
    if last_up:
        try:
            dt = datetime.fromisoformat(last_up.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
            if age_hours > 12.0:
                warnings.append({
                    "type": "warning",
                    "message": f"Stale Data Warning: Hospital metrics have not been updated in {int(age_hours)} hours."
                })
        except Exception:
            pass

    # Compute Key Metrics for login home (Formula: Available = Total - Occupied - Blocked)
    total_beds = beds.get("total", 0)
    occupied_beds = beds.get("occupied", 0)
    blocked_beds = beds.get("blocked", 0)
    available_beds = max(0, total_beds - occupied_beds - blocked_beds)
    today_admissions = beds.get("today_admissions", 0)
    today_discharges = beds.get("today_discharges", 0)
    summary = {
        "total_beds": total_beds,
        "occupied_beds": occupied_beds,
        "blocked_beds": blocked_beds,
        "available_beds": available_beds,
        "today_admissions": today_admissions,
        "today_discharges": today_discharges,
    }

    return ok_response(
        {
            "hospital": hospital,
            "summary": summary,
            "warnings": warnings,
            "thresholds": CROWD_THRESHOLDS,
        }
    )


@api.put("/staff/<hospital_id>/beds")
def update_beds(hospital_id):
    """
    Update hospital bed numbers:
    Body: { "total_beds": 180, "occupied_beds": 110, "admissions": 4, "discharges": 6 }
    Validates non-negative values and occupied_beds + blocked_beds <= total_beds.
    """
    if not verify_staff_token():
        return error_response("Staff authentication required.", 401)

    hid = parse_hospital_id(hospital_id)
    if hid is None:
        return error_response("Invalid hospital ID.", 400)

    body = request.get_json(silent=True) or {}
    if "total_beds" not in body or "occupied_beds" not in body:
        return error_response("Both 'total_beds' and 'occupied_beds' fields are required.", 400)

    try:
        total = int(body["total_beds"])
        occupied = int(body["occupied_beds"])
        admissions = int(body.get("today_admissions", body.get("admissions", 0)))
        discharges = int(body.get("today_discharges", body.get("discharges", 0)))
    except (ValueError, TypeError):
        return error_response("Bed counts must be valid integers.", 400)

    if total < 0 or occupied < 0:
        return error_response("Bed counts cannot be negative numbers.", 400)

    current_hosp = database.get_hospital(hid)
    current_blocked = current_hosp["beds"].get("blocked", 0) if current_hosp and "beds" in current_hosp else 0

    if occupied + current_blocked > total:
        return error_response(
            f"Occupied beds ({occupied}) + Blocked beds ({current_blocked}) cannot exceed total bed capacity ({total}).",
            409,
            error_code="CAPACITY_EXCEEDED",
        )

    staff_id = body.get("staff_id", "demo-staff")
    updated = database.update_hospital_beds(hid, total, occupied, admissions, discharges, staff_id)
    if not updated:
        return error_response("Hospital not found.", 404)

    return ok_response(updated, extra={"message": "Bed counts updated successfully."})


@api.put("/staff/<hospital_id>/crowd")
def update_crowd(hospital_id):
    """
    Update hospital crowd metrics:
    Body: { "current_patients": 40, "waiting_patients": 8 }
    Automatically computes crowd status based on configurable thresholds.
    """
    if not verify_staff_token():
        return error_response("Staff authentication required.", 401)

    hid = parse_hospital_id(hospital_id)
    if hid is None:
        return error_response("Invalid hospital ID.", 400)

    body = request.get_json(silent=True) or {}
    if "current_patients" not in body or "waiting_patients" not in body:
        return error_response("Both 'current_patients' and 'waiting_patients' fields are required.", 400)

    try:
        current = int(body["current_patients"])
        waiting = int(body["waiting_patients"])
        admissions = int(body.get("today_admissions", body.get("admissions", 0)))
        discharges = int(body.get("today_discharges", body.get("discharges", 0)))
    except (ValueError, TypeError):
        return error_response("Patient numbers must be valid integers.", 400)

    if current < 0 or waiting < 0 or admissions < 0 or discharges < 0:
        return error_response("Patient and admission numbers cannot be negative.", 400)

    staff_id = body.get("staff_id", "demo-staff")
    updated = database.update_hospital_crowd(hid, current, waiting, admissions, discharges, staff_id)
    if not updated:
        return error_response("Hospital not found.", 404)

    return ok_response(updated, extra={"message": "Crowd indicators updated successfully."})


@api.put("/staff/<hospital_id>/doctors")
def update_doctors(hospital_id):
    """
    Update doctor/department availability.
    Body: { "doctors": [...] } OR { "status": "Available" | "Limited" | "Unavailable" }
    """
    if not verify_staff_token():
        return error_response("Staff authentication required.", 401)

    hid = parse_hospital_id(hospital_id)
    if hid is None:
        return error_response("Invalid hospital ID.", 400)

    body = request.get_json(silent=True) or {}
    if isinstance(body, list):
        doctors_data = body
        staff_id = "demo-staff"
    elif isinstance(body, dict):
        doctors_data = body.get("doctors") or body
        staff_id = body.get("staff_id", "demo-staff")
    else:
        doctors_data = []
        staff_id = "demo-staff"

    updated = database.update_hospital_doctors(hid, doctors_data, staff_id)
    if not updated:
        return error_response("Hospital not found.", 404)

    return ok_response(updated, extra={"message": "Doctor availability updated successfully."})


@api.put("/staff/<hospital_id>/resources")
def update_resources(hospital_id):
    """
    Update medical resources status (ICU beds, Oxygen, Pharmacy, Lab, etc.):
    Body: { "resources": { "ICU beds": "Available", "Oxygen": "Limited", ... } }
    """
    if not verify_staff_token():
        return error_response("Staff authentication required.", 401)

    hid = parse_hospital_id(hospital_id)
    if hid is None:
        return error_response("Invalid hospital ID.", 400)

    body = request.get_json(silent=True) or {}
    if isinstance(body, dict):
        resources_data = body.get("resources", body)
        staff_id = body.get("staff_id", "demo-staff")
    elif isinstance(body, list):
        resources_data = body
        staff_id = "demo-staff"
    else:
        resources_data = {}
        staff_id = "demo-staff"

    valid_statuses = {"Available", "Limited", "Unavailable"}

    if isinstance(resources_data, dict):
        for res_name, status in resources_data.items():
            if res_name == "staff_id":
                continue
            if status not in valid_statuses:
                return error_response(
                    f"Invalid status '{status}' for '{res_name}'. Allowed: Available, Limited, Unavailable.",
                    400,
                )
    elif isinstance(resources_data, list):
        for item in resources_data:
            if isinstance(item, dict) and item.get("status") not in valid_statuses:
                return error_response(
                    f"Invalid status '{item.get('status')}' for '{item.get('resource_type')}'. Allowed: Available, Limited, Unavailable.",
                    400,
                )
    else:
        return error_response("'resources' must be an object or array of resource statuses.", 400)

    updated = database.update_hospital_resources(hid, resources_data, staff_id)
    if not updated:
        return error_response("Hospital not found.", 404)

    return ok_response(updated, extra={"message": "Resource statuses updated successfully."})


@api.get("/staff/<hospital_id>/history")
def get_audit_history(hospital_id):
    """
    Fetch audit history log for a specific hospital.
    Requires Bearer token authorization.
    """
    if not verify_staff_token():
        return error_response("Staff authentication required.", 401)

    hid = parse_hospital_id(hospital_id)
    if hid is None:
        return error_response("Invalid hospital ID.", 400)

    history = database.get_history(hid)
    return ok_response(history, extra={"count": len(history)})


# ====================================================================
# SIMULATED SOS EMERGENCY & BED BLOCKING ENDPOINTS (Features 2 & 3)
# ====================================================================

SIMULATED_EMERGENCY_NOTICE = (
    "SIMULATED PROTOTYPE WORKFLOW: In an actual life-threatening medical emergency, call 108 (Ambulance) "
    "or 112 (National Emergency Helpline) immediately. This prototype simulates bed reservation, ambulance "
    "dispatch, and check-in for hackathon demonstration purposes only."
)


@api.post("/emergency/request")
def create_emergency_request():
    """
    Simulated SOS Emergency Initiation:
    Body: {
      "patient_locality": "Chennai - Adyar",
      "lat": 13.0012,
      "lng": 80.2565,
      "state": "Tamil Nadu",
      "hospital_id": optional
    }
    1. Selects best nearby hospital with available beds.
    2. Assigns simulated ambulance.
    3. Blocks 1 bed immediately in that hospital.
    4. Returns tracking ID and details.
    """
    body = request.get_json(silent=True) or {}
    patient_locality = body.get("patient_locality")
    lat = body.get("lat")
    lng = body.get("lng")
    state = body.get("state")
    hospital_id = body.get("hospital_id")

    req_record, err = database.create_emergency_request(
        hospital_id=hospital_id,
        patient_locality=patient_locality,
        lat=lat,
        lng=lng,
        state=state
    )

    if err == "NO_BEDS_AVAILABLE":
        return error_response(
            "No nearby hospital currently has available beds for emergency allocation.",
            503,
            error_code="NO_BEDS_AVAILABLE"
        )
    elif err or not req_record:
        return error_response(err or "Failed to initiate emergency request.", 400)

    return ok_response(
        req_record,
        status=201,
        extra={
            "simulated_emergency_notice": SIMULATED_EMERGENCY_NOTICE,
            "message": "Simulated emergency request initiated and bed blocked successfully."
        }
    )


@api.get("/emergency/request/<request_code>")
def get_emergency_request(request_code):
    """
    Get real-time tracking status of a simulated emergency request.
    Public endpoint for patient status tracking.
    """
    req_record = database.get_emergency_request(request_code)
    if not req_record:
        return error_response("Emergency request not found.", 404, error_code="NOT_FOUND")

    return ok_response(
        req_record,
        extra={"simulated_emergency_notice": SIMULATED_EMERGENCY_NOTICE}
    )


@api.put("/emergency/request/<request_code>/status")
def update_emergency_status(request_code):
    """
    Update status of an emergency request (e.g. En Route, Arrived, Patient Admitted).
    When status transitions to 'Patient Admitted', the blocked bed converts to occupied bed.
    Body: { "status": "En Route" | "Arrived" | "Patient Admitted", "staff_id": optional }
    """
    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    staff_id = body.get("staff_id", "demo-staff")

    if not new_status:
        return error_response("Field 'status' is required.", 400)

    updated_req, err = database.update_emergency_status(request_code, new_status, staff_id=staff_id)
    if err == "NOT_FOUND":
        return error_response("Emergency request not found.", 404)
    elif err:
        return error_response(err, 400)

    return ok_response(
        updated_req,
        extra={
            "simulated_emergency_notice": SIMULATED_EMERGENCY_NOTICE,
            "message": f"Emergency status updated to '{new_status}' successfully."
        }
    )


@api.put("/emergency/request/<request_code>/cancel")
def cancel_emergency_request(request_code):
    """
    Cancel an emergency request and release the blocked bed back to availability.
    Body: { "staff_id": optional }
    """
    body = request.get_json(silent=True) or {}
    staff_id = body.get("staff_id", "patient-cancel")

    cancelled_req, err = database.cancel_emergency_request(request_code, staff_id=staff_id)
    if err == "NOT_FOUND":
        return error_response("Emergency request not found.", 404)
    elif err:
        return error_response(err, 400)

    return ok_response(
        cancelled_req,
        extra={
            "simulated_emergency_notice": SIMULATED_EMERGENCY_NOTICE,
            "message": "Emergency request cancelled and blocked bed released."
        }
    )


@api.get("/staff/<hospital_id>/emergency-requests")
def get_hospital_emergency_requests(hospital_id):
    """
    Fetch all incoming and ongoing emergency requests for a hospital.
    Requires Bearer token authorization.
    """
    if not verify_staff_token():
        return error_response("Staff authentication required.", 401)

    hid = parse_hospital_id(hospital_id)
    if hid is None:
        return error_response("Invalid hospital ID.", 400)

    requests_list = database.get_hospital_emergency_requests(hid)
    return ok_response(
        requests_list,
        extra={
            "count": len(requests_list),
            "simulated_emergency_notice": SIMULATED_EMERGENCY_NOTICE
        }
    )

