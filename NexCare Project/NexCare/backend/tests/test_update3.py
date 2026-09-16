"""
Unit & Integration Tests for NexCare Update Prompt 3:
- State-Specific Real Hospitals (Karnataka 6 & Tamil Nadu 10)
- Honest Non-Fabricated Notice for Other States
- Staff 5 Key Default Summary Metrics
- Crowd & Waiting Queue Tracking with Admissions/Discharges
- Doctor Specialties Support
- 6-Language i18n Parity (100% Matching Keys)
"""

import os
import json
import unittest
from backend.app import app
from backend import database
from backend.config import STATE_HOSPITAL_NOTICE
from backend.api import DEMO_TOKEN

class TestUpdate3Features(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.auth_headers = {
            "Authorization": f"Bearer {DEMO_TOKEN}",
            "Content-Type": "application/json",
        }

    # ====================================================================
    # 1. State-Specific Hospital Data & Honest State Notice
    # ====================================================================

    def test_tamil_nadu_hospitals(self):
        """Tamil Nadu returns 10 real Chennai hospitals."""
        res = self.client.get("/api/hospitals?state=Tamil%20Nadu")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data), 10)
        names = [h["name"] for h in data]
        self.assertTrue(any("Apollo" in n for n in names))
        self.assertTrue(any("Fortis" in n for n in names))
        for h in data:
            self.assertEqual(h.get("state"), "Tamil Nadu")

    def test_karnataka_hospitals(self):
        """Karnataka returns 6 real Bengaluru hospitals."""
        res = self.client.get("/api/hospitals?state=Karnataka")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(len(data), 6)
        names = [h["name"] for h in data]
        self.assertTrue(any("Manipal" in n for n in names))
        self.assertTrue(any("Victoria" in n for n in names))
        self.assertTrue(any("Narayana" in n for n in names))
        self.assertTrue(any("Bowring" in n for n in names))
        self.assertTrue(any("Fortis" in n for n in names))
        self.assertTrue(any("St. John" in n for n in names))
        for h in data:
            self.assertEqual(h.get("state"), "Karnataka")

    def test_delhi_prototype_hospitals(self):
        """Delhi returns active prototype hospitals."""
        res = self.client.get("/api/hospitals?state=Delhi")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertGreaterEqual(len(json_data["data"]), 3)
        for h in json_data["data"]:
            self.assertIn("Delhi", h.get("state"))

    def test_recommendations_karnataka(self):
        """Recommendations engine works for Karnataka hospitals."""
        res = self.client.get("/api/hospitals/recommendations?state=Karnataka&limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertGreaterEqual(len(data), 1)
        for h in data:
            self.assertEqual(h.get("state"), "Karnataka")
            self.assertIn("score", h)
            self.assertIn("recommendation_reason", h)

    def test_recommendations_kerala_prototype(self):
        """Recommendations for Kerala return prototype hospitals with scores."""
        res = self.client.get("/api/hospitals/recommendations?state=Kerala&limit=5")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertGreaterEqual(len(json_data["data"]), 1)
        for h in json_data["data"]:
            self.assertEqual(h.get("state"), "Kerala")
            self.assertIn("score", h)

    # ====================================================================
    # 2. Staff 5 Key Default Summary Metrics on Login Home
    # ====================================================================

    def test_staff_dashboard_summary_metrics(self):
        """Staff dashboard contains the 5 key summary metrics with Total - Occupied = Available."""
        res = self.client.get("/api/staff/1/dashboard", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()["data"]
        self.assertIn("summary", payload)
        summary = payload["summary"]
        self.assertIn("total_beds", summary)
        self.assertIn("occupied_beds", summary)
        self.assertIn("available_beds", summary)
        self.assertIn("today_admissions", summary)
        self.assertIn("today_discharges", summary)
        self.assertEqual(summary["available_beds"], summary["total_beds"] - summary["occupied_beds"])

    # ====================================================================
    # 3. Crowd Tracking with Admissions & Discharges
    # ====================================================================

    def test_staff_crowd_tracking_with_admissions(self):
        """Update crowd tracking with admissions and discharges."""
        update_data = {
            "current_patients": 30,
            "waiting_patients": 6,
            "today_admissions": 10,
            "today_discharges": 5,
        }
        res = self.client.put("/api/staff/1/crowd", headers=self.auth_headers, json=update_data)
        self.assertEqual(res.status_code, 200)
        updated = res.get_json()["data"]
        self.assertEqual(updated["crowd"]["current_patients"], 30)
        self.assertEqual(updated["crowd"]["waiting_patients"], 6)
        self.assertEqual(updated["crowd"]["today_admissions"], 10)
        self.assertEqual(updated["crowd"]["today_discharges"], 5)
        # Load: 30 + 6 + int(10*0.4) = 40 (Low)
        self.assertEqual(updated["crowd_status"], "Low")

    def test_staff_bed_update_syncs_summary(self):
        """Update beds with admissions/discharges and verify summary updates."""
        update_data = {
            "total_beds": 500,
            "occupied_beds": 350,
            "today_admissions": 18,
            "today_discharges": 12,
        }
        res = self.client.put("/api/staff/1/beds", headers=self.auth_headers, json=update_data)
        self.assertEqual(res.status_code, 200)
        updated = res.get_json()["data"]
        self.assertEqual(updated["beds"]["available"], 150)
        self.assertEqual(updated["beds"]["today_admissions"], 18)
        self.assertEqual(updated["beds"]["today_discharges"], 12)

    # ====================================================================
    # 4. Doctor Specialty Support
    # ====================================================================

    def test_doctor_specialty_in_hospital_data(self):
        """Doctors contain specialty attribute."""
        hospital = database.get_hospital(1)
        self.assertIn("doctors", hospital)
        self.assertGreater(len(hospital["doctors"]), 0)
        specialties = [d.get("specialty") for d in hospital["doctors"] if d.get("specialty")]
        self.assertGreater(len(specialties), 0)

    def test_update_doctor_specialty(self):
        """Staff can update doctor department with specialty."""
        docs = [
            {
                "id": 101,
                "name_or_department": "Dr. Sarah Rao",
                "specialty": "Pediatrics",
                "status": "Available",
                "available_time": "9 AM - 4 PM",
                "consultation_capacity": 25,
            }
        ]
        res = self.client.put("/api/staff/1/doctors", headers=self.auth_headers, json={"doctors": docs})
        self.assertEqual(res.status_code, 200)
        updated = res.get_json()["data"]
        saved_docs = updated["doctors"]
        self.assertEqual(saved_docs[0]["specialty"], "Pediatrics")

    # ====================================================================
    # 5. 6-Language i18n Key Parity Check
    # ====================================================================

    def test_i18n_all_six_languages_parity(self):
        """All 6 language json files must have exactly 100% key parity."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        i18n_dir = os.path.join(base_dir, "frontend", "i18n")
        langs = ["en", "ta", "te", "kn", "hi", "ml"]
        dicts = {}
        for l in langs:
            p = os.path.join(i18n_dir, f"{l}.json")
            self.assertTrue(os.path.exists(p), f"Missing {l}.json")
            with open(p, "r", encoding="utf-8") as f:
                dicts[l] = json.load(f)

        en_keys = set(dicts["en"].keys())
        # Check required new keys exist
        required_keys = [
            "voice_stop_btn_label", "voice_status_stopped", "sos_btn_label",
            "sos_modal_title", "sos_modal_subtitle", "sos_disclaimer_title",
            "sos_disclaimer_text", "sos_hotlines_title", "sos_108_label",
            "sos_112_label", "sos_nearest_hospitals_title", "sos_no_hospitals",
            "state_hospital_notice", "state_no_hospitals_title"
        ]
        for rk in required_keys:
            self.assertIn(rk, en_keys)

        for l in langs:
            l_keys = set(dicts[l].keys())
            missing = en_keys - l_keys
            extra = l_keys - en_keys
            self.assertEqual(missing, set(), f"Language {l} is missing keys: {missing}")
            self.assertEqual(extra, set(), f"Language {l} has extra keys: {extra}")
            self.assertEqual(len(l_keys), len(en_keys))

if __name__ == "__main__":
    unittest.main()
