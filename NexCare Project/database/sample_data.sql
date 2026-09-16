-- ====================================================================
-- NexCare Sample Data (MySQL)
-- Realistic Simulated Demo Dataset for Tamil Nadu (Chennai) and Karnataka (Bengaluru)
-- ====================================================================
-- MANDATORY DISCLAIMER:
-- Hospital names and locations are real publicly known facilities.
-- Availability information shown here is simulated demo data and must be
-- verified directly with the hospital.
-- Never use this data for real-life medical decisions.
-- ====================================================================

USE nexcare;

-- 1. Insert Real Hospitals with state, coordinates, and contact details
INSERT INTO hospitals (id, name, state, locality, address, approx_lat, approx_lng, type, contact_number) VALUES
-- Tamil Nadu (Chennai) Facilities (IDs 1-10)
(1, 'Apollo Main Hospitals', 'Tamil Nadu', 'Greams Road', '21, Greams Lane, Thousand Lights, Greams Road, Chennai - 600006', 13.0560000, 80.2520000, 'Private', '+91 44 2829 0200'),
(2, 'Rajiv Gandhi Government General Hospital', 'Tamil Nadu', 'Park Town', 'EVR Periyar Salai, Park Town, Chennai - 600003', 13.0825000, 80.2760000, 'Government', '+91 44 2530 5000'),
(3, 'Government Multi Super Speciality Hospital', 'Tamil Nadu', 'Omandurar', 'Omandurar Government Estate, Anna Salai, Chennai - 600002', 13.0694000, 80.2718000, 'Government', '+91 44 2566 6000'),
(4, 'Government Kilpauk Medical College Hospital', 'Tamil Nadu', 'Kilpauk', '822, Poonamallee High Road, Near Kilpauk, Chennai - 600010', 13.0805000, 80.2428000, 'Government', '+91 44 2836 4951'),
(5, 'Fortis Malar Hospital', 'Tamil Nadu', 'Adyar', '52, 1st Main Road, Gandhi Nagar, Adyar, Chennai - 600020', 13.0067000, 80.2570000, 'Private', '+91 44 4289 2222'),
(6, 'MIOT International', 'Tamil Nadu', 'Manapakkam', '4/112, Mount Poonamallee Road, Manapakkam, Chennai - 600089', 13.0232000, 80.1786000, 'Private', '+91 44 4200 2288'),
(7, 'Sri Ramachandra Medical Centre', 'Tamil Nadu', 'Porur', 'No. 1, Ramachandra Nagar, Porur, Chennai - 600116', 13.0382000, 80.1432000, 'Private', '+91 44 4592 8500'),
(8, 'Madras Medical Mission Hospital', 'Tamil Nadu', 'Mogappair', '4A, Dr. J. J. Nagar, Mogappair, Chennai - 600037', 13.0850000, 80.1764000, 'Private', '+91 44 2656 8000'),
(9, 'Dr. Mehta''s Hospitals', 'Tamil Nadu', 'Chetpet', 'No. 2, McNichols Road, 3rd Lane, Chetpet, Chennai - 600031', 13.0722000, 80.2372000, 'Private', '+91 44 4227 1001'),
(10, 'Kauvery Hospital', 'Tamil Nadu', 'Vadapalani', 'No. 12, Arcot Road, Vadapalani, Chennai - 600026', 13.0514000, 80.2104000, 'Private', '+91 44 4000 6000'),

-- Karnataka (Bengaluru) Facilities (IDs 11-16)
(11, 'Manipal Hospital Old Airport Road', 'Karnataka', 'Old Airport Road', '98, HAL Old Airport Rd, Kodihalli, Bengaluru, Karnataka - 560017', 12.9587000, 77.6483000, 'Private', '+91 80 2502 4444'),
(12, 'Victoria Hospital (Bangalore Medical College)', 'Karnataka', 'Kalasipalya', 'Fort Road, Near City Market, Kalasipalya, Bengaluru, Karnataka - 560002', 12.9628000, 77.5752000, 'Government', '+91 80 2670 1150'),
(13, 'Narayana Institute of Cardiac Sciences (Health City)', 'Karnataka', 'Bommasandra', '258/A, Bommasandra Industrial Area, Anekal Taluk, Bengaluru, Karnataka - 560099', 12.8173000, 77.6917000, 'Private', '+91 80 7122 2222'),
(14, 'Bowring and Lady Curzon Hospital', 'Karnataka', 'Shivaji Nagar', 'Lady Curzon Road, Tasker Town, Shivaji Nagar, Bengaluru, Karnataka - 560001', 12.9822000, 77.6047000, 'Government', '+91 80 2559 1362'),
(15, 'Fortis Hospital Bannerghatta Road', 'Karnataka', 'Bannerghatta Road', '154/9, Bannerghatta Road, Opposite IIM-B, Bengaluru, Karnataka - 560076', 12.8943000, 77.5985000, 'Private', '+91 80 6621 4444'),
(16, 'St. John''s Medical College Hospital', 'Karnataka', 'Koramangala', 'Sarjapur Road, John Nagar, Koramangala, Bengaluru, Karnataka - 560034', 12.9317000, 77.6186000, 'Private', '+91 80 2206 5000');

-- 2. Insert Simulated Bed Statistics (with Today''s Admissions & Discharges)
INSERT INTO hospital_beds (hospital_id, total_beds, occupied_beds, today_admissions, today_discharges) VALUES
(1, 500, 430, 24, 18),   -- Apollo (70 available)
(2, 1800, 1710, 85, 62), -- RGGGH (90 available)
(3, 400, 300, 18, 15),   -- Omandurar (100 available)
(4, 530, 490, 30, 22),   -- Kilpauk (40 available)
(5, 180, 112, 12, 8),    -- Fortis Malar (68 available)
(6, 1000, 760, 42, 35),  -- MIOT (240 available)
(7, 1200, 690, 50, 40),  -- SRMC Porur (510 available)
(8, 300, 210, 15, 11),   -- MMM (90 available)
(9, 150, 82, 9, 7),      -- Dr. Mehta's (68 available)
(10, 250, 205, 14, 10),  -- Kauvery (45 available)
(11, 600, 490, 28, 20),  -- Manipal Bengaluru (110 available)
(12, 1000, 920, 52, 41), -- Victoria Hospital BMCRI (80 available)
(13, 500, 380, 22, 17),  -- Narayana Health City (120 available)
(14, 686, 610, 34, 25),  -- Bowring & Lady Curzon (76 available)
(15, 276, 210, 14, 11),  -- Fortis Bannerghatta (66 available)
(16, 1350, 1180, 60, 48);-- St. John's Medical College (170 available)

-- 3. Insert Doctor/Department Availability (with Specialty)
INSERT INTO doctors (hospital_id, name_or_department, specialty, status, available_time, consultation_capacity) VALUES
-- Chennai Doctors
(1, 'General Medicine & Emergency', 'Internal Medicine & Critical Care', 'Available', '24x7 / On-Duty', 45),
(1, 'Cardiology & Critical Care', 'Cardiology & Interventional Care', 'Available', '09:00 - 18:00', 30),
(2, 'Emergency Medicine (Triage)', 'Emergency Medicine & Trauma', 'Limited', '24x7 / On-Duty', 100),
(2, 'General Medicine OPD', 'General Medicine', 'Limited', '08:00 - 14:00', 120),
(3, 'Multi-Speciality Critical Care', 'Intensive & Critical Care', 'Available', '24x7 / On-Duty', 40),
(3, 'Cardiothoracic OPD', 'Cardiothoracic Surgery', 'Available', '09:00 - 16:00', 35),
(4, 'Burns & Plastic Surgery / Trauma', 'Plastic & Reconstructive Surgery', 'Limited', '24x7 / On-Duty', 50),
(4, 'General Medicine', 'General Medicine', 'Limited', '08:00 - 14:00', 60),
(5, 'Emergency Department', 'Emergency & Trauma Care', 'Available', '24x7 / On-Duty', 30),
(5, 'Cardiology & Internal Medicine', 'Cardiology', 'Available', '09:00 - 17:00', 25),
(6, 'Orthopaedics & Trauma Care', 'Orthopedics & Joint Replacement', 'Available', '24x7 / On-Duty', 60),
(6, 'Internal Medicine & Pulmonology', 'Pulmonology & Respiratory Medicine', 'Available', '09:00 - 18:00', 40),
(7, 'Emergency Medical Services', 'Emergency Medicine', 'Available', '24x7 / On-Duty', 75),
(7, 'General & Super Speciality OPD', 'General & Internal Medicine', 'Available', '08:30 - 17:30', 90),
(8, 'Cardiac Sciences & Emergency', 'Cardiology & Electrophysiology', 'Limited', '24x7 / On-Duty', 35),
(8, 'General Medicine', 'General Medicine', 'Available', '09:00 - 16:00', 30),
(9, 'Pediatrics & Internal Medicine', 'Pediatrics & Child Health', 'Available', '24x7 / On-Duty', 30),
(9, 'General OPD Clinic', 'Family & General Practice', 'Available', '09:00 - 17:00', 25),
(10, 'Accident & Emergency Care', 'Emergency Medicine', 'Unavailable', '24x7 / On-Duty', 20),
(10, 'Speciality Consultations', 'Super Speciality Medicine', 'Limited', '10:00 - 16:00', 25),

-- Bengaluru Doctors (Karnataka)
(11, 'Dr. S. K. Murthy (Critical Care)', 'Critical Care & Pulmonology', 'Available', '24x7 / On-Duty', 40),
(11, 'Dr. Ananya Hegde (Cardiology OPD)', 'Cardiology', 'Available', '09:00 - 17:30', 30),
(12, 'Emergency Triage & Trauma Unit', 'Emergency Medicine', 'Available', '24x7 / On-Duty', 80),
(12, 'Department of General Surgery', 'General & Laparoscopic Surgery', 'Available', '09:00 - 16:00', 60),
(13, 'Cardiac Emergency & Cath Lab', 'Cardiology & Cardiac Surgery', 'Available', '24x7 / On-Duty', 50),
(13, 'Cardiovascular OPD', 'Interventional Cardiology', 'Available', '09:00 - 18:00', 45),
(14, 'General Medicine OPD & Triage', 'General Medicine', 'Limited', '24x7 / On-Duty', 70),
(14, 'Pediatrics & Neonatal Care', 'Pediatrics', 'Available', '09:00 - 16:00', 40),
(15, 'Emergency & Acute Care', 'Emergency & Trauma Care', 'Available', '24x7 / On-Duty', 35),
(15, 'Orthopedics & Spine Institute', 'Orthopedics', 'Available', '09:30 - 17:00', 25),
(16, 'Department of Emergency Medicine', 'Emergency Medicine & Triage', 'Available', '24x7 / On-Duty', 65),
(16, 'Internal Medicine & Nephrology', 'Nephrology & Internal Medicine', 'Available', '08:30 - 17:00', 50);

-- 4. Insert Hospital General Resources (8 key resources per hospital)
INSERT INTO hospital_resources (hospital_id, resource_type, status) VALUES
-- Hospital 1: Apollo
(1, 'ICU beds', 'Limited'), (1, 'Oxygen', 'Available'), (1, 'Pharmacy', 'Available'), (1, 'Lab', 'Available'),
(1, 'X-ray', 'Available'), (1, 'CT scan', 'Available'), (1, 'Blood bank', 'Available'), (1, 'ED', 'Available'),

-- Hospital 2: RGGGH
(2, 'ICU beds', 'Limited'), (2, 'Oxygen', 'Available'), (2, 'Pharmacy', 'Limited'), (2, 'Lab', 'Available'),
(2, 'X-ray', 'Available'), (2, 'CT scan', 'Limited'), (2, 'Blood bank', 'Available'), (2, 'ED', 'Available'),

-- Hospital 3: Omandurar
(3, 'ICU beds', 'Available'), (3, 'Oxygen', 'Available'), (3, 'Pharmacy', 'Available'), (3, 'Lab', 'Available'),
(3, 'X-ray', 'Available'), (3, 'CT scan', 'Available'), (3, 'Blood bank', 'Available'), (3, 'ED', 'Available'),

-- Hospital 4: Kilpauk
(4, 'ICU beds', 'Limited'), (4, 'Oxygen', 'Available'), (4, 'Pharmacy', 'Available'), (4, 'Lab', 'Available'),
(4, 'X-ray', 'Available'), (4, 'CT scan', 'Limited'), (4, 'Blood bank', 'Limited'), (4, 'ED', 'Available'),

-- Hospital 5: Fortis Malar
(5, 'ICU beds', 'Available'), (5, 'Oxygen', 'Available'), (5, 'Pharmacy', 'Available'), (5, 'Lab', 'Available'),
(5, 'X-ray', 'Available'), (5, 'CT scan', 'Available'), (5, 'Blood bank', 'Available'), (5, 'ED', 'Available'),

-- Hospital 6: MIOT
(6, 'ICU beds', 'Limited'), (6, 'Oxygen', 'Available'), (6, 'Pharmacy', 'Available'), (6, 'Lab', 'Available'),
(6, 'X-ray', 'Available'), (6, 'CT scan', 'Available'), (6, 'Blood bank', 'Available'), (6, 'ED', 'Available'),

-- Hospital 7: SRMC Porur
(7, 'ICU beds', 'Available'), (7, 'Oxygen', 'Available'), (7, 'Pharmacy', 'Available'), (7, 'Lab', 'Available'),
(7, 'X-ray', 'Available'), (7, 'CT scan', 'Available'), (7, 'Blood bank', 'Available'), (7, 'ED', 'Available'),

-- Hospital 8: MMM
(8, 'ICU beds', 'Limited'), (8, 'Oxygen', 'Available'), (8, 'Pharmacy', 'Available'), (8, 'Lab', 'Available'),
(8, 'X-ray', 'Available'), (8, 'CT scan', 'Available'), (8, 'Blood bank', 'Limited'), (8, 'ED', 'Available'),

-- Hospital 9: Dr. Mehta's
(9, 'ICU beds', 'Available'), (9, 'Oxygen', 'Available'), (9, 'Pharmacy', 'Available'), (9, 'Lab', 'Available'),
(9, 'X-ray', 'Available'), (9, 'CT scan', 'Limited'), (9, 'Blood bank', 'Available'), (9, 'ED', 'Available'),

-- Hospital 10: Kauvery
(10, 'ICU beds', 'Limited'), (10, 'Oxygen', 'Available'), (10, 'Pharmacy', 'Available'), (10, 'Lab', 'Available'),
(10, 'X-ray', 'Available'), (10, 'CT scan', 'Limited'), (10, 'Blood bank', 'Limited'), (10, 'ED', 'Limited'),

-- Hospital 11: Manipal Bengaluru
(11, 'ICU beds', 'Available'), (11, 'Oxygen', 'Available'), (11, 'Pharmacy', 'Available'), (11, 'Lab', 'Available'),
(11, 'X-ray', 'Available'), (11, 'CT scan', 'Available'), (11, 'Blood bank', 'Available'), (11, 'ED', 'Available'),

-- Hospital 12: Victoria BMCRI
(12, 'ICU beds', 'Limited'), (12, 'Oxygen', 'Available'), (12, 'Pharmacy', 'Available'), (12, 'Lab', 'Available'),
(12, 'X-ray', 'Available'), (12, 'CT scan', 'Available'), (12, 'Blood bank', 'Available'), (12, 'ED', 'Available'),

-- Hospital 13: Narayana Health City
(13, 'ICU beds', 'Available'), (13, 'Oxygen', 'Available'), (13, 'Pharmacy', 'Available'), (13, 'Lab', 'Available'),
(13, 'X-ray', 'Available'), (13, 'CT scan', 'Available'), (13, 'Blood bank', 'Available'), (13, 'ED', 'Available'),

-- Hospital 14: Bowring Hospital
(14, 'ICU beds', 'Limited'), (14, 'Oxygen', 'Available'), (14, 'Pharmacy', 'Limited'), (14, 'Lab', 'Available'),
(14, 'X-ray', 'Available'), (14, 'CT scan', 'Limited'), (14, 'Blood bank', 'Available'), (14, 'ED', 'Available'),

-- Hospital 15: Fortis Bannerghatta
(15, 'ICU beds', 'Available'), (15, 'Oxygen', 'Available'), (15, 'Pharmacy', 'Available'), (15, 'Lab', 'Available'),
(15, 'X-ray', 'Available'), (15, 'CT scan', 'Available'), (15, 'Blood bank', 'Available'), (15, 'ED', 'Available'),

-- Hospital 16: St. John's Medical College
(16, 'ICU beds', 'Available'), (16, 'Oxygen', 'Available'), (16, 'Pharmacy', 'Available'), (16, 'Lab', 'Available'),
(16, 'X-ray', 'Available'), (16, 'CT scan', 'Available'), (16, 'Blood bank', 'Available'), (16, 'ED', 'Available');

-- 5. Insert Crowd Status & Waiting Metrics (with Today''s Admissions & Discharges)
INSERT INTO crowd_updates (hospital_id, current_patients, waiting_patients, today_admissions, today_discharges, crowd_status) VALUES
(1, 190, 24, 24, 18, 'Moderate'),
(2, 760, 130, 85, 62, 'High'),
(3, 150, 18, 18, 15, 'Moderate'),
(4, 240, 45, 30, 22, 'High'),
(5, 32, 6, 12, 8, 'Low'),
(6, 120, 22, 42, 35, 'Moderate'),
(7, 28, 9, 50, 40, 'Low'),
(8, 65, 14, 15, 11, 'Moderate'),
(9, 25, 5, 9, 7, 'Low'),
(10, 145, 34, 14, 10, 'High'),
(11, 45, 8, 28, 20, 'Moderate'),
(12, 210, 38, 52, 41, 'High'),
(13, 35, 6, 22, 17, 'Low'),
(14, 160, 28, 34, 25, 'High'),
(15, 26, 5, 14, 11, 'Low'),
(16, 180, 25, 60, 48, 'High');

-- 6. Insert Staff Users (Demo Credentials)
-- All demo passwords default to 'demo123'
INSERT INTO staff_users (hospital_id, staff_id, hashed_password, name) VALUES
(1, 'staff_apollo', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Dr. S. K. Apollo Admin'),
(2, 'staff_rggh', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Dr. V. Ramanathan (RGGGH)'),
(3, 'staff_omandurar', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Dr. K. Meenakshi (Omandurar)'),
(4, 'staff_kilpauk', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Dr. A. Joseph (KMCH)'),
(5, 'staff_fortis', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Nurse Supervisor Deepa (Fortis)'),
(5, 'demo-staff', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Default Demo Staff (Fortis)'),
(6, 'staff_miot', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Duty Manager Karthik (MIOT)'),
(7, 'staff_srmc', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Chief Administrator Priya (SRMC)'),
(8, 'staff_mmm', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Dr. Thomas Kurian (MMM)'),
(9, 'staff_mehta', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Operations Head Anand (Mehta)'),
(10, 'staff_kauvery', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Nurse In-Charge Geetha (Kauvery)'),
(11, 'staff_manipal', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Dr. Ramesh Rao (Manipal Bengaluru)'),
(13, 'staff_narayana', '5fa72351376ced08e8e160d3141eb7d0f00f3543f29abfe82e1b0251b9f7b2e9', 'Admin Deepa Hegde (Narayana Health)');

-- 7. Insert Sample Audit History
INSERT INTO update_history (hospital_id, staff_id, field_changed, old_value, new_value, changed_at) VALUES
(5, 'staff_fortis', 'beds', '{"total_beds": 180, "occupied_beds": 115}', '{"total_beds": 180, "occupied_beds": 112, "admissions": 12, "discharges": 8}', NOW() - INTERVAL 20 MINUTE),
(5, 'staff_fortis', 'crowd', '{"current_patients": 35, "waiting_patients": 9}', '{"current_patients": 32, "waiting_patients": 6, "today_admissions": 12, "today_discharges": 8}', NOW() - INTERVAL 15 MINUTE),
(1, 'staff_apollo', 'beds', '{"total_beds": 500, "occupied_beds": 435}', '{"total_beds": 500, "occupied_beds": 430, "admissions": 24, "discharges": 18}', NOW() - INTERVAL 45 MINUTE),
(11, 'staff_manipal', 'beds', '{"total_beds": 600, "occupied_beds": 495}', '{"total_beds": 600, "occupied_beds": 490, "admissions": 28, "discharges": 20}', NOW() - INTERVAL 10 MINUTE);

-- 8. Insert Simulated Ambulances (Available by Default)
INSERT INTO ambulances (hospital_id, ambulance_code, status, driver_name, contact_number) VALUES
(1, 'AMB-TN-01', 'Available', 'Rajesh Kumar', '+91 98401 10001'),
(1, 'AMB-TN-02', 'Available', 'M. Saravanan', '+91 98401 10002'),
(2, 'AMB-TN-03', 'Available', 'Senthil Nathan', '+91 98401 10003'),
(3, 'AMB-TN-04', 'Available', 'P. Anand', '+91 98401 10004'),
(4, 'AMB-TN-05', 'Available', 'K. Vignesh', '+91 98401 10005'),
(5, 'AMB-TN-06', 'Available', 'Deepak Selvam', '+91 98401 10006'),
(5, 'AMB-TN-07', 'Available', 'R. Manikandan', '+91 98401 10007'),
(6, 'AMB-TN-08', 'Available', 'S. Muthu', '+91 98401 10008'),
(7, 'AMB-TN-09', 'Available', 'A. Karthik', '+91 98401 10009'),
(8, 'AMB-TN-10', 'Available', 'N. Balaji', '+91 98401 10010'),
(9, 'AMB-TN-11', 'Available', 'C. Prakash', '+91 98401 10011'),
(10, 'AMB-TN-12', 'Available', 'G. Ramesh', '+91 98401 10012'),
(11, 'AMB-KA-01', 'Available', 'Sunil Gowda', '+91 98402 10001'),
(11, 'AMB-KA-02', 'Available', 'Manjunath B.', '+91 98402 10002'),
(12, 'AMB-KA-03', 'Available', 'C. Venkatesh', '+91 98402 10003'),
(13, 'AMB-KA-04', 'Available', 'Suresh Hegde', '+91 98402 10004'),
(14, 'AMB-KA-05', 'Available', 'Prashanth Nayak', '+91 98402 10005'),
(15, 'AMB-KA-06', 'Available', 'Anand Kulkarni', '+91 98402 10006'),
(16, 'AMB-KA-07', 'Available', 'Vijay Kumar', '+91 98402 10007');

-- ====================================================================
-- EXTENSION PATTERN: ADDING MORE INDIAN STATES (BEGINNER GUIDE)
-- ====================================================================
-- Adding new states requires zero code changes! Just insert rows with the new `state` name:
--
-- Example for adding a Delhi or Kerala hospital:
--   INSERT INTO hospitals (id, name, state, locality, address, approx_lat, approx_lng, type, contact_number)
--   VALUES (17, 'All India Institute of Medical Sciences (AIIMS)', 'Delhi (NCT)', 'Ansari Nagar', 'Sri Aurobindo Marg, Ansari Nagar East, New Delhi - 110029', 28.5672, 77.2100, 'Government', '+91 11 2658 8500');
--
-- Next insert its associated beds, doctors, 8 resources, and crowd metrics as shown above.
-- The API and UI will immediately include the new hospital and its state!
-- ====================================================================
