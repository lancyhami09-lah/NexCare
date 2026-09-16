"""
NexCare Automated Test Suite
Exercises all API endpoints, validation guards, and recommendation algorithm
"""

import unittest
import json
import os
import sys

# Ensure backend package can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
workspace_dir = os.path.dirname(parent_dir)
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from backend.app import create_app
from backend.recommendation import (
    rank_hospitals,
    compute_distance_subscore,
    compute_bed_subscore,
    compute_doctor_subscore,
    compute_resource_subscore,
    compute_crowd_subscore,
)
from backend.config import CROWD_THRESHOLDS, AREAS


class NexCareAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.token = "nexcare-demo-staff-token-2026"
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

    # 1. Health Check
    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("active_data_mode", data)

    # 1b. States & Cities Endpoints (Section 13)
    def test_get_states(self):
        res = self.client.get("/api/states")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)
        self.assertGreaterEqual(len(data["data"]), 19)
        # Verify Tamil Nadu and Karnataka are pinned first
        self.assertEqual(data["data"][0], "Tamil Nadu")
        self.assertEqual(data["data"][1], "Karnataka")

    def test_get_state_cities_populated_karnataka(self):
        res = self.client.get("/api/states/Karnataka/cities")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["state"], "Karnataka")
        self.assertTrue(data["data_available"])
        self.assertTrue(any("Koramangala" in c for c in data["cities"]))
        self.assertTrue(any("Bannerghatta" in c for c in data["cities"]))
        self.assertEqual(data["state_note"], "")

    def test_get_state_cities_populated_tamil_nadu(self):
        res = self.client.get("/api/states/Tamil%20Nadu/cities")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["state"], "Tamil Nadu")
        self.assertTrue(data["data_available"])
        self.assertTrue(any("Adyar" in c for c in data["cities"]))
        self.assertTrue(any("Anna Nagar" in c for c in data["cities"]))

    def test_get_state_cities_all_states_available(self):
        # Delhi
        res = self.client.get("/api/states/Delhi/cities")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data_available"])
        self.assertEqual(data.get("state_note", ""), "")
        self.assertTrue(any("Delhi" in c for c in data["cities"]))

    def test_get_state_cities_not_found(self):
        res = self.client.get("/api/states/NonExistentState999/cities")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_recommendations_with_state_and_city(self):
        res = self.client.get("/api/hospitals/recommendations?state=Karnataka&city=Koramangala&limit=3")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["data"]), 1)
        self.assertIn("score", data["data"][0])
        self.assertIn("recommendation_reason", data["data"][0])

    # 2. Areas Endpoint
    def test_get_areas(self):
        res = self.client.get("/api/areas")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 12)
        self.assertIn("Adyar", data["data"])
        self.assertIn("Tambaram", data["data"])
        self.assertIn("Porur", data["data"])

    # 3. Hospitals Listing & Filtering
    def test_get_hospitals(self):
        res = self.client.get("/api/hospitals")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["data"]), 10)
        
        # Check presence of mandatory disclaimer
        self.assertIn("disclaimer", data)
        self.assertIn("emergency_message", data)

        # Check fields of first hospital
        h1 = data["data"][0]
        self.assertIn("id", h1)
        self.assertIn("name", h1)
        self.assertIn("locality", h1)
        self.assertIn("beds", h1)
        self.assertIn("doctor_status", h1)
        self.assertIn("crowd_status", h1)

    def test_get_hospitals_filtered_by_locality(self):
        res = self.client.get("/api/hospitals?locality=Adyar")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        for h in data["data"]:
            self.assertEqual(h["locality"].lower(), "adyar")

    def test_get_hospitals_filtered_by_type(self):
        res = self.client.get("/api/hospitals?type=Government")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        for h in data["data"]:
            self.assertEqual(h["type"], "Government")

    def test_get_hospital_details(self):
        res = self.client.get("/api/hospitals/1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["data"]["id"], 1)
        self.assertIn("Apollo", data["data"]["name"])

    def test_get_hospital_details_not_found(self):
        res = self.client.get("/api/hospitals/9999")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_get_hospital_details_invalid_id(self):
        res = self.client.get("/api/hospitals/invalid-id")
        self.assertEqual(res.status_code, 400)

    # 4. Recommendation Engine
    def test_get_recommendations(self):
        res = self.client.get("/api/hospitals/recommendations?locality=Adyar&limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 5)
        
        # Verify scores are sorted descending
        scores = [h["score"] for h in data["data"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Check each recommendation has score breakdown and plain-language explanation
        top1 = data["data"][0]
        self.assertIn("score", top1)
        self.assertIn("factor_scores", top1)
        self.assertIn("recommendation_reason", top1)
        self.assertIn("algorithm_disclaimer", top1)
        self.assertTrue(len(top1["recommendation_reason"]) > 10)

    # 5. Staff Authentication
    def test_staff_login_success(self):
        res = self.client.post(
            "/api/staff/login",
            data=json.dumps({"staff_id": "staff_fortis", "password": "demo123"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["hospital_id"], 5)
        self.assertEqual(data["data"]["token"], self.token)

    def test_staff_login_invalid_password(self):
        res = self.client.post(
            "/api/staff/login",
            data=json.dumps({"staff_id": "staff_fortis", "password": "wrongpassword"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_staff_login_missing_fields(self):
        res = self.client.post(
            "/api/staff/login",
            data=json.dumps({"staff_id": "staff_fortis"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    # 6. Staff Dashboard
    def test_staff_dashboard_unauthorized(self):
        res = self.client.get("/api/staff/5/dashboard")
        self.assertEqual(res.status_code, 401)

    def test_staff_dashboard_authorized(self):
        res = self.client.get("/api/staff/5/dashboard", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("hospital", data["data"])
        self.assertIn("warnings", data["data"])

    # 7. Bed Updates & Validation
    def test_update_beds_valid(self):
        res = self.client.put(
            "/api/staff/5/beds",
            headers=self.auth_headers,
            data=json.dumps({
                "total_beds": 200,
                "occupied_beds": 120,
                "admissions": 5,
                "discharges": 3
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        beds = data["data"]["beds"]
        self.assertEqual(beds["total"], 200)
        self.assertEqual(beds["occupied"], 120)
        self.assertEqual(beds["available"], 80)

    def test_update_beds_conflict_occupied_exceeds_total(self):
        res = self.client.put(
            "/api/staff/5/beds",
            headers=self.auth_headers,
            data=json.dumps({"total_beds": 100, "occupied_beds": 150}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data.get("error_code"), "CAPACITY_EXCEEDED")

    def test_update_beds_negative_values(self):
        res = self.client.put(
            "/api/staff/5/beds",
            headers=self.auth_headers,
            data=json.dumps({"total_beds": -50, "occupied_beds": 20}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    # 8. Crowd Updates & Validation
    def test_update_crowd_valid(self):
        res = self.client.put(
            "/api/staff/5/crowd",
            headers=self.auth_headers,
            data=json.dumps({"current_patients": 30, "waiting_patients": 8}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        # Total = 38 <= 40 -> Low
        self.assertEqual(data["data"]["crowd_status"], "Low")

    def test_update_crowd_high_threshold(self):
        res = self.client.put(
            "/api/staff/5/crowd",
            headers=self.auth_headers,
            data=json.dumps({"current_patients": 85, "waiting_patients": 20}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        # Total = 105 > 80 -> High
        self.assertEqual(data["data"]["crowd_status"], "High")

    # 9. Doctor & Resource Updates
    def test_update_doctors(self):
        res = self.client.put(
            "/api/staff/5/doctors",
            headers=self.auth_headers,
            data=json.dumps({
                "doctors": [
                    {"name_or_department": "Emergency Medicine", "status": "Available", "available_time": "24x7", "consultation_capacity": 40}
                ]
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    def test_update_resources(self):
        res = self.client.put(
            "/api/staff/5/resources",
            headers=self.auth_headers,
            data=json.dumps({
                "resources": {
                    "ICU beds": "Available",
                    "Oxygen": "Available",
                    "CT scan": "Limited"
                }
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    def test_update_all_eight_canonical_resources(self):
        canonical_payload = {
            "ICU Beds": "Limited",
            "Oxygen Support": "Available",
            "Pharmacy": "Available",
            "Laboratory": "Available",
            "X-ray": "Available",
            "CT Scan": "Limited",
            "Blood Bank": "Available",
            "Emergency Department": "Available"
        }
        res = self.client.put(
            "/api/staff/5/resources",
            headers=self.auth_headers,
            data=json.dumps({"resources": canonical_payload}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        h = res.get_json()["data"]
        res_map = {r["resource_type"]: r["status"] for r in h["resources"]}
        self.assertEqual(res_map["ICU Beds"], "Limited")
        self.assertEqual(res_map["CT Scan"], "Limited")
        self.assertEqual(res_map["Oxygen Support"], "Available")
        self.assertEqual(res_map["Emergency Department"], "Available")

    # 10. Audit History
    def test_audit_history(self):
        res = self.client.get("/api/staff/5/history", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)
        self.assertGreaterEqual(len(data["data"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
