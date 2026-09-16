-- ====================================================================
-- NexCare Database Schema (MySQL)
-- Healthcare Support Application - Chennai Hospital Availability System
-- ====================================================================
-- DISCLAIMER: Hospital names and locations are real. Availability 
-- information shown here is simulated demo data and must be verified
-- directly with the hospital.
-- ====================================================================

CREATE DATABASE IF NOT EXISTS nexcare
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE nexcare;

-- Disable foreign key checks during schema creation
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS emergency_requests;
DROP TABLE IF EXISTS ambulances;
DROP TABLE IF EXISTS update_history;
DROP TABLE IF EXISTS crowd_updates;
DROP TABLE IF EXISTS hospital_resources;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS hospital_beds;
DROP TABLE IF EXISTS staff_users;
DROP TABLE IF EXISTS hospitals;

SET FOREIGN_KEY_CHECKS = 1;

-- 1. Hospitals Table
CREATE TABLE hospitals (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(180) NOT NULL,
  state VARCHAR(80) NOT NULL DEFAULT 'Tamil Nadu',
  locality VARCHAR(80) NOT NULL,
  address VARCHAR(255) NOT NULL,
  approx_lat DECIMAL(10, 7) NOT NULL,
  approx_lng DECIMAL(10, 7) NOT NULL,
  type ENUM('Government', 'Private') NOT NULL DEFAULT 'Private',
  contact_number VARCHAR(30) NOT NULL DEFAULT '+91 44 4000 0000',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_state (state),
  INDEX idx_locality (locality),
  INDEX idx_type (type)
) ENGINE=InnoDB;

-- 2. Staff Users Table (Demo Authentication)
-- NOTE: Demo credentials only — not production-grade authentication.
CREATE TABLE staff_users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  hospital_id INT NOT NULL,
  staff_id VARCHAR(80) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  name VARCHAR(120) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
  INDEX idx_staff_id (staff_id)
) ENGINE=InnoDB;

-- 3. Hospital Beds Table
CREATE TABLE hospital_beds (
  id INT PRIMARY KEY AUTO_INCREMENT,
  hospital_id INT NOT NULL,
  total_beds INT NOT NULL DEFAULT 100,
  occupied_beds INT NOT NULL DEFAULT 0,
  blocked_beds INT NOT NULL DEFAULT 0,
  today_admissions INT NOT NULL DEFAULT 0,
  today_discharges INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
  INDEX idx_hospital_beds (hospital_id)
) ENGINE=InnoDB;

-- 4. Doctors & Departments Table
CREATE TABLE doctors (
  id INT PRIMARY KEY AUTO_INCREMENT,
  hospital_id INT NOT NULL,
  name_or_department VARCHAR(160) NOT NULL,
  specialty VARCHAR(100) NOT NULL DEFAULT 'General Medicine',
  status ENUM('Available', 'Limited', 'Unavailable') NOT NULL DEFAULT 'Available',
  available_time VARCHAR(80) DEFAULT '09:00 - 17:00',
  consultation_capacity INT DEFAULT 30,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
  INDEX idx_hospital_doctors (hospital_id)
) ENGINE=InnoDB;

-- 5. Hospital General Resources Table
CREATE TABLE hospital_resources (
  id INT PRIMARY KEY AUTO_INCREMENT,
  hospital_id INT NOT NULL,
  resource_type VARCHAR(80) NOT NULL,
  status ENUM('Available', 'Limited', 'Unavailable') NOT NULL DEFAULT 'Available',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
  INDEX idx_hospital_resources (hospital_id, resource_type)
) ENGINE=InnoDB;

-- 6. Crowd Status & Waiting Metrics Table
CREATE TABLE crowd_updates (
  id INT PRIMARY KEY AUTO_INCREMENT,
  hospital_id INT NOT NULL,
  current_patients INT NOT NULL DEFAULT 0,
  waiting_patients INT NOT NULL DEFAULT 0,
  today_admissions INT NOT NULL DEFAULT 0,
  today_discharges INT NOT NULL DEFAULT 0,
  crowd_status ENUM('Low', 'Moderate', 'High') NOT NULL DEFAULT 'Low',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
  INDEX idx_hospital_crowd (hospital_id)
) ENGINE=InnoDB;

-- 7. Audit History Table
CREATE TABLE update_history (
  id INT PRIMARY KEY AUTO_INCREMENT,
  hospital_id INT NOT NULL,
  staff_id VARCHAR(80) NOT NULL,
  field_changed VARCHAR(120) NOT NULL,
  old_value JSON DEFAULT NULL,
  new_value JSON DEFAULT NULL,
  changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
  INDEX idx_history_hospital (hospital_id),
  INDEX idx_history_time (changed_at DESC)
) ENGINE=InnoDB;

-- 8. Simulated Ambulances Table
CREATE TABLE ambulances (
  id INT PRIMARY KEY AUTO_INCREMENT,
  ambulance_code VARCHAR(40) UNIQUE NOT NULL,
  hospital_id INT NOT NULL,
  status ENUM('Available', 'Assigned', 'Maintenance') NOT NULL DEFAULT 'Available',
  driver_name VARCHAR(120) NOT NULL DEFAULT 'Simulated Driver',
  contact_number VARCHAR(30) NOT NULL DEFAULT '+91 98000 00000',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
  INDEX idx_ambulance_hospital (hospital_id),
  INDEX idx_ambulance_status (status)
) ENGINE=InnoDB;

-- 9. Simulated SOS Emergency Requests Table
CREATE TABLE emergency_requests (
  id INT PRIMARY KEY AUTO_INCREMENT,
  request_code VARCHAR(50) UNIQUE NOT NULL,
  hospital_id INT NOT NULL,
  ambulance_id INT DEFAULT NULL,
  ambulance_code VARCHAR(40) DEFAULT NULL,
  patient_locality VARCHAR(120) DEFAULT NULL,
  patient_lat DECIMAL(10, 7) DEFAULT NULL,
  patient_lng DECIMAL(10, 7) DEFAULT NULL,
  status ENUM('Pending', 'Ambulance Assigned', 'En Route', 'Arrived', 'Patient Admitted', 'Cancelled') NOT NULL DEFAULT 'Ambulance Assigned',
  bed_blocked BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
  FOREIGN KEY (ambulance_id) REFERENCES ambulances(id) ON DELETE SET NULL,
  INDEX idx_request_code (request_code),
  INDEX idx_request_hospital (hospital_id),
  INDEX idx_request_status (status)
) ENGINE=InnoDB;

-- ====================================================================
-- BEGINNER DEVELOPER GUIDE: HOW TO ADD MORE STATES & HOSPITALS
-- ====================================================================
-- To expand NexCare coverage to a new Indian state (e.g. Maharashtra, Kerala):
--
-- STEP 1: Insert the hospital record into the `hospitals` table:
--   INSERT INTO hospitals (id, name, state, locality, address, approx_lat, approx_lng, type, contact_number)
--   VALUES (17, 'Lilavati Hospital & Research Centre', 'Maharashtra', 'Bandra West', 'A-791, Bandra Reclamation, Mumbai - 400050', 19.0514, 72.8295, 'Private', '+91 22 2675 1000');
--
-- STEP 2: Insert initial bed metrics into `hospital_beds`:
--   INSERT INTO hospital_beds (hospital_id, total_beds, occupied_beds, today_admissions, today_discharges)
--   VALUES (17, 323, 210, 15, 12);
--
-- STEP 3: Insert doctor entries into `doctors`:
--   INSERT INTO doctors (hospital_id, name_or_department, specialty, status, available_time, consultation_capacity)
--   VALUES (17, 'Cardiac Sciences Unit', 'Cardiology', 'Available', '24x7 / On-Duty', 40);
--
-- STEP 4: Insert the 8 standard resources into `hospital_resources`:
--   INSERT INTO hospital_resources (hospital_id, resource_type, status) VALUES
--   (17, 'ICU beds', 'Available'), (17, 'Oxygen', 'Available'), (17, 'Pharmacy', 'Available'),
--   (17, 'Lab', 'Available'), (17, 'X-ray', 'Available'), (17, 'CT scan', 'Available'),
--   (17, 'Blood bank', 'Available'), (17, 'ED', 'Available');
--
-- STEP 5: Insert crowd tracking figures into `crowd_updates`:
--   INSERT INTO crowd_updates (hospital_id, current_patients, waiting_patients, today_admissions, today_discharges, crowd_status)
--   VALUES (17, 28, 7, 15, 12, 'Low');
--
-- Once inserted, NexCare automatically detects the new state, lists it in state dropdowns,
-- and routes queries to the newly added hospital rows!
-- ====================================================================
