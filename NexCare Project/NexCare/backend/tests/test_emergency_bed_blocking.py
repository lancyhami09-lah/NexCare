"""
Unit & Integration Tests for Feature 2 (Simulated SOS Emergency Workflow)
and Feature 3 (Automatic Bed Blocking Data Integrity).
"""

import unittest
from backend.app import app
from backend import database
from backend.api import DEMO_TOKEN, SIMULATED_EMERGENCY_NOTICE


class TestEmergencyAndBedBlocking(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.auth_headers = {
            "Authorization": f"Bearer {DEMO_TOKEN}",
            "Content-Type": "application/json",
        }

    def tearDown(self):
        database.MOCK_EMERGENCY_REQUESTS.clear()
        for h in database.MOCK_HOSPITALS:
            if "beds" in h:
                h["beds"]["blocked"] = 0
                tot = h["beds"].get("total", 0)
                occ = h["beds"].get("occupied", 0)
                h["beds"]["available"] = max(0, tot - occ)
        for a in database.MOCK_AMBULANCES:
            a["status"] = "Available"

    def test_emergency_creation_and_bed_blocking(self):
        """Test emergency request creation blocks 1 bed and returns tracking ID."""
        # Get baseline bed metrics for hospital 1
        h_before = database.get_hospital(1)
        tot_before = h_before["beds"]["total"]
        occ_before = h_before["beds"]["occupied"]
        blk_before = h_before["beds"].get("blocked", 0)
        avail_before = h_before["beds"]["available"]
        self.assertEqual(avail_before, max(0, tot_before - occ_before - blk_before))

        # Create emergency request for hospital 1
        payload = {
            "hospital_id": 1,
            "patient_locality": "Chennai - Greams Road",
            "lat": 13.056,
            "lng": 80.252,
            "state": "Tamil Nadu"
        }
        res = self.client.post("/api/emergency/request", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()["data"]

        # Validate tracking ID
        self.assertIn("request_code", data)
        self.assertTrue(data["request_code"].startswith("EMG-"))
        self.assertEqual(data["hospital_id"], 1)
        self.assertTrue(data["bed_blocked"])
        self.assertEqual(data["status"], "Ambulance Assigned")
        self.assertIn("ambulance_code", data)
        self.assertIn("driver_name", data)
        self.assertIn("driver_contact", data)
        self.assertIn("simulated_emergency_notice", res.get_json())

        # Verify bed is blocked in hospital 1
        h_after = database.get_hospital(1)
        self.assertEqual(h_after["beds"]["blocked"], blk_before + 1)
        self.assertEqual(h_after["beds"]["available"], avail_before - 1)
        self.assertEqual(
            h_after["beds"]["available"],
            max(0, h_after["beds"]["total"] - h_after["beds"]["occupied"] - h_after["beds"]["blocked"])
        )

    def test_emergency_tracking_and_progression_to_admitted(self):
        """Test status transitions: Assigned -> En Route -> Arrived -> Admitted."""
        payload = {
            "hospital_id": 2,
            "patient_locality": "Chennai - Park Town",
            "state": "Tamil Nadu"
        }
        res = self.client.post("/api/emergency/request", json=payload)
        self.assertEqual(res.status_code, 201)
        req = res.get_json()["data"]
        code = req["request_code"]

        # 1. Fetch tracking status
        res_track = self.client.get(f"/api/emergency/request/{code}")
        self.assertEqual(res_track.status_code, 200)
        self.assertEqual(res_track.get_json()["data"]["status"], "Ambulance Assigned")

        # 2. Update to 'En Route'
        res_enroute = self.client.put(f"/api/emergency/request/{code}/status", json={"status": "En Route"})
        self.assertEqual(res_enroute.status_code, 200)
        self.assertEqual(res_enroute.get_json()["data"]["status"], "En Route")

        # 3. Update to 'Arrived'
        res_arrived = self.client.put(f"/api/emergency/request/{code}/status", json={"status": "Arrived"})
        self.assertEqual(res_arrived.status_code, 200)
        self.assertEqual(res_arrived.get_json()["data"]["status"], "Arrived")

        # 4. Check hospital bed before admission
        h_pre_admit = database.get_hospital(2)
        blk_pre = h_pre_admit["beds"]["blocked"]
        occ_pre = h_pre_admit["beds"]["occupied"]

        # 5. Update to 'Patient Admitted' (converts blocked bed to occupied bed)
        res_admit = self.client.put(f"/api/emergency/request/{code}/status", json={"status": "Patient Admitted"})
        self.assertEqual(res_admit.status_code, 200)
        admitted_req = res_admit.get_json()["data"]
        self.assertEqual(admitted_req["status"], "Patient Admitted")
        self.assertFalse(admitted_req["bed_blocked"])

        # Check hospital bed converted: blocked -1, occupied +1
        h_post_admit = database.get_hospital(2)
        self.assertEqual(h_post_admit["beds"]["blocked"], blk_pre - 1)
        self.assertEqual(h_post_admit["beds"]["occupied"], occ_pre + 1)
        self.assertEqual(
            h_post_admit["beds"]["available"],
            max(0, h_post_admit["beds"]["total"] - h_post_admit["beds"]["occupied"] - h_post_admit["beds"]["blocked"])
        )

        # 6. Test Idempotency: calling Admitted again does NOT double increment
        res_admit_again = self.client.put(f"/api/emergency/request/{code}/status", json={"status": "Patient Admitted"})
        self.assertEqual(res_admit_again.status_code, 200)
        h_post_admit2 = database.get_hospital(2)
        self.assertEqual(h_post_admit2["beds"]["occupied"], occ_pre + 1)
        self.assertEqual(h_post_admit2["beds"]["blocked"], blk_pre - 1)

    def test_emergency_cancellation_releases_bed(self):
        """Test emergency cancellation releases blocked bed and restores availability."""
        payload = {
            "hospital_id": 3,
            "patient_locality": "Chennai - Anna Salai",
            "state": "Tamil Nadu"
        }
        res = self.client.post("/api/emergency/request", json=payload)
        self.assertEqual(res.status_code, 201)
        code = res.get_json()["data"]["request_code"]

        h_after_create = database.get_hospital(3)
        blk_after_create = h_after_create["beds"]["blocked"]
        avail_after_create = h_after_create["beds"]["available"]

        # Cancel request
        res_cancel = self.client.put(f"/api/emergency/request/{code}/cancel", json={})
        self.assertEqual(res_cancel.status_code, 200)
        self.assertEqual(res_cancel.get_json()["data"]["status"], "Cancelled")

        # Verify bed is released
        h_after_cancel = database.get_hospital(3)
        self.assertEqual(h_after_cancel["beds"]["blocked"], blk_after_create - 1)
        self.assertEqual(h_after_cancel["beds"]["available"], avail_after_create + 1)

        # Idempotency: cancelling again does not double release
        res_cancel2 = self.client.put(f"/api/emergency/request/{code}/cancel", json={})
        self.assertEqual(res_cancel2.status_code, 200)
        h_after_cancel2 = database.get_hospital(3)
        self.assertEqual(h_after_cancel2["beds"]["blocked"], blk_after_create - 1)

    def test_staff_dashboard_and_incoming_requests(self):
        """Staff dashboard contains blocked_beds and incoming requests endpoint returns records."""
        # Hospital 4
        payload = {
            "hospital_id": 4,
            "patient_locality": "Chennai - Kilpauk",
            "state": "Tamil Nadu"
        }
        res_req = self.client.post("/api/emergency/request", json=payload)
        self.assertEqual(res_req.status_code, 201)

        # Check staff dashboard
        res_dash = self.client.get("/api/staff/4/dashboard", headers=self.auth_headers)
        self.assertEqual(res_dash.status_code, 200)
        summary = res_dash.get_json()["data"]["summary"]
        self.assertIn("blocked_beds", summary)
        self.assertGreaterEqual(summary["blocked_beds"], 1)
        self.assertEqual(
            summary["available_beds"],
            max(0, summary["total_beds"] - summary["occupied_beds"] - summary["blocked_beds"])
        )

        # Check staff incoming emergency requests
        res_staff_reqs = self.client.get("/api/staff/4/emergency-requests", headers=self.auth_headers)
        self.assertEqual(res_staff_reqs.status_code, 200)
        reqs = res_staff_reqs.get_json()["data"]
        self.assertGreaterEqual(len(reqs), 1)
        self.assertTrue(any(r["hospital_id"] == 4 for r in reqs))

    def test_capacity_exceeded_with_blocked_beds(self):
        """Staff cannot set occupied beds such that occupied + blocked > total."""
        h = database.get_hospital(5)
        tot = h["beds"]["total"]
        blk = h["beds"].get("blocked", 0)

        # Try to set occupied so occupied + blocked > total
        attempted_occ = tot - blk + 1
        res = self.client.put(
            "/api/staff/5/beds",
            headers=self.auth_headers,
            json={"total_beds": tot, "occupied_beds": attempted_occ}
        )
        self.assertEqual(res.status_code, 409)
        self.assertIn("CAPACITY_EXCEEDED", res.get_json().get("error_code", ""))


if __name__ == "__main__":
    unittest.main()
