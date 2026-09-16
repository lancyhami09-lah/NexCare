"""
NexCare Recommendation Engine Weights & Logic Verification Tests
Verifies that ranking is strictly driven by the 5 weighted factors and
that a farther-but-better-resourced hospital outranks a closer-but-crowded one.
"""

import unittest
import os
import sys

# Ensure backend package can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
workspace_dir = os.path.dirname(parent_dir)
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from backend.recommendation import (
    WEIGHTS,
    rank_hospitals,
    compute_distance_subscore,
    compute_bed_subscore,
    compute_doctor_subscore,
    compute_resource_subscore,
    compute_crowd_subscore,
)
from backend.database import repo


class RecommendationWeightsTestCase(unittest.TestCase):

    def test_weights_definition(self):
        """Verify weights match requirements and sum to exactly 1.0 (100%)."""
        self.assertEqual(WEIGHTS["beds"], 0.30, "Bed weight must be 30%")
        self.assertEqual(WEIGHTS["distance"], 0.20, "Distance weight must be 20%")
        self.assertEqual(WEIGHTS["doctors"], 0.20, "Doctor weight must be 20%")
        self.assertEqual(WEIGHTS["resources"], 0.15, "Resources weight must be 15%")
        self.assertEqual(WEIGHTS["crowd"], 0.15, "Crowd weight must be 15%")
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=5)

    def test_subscore_normalizations(self):
        """Verify each sub-score function normalizes to [0.0, 1.0]."""
        # Distance
        self.assertAlmostEqual(compute_distance_subscore(1.0), 1.0)
        self.assertAlmostEqual(compute_distance_subscore(25.0), 0.0)
        self.assertTrue(0.0 <= compute_distance_subscore(10.0) <= 1.0)

        # Beds
        h_full = {"beds": {"total": 100, "occupied": 100, "available": 0}}
        h_half = {"beds": {"total": 100, "occupied": 50, "available": 50}}
        self.assertAlmostEqual(compute_bed_subscore(h_full), 0.0)
        self.assertAlmostEqual(compute_bed_subscore(h_half), 0.5)

        # Doctors
        self.assertAlmostEqual(compute_doctor_subscore({"doctor_status": "Available"}), 1.0)
        self.assertAlmostEqual(compute_doctor_subscore({"doctor_status": "Limited"}), 0.55)
        self.assertAlmostEqual(compute_doctor_subscore({"doctor_status": "Unavailable"}), 0.0)

        # Crowd
        self.assertAlmostEqual(compute_crowd_subscore({"crowd_status": "Low"}), 1.0)
        self.assertAlmostEqual(compute_crowd_subscore({"crowd_status": "Moderate"}), 0.55)
        self.assertAlmostEqual(compute_crowd_subscore({"crowd_status": "High"}), 0.10)

    def test_farther_better_resourced_hospital_outranks_closer_crowded_one(self):
        """
        Critical requirement test:
        Hospital A: Closest (1.2 km), but 96% occupied (4 beds left), High crowd, Limited doctors.
        Hospital B: Farther (7.0 km), but 40% available beds, Low crowd, Available doctors, Available resources.
        Expected: Hospital B ranks #1 and Hospital A ranks #2.
        """
        hospital_a = {
            "id": 101,
            "name": "Hospital A (Close but Overcrowded)",
            "locality": "Adyar",
            "distance_km": 1.2,  # Close
            "beds": {"total": 100, "occupied": 96, "available": 4},  # 4% available
            "doctor_status": "Limited",
            "crowd_status": "High",
            "crowd": {"current_patients": 200, "waiting_patients": 60},
            "resources": [
                {"resource_type": "ICU beds", "status": "Limited"},
                {"resource_type": "Oxygen", "status": "Available"},
                {"resource_type": "Pharmacy", "status": "Limited"},
                {"resource_type": "Lab", "status": "Limited"},
            ]
        }

        hospital_b = {
            "id": 102,
            "name": "Hospital B (Farther but Well-Resourced)",
            "locality": "Porur",
            "distance_km": 7.0,  # Farther
            "beds": {"total": 200, "occupied": 120, "available": 80},  # 40% available
            "doctor_status": "Available",
            "crowd_status": "Low",
            "crowd": {"current_patients": 30, "waiting_patients": 5},
            "resources": [
                {"resource_type": "ICU beds", "status": "Available"},
                {"resource_type": "Oxygen", "status": "Available"},
                {"resource_type": "Pharmacy", "status": "Available"},
                {"resource_type": "Lab", "status": "Available"},
            ]
        }

        ranked = rank_hospitals([hospital_a, hospital_b], patient_locality="Adyar")
        
        self.assertEqual(len(ranked), 2)
        # Hospital B must be ranked #1
        self.assertEqual(ranked[0]["id"], 102, "Hospital B must outrank Hospital A due to beds, crowd, and doctors")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])
        
        # Verify plain-language explanation mentions strengths
        self.assertIn("available beds", ranked[0]["recommendation_reason"])
        self.assertIn("lower crowd", ranked[0]["recommendation_reason"])

    def test_real_dataset_recommendations(self):
        """Verify recommendations on the 10 real Chennai hospitals."""
        hospitals = repo.get_hospitals(patient_locality="Adyar")
        ranked = rank_hospitals(hospitals, patient_locality="Adyar", limit=5)
        
        self.assertEqual(len(ranked), 5)
        # Scores must be in descending order
        scores = [h["score"] for h in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Check disclaimer presence
        for h in ranked:
            self.assertIn("algorithm_disclaimer", h)
            self.assertTrue(len(h["recommendation_reason"]) > 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
