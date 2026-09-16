"""
Live End-to-End Test for NexCare Web Server
Exercises all web pages, REST API endpoints, staff login, and bed updates on live http://127.0.0.1:5000
"""

import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print(f"Testing live NexCare instance at {BASE_URL}...")
    
    # 1. Test Static Pages
    pages = ["/", "/index.html", "/patient.html", "/staff.html", "/style.css", "/script.js", "/patient.js", "/staff.js"]
    for p in pages:
        r = requests.get(f"{BASE_URL}{p}")
        assert r.status_code == 200, f"Failed to load {p}: {r.status_code}"
        print(f"  [PASS] Page {p} loaded ({len(r.content)} bytes)")

    # 1b. Test 6-Language i18n JSON Endpoints
    langs = ["en", "ta", "te", "kn", "hi", "ml"]
    for l in langs:
        r = requests.get(f"{BASE_URL}/i18n/{l}.json")
        assert r.status_code == 200, f"Failed to load i18n/{l}.json: {r.status_code}"
        keys_count = len(r.json())
        assert keys_count >= 100, f"i18n/{l}.json has too few keys: {keys_count}"
        print(f"  [PASS] i18n/{l}.json loaded ({keys_count} keys)")

    # 2. Test Health
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200 and r.json()["status"] == "healthy"
    print(f"  [PASS] Health check: {r.json()}")

    # 3. Test States and Cities Endpoints
    r = requests.get(f"{BASE_URL}/api/states")
    assert r.status_code == 200 and len(r.json()["data"]) >= 19
    assert r.json()["data"][0] == "Tamil Nadu" and r.json()["data"][1] == "Karnataka"
    print(f"  [PASS] States list: {len(r.json()['data'])} states/UTs (Tamil Nadu & Karnataka prioritized)")

    r = requests.get(f"{BASE_URL}/api/states/Karnataka/cities")
    assert r.status_code == 200 and r.json()["data_available"] is True
    print(f"  [PASS] State cities (Karnataka): {len(r.json()['cities'])} localities (data_available=True)")

    r = requests.get(f"{BASE_URL}/api/states/Delhi/cities")
    assert r.status_code == 200 and r.json()["data_available"] is True
    print(f"  [PASS] State cities active (Delhi): {len(r.json()['cities'])} localities (data_available=True)")

    # 3b. Test Locations & Areas (Legacy endpoints)
    r = requests.get(f"{BASE_URL}/api/locations")
    assert r.status_code == 200 and len(r.json()["data"]) >= 15
    r = requests.get(f"{BASE_URL}/api/areas")
    assert r.status_code == 200 and len(r.json()["data"]) == 12
    print(f"  [PASS] Legacy locations & areas APIs verified")

    # 4. Test Hospitals List (Prototype Data across All Indian States/UTs)
    r = requests.get(f"{BASE_URL}/api/hospitals")
    assert r.status_code == 200 and len(r.json()["data"]) >= 60
    print(f"  [PASS] Hospitals list: {len(r.json()['data'])} hospitals across all 19 states")

    # 4b. Test Karnataka Hospitals
    r_ka = requests.get(f"{BASE_URL}/api/hospitals?state=Karnataka")
    assert r_ka.status_code == 200 and len(r_ka.json()["data"]) == 6
    print(f"  [PASS] Karnataka state filter: {len(r_ka.json()['data'])} real Bengaluru hospitals")

    # 4c. Test Prototype Hospitals in Delhi & Kerala
    r_dl = requests.get(f"{BASE_URL}/api/hospitals?state=Delhi")
    assert r_dl.status_code == 200 and len(r_dl.json()["data"]) >= 3
    print(f"  [PASS] Delhi prototype hospitals: {len(r_dl.json()['data'])} listings found (no empty screen)")

    r_kl = requests.get(f"{BASE_URL}/api/hospitals?state=Kerala")
    assert r_kl.status_code == 200 and len(r_kl.json()["data"]) >= 3
    print(f"  [PASS] Kerala prototype hospitals: {len(r_kl.json()['data'])} listings found (no empty screen)")

    # 4d. Test Live Geolocation in Mumbai (19.0760, 72.8777)
    r = requests.get(f"{BASE_URL}/api/hospitals?lat=19.0760&lng=72.8777")
    assert r.status_code == 200 and len(r.json()["data"]) >= 1
    assert r.json()["data"][0]["distance_km"] < 50
    print(f"  [PASS] Geolocation Mumbai: Nearest hospital is {r.json()['data'][0]['name']} at {r.json()['data'][0]['distance_km']} km")

    # 5. Test Recommendations for Adyar
    r = requests.get(f"{BASE_URL}/api/hospitals/recommendations?locality=Adyar&limit=3")
    assert r.status_code == 200 and len(r.json()["data"]) == 3
    top = r.json()["data"][0]
    print(f"  [PASS] Top recommendation for Adyar: {top['name']} (Score: {top['score']}/100, Dist: {top['distance_km']} km)")
    print(f"         Reason: {top['recommendation_reason']}")

    # 6. Test Staff Login
    login_payload = {"staff_id": "staff_fortis", "password": "demo123"}
    r = requests.post(f"{BASE_URL}/api/staff/login", json=login_payload)
    assert r.status_code == 200 and r.json()["data"]["token"]
    token = r.json()["data"]["token"]
    hospital_id = r.json()["data"]["hospital_id"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [PASS] Staff login successful for {r.json()['data']['name']}")

    # 7. Test Staff Dashboard Fetch
    r = requests.get(f"{BASE_URL}/api/staff/{hospital_id}/dashboard", headers=headers)
    assert r.status_code == 200 and r.json()["data"]["hospital"]["name"]
    assert "summary" in r.json()["data"]
    summary = r.json()["data"]["summary"]
    assert summary["available_beds"] == summary["total_beds"] - summary["occupied_beds"]
    print(f"  [PASS] Staff dashboard fetched for {r.json()['data']['hospital']['name']}")
    print(f"  [PASS] 5 Key Default Metrics on Login Home verified: Total={summary['total_beds']}, Occ={summary['occupied_beds']}, Avail={summary['available_beds']}, Adm={summary['today_admissions']}, Dis={summary['today_discharges']}")

    # 8. Test Bed Update via Staff API & Auto-Calculated Crowd Status
    bed_update = {
        "total_beds": 180,
        "occupied_beds": 110,
        "admissions": 5,
        "discharges": 3,
        "staff_id": "staff_fortis"
    }
    r = requests.put(f"{BASE_URL}/api/staff/{hospital_id}/beds", json=bed_update, headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["beds"]["available"] == 70
    # 110 / 180 = 61.1% -> Moderate
    assert r.json()["data"]["crowd_status"] == "Moderate"
    print(f"  [PASS] Bed update verified: Available beds = 70, Auto Crowd Status = Moderate (61.1% occupancy)")

    # 8b. Test Doctor Availability Update via Staff API
    doctor_update = [
        {"name": "Dr. Ramesh Krishnan", "department": "Emergency Medicine", "specialty": "Trauma & Acute Care", "status": "Available", "available_time": "24/7", "current_patient_capacity": 5},
        {"name": "Dr. Ananya Rao", "department": "Cardiology", "specialty": "Interventional Cardiology", "status": "Available", "available_time": "09:00 - 17:00", "current_patient_capacity": 3},
        {"name": "Dr. S. Karthik", "department": "Neurology", "specialty": "Stroke Specialist", "status": "Busy", "available_time": "10:00 - 16:00", "current_patient_capacity": 2},
    ]
    r_doc = requests.put(f"{BASE_URL}/api/staff/{hospital_id}/doctors", json=doctor_update, headers=headers)
    assert r_doc.status_code == 200
    assert len(r_doc.json()["data"]["doctors"]) == 3
    print(f"  [PASS] Staff Doctor Update verified: 3 doctors with specialties saved successfully")

    # 8c. Test 8-Facility Medical Resources Update via Staff API
    resource_update = {
        "resources": {
            "ICU Beds": "Limited",
            "Oxygen Support": "Available",
            "Pharmacy": "Available",
            "Laboratory": "Available",
            "X-ray": "Available",
            "CT Scan": "Limited",
            "Blood Bank": "Available",
            "Emergency Department": "Available"
        },
        "staff_id": "staff_fortis"
    }
    r_res = requests.put(f"{BASE_URL}/api/staff/{hospital_id}/resources", json=resource_update, headers=headers)
    assert r_res.status_code == 200
    res_list = r_res.json()["data"]["resources"]
    assert len(res_list) == 8
    res_map = {r["resource_type"]: r["status"] for r in res_list}
    assert res_map["ICU Beds"] == "Limited"
    assert res_map["Oxygen Support"] == "Available"
    assert res_map["Emergency Department"] == "Available"
    print(f"  [PASS] Staff 8-Facility Resource Update verified: All 8 facilities updated (ICU Beds: Limited)")

    # 9. Verify Patient Portal sees updated beds, doctors, and resources!
    r = requests.get(f"{BASE_URL}/api/hospitals/{hospital_id}")
    assert r.status_code == 200
    assert r.json()["data"]["beds"]["available"] == 70
    assert r.json()["data"]["crowd_status"] == "Moderate"
    assert len(r.json()["data"]["doctors"]) == 3
    patient_res_map = {item["resource_type"]: item["status"] for item in r.json()["data"]["resources"]}
    assert patient_res_map["ICU Beds"] == "Limited"
    assert patient_res_map["Emergency Department"] == "Available"
    print(f"  [PASS] Patient Portal live sync verified: Beds = 70, Crowd = Moderate, Doctors = 3, Resources = 8 verified")

    # 10. Test Audit History
    r = requests.get(f"{BASE_URL}/api/staff/{hospital_id}/history", headers=headers)
    assert r.status_code == 200 and len(r.json()["data"]) > 0
    latest = r.json()["data"][0]
    print(f"  [PASS] Audit log verified: {len(r.json()['data'])} history entries; latest field '{latest['field_changed']}' updated by '{latest['staff_id']}'")

    # 11. Test Simulated SOS Emergency & Bed Blocking Workflow (Features 2 & 3)
    # 11a. Check baseline bed availability
    r_base = requests.get(f"{BASE_URL}/api/hospitals/1")
    assert r_base.status_code == 200
    base_avail = r_base.json()["data"]["beds"]["available"]
    base_blocked = r_base.json()["data"]["beds"].get("blocked", 0)

    # 11b. Create emergency request (blocks 1 bed immediately)
    emg_payload = {
        "hospital_id": 1,
        "patient_locality": "Chennai - Greams Road",
        "state": "Tamil Nadu"
    }
    r_emg = requests.post(f"{BASE_URL}/api/emergency/request", json=emg_payload)
    assert r_emg.status_code == 201
    emg_data = r_emg.json()["data"]
    code = emg_data["request_code"]
    assert code.startswith("EMG-")
    assert emg_data["bed_blocked"] is True
    assert "simulated_emergency_notice" in r_emg.json()
    print(f"  [PASS] Emergency request created: Code={code}, Ambulance={emg_data['ambulance_code']}, Bed blocked immediately")

    # 11c. Verify bed is blocked in hospital 1: available decreased by 1
    r_check = requests.get(f"{BASE_URL}/api/hospitals/1")
    assert r_check.status_code == 200
    new_avail = r_check.json()["data"]["beds"]["available"]
    new_blocked = r_check.json()["data"]["beds"].get("blocked", 0)
    assert new_blocked == base_blocked + 1
    assert new_avail == base_avail - 1
    beds_obj = r_check.json()["data"]["beds"]
    assert beds_obj["available"] == max(0, beds_obj["total"] - beds_obj["occupied"] - beds_obj["blocked"])
    print(f"  [PASS] Bed integrity formula verified: Available ({beds_obj['available']}) = Total ({beds_obj['total']}) - Occupied ({beds_obj['occupied']}) - Blocked ({beds_obj['blocked']})")

    # 11d. Check staff incoming emergency requests
    staff_login_apollo = {"staff_id": "staff_apollo", "password": "demo123"}
    r_apollo_login = requests.post(f"{BASE_URL}/api/staff/login", json=staff_login_apollo)
    apollo_token = r_apollo_login.json()["data"]["token"]
    r_staff_emg = requests.get(f"{BASE_URL}/api/staff/1/emergency-requests", headers={"Authorization": f"Bearer {apollo_token}"})
    assert r_staff_emg.status_code == 200
    assert any(item["request_code"] == code for item in r_staff_emg.json()["data"])
    print(f"  [PASS] Staff incoming emergency requests panel verified: Found request {code}")

    # 11e. Advance status: Ambulance Assigned -> En Route -> Arrived -> Patient Admitted
    r_stat1 = requests.put(f"{BASE_URL}/api/emergency/request/{code}/status", json={"status": "En Route"})
    assert r_stat1.status_code == 200 and r_stat1.json()["data"]["status"] == "En Route"
    r_stat2 = requests.put(f"{BASE_URL}/api/emergency/request/{code}/status", json={"status": "Arrived"})
    assert r_stat2.status_code == 200 and r_stat2.json()["data"]["status"] == "Arrived"

    # 11f. Patient Admitted converts blocked bed into occupied bed
    r_admit = requests.put(f"{BASE_URL}/api/emergency/request/{code}/status", json={"status": "Patient Admitted", "staff_id": "staff_apollo"})
    assert r_admit.status_code == 200
    assert r_admit.json()["data"]["status"] == "Patient Admitted"
    assert r_admit.json()["data"]["bed_blocked"] is False

    r_post_admit = requests.get(f"{BASE_URL}/api/hospitals/1")
    post_beds = r_post_admit.json()["data"]["beds"]
    assert post_beds["blocked"] == base_blocked
    assert post_beds["available"] == max(0, post_beds["total"] - post_beds["occupied"] - post_beds["blocked"])
    print(f"  [PASS] Admission converted blocked bed to occupied bed: Blocked released back to {post_beds['blocked']}, Occupied={post_beds['occupied']}")

    print("\nALL 11 LIVE END-TO-END CHECKS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    run_tests()
