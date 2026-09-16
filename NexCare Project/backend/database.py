"""
NexCare Database & Data Repository Layer
Supports dual operation:
1. Production-ready MySQL database backend (via mysql-connector-python)
2. Zero-dependency In-Memory Mock repository for rapid evaluation and demo fallback
"""

import json
import logging
import hashlib
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from .config import (
    DATA_MODE,
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DB,
    CROWD_THRESHOLDS,
    LOCALITY_COORDINATES,
    ALL_INDIA_COORDINATES,
    INDIA_LOCATIONS,
    haversine_distance,
)

logger = logging.getLogger("nexcare.database")
logging.basicConfig(level=logging.INFO)

RESOURCE_TYPES = [
    "ICU Beds",
    "Oxygen Support",
    "Pharmacy",
    "Laboratory",
    "X-ray",
    "CT Scan",
    "Blood Bank",
    "Emergency Department",
]

CANONICAL_RESOURCE_MAP = {
    "icu beds": "ICU Beds",
    "icu": "ICU Beds",
    "oxygen": "Oxygen Support",
    "oxygen support": "Oxygen Support",
    "pharmacy": "Pharmacy",
    "lab": "Laboratory",
    "laboratory": "Laboratory",
    "x-ray": "X-ray",
    "xray": "X-ray",
    "ct scan": "CT Scan",
    "ct": "CT Scan",
    "blood bank": "Blood Bank",
    "bloodbank": "Blood Bank",
    "ed": "Emergency Department",
    "emergency": "Emergency Department",
    "emergency department": "Emergency Department",
}

# Helper to hash passwords for demo authentication verification
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def compute_crowd_status_from_beds(total_beds: int, occupied_beds: int) -> str:
    """
    Auto-calculate crowd status based on bed occupancy percentage:
    occupancy % = Occupied Beds / Total Bed Capacity
    Green (Low) <= 40%
    Yellow (Moderate) 41% - 80%
    Red (High) > 80%
    """
    if not total_beds or total_beds <= 0:
        return "Low"
    occupancy_pct = (occupied_beds / total_beds) * 100.0
    if occupancy_pct <= 40.0:
        return "Low"
    elif occupancy_pct <= 80.0:
        return "Moderate"
    else:
        return "High"


def compute_crowd_status(current: int = 0, waiting: int = 0, admissions: int = 0, total_beds: int = 0, occupied_beds: int = 0) -> str:
    """
    Compute crowd status. If total_beds is provided, uses bed occupancy auto-calculation.
    Otherwise falls back to queue threshold calculation.
    """
    if total_beds > 0:
        return compute_crowd_status_from_beds(total_beds, occupied_beds)
    load = current + waiting + int(admissions * 0.4)
    if load <= CROWD_THRESHOLDS["low_max"]:
        return "Low"
    if load <= CROWD_THRESHOLDS["moderate_max"]:
        return "Moderate"
    return "High"

# ====================================================================
# IN-MEMORY MOCK DATA STORE (Tamil Nadu & Karnataka real hospitals)
# ====================================================================

MOCK_HOSPITALS = [
    {
        "id": 1,
        "name": "Apollo Main Hospitals",
        "state": "Tamil Nadu",
        "locality": "Greams Road",
        "address": "21, Greams Lane, Thousand Lights, Greams Road, Chennai - 600006",
        "approx_lat": 13.056,
        "approx_lng": 80.252,
        "type": "Private",
        "contact_number": "+91 44 2829 0200",
        "beds": {
            "total": 500,
            "occupied": 430,
            "available": 70,
            "today_admissions": 24,
            "today_discharges": 18
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 190,
            "waiting_patients": 24,
            "today_admissions": 24,
            "today_discharges": 18
        },
        "doctors": [
            {
                "id": 101,
                "name": "Dr. S. Ramanathan",
                "name_or_department": "General Medicine & Emergency",
                "department": "Emergency Medicine",
                "specialty": "Internal Medicine & Critical Care",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 45
            },
            {
                "id": 102,
                "name": "Dr. K. Swaminathan",
                "name_or_department": "Cardiology & Critical Care",
                "department": "Cardiology",
                "specialty": "Cardiology & Interventional Care",
                "status": "Available",
                "available_time": "09:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2001,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517650+00:00"
    },
    {
        "id": 2,
        "name": "Rajiv Gandhi Government General Hospital",
        "state": "Tamil Nadu",
        "locality": "Park Town",
        "address": "EVR Periyar Salai, Park Town, Chennai - 600003",
        "approx_lat": 13.0825,
        "approx_lng": 80.276,
        "type": "Government",
        "contact_number": "+91 44 2530 5000",
        "beds": {
            "total": 1800,
            "occupied": 1710,
            "available": 90,
            "today_admissions": 85,
            "today_discharges": 62
        },
        "doctor_status": "Limited",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 760,
            "waiting_patients": 130,
            "today_admissions": 85,
            "today_discharges": 62
        },
        "doctors": [
            {
                "id": 201,
                "name": "Dr. V. Chandran",
                "name_or_department": "Emergency Medicine (Triage)",
                "department": "Trauma & Emergency",
                "specialty": "Emergency Medicine & Trauma",
                "status": "Limited",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 100
            },
            {
                "id": 202,
                "name": "Dr. M. Soundararajan",
                "name_or_department": "General Medicine OPD",
                "department": "General Medicine",
                "specialty": "General Medicine",
                "status": "Limited",
                "available_time": "08:00 - 14:00",
                "consultation_capacity": 120
            },
            {
                "id": 2002,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Limited"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517669+00:00"
    },
    {
        "id": 3,
        "name": "Government Multi Super Speciality Hospital",
        "state": "Tamil Nadu",
        "locality": "Omandurar",
        "address": "Omandurar Government Estate, Anna Salai, Chennai - 600002",
        "approx_lat": 13.0694,
        "approx_lng": 80.2718,
        "type": "Government",
        "contact_number": "+91 44 2566 6000",
        "beds": {
            "total": 400,
            "occupied": 300,
            "available": 100,
            "today_admissions": 18,
            "today_discharges": 15
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 150,
            "waiting_patients": 18,
            "today_admissions": 18,
            "today_discharges": 15
        },
        "doctors": [
            {
                "id": 301,
                "name": "Dr. K. Meenakshi",
                "name_or_department": "Multi-Speciality Critical Care",
                "department": "Critical Care",
                "specialty": "Intensive & Critical Care",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 40
            },
            {
                "id": 302,
                "name": "Dr. P. Ravichandran",
                "name_or_department": "Cardiothoracic OPD",
                "department": "Cardiothoracic",
                "specialty": "Cardiothoracic Surgery",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 35
            },
            {
                "id": 2003,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517674+00:00"
    },
    {
        "id": 4,
        "name": "Government Kilpauk Medical College Hospital",
        "state": "Tamil Nadu",
        "locality": "Kilpauk",
        "address": "822, Poonamallee High Road, Near Kilpauk, Chennai - 600010",
        "approx_lat": 13.0805,
        "approx_lng": 80.2428,
        "type": "Government",
        "contact_number": "+91 44 2836 4951",
        "beds": {
            "total": 530,
            "occupied": 490,
            "available": 40,
            "today_admissions": 30,
            "today_discharges": 22
        },
        "doctor_status": "Limited",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 240,
            "waiting_patients": 45,
            "today_admissions": 30,
            "today_discharges": 22
        },
        "doctors": [
            {
                "id": 401,
                "name": "Dr. A. Joseph",
                "name_or_department": "Burns & Plastic Surgery / Trauma",
                "department": "Burns & Trauma",
                "specialty": "Plastic & Reconstructive Surgery",
                "status": "Limited",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 402,
                "name": "Dr. R. Kavitha",
                "name_or_department": "General Medicine",
                "department": "Internal Medicine",
                "specialty": "General Medicine",
                "status": "Limited",
                "available_time": "08:00 - 14:00",
                "consultation_capacity": 60
            },
            {
                "id": 2004,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Limited"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517678+00:00"
    },
    {
        "id": 5,
        "name": "Fortis Malar Hospital",
        "state": "Tamil Nadu",
        "locality": "Adyar",
        "address": "52, 1st Main Road, Gandhi Nagar, Adyar, Chennai - 600020",
        "approx_lat": 13.0067,
        "approx_lng": 80.257,
        "type": "Private",
        "contact_number": "+91 44 4289 2222",
        "beds": {
            "total": 180,
            "occupied": 112,
            "available": 68,
            "today_admissions": 12,
            "today_discharges": 8
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 8
        },
        "doctors": [
            {
                "id": 501,
                "name": "Dr. N. Parthasarathy",
                "name_or_department": "Emergency Department",
                "department": "Emergency Medicine",
                "specialty": "Emergency & Trauma Care",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 30
            },
            {
                "id": 502,
                "name": "Dr. Anita George",
                "name_or_department": "Cardiology & Internal Medicine",
                "department": "Cardiology",
                "specialty": "Cardiology",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2005,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517684+00:00"
    },
    {
        "id": 6,
        "name": "MIOT International",
        "state": "Tamil Nadu",
        "locality": "Manapakkam",
        "address": "4/112, Mount Poonamallee Road, Manapakkam, Chennai - 600089",
        "approx_lat": 13.0232,
        "approx_lng": 80.1786,
        "type": "Private",
        "contact_number": "+91 44 4200 2288",
        "beds": {
            "total": 1000,
            "occupied": 760,
            "available": 240,
            "today_admissions": 42,
            "today_discharges": 35
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 120,
            "waiting_patients": 22,
            "today_admissions": 42,
            "today_discharges": 35
        },
        "doctors": [
            {
                "id": 601,
                "name": "Dr. Prithvi Mohandas",
                "name_or_department": "Orthopaedics & Trauma Care",
                "department": "Orthopedics",
                "specialty": "Orthopedics & Joint Replacement",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 60
            },
            {
                "id": 602,
                "name": "Dr. S. Sundaram",
                "name_or_department": "Internal Medicine & Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonology & Respiratory Medicine",
                "status": "Available",
                "available_time": "09:00 - 18:00",
                "consultation_capacity": 40
            },
            {
                "id": 2006,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517908+00:00"
    },
    {
        "id": 7,
        "name": "Sri Ramachandra Medical Centre",
        "state": "Tamil Nadu",
        "locality": "Porur",
        "address": "No. 1, Ramachandra Nagar, Porur, Chennai - 600116",
        "approx_lat": 13.0382,
        "approx_lng": 80.1432,
        "type": "Private",
        "contact_number": "+91 44 4592 8500",
        "beds": {
            "total": 1200,
            "occupied": 690,
            "available": 510,
            "today_admissions": 50,
            "today_discharges": 40
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 28,
            "waiting_patients": 9,
            "today_admissions": 50,
            "today_discharges": 40
        },
        "doctors": [
            {
                "id": 701,
                "name": "Dr. T. S. Chandrasekhar",
                "name_or_department": "Emergency Medical Services",
                "department": "Emergency Medicine",
                "specialty": "Emergency Medicine",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 75
            },
            {
                "id": 702,
                "name": "Dr. Shanthi Mohan",
                "name_or_department": "General & Super Speciality OPD",
                "department": "Internal Medicine",
                "specialty": "General & Internal Medicine",
                "status": "Available",
                "available_time": "08:30 - 17:30",
                "consultation_capacity": 90
            },
            {
                "id": 2007,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517912+00:00"
    },
    {
        "id": 8,
        "name": "Madras Medical Mission Hospital",
        "state": "Tamil Nadu",
        "locality": "Mogappair",
        "address": "4A, Dr. J. J. Nagar, Mogappair, Chennai - 600037",
        "approx_lat": 13.085,
        "approx_lng": 80.1764,
        "type": "Private",
        "contact_number": "+91 44 2656 8000",
        "beds": {
            "total": 300,
            "occupied": 210,
            "available": 90,
            "today_admissions": 15,
            "today_discharges": 11
        },
        "doctor_status": "Limited",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 65,
            "waiting_patients": 14,
            "today_admissions": 15,
            "today_discharges": 11
        },
        "doctors": [
            {
                "id": 801,
                "name": "Dr. Thomas Kurian",
                "name_or_department": "Cardiac Sciences & Emergency",
                "department": "Cardiology",
                "specialty": "Cardiology & Electrophysiology",
                "status": "Limited",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 35
            },
            {
                "id": 802,
                "name": "Dr. Susan Varghese",
                "name_or_department": "General Medicine",
                "department": "General Medicine",
                "specialty": "General Medicine",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 30
            },
            {
                "id": 2008,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Limited"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517916+00:00"
    },
    {
        "id": 9,
        "name": "Dr. Mehta's Hospitals",
        "state": "Tamil Nadu",
        "locality": "Chetpet",
        "address": "No. 2, McNichols Road, 3rd Lane, Chetpet, Chennai - 600031",
        "approx_lat": 13.0722,
        "approx_lng": 80.2372,
        "type": "Private",
        "contact_number": "+91 44 4227 1001",
        "beds": {
            "total": 150,
            "occupied": 82,
            "available": 68,
            "today_admissions": 9,
            "today_discharges": 7
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 25,
            "waiting_patients": 5,
            "today_admissions": 9,
            "today_discharges": 7
        },
        "doctors": [
            {
                "id": 901,
                "name": "Dr. Usha Mehta",
                "name_or_department": "Pediatrics & Internal Medicine",
                "department": "Pediatrics",
                "specialty": "Pediatrics & Child Health",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 30
            },
            {
                "id": 902,
                "name": "Dr. R. Anand",
                "name_or_department": "General OPD Clinic",
                "department": "Family Medicine",
                "specialty": "Family & General Practice",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2009,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517922+00:00"
    },
    {
        "id": 10,
        "name": "Kauvery Hospital",
        "state": "Tamil Nadu",
        "locality": "Vadapalani",
        "address": "No. 12, Arcot Road, Vadapalani, Chennai - 600026",
        "approx_lat": 13.0514,
        "approx_lng": 80.2104,
        "type": "Private",
        "contact_number": "+91 44 4000 6000",
        "beds": {
            "total": 250,
            "occupied": 205,
            "available": 45,
            "today_admissions": 14,
            "today_discharges": 10
        },
        "doctor_status": "Unavailable",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 145,
            "waiting_patients": 34,
            "today_admissions": 14,
            "today_discharges": 10
        },
        "doctors": [
            {
                "id": 1001,
                "name": "Dr. K. Srinivas",
                "name_or_department": "Accident & Emergency Care",
                "department": "Emergency Medicine",
                "specialty": "Emergency Medicine",
                "status": "Unavailable",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 20
            },
            {
                "id": 1002,
                "name": "Dr. Geetha Rajan",
                "name_or_department": "Speciality Consultations",
                "department": "Super Speciality",
                "specialty": "Super Speciality Medicine",
                "status": "Limited",
                "available_time": "10:00 - 16:00",
                "consultation_capacity": 25
            },
            {
                "id": 2010,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Limited"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Limited"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517926+00:00"
    },
    {
        "id": 11,
        "name": "Manipal Hospital Old Airport Road",
        "state": "Karnataka",
        "locality": "Old Airport Road",
        "address": "98, HAL Old Airport Rd, Kodihalli, Bengaluru, Karnataka - 560017",
        "approx_lat": 12.9587,
        "approx_lng": 77.6483,
        "type": "Private",
        "contact_number": "+91 80 2502 4444",
        "beds": {
            "total": 600,
            "occupied": 490,
            "available": 110,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 45,
            "waiting_patients": 8,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 1101,
                "name": "Dr. S. K. Murthy",
                "name_or_department": "Critical Care & Pulmonology",
                "department": "Critical Care",
                "specialty": "Critical Care & Pulmonology",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 40
            },
            {
                "id": 1102,
                "name": "Dr. Ananya Hegde",
                "name_or_department": "Cardiology Institute",
                "department": "Cardiology",
                "specialty": "Cardiology & Cardiac Surgery",
                "status": "Available",
                "available_time": "09:00 - 17:30",
                "consultation_capacity": 30
            },
            {
                "id": 2011,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517929+00:00"
    },
    {
        "id": 12,
        "name": "Victoria Hospital (Bangalore Medical College)",
        "state": "Karnataka",
        "locality": "Kalasipalya",
        "address": "Fort Road, Near City Market, Kalasipalya, Bengaluru, Karnataka - 560002",
        "approx_lat": 12.9628,
        "approx_lng": 77.5752,
        "type": "Government",
        "contact_number": "+91 80 2670 1150",
        "beds": {
            "total": 1000,
            "occupied": 920,
            "available": 80,
            "today_admissions": 52,
            "today_discharges": 41
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 210,
            "waiting_patients": 38,
            "today_admissions": 52,
            "today_discharges": 41
        },
        "doctors": [
            {
                "id": 1201,
                "name": "Dr. B. K. Shivakumar",
                "name_or_department": "Emergency Triage & Trauma Unit",
                "department": "Trauma Care",
                "specialty": "Emergency Medicine",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 80
            },
            {
                "id": 1202,
                "name": "Dr. Leela Prasad",
                "name_or_department": "Department of General Surgery",
                "department": "Surgery",
                "specialty": "General & Laparoscopic Surgery",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 60
            },
            {
                "id": 2012,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517935+00:00"
    },
    {
        "id": 13,
        "name": "Narayana Institute of Cardiac Sciences (Health City)",
        "state": "Karnataka",
        "locality": "Bommasandra",
        "address": "258/A, Bommasandra Industrial Area, Anekal Taluk, Bengaluru, Karnataka - 560099",
        "approx_lat": 12.8173,
        "approx_lng": 77.6917,
        "type": "Private",
        "contact_number": "+91 80 7122 2222",
        "beds": {
            "total": 500,
            "occupied": 380,
            "available": 120,
            "today_admissions": 22,
            "today_discharges": 17
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 35,
            "waiting_patients": 6,
            "today_admissions": 22,
            "today_discharges": 17
        },
        "doctors": [
            {
                "id": 1301,
                "name": "Dr. Devi Shetty",
                "name_or_department": "Cardiac Emergency & Cath Lab",
                "department": "Cardiology",
                "specialty": "Cardiology & Cardiac Surgery",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 1302,
                "name": "Dr. Rajesh Gowda",
                "name_or_department": "Cardiovascular OPD",
                "department": "Cardiovascular",
                "specialty": "Interventional Cardiology",
                "status": "Available",
                "available_time": "09:00 - 18:00",
                "consultation_capacity": 45
            },
            {
                "id": 2013,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517941+00:00"
    },
    {
        "id": 14,
        "name": "Bowring and Lady Curzon Hospital",
        "state": "Karnataka",
        "locality": "Shivaji Nagar",
        "address": "Lady Curzon Road, Tasker Town, Shivaji Nagar, Bengaluru, Karnataka - 560001",
        "approx_lat": 12.9822,
        "approx_lng": 77.6047,
        "type": "Government",
        "contact_number": "+91 80 2559 1362",
        "beds": {
            "total": 686,
            "occupied": 610,
            "available": 76,
            "today_admissions": 34,
            "today_discharges": 25
        },
        "doctor_status": "Limited",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 160,
            "waiting_patients": 28,
            "today_admissions": 34,
            "today_discharges": 25
        },
        "doctors": [
            {
                "id": 1401,
                "name": "Dr. H. N. Manjunath",
                "name_or_department": "General Medicine OPD & Triage",
                "department": "General Medicine",
                "specialty": "General Medicine",
                "status": "Limited",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 70
            },
            {
                "id": 1402,
                "name": "Dr. Sumathi Rao",
                "name_or_department": "Pediatrics & Neonatal Care",
                "department": "Pediatrics",
                "specialty": "Pediatrics",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2014,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Limited"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517944+00:00"
    },
    {
        "id": 15,
        "name": "Fortis Hospital Bannerghatta Road",
        "state": "Karnataka",
        "locality": "Bannerghatta Road",
        "address": "154/9, Bannerghatta Road, Opposite IIM-B, Bengaluru, Karnataka - 560076",
        "approx_lat": 12.8943,
        "approx_lng": 77.5985,
        "type": "Private",
        "contact_number": "+91 80 6621 4444",
        "beds": {
            "total": 276,
            "occupied": 210,
            "available": 66,
            "today_admissions": 14,
            "today_discharges": 11
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 26,
            "waiting_patients": 5,
            "today_admissions": 14,
            "today_discharges": 11
        },
        "doctors": [
            {
                "id": 1501,
                "name": "Dr. Priya Venkatesh",
                "name_or_department": "Emergency & Acute Care",
                "department": "Emergency Medicine",
                "specialty": "Emergency & Trauma Care",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 35
            },
            {
                "id": 1502,
                "name": "Dr. Vivek Kumar",
                "name_or_department": "Orthopedics & Spine Institute",
                "department": "Orthopedics",
                "specialty": "Orthopedics",
                "status": "Available",
                "available_time": "09:30 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2015,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517949+00:00"
    },
    {
        "id": 16,
        "name": "St. John's Medical College Hospital",
        "state": "Karnataka",
        "locality": "Koramangala",
        "address": "Sarjapur Road, John Nagar, Koramangala, Bengaluru, Karnataka - 560034",
        "approx_lat": 12.9317,
        "approx_lng": 77.6186,
        "type": "Private",
        "contact_number": "+91 80 2206 5000",
        "beds": {
            "total": 1350,
            "occupied": 1180,
            "available": 170,
            "today_admissions": 60,
            "today_discharges": 48
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 180,
            "waiting_patients": 25,
            "today_admissions": 60,
            "today_discharges": 48
        },
        "doctors": [
            {
                "id": 1601,
                "name": "Dr. George Mathew",
                "name_or_department": "Department of Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Medicine & Triage",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 65
            },
            {
                "id": 1602,
                "name": "Dr. Mary Thomas",
                "name_or_department": "Internal Medicine & Nephrology",
                "department": "Nephrology",
                "specialty": "Nephrology & Internal Medicine",
                "status": "Available",
                "available_time": "08:30 - 17:00",
                "consultation_capacity": 50
            },
            {
                "id": 2016,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T17:11:39.517953+00:00"
    },
    {
        "id": 17,
        "name": "Thiruvananthapuram General Hospital",
        "state": "Kerala",
        "locality": "Thiruvananthapuram",
        "address": "100, MG Road, Near Central Circle, Thiruvananthapuram, Kerala",
        "approx_lat": 8.5241,
        "approx_lng": 76.9366,
        "type": "Private",
        "contact_number": "+91 17 2800 0017",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2017,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2018,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2019,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 18,
        "name": "Kochi Multi-Specialty Hospital",
        "state": "Kerala",
        "locality": "Kochi",
        "address": "101, MG Road, Near Central Circle, Kochi, Kerala",
        "approx_lat": 9.9392,
        "approx_lng": 76.2753,
        "type": "Government",
        "contact_number": "+91 18 2800 0018",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2020,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2021,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2022,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2023,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 19,
        "name": "Care Medical Centre Kozhikode",
        "state": "Kerala",
        "locality": "Kozhikode",
        "address": "102, MG Road, Near Central Circle, Kozhikode, Kerala",
        "approx_lat": 11.2748,
        "approx_lng": 75.7964,
        "type": "Private",
        "contact_number": "+91 19 2800 0019",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2024,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2025,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2026,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 20,
        "name": "Visakhapatnam General Hospital",
        "state": "Andhra Pradesh",
        "locality": "Visakhapatnam",
        "address": "100, MG Road, Near Central Circle, Visakhapatnam, Andhra Pradesh",
        "approx_lat": 17.6868,
        "approx_lng": 83.2185,
        "type": "Private",
        "contact_number": "+91 20 2800 0020",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2027,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2028,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2029,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 21,
        "name": "Vijayawada Multi-Specialty Hospital",
        "state": "Andhra Pradesh",
        "locality": "Vijayawada",
        "address": "101, MG Road, Near Central Circle, Vijayawada, Andhra Pradesh",
        "approx_lat": 16.5142,
        "approx_lng": 80.656,
        "type": "Government",
        "contact_number": "+91 21 2800 0021",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2030,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2031,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2032,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2033,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 22,
        "name": "Care Medical Centre Guntur",
        "state": "Andhra Pradesh",
        "locality": "Guntur",
        "address": "102, MG Road, Near Central Circle, Guntur, Andhra Pradesh",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 22 2800 0022",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2034,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2035,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2036,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 23,
        "name": "Hyderabad General Hospital",
        "state": "Telangana",
        "locality": "Hyderabad",
        "address": "100, MG Road, Near Central Circle, Hyderabad, Telangana",
        "approx_lat": 17.385,
        "approx_lng": 78.4867,
        "type": "Private",
        "contact_number": "+91 23 2800 0023",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2037,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2038,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2039,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 24,
        "name": "Warangal Multi-Specialty Hospital",
        "state": "Telangana",
        "locality": "Warangal",
        "address": "101, MG Road, Near Central Circle, Warangal, Telangana",
        "approx_lat": 17.9769,
        "approx_lng": 79.6021,
        "type": "Government",
        "contact_number": "+91 24 2800 0024",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2040,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2041,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2042,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2043,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 25,
        "name": "Care Medical Centre Nizamabad",
        "state": "Telangana",
        "locality": "Nizamabad",
        "address": "102, MG Road, Near Central Circle, Nizamabad, Telangana",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 25 2800 0025",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2044,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2045,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2046,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 26,
        "name": "Mumbai General Hospital",
        "state": "Maharashtra",
        "locality": "Mumbai",
        "address": "100, MG Road, Near Central Circle, Mumbai, Maharashtra",
        "approx_lat": 19.076,
        "approx_lng": 72.8777,
        "type": "Private",
        "contact_number": "+91 26 2800 0026",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2047,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2048,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2049,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 27,
        "name": "Pune Multi-Specialty Hospital",
        "state": "Maharashtra",
        "locality": "Pune",
        "address": "101, MG Road, Near Central Circle, Pune, Maharashtra",
        "approx_lat": 18.5284,
        "approx_lng": 73.8647,
        "type": "Government",
        "contact_number": "+91 27 2800 0027",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2050,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2051,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2052,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2053,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 28,
        "name": "Care Medical Centre Nagpur",
        "state": "Maharashtra",
        "locality": "Nagpur",
        "address": "102, MG Road, Near Central Circle, Nagpur, Maharashtra",
        "approx_lat": 21.1618,
        "approx_lng": 79.1042,
        "type": "Private",
        "contact_number": "+91 28 2800 0028",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2054,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2055,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2056,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 29,
        "name": "New Delhi General Hospital",
        "state": "Delhi (NCT)",
        "locality": "New Delhi",
        "address": "100, MG Road, Near Central Circle, New Delhi, Delhi (NCT)",
        "approx_lat": 28.6139,
        "approx_lng": 77.209,
        "type": "Private",
        "contact_number": "+91 29 2800 0029",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2057,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2058,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2059,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 30,
        "name": "Central Delhi Multi-Specialty Hospital",
        "state": "Delhi (NCT)",
        "locality": "Central Delhi",
        "address": "101, MG Road, Near Central Circle, Central Delhi, Delhi (NCT)",
        "approx_lat": 28.6528,
        "approx_lng": 77.2247,
        "type": "Government",
        "contact_number": "+91 30 2800 0030",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2060,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2061,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2062,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2063,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 31,
        "name": "Care Medical Centre South Delhi",
        "state": "Delhi (NCT)",
        "locality": "South Delhi",
        "address": "102, MG Road, Near Central Circle, South Delhi, Delhi (NCT)",
        "approx_lat": 28.5515,
        "approx_lng": 77.257,
        "type": "Private",
        "contact_number": "+91 31 2800 0031",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2064,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2065,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2066,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 32,
        "name": "Ahmedabad General Hospital",
        "state": "Gujarat",
        "locality": "Ahmedabad",
        "address": "100, MG Road, Near Central Circle, Ahmedabad, Gujarat",
        "approx_lat": 23.0225,
        "approx_lng": 72.5714,
        "type": "Private",
        "contact_number": "+91 32 2800 0032",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2067,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2068,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2069,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 33,
        "name": "Surat Multi-Specialty Hospital",
        "state": "Gujarat",
        "locality": "Surat",
        "address": "101, MG Road, Near Central Circle, Surat, Gujarat",
        "approx_lat": 21.1782,
        "approx_lng": 72.8391,
        "type": "Government",
        "contact_number": "+91 33 2800 0033",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2070,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2071,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2072,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2073,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 34,
        "name": "Care Medical Centre Vadodara",
        "state": "Gujarat",
        "locality": "Vadodara",
        "address": "102, MG Road, Near Central Circle, Vadodara, Gujarat",
        "approx_lat": 22.3232,
        "approx_lng": 73.1972,
        "type": "Private",
        "contact_number": "+91 34 2800 0034",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2074,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2075,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2076,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 35,
        "name": "Kolkata General Hospital",
        "state": "West Bengal",
        "locality": "Kolkata",
        "address": "100, MG Road, Near Central Circle, Kolkata, West Bengal",
        "approx_lat": 22.5726,
        "approx_lng": 88.3639,
        "type": "Private",
        "contact_number": "+91 35 2800 0035",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2077,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2078,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2079,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 36,
        "name": "Howrah Multi-Specialty Hospital",
        "state": "West Bengal",
        "locality": "Howrah",
        "address": "101, MG Road, Near Central Circle, Howrah, West Bengal",
        "approx_lat": 22.6038,
        "approx_lng": 88.2716,
        "type": "Government",
        "contact_number": "+91 36 2800 0036",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2080,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2081,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2082,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2083,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 37,
        "name": "Care Medical Centre Durgapur",
        "state": "West Bengal",
        "locality": "Durgapur",
        "address": "102, MG Road, Near Central Circle, Durgapur, West Bengal",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 37 2800 0037",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2084,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2085,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2086,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 38,
        "name": "Jaipur General Hospital",
        "state": "Rajasthan",
        "locality": "Jaipur",
        "address": "100, MG Road, Near Central Circle, Jaipur, Rajasthan",
        "approx_lat": 26.9124,
        "approx_lng": 75.7873,
        "type": "Private",
        "contact_number": "+91 38 2800 0038",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2087,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2088,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2089,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 39,
        "name": "Jodhpur Multi-Specialty Hospital",
        "state": "Rajasthan",
        "locality": "Jodhpur",
        "address": "101, MG Road, Near Central Circle, Jodhpur, Rajasthan",
        "approx_lat": 26.2469,
        "approx_lng": 73.0323,
        "type": "Government",
        "contact_number": "+91 39 2800 0039",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2090,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2091,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2092,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2093,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 40,
        "name": "Care Medical Centre Kota",
        "state": "Rajasthan",
        "locality": "Kota",
        "address": "102, MG Road, Near Central Circle, Kota, Rajasthan",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 40 2800 0040",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2094,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2095,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2096,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 41,
        "name": "Lucknow General Hospital",
        "state": "Uttar Pradesh",
        "locality": "Lucknow",
        "address": "100, MG Road, Near Central Circle, Lucknow, Uttar Pradesh",
        "approx_lat": 26.8467,
        "approx_lng": 80.9462,
        "type": "Private",
        "contact_number": "+91 41 2800 0041",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2097,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2098,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2099,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 42,
        "name": "Kanpur Multi-Specialty Hospital",
        "state": "Uttar Pradesh",
        "locality": "Kanpur",
        "address": "101, MG Road, Near Central Circle, Kanpur, Uttar Pradesh",
        "approx_lat": 26.4579,
        "approx_lng": 80.3399,
        "type": "Government",
        "contact_number": "+91 42 2800 0042",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2100,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2101,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2102,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2103,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 43,
        "name": "Care Medical Centre Varanasi",
        "state": "Uttar Pradesh",
        "locality": "Varanasi",
        "address": "102, MG Road, Near Central Circle, Varanasi, Uttar Pradesh",
        "approx_lat": 25.3336,
        "approx_lng": 82.9899,
        "type": "Private",
        "contact_number": "+91 43 2800 0043",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2104,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2105,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2106,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 44,
        "name": "Bhopal General Hospital",
        "state": "Madhya Pradesh",
        "locality": "Bhopal",
        "address": "100, MG Road, Near Central Circle, Bhopal, Madhya Pradesh",
        "approx_lat": 23.2599,
        "approx_lng": 77.4126,
        "type": "Private",
        "contact_number": "+91 44 2800 0044",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2107,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2108,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2109,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 45,
        "name": "Indore Multi-Specialty Hospital",
        "state": "Madhya Pradesh",
        "locality": "Indore",
        "address": "101, MG Road, Near Central Circle, Indore, Madhya Pradesh",
        "approx_lat": 22.7276,
        "approx_lng": 75.8657,
        "type": "Government",
        "contact_number": "+91 45 2800 0045",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2110,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2111,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2112,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2113,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 46,
        "name": "Care Medical Centre Jabalpur",
        "state": "Madhya Pradesh",
        "locality": "Jabalpur",
        "address": "102, MG Road, Near Central Circle, Jabalpur, Madhya Pradesh",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 46 2800 0046",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2114,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2115,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2116,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 47,
        "name": "Patna General Hospital",
        "state": "Bihar",
        "locality": "Patna",
        "address": "100, MG Road, Near Central Circle, Patna, Bihar",
        "approx_lat": 25.5941,
        "approx_lng": 85.1376,
        "type": "Private",
        "contact_number": "+91 47 2800 0047",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2117,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2118,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2119,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 48,
        "name": "Gaya Multi-Specialty Hospital",
        "state": "Bihar",
        "locality": "Gaya",
        "address": "101, MG Road, Near Central Circle, Gaya, Bihar",
        "approx_lat": 24.7994,
        "approx_lng": 85.0082,
        "type": "Government",
        "contact_number": "+91 48 2800 0048",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2120,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2121,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2122,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2123,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 49,
        "name": "Care Medical Centre Bhagalpur",
        "state": "Bihar",
        "locality": "Bhagalpur",
        "address": "102, MG Road, Near Central Circle, Bhagalpur, Bihar",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 49 2800 0049",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2124,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2125,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2126,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 50,
        "name": "Chandigarh General Hospital",
        "state": "Punjab",
        "locality": "Chandigarh",
        "address": "100, MG Road, Near Central Circle, Chandigarh, Punjab",
        "approx_lat": 30.7333,
        "approx_lng": 76.7794,
        "type": "Private",
        "contact_number": "+91 50 2800 0050",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2127,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2128,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2129,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 51,
        "name": "Ludhiana Multi-Specialty Hospital",
        "state": "Punjab",
        "locality": "Ludhiana",
        "address": "101, MG Road, Near Central Circle, Ludhiana, Punjab",
        "approx_lat": 30.909,
        "approx_lng": 75.8653,
        "type": "Government",
        "contact_number": "+91 51 2800 0051",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2130,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2131,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2132,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2133,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 52,
        "name": "Care Medical Centre Amritsar",
        "state": "Punjab",
        "locality": "Amritsar",
        "address": "102, MG Road, Near Central Circle, Amritsar, Punjab",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 52 2800 0052",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2134,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2135,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2136,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 53,
        "name": "Gurugram General Hospital",
        "state": "Haryana",
        "locality": "Gurugram",
        "address": "100, MG Road, Near Central Circle, Gurugram, Haryana",
        "approx_lat": 28.4595,
        "approx_lng": 77.0266,
        "type": "Private",
        "contact_number": "+91 53 2800 0053",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2137,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2138,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2139,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 54,
        "name": "Faridabad Multi-Specialty Hospital",
        "state": "Haryana",
        "locality": "Faridabad",
        "address": "101, MG Road, Near Central Circle, Faridabad, Haryana",
        "approx_lat": 28.4169,
        "approx_lng": 77.3258,
        "type": "Government",
        "contact_number": "+91 54 2800 0054",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2140,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2141,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2142,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2143,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 55,
        "name": "Care Medical Centre Panipat",
        "state": "Haryana",
        "locality": "Panipat",
        "address": "102, MG Road, Near Central Circle, Panipat, Haryana",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 55 2800 0055",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2144,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2145,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2146,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 56,
        "name": "Bhubaneswar General Hospital",
        "state": "Odisha",
        "locality": "Bhubaneswar",
        "address": "100, MG Road, Near Central Circle, Bhubaneswar, Odisha",
        "approx_lat": 20.2961,
        "approx_lng": 85.8245,
        "type": "Private",
        "contact_number": "+91 56 2800 0056",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2147,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2148,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2149,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 57,
        "name": "Cuttack Multi-Specialty Hospital",
        "state": "Odisha",
        "locality": "Cuttack",
        "address": "101, MG Road, Near Central Circle, Cuttack, Odisha",
        "approx_lat": 20.4705,
        "approx_lng": 85.891,
        "type": "Government",
        "contact_number": "+91 57 2800 0057",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2150,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2151,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2152,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2153,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 58,
        "name": "Care Medical Centre Rourkela",
        "state": "Odisha",
        "locality": "Rourkela",
        "address": "102, MG Road, Near Central Circle, Rourkela, Odisha",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 58 2800 0058",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2154,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2155,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2156,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 59,
        "name": "Guwahati General Hospital",
        "state": "Assam",
        "locality": "Guwahati",
        "address": "100, MG Road, Near Central Circle, Guwahati, Assam",
        "approx_lat": 26.1445,
        "approx_lng": 91.7362,
        "type": "Private",
        "contact_number": "+91 59 2800 0059",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2157,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2158,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2159,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 60,
        "name": "Silchar Multi-Specialty Hospital",
        "state": "Assam",
        "locality": "Silchar",
        "address": "101, MG Road, Near Central Circle, Silchar, Assam",
        "approx_lat": 20.008,
        "approx_lng": 78.008,
        "type": "Government",
        "contact_number": "+91 60 2800 0060",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2160,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2161,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2162,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2163,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 61,
        "name": "Care Medical Centre Dibrugarh",
        "state": "Assam",
        "locality": "Dibrugarh",
        "address": "102, MG Road, Near Central Circle, Dibrugarh, Assam",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 61 2800 0061",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2164,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2165,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2166,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 62,
        "name": "Panaji General Hospital",
        "state": "Goa",
        "locality": "Panaji",
        "address": "100, MG Road, Near Central Circle, Panaji, Goa",
        "approx_lat": 15.4909,
        "approx_lng": 73.8278,
        "type": "Private",
        "contact_number": "+91 62 2800 0062",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2167,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2168,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2169,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 63,
        "name": "Margao Multi-Specialty Hospital",
        "state": "Goa",
        "locality": "Margao",
        "address": "101, MG Road, Near Central Circle, Margao, Goa",
        "approx_lat": 15.2912,
        "approx_lng": 73.9942,
        "type": "Government",
        "contact_number": "+91 63 2800 0063",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2170,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2171,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2172,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2173,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 64,
        "name": "Care Medical Centre Vasco da Gama",
        "state": "Goa",
        "locality": "Vasco da Gama",
        "address": "102, MG Road, Near Central Circle, Vasco da Gama, Goa",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 64 2800 0064",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2174,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2175,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2176,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 65,
        "name": "Puducherry General Hospital",
        "state": "Puducherry",
        "locality": "Puducherry",
        "address": "100, MG Road, Near Central Circle, Puducherry, Puducherry",
        "approx_lat": 11.9416,
        "approx_lng": 79.8083,
        "type": "Private",
        "contact_number": "+91 65 2800 0065",
        "beds": {
            "total": 250,
            "occupied": 80,
            "available": 170,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctor_status": "Limited",
        "crowd_status": "Low",
        "crowd": {
            "current_patients": 32,
            "waiting_patients": 6,
            "today_admissions": 12,
            "today_discharges": 9
        },
        "doctors": [
            {
                "id": 2177,
                "name": "Dr. Ananya Rao",
                "name_or_department": "Dr. Ananya Rao \u2014 Cardiology",
                "department": "Cardiology",
                "specialty": "Cardiologist",
                "status": "Available",
                "available_time": "09:00 - 17:00",
                "consultation_capacity": 35
            },
            {
                "id": 2178,
                "name": "Dr. Vikram Nair",
                "name_or_department": "Dr. Vikram Nair \u2014 Orthopedics",
                "department": "Orthopedics",
                "specialty": "Orthopedic Surgeon",
                "status": "Available",
                "available_time": "10:00 - 18:00",
                "consultation_capacity": 30
            },
            {
                "id": 2179,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Limited",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Limited"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Limited"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 66,
        "name": "Karaikal Multi-Specialty Hospital",
        "state": "Puducherry",
        "locality": "Karaikal",
        "address": "101, MG Road, Near Central Circle, Karaikal, Puducherry",
        "approx_lat": 20.008,
        "approx_lng": 78.008,
        "type": "Government",
        "contact_number": "+91 66 2800 0066",
        "beds": {
            "total": 320,
            "occupied": 190,
            "available": 130,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctor_status": "Available",
        "crowd_status": "Moderate",
        "crowd": {
            "current_patients": 76,
            "waiting_patients": 15,
            "today_admissions": 18,
            "today_discharges": 14
        },
        "doctors": [
            {
                "id": 2180,
                "name": "Dr. Priya Menon",
                "name_or_department": "Dr. Priya Menon \u2014 Pediatrics",
                "department": "Pediatrics",
                "specialty": "Pediatrician",
                "status": "Available",
                "available_time": "09:00 - 16:00",
                "consultation_capacity": 40
            },
            {
                "id": 2181,
                "name": "Dr. Rajesh Kumar",
                "name_or_department": "Dr. Rajesh Kumar \u2014 Emergency Medicine",
                "department": "Emergency Medicine",
                "specialty": "Emergency Physician",
                "status": "Available",
                "available_time": "24x7 / On-Duty",
                "consultation_capacity": 50
            },
            {
                "id": 2182,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2183,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Available"
            },
            {
                "resource_type": "X-ray",
                "status": "Limited"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    },
    {
        "id": 67,
        "name": "Care Medical Centre Mahe",
        "state": "Puducherry",
        "locality": "Mahe",
        "address": "102, MG Road, Near Central Circle, Mahe, Puducherry",
        "approx_lat": 20.016,
        "approx_lng": 78.016,
        "type": "Private",
        "contact_number": "+91 67 2800 0067",
        "beds": {
            "total": 450,
            "occupied": 390,
            "available": 60,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctor_status": "Available",
        "crowd_status": "High",
        "crowd": {
            "current_patients": 156,
            "waiting_patients": 31,
            "today_admissions": 28,
            "today_discharges": 20
        },
        "doctors": [
            {
                "id": 2184,
                "name": "Dr. Sanjay Verma",
                "name_or_department": "Dr. Sanjay Verma \u2014 General Medicine",
                "department": "General Medicine",
                "specialty": "General Physician",
                "status": "Available",
                "available_time": "08:30 - 16:30",
                "consultation_capacity": 45
            },
            {
                "id": 2185,
                "name": "Dr. Sneha Patil",
                "name_or_department": "Dr. Sneha Patil \u2014 Neurology",
                "department": "Neurology",
                "specialty": "Neurologist",
                "status": "Available",
                "available_time": "10:00 - 17:00",
                "consultation_capacity": 25
            },
            {
                "id": 2186,
                "name": "Dr. Arun Sharma",
                "name_or_department": "Dr. Arun Sharma \u2014 Pulmonology",
                "department": "Pulmonology",
                "specialty": "Pulmonologist",
                "status": "Limited",
                "available_time": "09:00 - 15:00",
                "consultation_capacity": 30
            }
        ],
        "resources": [
            {
                "resource_type": "ICU Beds",
                "status": "Available"
            },
            {
                "resource_type": "Oxygen Support",
                "status": "Available"
            },
            {
                "resource_type": "Pharmacy",
                "status": "Available"
            },
            {
                "resource_type": "Laboratory",
                "status": "Limited"
            },
            {
                "resource_type": "X-ray",
                "status": "Available"
            },
            {
                "resource_type": "CT Scan",
                "status": "Available"
            },
            {
                "resource_type": "Blood Bank",
                "status": "Available"
            },
            {
                "resource_type": "Emergency Department",
                "status": "Available"
            }
        ],
        "last_updated": "2026-09-15T22:30:00.000Z"
    }
]

# Staff users for demo authentication
MOCK_STAFF = {
    "demo-staff": {"hospital_id": 5, "staff_id": "demo-staff", "password": "demo123", "name": "Default Demo Staff (Fortis)"},
    "staff_apollo": {"hospital_id": 1, "staff_id": "staff_apollo", "password": "demo123", "name": "Dr. S. K. Apollo Admin"},
    "staff_rggh": {"hospital_id": 2, "staff_id": "staff_rggh", "password": "demo123", "name": "Dr. V. Ramanathan (RGGGH)"},
    "staff_omandurar": {"hospital_id": 3, "staff_id": "staff_omandurar", "password": "demo123", "name": "Dr. K. Meenakshi (Omandurar)"},
    "staff_kilpauk": {"hospital_id": 4, "staff_id": "staff_kilpauk", "password": "demo123", "name": "Dr. A. Joseph (KMCH)"},
    "staff_fortis": {"hospital_id": 5, "staff_id": "staff_fortis", "password": "demo123", "name": "Nurse Supervisor Deepa (Fortis)"},
    "staff_miot": {"hospital_id": 6, "staff_id": "staff_miot", "password": "demo123", "name": "Duty Manager Karthik (MIOT)"},
    "staff_srmc": {"hospital_id": 7, "staff_id": "staff_srmc", "password": "demo123", "name": "Chief Administrator Priya (SRMC)"},
    "staff_mmm": {"hospital_id": 8, "staff_id": "staff_mmm", "password": "demo123", "name": "Dr. Thomas Kurian (MMM)"},
    "staff_mehta": {"hospital_id": 9, "staff_id": "staff_mehta", "password": "demo123", "name": "Operations Head Anand (Mehta)"},
    "staff_kauvery": {"hospital_id": 10, "staff_id": "staff_kauvery", "password": "demo123", "name": "Nurse In-Charge Geetha (Kauvery)"},
    "staff_manipal": {"hospital_id": 11, "staff_id": "staff_manipal", "password": "demo123", "name": "Dr. Ramesh Rao (Manipal Bengaluru)"},
    "staff_narayana": {"hospital_id": 13, "staff_id": "staff_narayana", "password": "demo123", "name": "Admin Deepa Hegde (Narayana Health)"},
    "staff_kerala": {"hospital_id": 17, "staff_id": "staff_kerala", "password": "demo123", "name": "Dr. K. George (Kochi General)"},
    "staff_delhi": {"hospital_id": 33, "staff_id": "staff_delhi", "password": "demo123", "name": "Dr. R. Sharma (Delhi General)"},
    "staff_mumbai": {"hospital_id": 29, "staff_id": "staff_mumbai", "password": "demo123", "name": "Dr. A. Deshmukh (Mumbai General)"},
}

MOCK_HISTORY = [
    {
        "hospital_id": 5,
        "staff_id": "staff_fortis",
        "field_changed": "beds",
        "old_value": {"total_beds": 180, "occupied_beds": 115},
        "new_value": {"total_beds": 180, "occupied_beds": 112, "today_admissions": 12, "today_discharges": 8},
        "changed_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "hospital_id": 5,
        "staff_id": "staff_fortis",
        "field_changed": "resources",
        "old_value": [{"resource_type": "ICU Beds", "status": "Available"}],
        "new_value": [{"resource_type": "ICU Beds", "status": "Available"}, {"resource_type": "Oxygen Support", "status": "Available"}],
        "changed_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "hospital_id": 1,
        "staff_id": "staff_apollo",
        "field_changed": "beds",
        "old_value": {"total_beds": 500, "occupied_beds": 360},
        "new_value": {"total_beds": 500, "occupied_beds": 348, "today_admissions": 15, "today_discharges": 10},
        "changed_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "hospital_id": 17,
        "staff_id": "staff_kerala",
        "field_changed": "resources",
        "old_value": [{"resource_type": "Oxygen Support", "status": "Available"}],
        "new_value": [{"resource_type": "Oxygen Support", "status": "Available"}, {"resource_type": "ICU Beds", "status": "Available"}],
        "changed_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "hospital_id": 21,
        "staff_id": "staff_delhi",
        "field_changed": "beds",
        "old_value": {"total_beds": 350, "occupied_beds": 240},
        "new_value": {"total_beds": 350, "occupied_beds": 228, "today_admissions": 8, "today_discharges": 5},
        "changed_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "hospital_id": 33,
        "staff_id": "staff_mumbai",
        "field_changed": "doctors",
        "old_value": [{"name": "Dr. Aarav Mehta", "status": "Available"}],
        "new_value": [{"name": "Dr. Aarav Mehta", "status": "Available"}, {"name": "Dr. Rohit Deshmukh", "status": "Available"}],
        "changed_at": datetime.now(timezone.utc).isoformat()
    }
]

# Simulated Ambulances for Emergency Routing
MOCK_AMBULANCES = [
    {"id": 1, "hospital_id": 1, "ambulance_code": "AMB-TN-01", "status": "Available", "driver_name": "Karthik R.", "contact_number": "+91 98401 22331"},
    {"id": 2, "hospital_id": 1, "ambulance_code": "AMB-TN-02", "status": "Available", "driver_name": "Suresh Kumar", "contact_number": "+91 98401 22332"},
    {"id": 3, "hospital_id": 2, "ambulance_code": "AMB-TN-03", "status": "Available", "driver_name": "Murugan P.", "contact_number": "+91 98401 22333"},
    {"id": 4, "hospital_id": 3, "ambulance_code": "AMB-TN-04", "status": "Available", "driver_name": "Venkatesh S.", "contact_number": "+91 98401 22334"},
    {"id": 5, "hospital_id": 4, "ambulance_code": "AMB-TN-05", "status": "Available", "driver_name": "Dinesh Babu", "contact_number": "+91 98401 22335"},
    {"id": 6, "hospital_id": 5, "ambulance_code": "AMB-TN-06", "status": "Available", "driver_name": "Praveen Raj", "contact_number": "+91 98401 22336"},
    {"id": 7, "hospital_id": 6, "ambulance_code": "AMB-TN-07", "status": "Available", "driver_name": "Anand S.", "contact_number": "+91 98401 22337"},
    {"id": 8, "hospital_id": 7, "ambulance_code": "AMB-TN-08", "status": "Available", "driver_name": "Vijay K.", "contact_number": "+91 98401 22338"},
    {"id": 9, "hospital_id": 8, "ambulance_code": "AMB-TN-09", "status": "Available", "driver_name": "Selvam M.", "contact_number": "+91 98401 22339"},
    {"id": 10, "hospital_id": 9, "ambulance_code": "AMB-TN-10", "status": "Available", "driver_name": "Gopal N.", "contact_number": "+91 98401 22340"},
    {"id": 11, "hospital_id": 10, "ambulance_code": "AMB-TN-11", "status": "Available", "driver_name": "Saravanan T.", "contact_number": "+91 98401 22341"},
    {"id": 12, "hospital_id": 11, "ambulance_code": "AMB-KA-01", "status": "Available", "driver_name": "Manjunath H.", "contact_number": "+91 98801 11221"},
    {"id": 13, "hospital_id": 12, "ambulance_code": "AMB-KA-02", "status": "Available", "driver_name": "Basavaraj M.", "contact_number": "+91 98801 11222"},
    {"id": 14, "hospital_id": 13, "ambulance_code": "AMB-KA-03", "status": "Available", "driver_name": "Ramesh Gowda", "contact_number": "+91 98801 11223"},
    {"id": 15, "hospital_id": 14, "ambulance_code": "AMB-KA-04", "status": "Available", "driver_name": "Shivakumar N.", "contact_number": "+91 98801 11224"},
    {"id": 16, "hospital_id": 15, "ambulance_code": "AMB-KA-05", "status": "Available", "driver_name": "Raghavendra K.", "contact_number": "+91 98801 11225"},
    {"id": 17, "hospital_id": 16, "ambulance_code": "AMB-KA-06", "status": "Available", "driver_name": "Prashanth B.", "contact_number": "+91 98801 11226"},
    {"id": 18, "hospital_id": 17, "ambulance_code": "AMB-KL-01", "status": "Available", "driver_name": "Biju Varghese", "contact_number": "+91 98470 12345"},
    {"id": 19, "hospital_id": 21, "ambulance_code": "AMB-DL-01", "status": "Available", "driver_name": "Amit Tyagi", "contact_number": "+91 98110 54321"},
    {"id": 20, "hospital_id": 29, "ambulance_code": "AMB-MH-01", "status": "Available", "driver_name": "Santosh Patil", "contact_number": "+91 98200 98765"},
    {"id": 21, "hospital_id": 33, "ambulance_code": "AMB-DL-02", "status": "Available", "driver_name": "Deepak Verma", "contact_number": "+91 98110 99887"},
]

# Ensure every hospital in mock database has at least one registered ambulance
_existing_amb_hids = {a["hospital_id"] for a in MOCK_AMBULANCES}
for _h in MOCK_HOSPITALS:
    _hid = _h["id"]
    if _hid not in _existing_amb_hids:
        _st_code = "".join([w[0] for w in _h.get("state", "IN").split() if w])[:2].upper()
        MOCK_AMBULANCES.append({
            "id": len(MOCK_AMBULANCES) + 1,
            "hospital_id": _hid,
            "ambulance_code": f"AMB-{_st_code}-{_hid:02d}",
            "status": "Available",
            "driver_name": f"Operator {_h.get('locality', 'Emergency')}",
            "contact_number": f"+91 98000 {_hid:05d}"
        })
        _existing_amb_hids.add(_hid)

# Mock in-memory emergency requests
MOCK_EMERGENCY_REQUESTS = []

# Enforce Automatic Bed Integrity Formula across all mock hospitals:
# Available Beds = Total Beds - Occupied Beds - Blocked Beds
for _h in MOCK_HOSPITALS:
    if "beds" in _h:
        if "blocked" not in _h["beds"]:
            _h["beds"]["blocked"] = 0
        _tot = _h["beds"].get("total", 0)
        _occ = _h["beds"].get("occupied", 0)
        _blk = _h["beds"].get("blocked", 0)
        _h["beds"]["available"] = max(0, _tot - _occ - _blk)

# Database connection manager
class DataRepository:
    def __init__(self):
        self.mode = DATA_MODE
        self._mysql_available = False
        if self.mode == "mysql":
            self._init_mysql()
        else:
            logger.info("[NexCare Repository] Running in In-Memory Mock Data Mode.")

    def _init_mysql(self):
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            if conn.is_connected():
                conn.close()
                self._mysql_available = True
                logger.info(f"[NexCare Repository] Successfully connected to MySQL database '{MYSQL_DB}'.")
        except Exception as e:
            logger.warning(f"[NexCare Repository] MySQL connection failed ({e}). Falling back to Mock Data Mode.")
            self.mode = "mock"
            self._mysql_available = False

    def get_connection(self):
        if self.mode != "mysql" or not self._mysql_available:
            return None
        import mysql.connector
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )

    def _find_state_for_locality(self, locality_name):
        """Helper to discover which state a locality belongs to from INDIA_LOCATIONS"""
        if not locality_name:
            return None
        loc_lower = locality_name.lower().strip()
        for state, cities in INDIA_LOCATIONS.items():
            for c in cities:
                if c.lower() == loc_lower or loc_lower in c.lower() or c.lower() in loc_lower:
                    return state
        return None

    def _calculate_hospital_distance(self, hospital, patient_locality=None, lat=None, lng=None):
        """Calculate dynamic distance from patient's coordinates or selected locality"""
        hosp_lat = hospital.get("approx_lat", 13.0400)
        hosp_lng = hospital.get("approx_lng", 80.2300)

        # 1. Direct coordinates if provided
        if lat is not None and lng is not None:
            try:
                return haversine_distance(float(lat), float(lng), hosp_lat, hosp_lng)
            except (ValueError, TypeError):
                pass

        # 2. Named locality or all-India city lookup
        if patient_locality:
            coords = ALL_INDIA_COORDINATES.get(patient_locality) or LOCALITY_COORDINATES.get(patient_locality)
            if coords:
                pat_lat, pat_lng = coords
                return haversine_distance(pat_lat, pat_lng, hosp_lat, hosp_lng)

        # 3. Fallback distance approximation
        return hospital.get("distance_km", 6.5)

    def get_hospitals(self, locality=None, hospital_type=None, patient_locality=None, search=None, lat=None, lng=None, state=None):
        if self.mode == "mysql" and self._mysql_available:
            try:
                return self._get_hospitals_mysql(locality, hospital_type, patient_locality, search, lat, lng, state)
            except Exception as e:
                logger.error(f"MySQL error in get_hospitals: {e}. Falling back to mock data.")
        
        target_state = state
        results = []
        for h in deepcopy(MOCK_HOSPITALS):
            # Compute dynamic distance
            h["distance_km"] = self._calculate_hospital_distance(h, patient_locality=patient_locality, lat=lat, lng=lng)
            
            # Apply state filter
            if target_state:
                h_state = h.get("state", "Tamil Nadu")
                t_low = target_state.lower().strip()
                hs_low = h_state.lower().strip()
                if t_low != hs_low and t_low not in hs_low and hs_low not in t_low:
                    continue

            # Apply locality filter
            if locality and h["locality"].lower() != locality.lower():
                continue
            if hospital_type and h["type"].lower() != hospital_type.lower():
                continue
            if search:
                s = search.lower()
                if s not in h["name"].lower() and s not in h["locality"].lower() and s not in h["address"].lower():
                    continue
            results.append(h)
        if patient_locality or (lat is not None and lng is not None):
            results.sort(key=lambda x: x.get("distance_km", 9999))
        return results

    def _get_hospitals_mysql(self, locality=None, hospital_type=None, patient_locality=None, search=None, lat=None, lng=None, state=None):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM hospitals WHERE 1=1"
        params = []
        
        target_state = state

        if target_state:
            query += " AND (LOWER(state) = LOWER(%s) OR LOWER(state) LIKE %s)"
            params.extend([target_state, f"%{target_state.lower()}%"])
        if locality:
            query += " AND LOWER(locality) = LOWER(%s)"
            params.append(locality)
        if hospital_type:
            query += " AND LOWER(type) = LOWER(%s)"
            params.append(hospital_type)
        if search:
            query += " AND (LOWER(name) LIKE %s OR LOWER(locality) LIKE %s OR LOWER(address) LIKE %s)"
            params.extend([f"%{search.lower()}%", f"%{search.lower()}%", f"%{search.lower()}%"])
        cursor.execute(query, params)
        hospitals_raw = cursor.fetchall()
        
        results = []
        for h in hospitals_raw:
            hid = h["id"]
            h["approx_lat"] = float(h["approx_lat"]) if h["approx_lat"] is not None else 13.04
            h["approx_lng"] = float(h["approx_lng"]) if h["approx_lng"] is not None else 80.23
            h["distance_km"] = self._calculate_hospital_distance(h, patient_locality=patient_locality, lat=lat, lng=lng)
            
            # Fetch beds
            cursor.execute("SELECT total_beds, occupied_beds, today_admissions, today_discharges, updated_at FROM hospital_beds WHERE hospital_id = %s LIMIT 1", (hid,))
            bed_row = cursor.fetchone()
            if bed_row:
                total = bed_row["total_beds"]
                occupied = bed_row["occupied_beds"]
                today_adm = bed_row.get("today_admissions", 0) or 0
                today_dis = bed_row.get("today_discharges", 0) or 0
                h["beds"] = {
                    "total": total,
                    "occupied": occupied,
                    "available": total - occupied,
                    "today_admissions": today_adm,
                    "today_discharges": today_dis,
                }
            else:
                h["beds"] = {"total": 100, "occupied": 50, "available": 50, "today_admissions": 0, "today_discharges": 0}

            # Fetch crowd
            cursor.execute("SELECT current_patients, waiting_patients, today_admissions, today_discharges, crowd_status FROM crowd_updates WHERE hospital_id = %s LIMIT 1", (hid,))
            crowd_row = cursor.fetchone()
            if crowd_row:
                h["crowd"] = {
                    "current_patients": crowd_row["current_patients"],
                    "waiting_patients": crowd_row["waiting_patients"],
                    "today_admissions": crowd_row.get("today_admissions", 0) or 0,
                    "today_discharges": crowd_row.get("today_discharges", 0) or 0,
                }
                h["crowd_status"] = crowd_row["crowd_status"]
            else:
                h["crowd"] = {"current_patients": 30, "waiting_patients": 5, "today_admissions": 0, "today_discharges": 0}
                h["crowd_status"] = "Low"

            # Fetch doctors with specialty
            cursor.execute("SELECT id, name_or_department, specialty, status, available_time, consultation_capacity FROM doctors WHERE hospital_id = %s", (hid,))
            doc_rows = cursor.fetchall()
            h["doctors"] = doc_rows or []
            if doc_rows:
                statuses = [d["status"] for d in doc_rows]
                if "Available" in statuses:
                    h["doctor_status"] = "Available"
                elif "Limited" in statuses:
                    h["doctor_status"] = "Limited"
                else:
                    h["doctor_status"] = "Unavailable"
            else:
                h["doctor_status"] = "Unavailable"

            # Fetch resources
            cursor.execute("SELECT resource_type, status FROM hospital_resources WHERE hospital_id = %s", (hid,))
            res_rows = cursor.fetchall()
            h["resources"] = res_rows or [{"resource_type": r, "status": "Available"} for r in RESOURCE_TYPES]
            
            h["last_updated"] = (h.get("updated_at") or datetime.now(timezone.utc)).isoformat()
            results.append(h)
        cursor.close()
        conn.close()
        if patient_locality or (lat is not None and lng is not None):
            results.sort(key=lambda x: x.get("distance_km", 9999))
        return results

    def get_hospital(self, hospital_id, patient_locality=None, lat=None, lng=None):
        hospitals = self.get_hospitals(patient_locality=patient_locality, lat=lat, lng=lng)
        for h in hospitals:
            if h["id"] == hospital_id:
                return h
        return None

    def verify_staff(self, staff_id, password):
        # Check mock credentials
        if staff_id in MOCK_STAFF:
            record = MOCK_STAFF[staff_id]
            if record["password"] == password:
                return {
                    "staff_id": record["staff_id"],
                    "hospital_id": record["hospital_id"],
                    "name": record["name"]
                }
        
        # Check MySQL credentials if available
        if self.mode == "mysql" and self._mysql_available:
            try:
                conn = self.get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT staff_id, hospital_id, hashed_password, name FROM staff_users WHERE staff_id = %s",
                    (staff_id,)
                )
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                if user:
                    pw_hash = hash_password(password)
                    if user["hashed_password"] in (password, pw_hash):
                        return {
                            "staff_id": user["staff_id"],
                            "hospital_id": user["hospital_id"],
                            "name": user["name"]
                        }
            except Exception as e:
                logger.error(f"MySQL error in verify_staff: {e}")
        return None

    def update_hospital_beds(self, hospital_id, total_beds, occupied_beds, admissions=0, discharges=0, staff_id="demo-staff"):
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Update in-memory
        h = next((item for item in MOCK_HOSPITALS if str(item["id"]) == str(hospital_id)), None)
        old_val = deepcopy(h["beds"]) if h else None
        if h:
            blocked_beds = h["beds"].get("blocked", 0) if "beds" in h else 0
            available_beds = max(0, total_beds - occupied_beds - blocked_beds)
            h["beds"] = {
                "total": total_beds,
                "occupied": occupied_beds,
                "blocked": blocked_beds,
                "available": available_beds,
                "today_admissions": admissions,
                "today_discharges": discharges,
            }
            # Auto-calculate crowd status from bed occupancy
            auto_crowd = compute_crowd_status_from_beds(total_beds, occupied_beds)
            h["crowd_status"] = auto_crowd
            if "crowd" in h:
                h["crowd"]["today_admissions"] = admissions
                h["crowd"]["today_discharges"] = discharges
            h["last_updated"] = now_iso
            MOCK_HISTORY.insert(0, {
                "hospital_id": hospital_id,
                "staff_id": staff_id,
                "field_changed": "beds",
                "old_value": old_val,
                "new_value": {
                    "total_beds": total_beds,
                    "occupied_beds": occupied_beds,
                    "blocked_beds": blocked_beds,
                    "available_beds": available_beds,
                    "today_admissions": admissions,
                    "today_discharges": discharges
                },
                "changed_at": now_iso
            })

        # Update MySQL if available
        if self.mode == "mysql" and self._mysql_available:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE hospital_beds SET total_beds = %s, occupied_beds = %s, today_admissions = %s, today_discharges = %s WHERE hospital_id = %s",
                    (total_beds, occupied_beds, admissions, discharges, hospital_id)
                )
                cursor.execute(
                    "INSERT INTO update_history (hospital_id, staff_id, field_changed, old_value, new_value) VALUES (%s, %s, %s, %s, %s)",
                    (hospital_id, staff_id, "beds", json.dumps(old_val), json.dumps({"total_beds": total_beds, "occupied_beds": occupied_beds, "admissions": admissions, "discharges": discharges}))
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                logger.error(f"MySQL error in update_hospital_beds: {e}")

        return self.get_hospital(hospital_id)

    def update_hospital_crowd(self, hospital_id, current_patients, waiting_patients, admissions=0, discharges=0, staff_id="demo-staff"):
        crowd_stat = compute_crowd_status(current_patients, waiting_patients, admissions)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Update in-memory
        h = next((item for item in MOCK_HOSPITALS if item["id"] == hospital_id), None)
        old_val = deepcopy(h["crowd"]) if h else None
        if h:
            h["crowd"] = {
                "current_patients": current_patients,
                "waiting_patients": waiting_patients,
                "today_admissions": admissions,
                "today_discharges": discharges
            }
            # Keep beds admissions/discharges synchronized
            if "beds" in h:
                h["beds"]["today_admissions"] = admissions
                h["beds"]["today_discharges"] = discharges
            h["crowd_status"] = crowd_stat
            h["last_updated"] = now_iso
            MOCK_HISTORY.insert(0, {
                "hospital_id": hospital_id,
                "staff_id": staff_id,
                "field_changed": "crowd",
                "old_value": old_val,
                "new_value": {
                    "current_patients": current_patients,
                    "waiting_patients": waiting_patients,
                    "today_admissions": admissions,
                    "today_discharges": discharges,
                    "crowd_status": crowd_stat
                },
                "changed_at": now_iso
            })

        # Update MySQL if available
        if self.mode == "mysql" and self._mysql_available:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE crowd_updates SET current_patients = %s, waiting_patients = %s, today_admissions = %s, today_discharges = %s, crowd_status = %s WHERE hospital_id = %s",
                    (current_patients, waiting_patients, admissions, discharges, crowd_stat, hospital_id)
                )
                cursor.execute(
                    "INSERT INTO update_history (hospital_id, staff_id, field_changed, old_value, new_value) VALUES (%s, %s, %s, %s, %s)",
                    (hospital_id, staff_id, "crowd", json.dumps(old_val), json.dumps({"current_patients": current_patients, "waiting_patients": waiting_patients, "today_admissions": admissions, "today_discharges": discharges, "crowd_status": crowd_stat}))
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                logger.error(f"MySQL error in update_hospital_crowd: {e}")

        return self.get_hospital(hospital_id)

    def update_hospital_doctors(self, hospital_id, doctors_data, staff_id="demo-staff"):
        now_iso = datetime.now(timezone.utc).isoformat()
        h = next((item for item in MOCK_HOSPITALS if item["id"] == hospital_id), None)
        old_val = deepcopy(h["doctors"]) if h else None

        if h:
            if isinstance(doctors_data, list):
                h["doctors"] = doctors_data
                statuses = [d.get("status", "Available") for d in doctors_data]
                if "Available" in statuses:
                    h["doctor_status"] = "Available"
                elif "Limited" in statuses:
                    h["doctor_status"] = "Limited"
                else:
                    h["doctor_status"] = "Unavailable"
            elif isinstance(doctors_data, dict):
                stat = doctors_data.get("status", "Available")
                h["doctor_status"] = stat
                for d in h["doctors"]:
                    d["status"] = stat

            h["last_updated"] = now_iso
            MOCK_HISTORY.insert(0, {
                "hospital_id": hospital_id,
                "staff_id": staff_id,
                "field_changed": "doctors",
                "old_value": old_val,
                "new_value": deepcopy(h["doctors"]),
                "changed_at": now_iso
            })

        return self.get_hospital(hospital_id)

    def update_hospital_resources(self, hospital_id, resources_data, staff_id="demo-staff"):
        now_iso = datetime.now(timezone.utc).isoformat()
        h = next((item for item in MOCK_HOSPITALS if item["id"] == hospital_id), None)
        old_val = deepcopy(h["resources"]) if h else None

        if h:
            if isinstance(resources_data, list):
                norm_list = []
                for item in resources_data:
                    raw_type = item.get("resource_type", "")
                    cname = CANONICAL_RESOURCE_MAP.get(raw_type.lower().strip(), raw_type)
                    norm_list.append({"resource_type": cname, "status": item.get("status", "Available")})
                h["resources"] = norm_list
            elif isinstance(resources_data, dict):
                norm_input = {}
                for k, v in resources_data.items():
                    if k == "staff_id":
                        continue
                    cname = CANONICAL_RESOURCE_MAP.get(k.lower().strip(), k)
                    norm_input[cname] = v

                for r in h["resources"]:
                    rtype = r["resource_type"]
                    cname = CANONICAL_RESOURCE_MAP.get(rtype.lower().strip(), rtype)
                    r["resource_type"] = cname
                    if cname in norm_input:
                        r["status"] = norm_input[cname]
                    elif rtype in resources_data:
                        r["status"] = resources_data[rtype]

            h["last_updated"] = now_iso
            MOCK_HISTORY.insert(0, {
                "hospital_id": hospital_id,
                "staff_id": staff_id,
                "field_changed": "resources",
                "old_value": old_val,
                "new_value": deepcopy(h["resources"]),
                "changed_at": now_iso
            })

        return self.get_hospital(hospital_id)

    def get_history(self, hospital_id):
        if self.mode == "mysql" and self._mysql_available:
            try:
                conn = self.get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT staff_id, field_changed, old_value, new_value, changed_at FROM update_history WHERE hospital_id = %s ORDER BY changed_at DESC LIMIT 50",
                    (hospital_id,)
                )
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                for r in rows:
                    if isinstance(r.get("old_value"), str):
                        try:
                            r["old_value"] = json.loads(r["old_value"])
                        except Exception:
                            pass
                    if isinstance(r.get("new_value"), str):
                        try:
                            r["new_value"] = json.loads(r["new_value"])
                        except Exception:
                            pass
                    if hasattr(r["changed_at"], "isoformat"):
                        r["changed_at"] = r["changed_at"].isoformat()
                return rows
            except Exception as e:
                logger.error(f"MySQL error in get_history: {e}")

        # In-memory history
        return [item for item in deepcopy(MOCK_HISTORY) if str(item["hospital_id"]) == str(hospital_id)]

    def create_emergency_request(self, hospital_id=None, patient_locality=None, lat=None, lng=None, state=None):
        """
        Creates a simulated emergency request:
        1. Identifies the best-suited hospital with available beds (available >= 1).
        2. Assigns a simulated ambulance.
        3. Automatically blocks 1 bed in that hospital (Available = Total - Occupied - Blocked).
        4. Generates unique tracking ID 'EMG-...'.
        5. Returns request payload.
        """
        from .recommendation import rank_hospitals

        selected_hospital = None
        # If user explicitly requested or pre-selected a hospital:
        if hospital_id:
            h = next((item for item in MOCK_HOSPITALS if str(item["id"]) == str(hospital_id)), None)
            if h and h.get("beds", {}).get("available", 0) >= 1:
                selected_hospital = h

        # Otherwise, dynamically find top recommended hospital with available bed
        if not selected_hospital:
            candidate_hospitals = self.get_hospitals(
                patient_locality=patient_locality,
                lat=lat,
                lng=lng,
                state=state
            )
            ranked = rank_hospitals(
                candidate_hospitals,
                patient_locality=patient_locality,
                lat=lat,
                lng=lng
            )
            for cand in ranked:
                cand_h = next((item for item in MOCK_HOSPITALS if str(item["id"]) == str(cand["id"])), None)
                if cand_h and cand_h.get("beds", {}).get("available", 0) >= 1:
                    selected_hospital = cand_h
                    break

        # Fallback: any hospital in candidate pool with available bed >= 1
        if not selected_hospital:
            for cand_h in MOCK_HOSPITALS:
                if cand_h.get("beds", {}).get("available", 0) >= 1:
                    if not state or cand_h.get("state", "").lower() == state.lower():
                        selected_hospital = cand_h
                        break

        if not selected_hospital:
            return None, "NO_BEDS_AVAILABLE"

        # Assign available ambulance
        assigned_amb = None
        for a in MOCK_AMBULANCES:
            if str(a["hospital_id"]) == str(selected_hospital["id"]) and a["status"] == "Available":
                assigned_amb = a
                break

        if not assigned_amb:
            for a in MOCK_AMBULANCES:
                if a["status"] == "Available":
                    assigned_amb = a
                    break

        if not assigned_amb:
            # Fallback dynamic ambulance creation
            assigned_amb = {
                "id": len(MOCK_AMBULANCES) + 1,
                "hospital_id": selected_hospital["id"],
                "ambulance_code": f"AMB-EMG-{len(MOCK_AMBULANCES) + 1:02d}",
                "status": "Available",
                "driver_name": "Emergency Pilot",
                "contact_number": "+91 98401 99999"
            }
            MOCK_AMBULANCES.append(assigned_amb)

        assigned_amb["status"] = "Assigned"

        # AUTOMATIC BED BLOCKING (Feature 3)
        # Block 1 bed immediately
        now_iso = datetime.now(timezone.utc).isoformat()
        b = selected_hospital["beds"]
        b["blocked"] = b.get("blocked", 0) + 1
        b["available"] = max(0, b.get("total", 0) - b.get("occupied", 0) - b["blocked"])
        selected_hospital["last_updated"] = now_iso

        # Unique Tracking Code: EMG-<timestamp>-<hex>
        clean_uuid = uuid.uuid4().hex[:6].upper()
        req_code = f"EMG-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{clean_uuid}"

        request_record = {
            "id": len(MOCK_EMERGENCY_REQUESTS) + 1,
            "request_code": req_code,
            "hospital_id": selected_hospital["id"],
            "hospital_name": selected_hospital["name"],
            "hospital_locality": selected_hospital["locality"],
            "hospital_contact": selected_hospital.get("contact_number", "+91 44 4000 0000"),
            "ambulance_id": assigned_amb["id"],
            "ambulance_code": assigned_amb["ambulance_code"],
            "driver_name": assigned_amb["driver_name"],
            "driver_contact": assigned_amb["contact_number"],
            "patient_locality": patient_locality or selected_hospital.get("locality", "Current Location"),
            "patient_lat": float(lat) if lat is not None else selected_hospital.get("approx_lat", 13.04),
            "patient_lng": float(lng) if lng is not None else selected_hospital.get("approx_lng", 80.23),
            "estimated_eta_mins": 12,
            "status": "Ambulance Assigned",
            "bed_blocked": True,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        MOCK_EMERGENCY_REQUESTS.insert(0, request_record)

        # Audit history
        MOCK_HISTORY.insert(0, {
            "hospital_id": selected_hospital["id"],
            "staff_id": "system-sos-emergency",
            "field_changed": "bed_blocked_sos",
            "old_value": {"blocked_beds": b["blocked"] - 1},
            "new_value": {"request_code": req_code, "blocked_beds": b["blocked"], "available_beds": b["available"]},
            "changed_at": now_iso,
        })

        return deepcopy(request_record), None

    def get_emergency_request(self, request_code):
        for r in MOCK_EMERGENCY_REQUESTS:
            if r["request_code"] == request_code:
                return deepcopy(r)
        return None

    def get_hospital_emergency_requests(self, hospital_id):
        results = []
        for r in MOCK_EMERGENCY_REQUESTS:
            if str(r["hospital_id"]) == str(hospital_id):
                results.append(deepcopy(r))
        return results

    def update_emergency_status(self, request_code, new_status, staff_id="demo-staff"):
        valid_statuses = ["Ambulance Assigned", "En Route", "Arrived", "Patient Admitted"]
        if new_status not in valid_statuses:
            return None, f"Invalid status '{new_status}'. Allowed: {', '.join(valid_statuses)}"

        req = next((r for r in MOCK_EMERGENCY_REQUESTS if r["request_code"] == request_code), None)
        if not req:
            return None, "Emergency request not found"

        if req["status"] == "Cancelled":
            return None, "Cannot update a cancelled emergency request"

        # Idempotent check for admission
        if req["status"] == "Patient Admitted" and new_status == "Patient Admitted":
            return deepcopy(req), None

        now_iso = datetime.now(timezone.utc).isoformat()
        old_status = req["status"]

        if new_status == "Patient Admitted":
            # Convert blocked bed to occupied bed
            if req.get("bed_blocked"):
                hid = req["hospital_id"]
                h = next((item for item in MOCK_HOSPITALS if item["id"] == hid), None)
                if h and "beds" in h:
                    b = h["beds"]
                    b["blocked"] = max(0, b.get("blocked", 1) - 1)
                    b["occupied"] = b.get("occupied", 0) + 1
                    b["today_admissions"] = b.get("today_admissions", 0) + 1
                    b["available"] = max(0, b.get("total", 0) - b.get("occupied", 0) - b.get("blocked", 0))
                    if "crowd" in h:
                        h["crowd"]["today_admissions"] = b["today_admissions"]
                    h["crowd_status"] = compute_crowd_status_from_beds(b.get("total", 0), b.get("occupied", 0))
                    h["last_updated"] = now_iso
                req["bed_blocked"] = False

            # Free ambulance
            amb = next((a for a in MOCK_AMBULANCES if a["id"] == req.get("ambulance_id")), None)
            if amb:
                amb["status"] = "Available"

        req["status"] = new_status
        req["updated_at"] = now_iso

        # Log history
        MOCK_HISTORY.insert(0, {
            "hospital_id": req["hospital_id"],
            "staff_id": staff_id,
            "field_changed": "emergency_status",
            "old_value": {"request_code": request_code, "status": old_status},
            "new_value": {"request_code": request_code, "status": new_status, "bed_blocked": req.get("bed_blocked", False)},
            "changed_at": now_iso,
        })

        return deepcopy(req), None

    def cancel_emergency_request(self, request_code, staff_id="patient-cancel"):
        req = next((r for r in MOCK_EMERGENCY_REQUESTS if r["request_code"] == request_code), None)
        if not req:
            return None, "Emergency request not found"

        # Idempotent check
        if req["status"] == "Cancelled":
            return deepcopy(req), None

        if req["status"] == "Patient Admitted":
            return None, "Cannot cancel request: patient has already been admitted"

        now_iso = datetime.now(timezone.utc).isoformat()
        old_status = req["status"]

        # Release blocked bed
        if req.get("bed_blocked"):
            hid = req["hospital_id"]
            h = next((item for item in MOCK_HOSPITALS if item["id"] == hid), None)
            if h and "beds" in h:
                b = h["beds"]
                b["blocked"] = max(0, b.get("blocked", 1) - 1)
                b["available"] = max(0, b.get("total", 0) - b.get("occupied", 0) - b.get("blocked", 0))
                h["last_updated"] = now_iso
            req["bed_blocked"] = False

        # Free ambulance
        amb = next((a for a in MOCK_AMBULANCES if a["id"] == req.get("ambulance_id")), None)
        if amb:
            amb["status"] = "Available"

        req["status"] = "Cancelled"
        req["updated_at"] = now_iso

        # Log history
        MOCK_HISTORY.insert(0, {
            "hospital_id": req["hospital_id"],
            "staff_id": staff_id,
            "field_changed": "emergency_cancelled",
            "old_value": {"request_code": request_code, "status": old_status},
            "new_value": {"request_code": request_code, "status": "Cancelled", "bed_released": True},
            "changed_at": now_iso,
        })

        return deepcopy(req), None

# Singleton database repository instance
repo = DataRepository()

# Expose top-level functions matching interface
def get_hospitals(locality=None, hospital_type=None, patient_locality=None, search=None, lat=None, lng=None, state=None):
    return repo.get_hospitals(locality, hospital_type, patient_locality, search, lat=lat, lng=lng, state=state)

def get_hospital(hospital_id, patient_locality=None, lat=None, lng=None):
    return repo.get_hospital(hospital_id, patient_locality, lat=lat, lng=lng)

def verify_staff(staff_id, password):
    return repo.verify_staff(staff_id, password)

def update_hospital_beds(hospital_id, total, occupied, admissions=0, discharges=0, staff_id="demo-staff"):
    return repo.update_hospital_beds(hospital_id, total, occupied, admissions, discharges, staff_id)

def update_hospital_crowd(hospital_id, current, waiting, admissions=0, discharges=0, staff_id="demo-staff"):
    return repo.update_hospital_crowd(hospital_id, current, waiting, admissions, discharges, staff_id)

def update_hospital_doctors(hospital_id, doctors_data, staff_id="demo-staff"):
    return repo.update_hospital_doctors(hospital_id, doctors_data, staff_id)

def update_hospital_resources(hospital_id, resources_data, staff_id="demo-staff"):
    return repo.update_hospital_resources(hospital_id, resources_data, staff_id)

def get_history(hospital_id):
    return repo.get_history(hospital_id)

def create_emergency_request(hospital_id=None, patient_locality=None, lat=None, lng=None, state=None):
    return repo.create_emergency_request(hospital_id, patient_locality, lat, lng, state)

def get_emergency_request(request_code):
    return repo.get_emergency_request(request_code)

def get_hospital_emergency_requests(hospital_id):
    return repo.get_hospital_emergency_requests(hospital_id)

def update_emergency_status(request_code, new_status, staff_id="demo-staff"):
    return repo.update_emergency_status(request_code, new_status, staff_id)

def cancel_emergency_request(request_code, staff_id="patient-cancel"):
    return repo.cancel_emergency_request(request_code, staff_id)

