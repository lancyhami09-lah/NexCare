"""
NexCare Recommendation Engine
Strict, transparent, and testable 5-factor multi-dimensional ranking algorithm.

Factors & Weights:
- Bed Availability:   30% (weight: 0.30)
- Distance Proximity: 20% (weight: 0.20)
- Doctor Availability:20% (weight: 0.20)
- General Resources:  15% (weight: 0.15)
- Crowd Level:        15% (weight: 0.15)
Total:               100% (weight: 1.00)

Guiding Rule:
No hospital is ranked by distance alone. A farther-but-better-resourced hospital
(with beds, doctors, resources, and low crowd) will outrank a closer-but-crowded one.

DISCLAIMER:
All rankings are algorithmic suggestions based on simulated demo indicators.
They do NOT constitute medical advice, triage, diagnosis, or guarantees of admission.
"""

from copy import deepcopy

WEIGHTS = {
    "beds": 0.30,
    "distance": 0.20,
    "doctors": 0.20,
    "resources": 0.15,
    "crowd": 0.15,
}

MAX_CONSIDERED_DISTANCE_KM = 25.0


def compute_distance_subscore(distance_km: float) -> float:
    """Normalize distance to 0.0 - 1.0 (closer = higher score)."""
    if distance_km is None:
        return 0.5
    if distance_km <= 1.5:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (distance_km / MAX_CONSIDERED_DISTANCE_KM)))


def compute_bed_subscore(hospital: dict) -> float:
    """Normalize bed availability ratio (available / total) to 0.0 - 1.0."""
    beds = hospital.get("beds", {})
    total = beds.get("total", 0)
    available = beds.get("available", 0)
    if total <= 0:
        return 0.0
    ratio = max(0.0, min(1.0, available / total))
    return round(ratio, 4)


def compute_doctor_subscore(hospital: dict) -> float:
    """Score doctor availability based on department statuses (0.0 - 1.0)."""
    doctors = hospital.get("doctors", [])
    if doctors:
        status_map = {"Available": 1.0, "Limited": 0.55, "Unavailable": 0.0}
        scores = [status_map.get(d.get("status"), 0.5) for d in doctors]
        return round(sum(scores) / len(scores), 4)
    # Fallback to overall doctor_status
    status = hospital.get("doctor_status", "Available")
    return {"Available": 1.0, "Limited": 0.55, "Unavailable": 0.0}.get(status, 0.5)


def compute_resource_subscore(hospital: dict) -> float:
    """Score general medical resources (ICU, Oxygen, Lab, Pharmacy, etc.) (0.0 - 1.0)."""
    resources = hospital.get("resources", [])
    if not resources:
        return 0.5
    status_map = {"Available": 1.0, "Limited": 0.5, "Unavailable": 0.0}
    scores = [status_map.get(r.get("status"), 0.5) for r in resources]
    return round(sum(scores) / len(scores), 4)


def compute_crowd_subscore(hospital: dict) -> float:
    """Score crowd level (lower crowd = higher score) (0.0 - 1.0)."""
    crowd_status = hospital.get("crowd_status", "Moderate")
    return {"Low": 1.0, "Moderate": 0.55, "High": 0.1}.get(crowd_status, 0.55)


def generate_plain_language_explanation(hospital: dict, factors: dict, patient_locality: str = None) -> str:
    """
    Generate an easy-to-read, plain-language reason explaining why
    this hospital was recommended or ranked as it is compared with other nearby facilities.
    """
    beds = hospital.get("beds", {})
    available_beds = beds.get("available", 0)
    crowd_status = hospital.get("crowd_status", "Moderate")
    crowd = hospital.get("crowd", {})
    waiting = crowd.get("waiting_patients", 0)
    distance = hospital.get("distance_km", 0)

    strengths = []
    cautions = []

    # Bed availability (30% weight)
    if factors["beds"] >= 0.25:
        strengths.append(f"available beds ({available_beds} beds ready)")
    elif factors["beds"] < 0.10:
        cautions.append(f"critical bed occupancy ({available_beds} beds left)")

    # Doctor availability (20% weight)
    if factors["doctors"] >= 0.8:
        strengths.append("doctors on-duty across key departments")
    elif factors["doctors"] <= 0.2:
        cautions.append("doctor consultations temporarily unavailable")

    # Resource availability (15% weight)
    key_available = [r["resource_type"] for r in hospital.get("resources", []) if r.get("status") == "Available"]
    if len(key_available) >= 7:
        strengths.append("required emergency and medical resources (ICU, Oxygen, Lab, Pharmacy)")
    elif factors["resources"] >= 0.7:
        strengths.append("essential medical resources ready")

    # Crowd level (15% weight)
    if crowd_status == "Low":
        strengths.append(f"lower crowd ({waiting} waiting)" if waiting > 0 else "lower crowd congestion (within normal capacity)")
    elif crowd_status == "High":
        cautions.append(f"high crowd load ({waiting} waiting in queue)" if waiting > 0 else "high crowd occupancy nearing maximum capacity")

    # Proximity note
    proximity_phrase = f"located {distance} km from {patient_locality}" if patient_locality else f"approx. {distance} km away"

    if strengths:
        reason = f"Recommended because it has {', '.join(strengths[:-1])}{' and ' if len(strengths) > 1 else ''}{strengths[-1]} compared with other nearby hospitals ({proximity_phrase})."
    else:
        reason = f"Maintains a balanced overall rating ({proximity_phrase})."

    if cautions:
        reason += f" Please note: {', '.join(cautions)}."

    return reason


def rank_hospitals(hospitals: list, patient_locality: str = None, limit: int = None, lat: float = None, lng: float = None, **kwargs) -> list:
    """
    Takes a list of hospital dictionaries and optional patient_locality,
    evaluates each strictly against the 5 weighted factors, attaches detailed scores
    and plain-language explanations, and returns a descending sorted list.
    """
    scored_hospitals = []
    for h in hospitals:
        distance = h.get("distance_km", 6.5)
        
        factor_scores = {
            "beds": compute_bed_subscore(h),
            "distance": compute_distance_subscore(distance),
            "doctors": compute_doctor_subscore(h),
            "resources": compute_resource_subscore(h),
            "crowd": compute_crowd_subscore(h),
        }

        # Weighted sum: strictly 0.0 to 100.0
        total_score = sum(factor_scores[k] * WEIGHTS[k] for k in WEIGHTS) * 100.0
        total_score = round(total_score, 1)

        explanation = generate_plain_language_explanation(h, factor_scores, patient_locality)

        ranked_item = deepcopy(h)
        ranked_item["score"] = total_score
        ranked_item["factor_scores"] = {
            k: round(v * 100, 1) for k, v in factor_scores.items()
        }
        ranked_item["weights"] = {
            k: int(v * 100) for k, v in WEIGHTS.items()
        }
        ranked_item["recommendation_reason"] = explanation
        ranked_item["algorithm_disclaimer"] = (
            "Simulated recommendation score based strictly on the 5 demo availability indicators. "
            "Not a medical triage evaluation or guarantee of admission."
        )
        scored_hospitals.append(ranked_item)

    # Sort strictly by total score descending, secondarily by distance ascending
    scored_hospitals.sort(key=lambda x: (-x["score"], x.get("distance_km", 999), x.get("name", "")))

    if limit and limit > 0:
        return scored_hospitals[:limit]
    return scored_hospitals
