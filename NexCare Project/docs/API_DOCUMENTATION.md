# NexCare REST API Documentation

This document describes all REST API endpoints provided by the NexCare backend server.

- **Base URL:** `http://localhost:5000/api`
- **Health URL:** `http://localhost:5000/health`
- **Content-Type:** `application/json`
- **Standard Response Envelopes:**
  - Success responses return `{ "success": true, "data": ..., "disclaimer": "...", "emergency_message": "..." }`
  - Error responses return `{ "success": false, "error": "...", "disclaimer": "..." }`

---

## Mandatory System Disclaimer

Every response contains the non-diagnostic, informational guidance disclaimer:
> *"NexCare is an informational guidance tool designed to help patients identify nearby healthcare facilities. It does NOT provide medical advice, diagnosis, bed reservations, or emergency dispatch. In a medical emergency, call 108 or 112 immediately."*

---

## Table of Endpoints

### Geographic & Location Endpoints (Public)
1. [`GET /api/states`](#1-get-apistates) — List all supported Indian states/UTs (Tamil Nadu & Karnataka prioritized)
2. [`GET /api/states/<state>/cities`](#2-get-apistatesstatecities) — List cities/localities for a state (with honest unpopulated notice)
3. [`GET /api/locations`](#3-get-apilocations) — All-India hierarchical states & cities directory
4. [`GET /api/areas`](#4-get-apiareas) — Supported Chennai localities (legacy endpoint)

### Hospital Discovery & Recommendation (Public)
5. [`GET /api/hospitals`](#5-get-apihospitals) — List & filter hospitals by state, city, type, or live GPS
6. [`GET /api/hospitals/<hospital_id>`](#6-get-apihospitalshospital_id) — Get detailed information for a single hospital
7. [`GET /api/hospitals/recommendations`](#7-get-apihospitalsrecommendations) — 5-Factor weighted recommendation engine

### Staff Dashboard & Operations (Authenticated)
8. [`POST /api/staff/login`](#8-post-apistafflogin) — Authenticate hospital staff member
9. [`GET /api/staff/<hospital_id>/dashboard`](#9-get-apistaffhospital_iddashboard) — Hospital status, 5 key metrics & automated warnings
10. [`PUT /api/staff/<hospital_id>/beds`](#10-put-apistaffhospital_idbeds) — Update bed counts with validation
11. [`PUT /api/staff/<hospital_id>/crowd`](#11-put-apistaffhospital_idcrowd) — Update patient queues and crowd level
12. [`PUT /api/staff/<hospital_id>/doctors`](#12-put-apistaffhospital_iddoctors) — Update doctor/department on-duty statuses & specialty
13. [`PUT /api/staff/<hospital_id>/resources`](#13-put-apistaffhospital_idresources) — Update diagnostic and critical resource readiness
14. [`GET /api/staff/<hospital_id>/history`](#14-get-apistaffhospital_idhistory) — Retrieve chronological audit log

### System Health
15. [`GET /health`](#15-get-health) — Service health status and active data mode

---

## 1. GET `/api/states`

- **Method:** `GET`
- **URL:** `/api/states`
- **Purpose:** Retrieve the list of all 19+ Indian states and Union Territories. Tamil Nadu and Karnataka are pinned at the top for immediate access.
- **Headers:** None required.
- **Request Body:** None.
- **Response (`200 OK`):**
```json
{
  "success": true,
  "data": [
    "Tamil Nadu",
    "Karnataka",
    "Andhra Pradesh",
    "Delhi (NCT)",
    "Gujarat",
    "Kerala",
    "Maharashtra",
    "Telangana",
    "West Bengal"
  ],
  "count": 19,
  "active_coverage": ["Tamil Nadu", "Karnataka"],
  "disclaimer": "NexCare is an informational guidance tool...",
  "emergency_message": "If this is a medical emergency, contact 108/112 immediately."
}
```

---

## 2. GET `/api/states/<state>/cities`

- **Method:** `GET`
- **URL:** `/api/states/<state>/cities`
- **Purpose:** List cities and localities for a specified state. For unpopulated states, returns an honest notice indicating that verified partner hospitals are not yet active.
- **Parameters:**
  - `state` *(path param)*: Name of the state (e.g., `Karnataka`, `Tamil Nadu`, `Delhi`).
- **Response for Active State (`200 OK`):**
```json
{
  "success": true,
  "state": "Karnataka",
  "data_available": true,
  "state_note": "",
  "cities": [
    "Bengaluru - Old Airport Road",
    "Bengaluru - Kalasipalya",
    "Bengaluru - Bommasandra",
    "Bengaluru - Shivaji Nagar",
    "Bengaluru - Bannerghatta Road",
    "Bengaluru - Koramangala",
    "Bengaluru",
    "Mysuru",
    "Mangaluru"
  ],
  "count": 13,
  "data": [...]
}
```
- **Response for Unpopulated State (`200 OK`):**
```json
{
  "success": true,
  "state": "Delhi (NCT)",
  "data_available": false,
  "state_note": "Hospital listings are not yet available for this state. Full verified hospital data is currently active for Tamil Nadu and Karnataka.",
  "cities": [
    "New Delhi",
    "Central Delhi",
    "South Delhi"
  ],
  "count": 6
}
```
- **Error Response (`404 Not Found`):** If state is not found in directory.

---

## 3. GET `/api/locations`

- **Method:** `GET`
- **URL:** `/api/locations`
- **Purpose:** Full hierarchical dictionary mapping Indian states to lists of cities/localities.
- **Response (`200 OK`):**
```json
{
  "success": true,
  "data": {
    "Tamil Nadu": ["Chennai - Adyar", "Chennai - Anna Nagar", "..."],
    "Karnataka": ["Bengaluru - Koramangala", "Bengaluru - Whitefield", "..."]
  },
  "coverage_note": "Full hospital data is currently available for Chennai and Bengaluru.",
  "default_state": "Tamil Nadu",
  "default_city": "Chennai - Adyar"
}
```

---

## 4. GET `/api/areas`

- **Method:** `GET`
- **URL:** `/api/areas`
- **Purpose:** Retrieve the list of 12 supported Chennai localities (legacy endpoint for backward compatibility).
- **Response (`200 OK`):**
```json
{
  "success": true,
  "data": [
    "Adyar",
    "Anna Nagar",
    "Egmore",
    "Guindy",
    "Manapakkam",
    "Mogappair",
    "Perambur",
    "Porur",
    "Sholinganallur",
    "T. Nagar",
    "Tambaram",
    "Velachery"
  ]
}
```

---

## 5. GET `/api/hospitals`

- **Method:** `GET`
- **URL:** `/api/hospitals`
- **Purpose:** List hospitals with current simulated availability status. Supports flexible filtering and live GPS distance calculation.
- **Query Parameters:**
  - `state` *(optional)*: Filter by state name (`Tamil Nadu` or `Karnataka`).
  - `city` / `locality` *(optional)*: Filter by city or locality (e.g. `Adyar`, `Koramangala`).
  - `type` *(optional)*: Filter by hospital type (`Government` or `Private`).
  - `patient_locality` *(optional)*: Patient's selected locality to calculate distance.
  - `search` *(optional)*: Keyword search in hospital name and address.
  - `lat`, `lng` *(optional)*: Live patient GPS coordinates for real-time Haversine distance computation.
- **Response (`200 OK`):**
```json
{
  "success": true,
  "count": 16,
  "data": [
    {
      "id": 5,
      "name": "Fortis Malar Hospital",
      "locality": "Adyar",
      "city": "Chennai",
      "state": "Tamil Nadu",
      "address": "52, 1st Main Road, Gandhi Nagar, Adyar, Chennai - 600020",
      "type": "Private",
      "contact_number": "+91 44 4289 2222",
      "distance_km": 0.6,
      "beds": {
        "total": 180,
        "occupied": 110,
        "available": 70
      },
      "doctor_status": "Available",
      "crowd_status": "Low",
      "crowd": {
        "current_patients": 32,
        "waiting_patients": 6
      },
      "last_updated": "2026-09-15T06:21:00Z"
    }
  ]
}
```

---

## 6. GET `/api/hospitals/<hospital_id>`

- **Method:** `GET`
- **URL:** `/api/hospitals/<hospital_id>`
- **Purpose:** Fetch detailed record of a single hospital including full doctors list with specialties, all medical resources, and contact information.
- **Parameters:**
  - `hospital_id` *(path param, integer)*: Valid hospital ID (1 to 16).
- **Response (`200 OK`):**
```json
{
  "success": true,
  "data": {
    "id": 5,
    "name": "Fortis Malar Hospital",
    "locality": "Adyar",
    "address": "52, 1st Main Road, Gandhi Nagar, Adyar, Chennai - 600020",
    "type": "Private",
    "contact_number": "+91 44 4289 2222",
    "distance_km": 0.6,
    "beds": { "total": 180, "occupied": 110, "available": 70 },
    "crowd": { "current_patients": 32, "waiting_patients": 6 },
    "doctor_status": "Available",
    "crowd_status": "Low",
    "doctors": [
      {
        "id": 501,
        "name_or_department": "Emergency Medicine",
        "specialty": "Emergency Medicine",
        "status": "Available",
        "available_time": "24x7",
        "consultation_capacity": 40
      }
    ],
    "resources": {
      "ICU beds": "Available",
      "Oxygen": "Available",
      "Blood bank": "Available",
      "CT scan": "Available",
      "Pharmacy": "Available",
      "Lab": "Available"
    },
    "last_updated": "2026-09-15T06:21:00Z"
  }
}
```

---

## 7. GET `/api/hospitals/recommendations`

- **Method:** `GET`
- **URL:** `/api/hospitals/recommendations`
- **Purpose:** Execute the 5-factor weighted recommendation algorithm to rank hospitals and provide a plain-language explanation of each recommendation.
- **Query Parameters:**
  - `locality` / `city` *(optional)*: Locality to anchor distance calculations.
  - `state` *(optional)*: State name (e.g. `Tamil Nadu` or `Karnataka`).
  - `lat`, `lng` *(optional)*: Live patient GPS coordinates.
  - `limit` *(optional, default: 5)*: Number of top recommendations to return.
- **Algorithm Weights:**
  - Distance: **25%**
  - Available Bed Capacity: **25%**
  - Doctor Availability: **20%**
  - Critical Resource Readiness: **15%**
  - Crowd Level: **15%**
- **Response (`200 OK`):**
```json
{
  "success": true,
  "count": 5,
  "data": [
    {
      "id": 5,
      "name": "Fortis Malar Hospital",
      "score": 81.3,
      "distance_km": 0.6,
      "factor_scores": {
        "distance": 97.0,
        "beds": 70.0,
        "doctors": 100.0,
        "resources": 100.0,
        "crowd": 90.0
      },
      "recommendation_reason": "Recommended because it has available beds (70 beds ready), doctors on-duty across key departments, required emergency and medical resources (ICU, Oxygen, Lab, Pharmacy) and lower crowd (6 waiting) compared with other nearby hospitals (located 0.6 km from Adyar).",
      "algorithm_disclaimer": "This score is a mathematical recommendation based on reported metrics. It does not replace clinical triage.",
      "beds": { "total": 180, "occupied": 110, "available": 70 },
      "crowd_status": "Low"
    }
  ]
}
```

---

## 8. POST `/api/staff/login`

- **Method:** `POST`
- **URL:** `/api/staff/login`
- **Purpose:** Authenticate hospital staff using demo credentials.
- **Headers:** `Content-Type: application/json`
- **Request Body:**
```json
{
  "staff_id": "staff_fortis",
  "password": "demo123"
}
```
- **Demo Staff Accounts:**
  - `staff_apollo` (Apollo Hospitals, Chennai) — `demo123`
  - `staff_fortis` (Fortis Malar Hospital, Chennai) — `demo123`
  - `staff_rggh` (Rajiv Gandhi Govt General Hospital, Chennai) — `demo123`
  - `staff_manipal` (Manipal Hospital, Bengaluru) — `demo123`
  - `staff_narayana` (Narayana Health City, Bengaluru) — `demo123`
- **Response (`200 OK`):**
```json
{
  "success": true,
  "data": {
    "staff_id": "staff_fortis",
    "name": "Nurse Supervisor Deepa",
    "role": "Nurse Supervisor",
    "hospital_id": 5,
    "hospital_name": "Fortis Malar Hospital",
    "token": "nexcare-demo-staff-token-2026",
    "expires_in_seconds": 86400
  }
}
```
- **Error Response (`401 Unauthorized`):** If password does not match or staff ID is unrecognized.

---

## 9. GET `/api/staff/<hospital_id>/dashboard`

- **Method:** `GET`
- **URL:** `/api/staff/<hospital_id>/dashboard`
- **Purpose:** Retrieve full hospital status, the 5 key summary metrics, and automated system warnings.
- **Headers:** `Authorization: Bearer <token>`
- **Response (`200 OK`):**
```json
{
  "success": true,
  "data": {
    "hospital": { "id": 5, "name": "Fortis Malar Hospital", ... },
    "summary": {
      "total_beds": 180,
      "occupied_beds": 110,
      "available_beds": 70,
      "today_admissions": 5,
      "today_discharges": 3
    },
    "warnings": [
      "CRITICAL: Emergency Department reported as Unavailable.",
      "STALENESS: Hospital data has not been updated in over 12 hours. Please re-verify current availability."
    ],
    "recent_activity": [...]
  }
}
```

---

## 10. PUT `/api/staff/<hospital_id>/beds`

- **Method:** `PUT`
- **URL:** `/api/staff/<hospital_id>/beds`
- **Purpose:** Update total and occupied beds. Automatically tracks admissions and discharges.
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Request Body:**
```json
{
  "total_beds": 180,
  "occupied_beds": 110,
  "admissions": 5,
  "discharges": 3,
  "staff_id": "staff_fortis"
}
```
- **Validation Rules:**
  - `occupied_beds` cannot exceed `total_beds` (returns `409 Conflict` with `error_code: CAPACITY_EXCEEDED`).
  - Values must be non-negative integers (returns `400 Bad Request`).
- **Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Bed availability updated successfully.",
  "data": {
    "beds": {
      "total": 180,
      "occupied": 110,
      "available": 70
    },
    "admissions": 5,
    "discharges": 3,
    "last_updated": "2026-09-15T16:28:41.123Z"
  }
}
```

---

## 11. PUT `/api/staff/<hospital_id>/crowd`

- **Method:** `PUT`
- **URL:** `/api/staff/<hospital_id>/crowd`
- **Purpose:** Update active patient queue counts. Automatically derives `crowd_status` (`Low`, `Moderate`, `High`).
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Request Body:**
```json
{
  "current_patients": 32,
  "waiting_patients": 6,
  "staff_id": "staff_fortis"
}
```
- **Status Thresholds:**
  - Total `<= 40`: `Low`
  - Total `41 - 80`: `Moderate`
  - Total `> 80`: `High`
- **Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Crowd indicators updated successfully.",
  "data": {
    "crowd": {
      "current_patients": 32,
      "waiting_patients": 6
    },
    "crowd_status": "Low"
  }
}
```

---

## 12. PUT `/api/staff/<hospital_id>/doctors`

- **Method:** `PUT`
- **URL:** `/api/staff/<hospital_id>/doctors`
- **Purpose:** Update status and consultation capacity of on-duty doctors and departments.
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Request Body:**
```json
{
  "doctors": [
    {
      "id": 501,
      "name_or_department": "Emergency Medicine",
      "specialty": "Emergency Medicine",
      "status": "Available",
      "available_time": "24x7 / On-Duty",
      "consultation_capacity": 40
    }
  ],
  "staff_id": "staff_fortis"
}
```
- **Allowed Statuses:** `Available`, `Limited`, `Unavailable`.

---

## 13. PUT `/api/staff/<hospital_id>/resources`

- **Method:** `PUT`
- **URL:** `/api/staff/<hospital_id>/resources`
- **Purpose:** Update readiness status of critical equipment and diagnostic services.
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Request Body:**
```json
{
  "resources": {
    "ICU beds": "Available",
    "Oxygen": "Available",
    "CT scan": "Limited",
    "Blood bank": "Available"
  },
  "staff_id": "staff_fortis"
}
```
- **Tracked Resources:** `ICU beds`, `Oxygen`, `Pharmacy`, `Lab`, `X-ray`, `CT scan`, `Blood bank`, `Emergency Department`.

---

## 14. GET `/api/staff/<hospital_id>/history`

- **Method:** `GET`
- **URL:** `/api/staff/<hospital_id>/history`
- **Purpose:** View timestamped audit trail of all changes submitted for this hospital.
- **Headers:** `Authorization: Bearer <token>`
- **Response (`200 OK`):**
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "hospital_id": 5,
      "staff_id": "staff_fortis",
      "field_changed": "beds",
      "old_value": { "total_beds": 180, "occupied_beds": 112 },
      "new_value": { "total_beds": 180, "occupied_beds": 110, "admissions": 5, "discharges": 3 },
      "changed_at": "2026-09-15T16:28:41.123Z"
    }
  ]
}
```

---

## 15. GET `/health`

- **Method:** `GET`
- **URL:** `/health`
- **Purpose:** Basic system liveness check and database connection mode reporter.
- **Headers:** None required.
- **Response (`200 OK`):**
```json
{
  "service": "NexCare Healthcare Support API",
  "version": "1.0.0",
  "status": "healthy",
  "active_data_mode": "mock",
  "mysql_connected": false,
  "timestamp": "2026-09-15T16:28:40.912Z"
}
```
