# NexCare — Healthcare Support Web Application

> **Smart Healthcare Availability & Transparent Hospital Recommendation System**  
> Helping patients find suitable nearby healthcare facilities by intelligently evaluating travel distance, available beds, on-duty physicians, medical resources, and patient crowd levels across India, with verified live data in Tamil Nadu (Chennai) and Karnataka (Bengaluru).

---

## Mandatory Medical & Data Disclaimers

> [!IMPORTANT]
> **Simulated Demo Data Notice:**  
> Hospital names, addresses, and geographic coordinates are real, publicly verifiable healthcare facilities in Tamil Nadu and Karnataka, India. Availability information (bed counts, doctor on-duty statuses, diagnostic equipment, and crowd counts) shown here is **simulated demo data** and must be verified directly with the hospital.

> [!CAUTION]
> **Emergency Medical Services Disclaimer:**  
> If this is a medical emergency, contact emergency services (**108 for Ambulance / 112 for National Emergency**) or visit the nearest emergency department immediately. **NexCare is an informational guidance tool — it does NOT provide medical advice, diagnosis, bed reservations, or emergency dispatch.**

---

## 1. Project Concept & Pitch

When urgent care is needed, navigating to simply the *closest* hospital can lead to critical delays if that facility is at maximum capacity, facing physician shortages, or overwhelmed with long waiting queues.

**NexCare** solves this by evaluating five operational dimensions with transparent mathematical weighting:
1. **Available Bed Capacity (30%)** — Real-time available-to-total bed ratio.
2. **Travel Proximity (20%)** — Real geographic distance calculated using the Haversine formula from the patient's chosen locality or live GPS coordinates.
3. **Doctor Availability (20%)** — Physician coverage across emergency medicine, cardiology, neurology, orthopedics, and pediatrics.
4. **Critical Medical Resources (15%)** — Operational readiness of ICU beds, Oxygen supply, Blood bank, CT scan, Lab, Pharmacy, and Emergency Department.
5. **Patient Crowd Levels (15%)** — Active patient congestion and triage queues to minimize wait times.

**Example Behavior:**  
If Hospital A is closest (e.g. 1.2 km away) but 98% occupied with 120 patients waiting in triage, and Hospital B is 3.8 km away with 70 available beds, full doctor coverage, and minimal queue, NexCare ranks Hospital B higher and explains why in clear, plain language in any of 6 Indian languages.

---

## 2. Project Architecture & Directory Structure

```
NexCare/
├── frontend/
│   ├── i18n/                 # Multi-language translation dictionaries (100% key parity)
│   │   ├── en.json           # English
│   │   ├── ta.json           # Tamil (தமிழ்)
│   │   ├── te.json           # Telugu (తెలుగు)
│   │   ├── kn.json           # Kannada (ಕನ್ನಡ)
│   │   ├── hi.json           # Hindi (हिन्दी)
│   │   └── ml.json           # Malayalam (മലയാളം)
│   ├── index.html            # Public landing portal & quick locality finder
│   ├── patient.html          # Public Patient Dashboard (search, filters, AI recommendations, modal, voice)
│   ├── staff.html            # Login-gated Hospital Staff Dashboard (beds, crowd, doctors, resources, warnings)
│   ├── style.css             # Healthcare design system (WCAG AA accessible, responsive, micro-animations)
│   ├── script.js             # Universal controller (i18n engine, Web Speech API Voice Assistant & Stop button)
│   ├── patient.js            # Patient portal controller (dynamic cards, modal, read-aloud buttons, SOS modal)
│   └── staff.js              # Staff portal controller (real-time validation, PUT updates, audit log)
├── backend/
│   ├── app.py                # Flask application factory, static file routing, health check
│   ├── api.py                # REST API blueprint with validation, auth guards, and error envelopes
│   ├── database.py           # Dual-mode repository (MySQL connector + zero-setup in-memory mock store)
│   ├── recommendation.py     # Pure 5-factor recommendation engine & plain-language explainer
│   ├── config.py             # Configuration, coordinates, thresholds, notices, and disclaimers
│   ├── requirements.txt      # Python dependencies (Flask, Flask-CORS, PyMySQL, python-dotenv)
│   └── tests/
│       ├── test_api.py       # API unit & integration test suite (28 tests)
│       ├── test_recommendation_weights.py # 5-factor weights verification tests (4 tests)
│       ├── test_all_india_location.py     # All-India geolocation and language parity tests (7 tests)
│       ├── test_update3.py   # Full features & sync tests (11 tests)
│       └── e2e_live_test.py  # Live end-to-end server verification runner (10 verification stages)
├── database/
│   ├── schema.sql            # Complete MySQL DDL schema (7 tables with PK, FK, cascades, indexes)
│   └── sample_data.sql       # Realistic dataset for 16 real hospitals & demo staff accounts
├── docs/
│   ├── README.md             # This comprehensive architecture and setup manual
│   └── API_DOCUMENTATION.md  # Complete REST API reference with request/response schemas
├── .env.example              # Environment variables template
└── .env                      # Local runtime environment config
```

---

## 3. Real Hospitals Dataset (Tamil Nadu & Karnataka)

The dataset includes **16 real, publicly verifiable hospitals** with realistic simulated availability:

### Tamil Nadu (10 Chennai Facilities)
| ID | Hospital Name | Locality | State | Type | Contact Number |
|---|---|---|---|---|---|
| 1 | Apollo Main Hospitals | Greams Road | Tamil Nadu | Private | +91 44 2829 0200 |
| 2 | Rajiv Gandhi Government General Hospital | Park Town | Tamil Nadu | Government | +91 44 2530 5000 |
| 3 | Govt Multi Super Speciality Hospital | Omandurar | Tamil Nadu | Government | +91 44 2566 6000 |
| 4 | Govt Kilpauk Medical College Hospital | Kilpauk | Tamil Nadu | Government | +91 44 2836 4951 |
| 5 | Fortis Malar Hospital | Adyar | Tamil Nadu | Private | +91 44 4289 2222 |
| 6 | MIOT International | Manapakkam | Tamil Nadu | Private | +91 44 4200 2288 |
| 7 | Sri Ramachandra Medical Centre | Porur | Tamil Nadu | Private | +91 44 4592 8500 |
| 8 | Madras Medical Mission Hospital | Mogappair | Tamil Nadu | Private | +91 44 2656 8000 |
| 9 | Dr. Mehta's Hospitals | Chetpet | Tamil Nadu | Private | +91 44 4227 1001 |
| 10 | Kauvery Hospital | Vadapalani | Tamil Nadu | Private | +91 44 4000 6000 |

### Karnataka (6 Bengaluru Facilities)
| ID | Hospital Name | Locality | State | Type | Contact Number |
|---|---|---|---|---|---|
| 11 | Manipal Hospital Old Airport Road | Old Airport Road | Karnataka | Private | +91 80 2502 4444 |
| 12 | Victoria Hospital (BMCRI) | Kalasipalya | Karnataka | Government | +91 80 2670 1150 |
| 13 | Narayana Institute of Cardiac Sciences | Bommasandra | Karnataka | Private | +91 80 7122 2222 |
| 14 | Bowring & Lady Curzon Hospital | Shivaji Nagar | Karnataka | Government | +91 80 2559 1362 |
| 15 | Fortis Hospital Bannerghatta Road | Bannerghatta Road | Karnataka | Private | +91 80 6621 4444 |
| 16 | St. John's Medical College Hospital | Koramangala | Karnataka | Private | +91 80 2206 5000 |

> [!NOTE]
> **Honest Notice for Unpopulated States:** When a patient selects a state outside Tamil Nadu or Karnataka, NexCare **never fabricates placeholder hospitals**. It displays an honest notice: *"Hospital listings are not yet available for this state. Full verified hospital data is currently active for Tamil Nadu and Karnataka."*

---

## 4. Quick Start & Setup Guide

### Prerequisites
- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14
- **Web Browser**: Chrome, Edge, Firefox, or Safari
- **MySQL (Optional)**: If you wish to use MySQL, install MySQL 8.0+. By default, NexCare runs out-of-the-box in **Zero-Config Mock Mode**!

### Step 1: Clone or Navigate to Workspace
```bash
cd "d:\NexCare Project"
```

### Step 2: Create and Activate a Python Virtual Environment
**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Default `.env` configuration (Zero-setup mock mode):
```ini
DATA_MODE=mock
SECRET_KEY=nexcare-local-demo-secret-key-change-me
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=nexcare
```
**Environment Variables Explained:**
- `DATA_MODE`: Set to `mock` for zero-configuration in-memory mode, or `mysql` for live database mode.
- `SECRET_KEY`: Cryptographic signing key for sessions and demo security tokens.
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`: MySQL connection parameters.

### Step 5: (Optional) MySQL Database Setup
If you want to run against a live MySQL server:
1. Open MySQL CLI or Workbench.
2. Execute `database/schema.sql` to generate database and tables:
   ```sql
   source d:/NexCare Project/database/schema.sql;
   ```
3. Execute `database/sample_data.sql` to populate sample data:
   ```sql
   source d:/NexCare Project/database/sample_data.sql;
   ```
4. Update `.env` to set `DATA_MODE=mysql` and your credentials.
*(Note: If MySQL is unreachable, NexCare automatically falls back to Mock Mode safely without crashing!)*

### Step 6: Start the NexCare Web Application
```bash
python -m backend.app
```
You will see:
```
=================================================================
  NexCare — Healthcare Support Web Application
  Active Data Mode: MOCK
  Server running at: http://127.0.0.1:5000
  Patient Portal:    http://127.0.0.1:5000/patient.html
  Staff Portal:      http://127.0.0.1:5000/staff.html
=================================================================
```

Open your browser and navigate to:
- **Home Landing Portal:** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Patient Hospital Finder:** [http://127.0.0.1:5000/patient.html](http://127.0.0.1:5000/patient.html)
- **Hospital Staff Dashboard:** [http://127.0.0.1:5000/staff.html](http://127.0.0.1:5000/staff.html)

---

## 5. Demo Staff Login Credentials

All demo accounts share the password: `demo123`.

| Staff ID | Hospital Name | Locality & State | Role / Staff Name |
|---|---|---|---|
| `staff_fortis` | Fortis Malar Hospital | Adyar, Chennai (TN) | Nurse Supervisor Deepa |
| `staff_apollo` | Apollo Main Hospitals | Greams Road, Chennai (TN) | Dr. S. K. Apollo Admin |
| `staff_rggh` | Rajiv Gandhi Govt General Hospital | Park Town, Chennai (TN) | Dr. V. Ramanathan (RGGGH) |
| `staff_srmc` | Sri Ramachandra Medical Centre | Porur, Chennai (TN) | Chief Administrator Priya |
| `staff_manipal` | Manipal Hospital Old Airport Rd | Old Airport Rd, Bengaluru (KA) | Dr. Sudarshan Ballal (Manipal) |
| `staff_narayana`| Narayana Institute of Cardiac Sciences | Bommasandra, Bengaluru (KA) | Dr. Devi Shetty (Narayana) |
| `staff_miot` | MIOT International | Manapakkam, Chennai (TN) | Duty Manager Karthik |
| `staff_omandurar`| Govt Multi Super Speciality Hospital | Omandurar, Chennai (TN) | Dr. K. Meenakshi |
| `demo-staff` | Fortis Malar Hospital (Quick Demo) | Adyar, Chennai (TN) | Default Demo Staff |

*(Note: On the Staff Login screen, clickable credential chips allow instant sign-in without typing).*

---

## 6. Transparent Recommendation Algorithm Explained

The pure scoring function resides in `backend/recommendation.py`:

$$\text{Total Score} = (0.30 \times \text{Beds}) + (0.20 \times \text{Distance}) + (0.20 \times \text{Doctors}) + (0.15 \times \text{Resources}) + (0.15 \times \text{Crowd})$$

### Factor Normalization Rules:
1. **Bed Availability ($30\%$)**:
   $$\text{Sub-score} = \frac{\text{Available Beds}}{\text{Total Beds}} \in [0.0, 1.0]$$
2. **Distance Proximity ($20\%$)**:
   Calculated using the Haversine formula:
   $$\text{Sub-score} = \max\left(0.0, 1.0 - \frac{\text{Distance (km)}}{25.0}\right)$$
3. **Doctor Availability ($20\%$)**:
   - `Available` = $1.0$
   - `Limited` = $0.55$
   - `Unavailable` = $0.0$
4. **Critical Medical Resources ($15\%$)**:
   Average readiness score across 8 key units (ICU beds, Oxygen, Pharmacy, Lab, X-ray, CT scan, Blood bank, ED):
   $$\text{Sub-score} = \frac{1}{8} \sum \text{Status Score}$$
5. **Patient Crowd ($15\%$)**:
   - `Low` ($\le 40$ patients) = $1.0$
   - `Moderate` ($41 - 80$ patients) = $0.55$
   - `High` ($> 80$ patients) = $0.10$

### Plain-Language Explainer Generator
The engine dynamically compiles a localized explanation justifying the recommendation:
> *"Recommended because it has available beds (68 beds ready), doctors on-duty across key departments, required emergency and medical resources (ICU, Oxygen, Lab, Pharmacy) and lower crowd (6 waiting) compared with other nearby hospitals (located 0.6 km from Adyar)."*

---

## 7. Advanced Features: Voice Assistant, 6 Languages & All-India Geolocation

### A. Web Speech API Voice Assistant & Stop Button
- **Universal Availability**: Available on Patient Dashboard (`patient.html`) and Home Portal (`index.html`).
- **Stop Button**: A dedicated **Stop** button immediately halts active speech recognition and stops any in-progress speech synthesis.
- **Language Synchronization**: Spoken announcements immediately sync to the currently chosen language (`en`, `ta`, `te`, `kn`, `hi`, `ml`).
- **Voice Actions**:
  - Speak locality names (e.g. *"Adyar"*, *"Porur"*, *"Koramangala"*, *"അഡയാർ"*).
  - Speak search triggers (*"Search"*, *"Find hospitals"*, *"தேடு"*, *"തിരയുക"*, *"खोज"*).
  - Speak recommendation triggers (*"Recommend"*, *"Best hospitals"*, *"பரிந்துரை"*, *"ശുപാർശ"*).
  - Read hospital details aloud (*"Read hospital"* or click card **"🔊 Read Aloud"**).
  - Read announcements (*"📢 Tell Me Nearby Hospitals"* reads top 3 hospitals, distances, beds, and crowds).

### B. Multi-Language Support (6 Indian Languages)
- **English (`en`)**
- **Tamil (`ta` — தமிழ்)**
- **Telugu (`te` — తెలుగు)**
- **Kannada (`kn` — ಕನ್ನಡ)**
- **Hindi (`hi` — हिन्दी)**
- **Malayalam (`ml` — മലയാളം)**
- Full 100% key parity across all 6 dictionaries (138 keys each) with zero placeholder text.

### C. All-India Geolocation & Honest Scope
- **Live GPS**: Click **"📍 Use My Current Location"** to compute distance via browser Geolocation.
- **Two-Step Selector**: State dropdown filters to City/Locality dropdown.
- **Honest Non-Fabrication**: States without verified partner hospitals display transparent notices rather than dummy listings.

---

## 8. Dashboard Data Flow & Communication Diagrams

### Patient Search & Recommendation Flow
```mermaid
sequenceDiagram
    autonumber
    actor Patient as Patient
    participant Browser as Patient Portal (patient.html)
    participant API as Flask REST API (/api)
    participant Engine as Recommendation Engine
    participant DB as Hospital Repository (Mock/MySQL)

    Patient->>Browser: Selects Locality (or speaks "Adyar")
    Browser->>API: GET /api/hospitals?patient_locality=Adyar
    API->>DB: Fetch hospital records & compute Haversine distance
    DB-->>API: 16 Hospital entities with distances
    API-->>Browser: JSON hospital cards
    Browser-->>Patient: Displays cards with badges (Beds, Doctors, Crowd)

    Patient->>Browser: Clicks "View Best Recommendations"
    Browser->>API: GET /api/hospitals/recommendations?locality=Adyar&limit=5
    API->>DB: Fetch hospital records
    API->>Engine: Rank 16 hospitals with 5 weighted factors
    Engine->>Engine: Compute Total Scores & Plain-Language Reasons
    Engine-->>API: Top sorted hospitals with breakdowns
    API-->>Browser: JSON recommendations payload
    Browser-->>Patient: Renders ranked cards, match % scores, and explanations
```

### Staff Update & Live Sync Flow
```mermaid
sequenceDiagram
    autonumber
    actor Staff as Hospital Staff
    participant StaffUI as Staff Portal (staff.html)
    participant API as Flask REST API (/api)
    participant DB as Hospital Repository (Mock/MySQL)
    participant PatientUI as Patient Portal (patient.html)

    Staff->>StaffUI: Enters staff_fortis / demo123
    StaffUI->>API: POST /api/staff/login
    API->>DB: Authenticate credentials
    DB-->>API: Staff details + Hospital ID 5
    API-->>StaffUI: Bearer Token + Hospital Details
    StaffUI->>API: GET /api/staff/5/dashboard (with Bearer Token)
    API->>DB: Fetch summary, resources, doctors, warnings
    DB-->>API: Hospital status + 5 summary metrics
    API-->>StaffUI: Dashboard JSON payload
    StaffUI-->>Staff: Displays bed metrics (Total, Occupied, Available, Admissions, Discharges)

    Staff->>StaffUI: Updates occupied beds (e.g. 110) + admissions (5) + discharges (3)
    StaffUI->>StaffUI: Client validation (occupied <= total, non-negative)
    StaffUI->>API: PUT /api/staff/5/beds (with Bearer Token)
    API->>API: Server validation (occupied <= total)
    API->>DB: Update bed numbers & append audit log entry
    DB-->>API: Confirmed updated hospital
    API-->>StaffUI: 200 OK (Available beds = 70)
    StaffUI-->>Staff: Live metric cards update + success toast

    Note over PatientUI: Patient refreshes or browses
    PatientUI->>API: GET /api/hospitals/5
    API->>DB: Fetch hospital 5
    DB-->>API: Bed record with available = 70
    API-->>PatientUI: Live synced data
    PatientUI-->>PatientUI: Shows 70 available beds in real time!
```

---

## 9. Automated Testing & Verification Suite

NexCare contains **50 automated unit and integration tests** along with an automated live end-to-end verification script:

### Run All Unit & Feature Tests:
```bash
python -m unittest discover -s backend/tests -p "test_*.py" -v
```

### Run Live End-to-End Server Test:
```bash
python backend/tests/e2e_live_test.py
```

### Complete curl Command Examples:

**1. Service Health Check:**
```bash
curl -X GET http://127.0.0.1:5000/health
```

**2. List All Indian States:**
```bash
curl -X GET http://127.0.0.1:5000/api/states
```

**3. List Cities for Karnataka:**
```bash
curl -X GET http://127.0.0.1:5000/api/states/Karnataka/cities
```

**4. List Hospitals Filtered by State:**
```bash
curl -X GET "http://127.0.0.1:5000/api/hospitals?state=Karnataka"
```

**5. Query Ranked Recommendations:**
```bash
curl -X GET "http://127.0.0.1:5000/api/hospitals/recommendations?locality=Adyar&limit=3"
```

**6. Staff Login:**
```bash
curl -X POST http://127.0.0.1:5000/api/staff/login \
  -H "Content-Type: application/json" \
  -d '{"staff_id": "staff_fortis", "password": "demo123"}'
```

**7. Update Bed Availability:**
```bash
curl -X PUT http://127.0.0.1:5000/api/staff/5/beds \
  -H "Authorization: Bearer nexcare-demo-staff-token-2026" \
  -H "Content-Type: application/json" \
  -d '{"total_beds": 180, "occupied_beds": 110, "admissions": 5, "discharges": 3, "staff_id": "staff_fortis"}'
```

**8. Update Crowd Level:**
```bash
curl -X PUT http://127.0.0.1:5000/api/staff/5/crowd \
  -H "Authorization: Bearer nexcare-demo-staff-token-2026" \
  -H "Content-Type: application/json" \
  -d '{"current_patients": 32, "waiting_patients": 6, "staff_id": "staff_fortis"}'
```

**9. Update Critical Resources:**
```bash
curl -X PUT http://127.0.0.1:5000/api/staff/5/resources \
  -H "Authorization: Bearer nexcare-demo-staff-token-2026" \
  -H "Content-Type: application/json" \
  -d '{"resources": {"ICU beds": "Available", "Oxygen": "Available"}, "staff_id": "staff_fortis"}'
```

**10. View Audit Trail:**
```bash
curl -X GET http://127.0.0.1:5000/api/staff/5/history \
  -H "Authorization: Bearer nexcare-demo-staff-token-2026"
```

---

## 10. Common Errors & Troubleshooting

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask_cors'` | Dependencies not installed in active environment | Run `pip install -r backend/requirements.txt` inside your virtual environment |
| `Occupied beds cannot exceed total beds (409 Conflict)` | Client sent `occupied_beds > total_beds` | Correct inputs so that `occupied_beds <= total_beds`. NexCare returns HTTP 409 with `CAPACITY_EXCEEDED` |
| `Bearer token required (401 Unauthorized)` | Accessing staff endpoints without token | Include header `Authorization: Bearer <token>` returned by `/api/staff/login` |
| `MySQL connection refused` | MySQL server not active or credentials incorrect | NexCare automatically falls back to in-memory Mock Mode with 100% functionality |
| `Port 5000 already in use` | Another server instance is currently running | Terminate the existing process or start with `python -m backend.app --port 5001` |
| Speech Recognition not working | Browser permissions denied or HTTP connection | Enable microphone access in browser settings; Chrome/Edge recommend localhost or HTTPS |
| Indic voice sounds generic | Browser lacks native Indic TTS voice package | NexCare detects missing voice and falls back cleanly to English TTS with an on-screen toast |

---

## 11. 30-Second Pitch for Teammates & Hackathon Judges

> *"In medical emergencies, the nearest hospital is often the worst choice if it is overwhelmed or lacking doctors. NexCare is an intelligent, transparent healthcare guidance system that balances travel distance with real bed capacity, doctor readiness, critical resources, and crowd congestion. It features real-time staff updates, accessible voice assistance with a stop button, 6 Indian languages, and an honest notice system across India that prevents patient misinformation."*

---

## 12. Numbered Compliance Checklist (Sections 1–16)

| Section | Requirement Description | Compliance Status | Implementation Notes |
|---|---|---|---|
| **Section 1** | Project Concept & Transparent Guidance (Non-dispatch) | **PASS** | Informational guidance tool; does not book beds or dispatch ambulances. |
| **Section 2** | Architecture & Clean Folder Structure | **PASS** | `frontend/`, `backend/`, `database/`, `docs/`, `.env` cleanly partitioned. |
| **Section 3** | Mandatory Disclaimers on all 4 key areas | **PASS** | Present on Patient Home, Hospital Details Modal, SOS Screen, and Staff Dashboard. |
| **Section 4** | Real Hospital Dataset (Tamil Nadu & Karnataka) | **PASS** | 16 real facilities (10 TN, 6 KA); honest notice on unpopulated states. |
| **Section 5** | Beginner Developer Extensibility (SQL Guides) | **PASS** | Appended step-by-step SQL guides to `schema.sql` and `sample_data.sql`. |
| **Section 6** | 5-Factor Weighted Recommendation Engine | **PASS** | Beds (30%), Dist (20%), Docs (20%), Res (15%), Crowd (15%) + Explainer. |
| **Section 7** | Voice Assistant, Stop Button & Language Sync | **PASS** | Web Speech API, Stop button, dynamic sync with active language. |
| **Section 8** | 6 Indian Languages (en, ta, te, kn, hi, ml) | **PASS** | All 6 json files with 100% key parity (138 keys each). |
| **Section 9** | All-India Scope, Geolocation & Honest Notices | **PASS** | Two-step State→City selector, GPS calculation, non-fabrication notices. |
| **Section 10** | Patient Dashboard UX & Modal Breakdown | **PASS** | Responsive card grids, resource badges, full details modal, SOS modal. |
| **Section 11** | Staff Dashboard & 5 Key Default Metrics | **PASS** | Total, Occupied, Available, Admissions, Discharges + Capacity validation. |
| **Section 12** | Database Layer & Zero-Config Mock Fallback | **PASS** | Works without MySQL setup via robust in-memory mock repository. |
| **Section 13** | REST API Layer & Uniform Envelopes | **PASS** | 15 endpoints with consistent success/error structures and disclaimers. |
| **Section 14** | Live Sync Between Staff Updates and Patient Portal | **PASS** | PUT `/api/staff/<id>/beds` instantly reflected on `/api/hospitals/<id>`. |
| **Section 15** | Automated Testing & Live Verification | **PASS** | 50 unit tests pass (100%), live E2E runner passes all 10 stages. |
| **Section 16** | Documentation Integrity & Setup Manual | **PASS** | `README.md` and `API_DOCUMENTATION.md` fully comprehensive. |
