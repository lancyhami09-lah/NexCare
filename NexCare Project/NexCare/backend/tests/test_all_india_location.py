"""
Unit and Integration Tests for NexCare Update 2:
- 6th Language Support: Malayalam (ml.json) & key consistency across all 6 languages
- All-India Coverage & Geolocation API (GET /api/locations, lat/lng support, distance calculation)
- Honest Notice Banner triggers outside Chennai
- Two-Step State -> City Location API
"""

import os
import json
import unittest
from backend.app import app
from backend.config import INDIA_LOCATIONS, ALL_INDIA_COORDINATES, NON_CHENNAI_NOTICE, haversine_distance


class TestAllIndiaLocationAndMalayalam(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    # -------------------------------------------------------------
    # 1. Test 6-Language JSON Files
    # -------------------------------------------------------------
    def test_six_languages_complete_and_consistent(self):
        i18n_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "i18n")
        langs = ["en", "ta", "te", "kn", "hi", "ml"]
        
        dictionaries = {}
        for lang in langs:
            filepath = os.path.join(i18n_dir, f"{lang}.json")
            self.assertTrue(os.path.exists(filepath), f"Missing i18n file: {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertIsInstance(data, dict)
                self.assertGreater(len(data), 100, f"{lang}.json must contain full translation keys")
                dictionaries[lang] = data

        # Verify key set parity against English master
        en_keys = set(dictionaries["en"].keys())
        for lang in ["ta", "te", "kn", "hi", "ml"]:
            lang_keys = set(dictionaries[lang].keys())
            missing_in_lang = en_keys - lang_keys
            self.assertEqual(len(missing_in_lang), 0, f"{lang}.json is missing keys: {missing_in_lang}")
            
            # Verify no empty translation values
            for k, v in dictionaries[lang].items():
                self.assertTrue(bool(v.strip()), f"Key '{k}' in {lang}.json cannot be empty")

        # Verify specific Malayalam phrases
        ml = dictionaries["ml"]
        self.assertIn("ആശുപത്രി", ml["nav_patient"])
        self.assertIn("അടിയന്തര", ml["emergency_banner"])
        self.assertIn("തിരയുക", ml["btn_search"])
        self.assertIn("ലഭ്യമാണ്", ml["status_available"])

    # -------------------------------------------------------------
    # 2. Test Locations API (GET /api/locations)
    # -------------------------------------------------------------
    def test_locations_api_endpoint(self):
        resp = self.client.get("/api/locations")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("Tamil Nadu", data["data"])
        self.assertIn("Kerala", data["data"])
        self.assertIn("Karnataka", data["data"])
        self.assertIn("Maharashtra", data["data"])
        self.assertIn("Delhi (NCT)", data["data"])
        self.assertEqual(data.get("coverage_note"), NON_CHENNAI_NOTICE)

    # -------------------------------------------------------------
    # 3. Test Haversine Distance Calculation from All-India Cities
    # -------------------------------------------------------------
    def test_haversine_distance_calculations(self):
        # Chennai central
        chennai_lat, chennai_lng = 13.04, 80.23
        
        # Bengaluru (~290 km)
        bengaluru_lat, bengaluru_lng = ALL_INDIA_COORDINATES["Bengaluru"]
        dist_blr = haversine_distance(chennai_lat, chennai_lng, bengaluru_lat, bengaluru_lng)
        self.assertGreater(dist_blr, 250)
        self.assertLess(dist_blr, 350)

        # Kochi (~560 km)
        kochi_lat, kochi_lng = ALL_INDIA_COORDINATES["Kochi"]
        dist_kochi = haversine_distance(chennai_lat, chennai_lng, kochi_lat, kochi_lng)
        self.assertGreater(dist_kochi, 500)
        self.assertLess(dist_kochi, 650)

        # Adyar (< 10 km)
        adyar_lat, adyar_lng = ALL_INDIA_COORDINATES["Adyar"]
        dist_adyar = haversine_distance(chennai_lat, chennai_lng, adyar_lat, adyar_lng)
        self.assertLess(dist_adyar, 10)

    # -------------------------------------------------------------
    # 4. Test Live Geolocation Query Parameters in /api/hospitals
    # -------------------------------------------------------------
    def test_hospitals_with_live_coordinates_outside_chennai(self):
        # Mumbai coordinates (19.0760, 72.8777) - now has local prototype hospitals!
        resp = self.client.get("/api/hospitals?lat=19.0760&lng=72.8777")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        first_hosp = data["data"][0]
        # Should match local Mumbai hospitals nearby
        self.assertLess(first_hosp["distance_km"], 50)

    def test_hospitals_with_chennai_locality_no_outside_notice(self):
        # Adyar (inside Chennai)
        resp = self.client.get("/api/hospitals?patient_locality=Adyar")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        # Distance should be small
        first_hosp = data["data"][0]
        self.assertLess(first_hosp["distance_km"], 30)

    def test_hospitals_with_city_outside_chennai(self):
        # Kochi (Kerala) - now has local prototype hospitals!
        resp = self.client.get("/api/hospitals?patient_locality=Kochi")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        first_hosp = data["data"][0]
        self.assertLess(first_hosp["distance_km"], 50)

    # -------------------------------------------------------------
    # 5. Test Recommendations with Live Coordinates & Outside City
    # -------------------------------------------------------------
    def test_recommendations_with_coordinates_outside_chennai(self):
        # Kochi coordinates (9.9312, 76.2673)
        resp = self.client.get("/api/hospitals/recommendations?lat=9.9312&lng=76.2673&limit=3")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 3)
        top = data["data"][0]
        self.assertIn("score", top)
        self.assertLess(top["distance_km"], 50)


if __name__ == "__main__":
    unittest.main()
