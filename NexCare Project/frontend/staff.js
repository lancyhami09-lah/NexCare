/**
 * NexCare Hospital Staff Portal Logic
 * Demo authentication, live availability editing, auto-calculations, and audit log
 */

let staffSession = null;
let currentHospitalData = null;

document.addEventListener('DOMContentLoaded', () => {
  // Check existing session
  const savedSession = localStorage.getItem('nexcare_staff_session');
  if (savedSession) {
    try {
      staffSession = JSON.parse(savedSession);
    } catch (e) {
      staffSession = null;
    }
  }

  setupAuth();
  setupForms();
  setupStaffEmergencyAlertListeners();

  if (staffSession && staffSession.token && staffSession.hospital_id) {
    showDashboardView();
  } else {
    showLoginView();
  }
});

// 1. Authentication Handlers
function setupAuth() {
  const loginForm = document.getElementById('staff-login-form');
  const logoutBtn = document.getElementById('btn-staff-logout');
  const errorBox = document.getElementById('login-error-msg');

  // Quick-fill demo account chips
  document.querySelectorAll('.demo-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const user = chip.getAttribute('data-user');
      document.getElementById('input-staff-id').value = user;
      document.getElementById('input-staff-password').value = 'demo123';
      errorBox.style.display = 'none';
    });
  });

  // Handle Login Submit
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.style.display = 'none';
    const staffId = document.getElementById('input-staff-id').value.trim();
    const password = document.getElementById('input-staff-password').value.trim();

    if (!staffId || !password) {
      errorBox.textContent = 'Please provide both Staff ID and password.';
      errorBox.style.display = 'block';
      return;
    }

    const res = await fetchAPI('/staff/login', {
      method: 'POST',
      body: JSON.stringify({ staff_id: staffId, password: password })
    });

    if (res.ok && res.data.success && res.data.data) {
      staffSession = res.data.data;
      localStorage.setItem('nexcare_staff_session', JSON.stringify(staffSession));
      showDashboardView();
    } else {
      errorBox.textContent = res.data.error || 'Login failed. Please check demo credentials.';
      errorBox.style.display = 'block';
    }
  });

  // Handle Logout
  logoutBtn.addEventListener('click', () => {
    staffSession = null;
    currentHospitalData = null;
    localStorage.removeItem('nexcare_staff_session');
    showLoginView();
  });
}

let staffEmergencyPollingTimer = null;

function showLoginView() {
  if (staffEmergencyPollingTimer) {
    clearInterval(staffEmergencyPollingTimer);
    staffEmergencyPollingTimer = null;
  }
  document.getElementById('staff-login-section').style.display = 'block';
  document.getElementById('staff-dashboard-section').style.display = 'none';
  document.getElementById('btn-staff-logout').style.display = 'none';
  const navAlert = document.getElementById('nav-staff-emergency-indicator');
  if (navAlert) navAlert.style.display = 'none';
}

function showDashboardView() {
  document.getElementById('staff-login-section').style.display = 'none';
  document.getElementById('staff-dashboard-section').style.display = 'block';
  document.getElementById('btn-staff-logout').style.display = 'inline-flex';
  
  // Surface active emergency requests immediately upon login without waiting for full dashboard render
  loadEmergencyRequests();
  loadDashboardData();

  if (staffEmergencyPollingTimer) clearInterval(staffEmergencyPollingTimer);
  staffEmergencyPollingTimer = setInterval(() => {
    if (staffSession) {
      loadEmergencyRequests();
    }
  }, 5000);
}

// 2. Load Live Dashboard Data
async function loadDashboardData() {
  if (!staffSession) return;

  const res = await fetchAPI(`/staff/${staffSession.hospital_id}/dashboard`, {
    headers: { 'Authorization': `Bearer ${staffSession.token}` }
  });

  if (!res.ok || !res.data.success) {
    if (res.status === 401) {
      alert('Your staff session has expired. Please sign in again.');
      document.getElementById('btn-staff-logout').click();
      return;
    }
    alert(res.data.error || 'Failed to load hospital data.');
    return;
  }

  const payload = res.data.data;
  currentHospitalData = payload.hospital;
  const warnings = payload.warnings || [];

  try { renderDashboardHeader(currentHospitalData); } catch (e) { console.error('Dashboard header error:', e); }
  try { renderWarnings(warnings); } catch (e) { console.error('Warnings error:', e); }
  try { renderKPIs(currentHospitalData); } catch (e) { console.error('KPIs error:', e); }
  try { populateBedsForm(currentHospitalData); } catch (e) { console.error('Beds form error:', e); }
  try { populateDoctorsForm(currentHospitalData); } catch (e) { console.error('Doctors form error:', e); }
  try { populateResourcesForm(currentHospitalData); } catch (e) { console.error('Resources form error:', e); }
  try { loadEmergencyRequests(); } catch (e) { console.error('Emergency requests error:', e); }
  try { loadAuditHistory(); } catch (e) { console.error('Audit history error:', e); }
}

// Helper to render colored status badge with icon
function getStatusBadge(status) {
  const s = (status || 'Available').toLowerCase();
  if (s === 'available') return '<span class="badge badge-green">🟢 Available</span>';
  if (s === 'limited' || s === 'busy') return '<span class="badge badge-yellow">🟡 Limited</span>';
  return '<span class="badge badge-red">🔴 Unavailable</span>';
}

// 3. Render Header, Warnings & KPIs
function renderDashboardHeader(h) {
  document.getElementById('dash-hospital-name').textContent = h.name;
  document.getElementById('dash-hospital-address').textContent = `${h.locality} • ${h.address}`;
  document.getElementById('dash-hospital-type').textContent = `${h.type} Healthcare Facility`;
  document.getElementById('dash-staff-name').textContent = `${staffSession.name} (${staffSession.staff_id})`;
  const updatedDate = h.last_updated ? new Date(h.last_updated).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Recent';
  document.getElementById('dash-last-updated').textContent = updatedDate;
}

function renderWarnings(warnings) {
  const container = document.getElementById('staff-warning-container');
  if (warnings.length === 0) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = warnings.map(w => `
    <div class="staff-warning-box" style="${w.type === 'warning' ? 'background-color:#fef3c7; border-color:#d97706; color:#92400e;' : ''}">
      <span>⚠️ <strong>Facility Alert:</strong> ${w.message}</span>
    </div>
  `).join('');
}

function renderKPIs(h) {
  const beds = h.beds || { total: 0, occupied: 0, blocked: 0, available: 0, today_admissions: 0, today_discharges: 0 };
  const total = beds.total || 0;
  const occupied = beds.occupied || 0;
  const blocked = beds.blocked || 0;
  const available = beds.available != null ? beds.available : Math.max(0, total - occupied - blocked);
  const admissions = beds.today_admissions || 0;
  const discharges = beds.today_discharges || 0;

  // Key Summary Metrics on Login Home
  document.getElementById('stat-total-beds').textContent = total;
  document.getElementById('stat-occupied-beds').textContent = occupied;
  const statBlocked = document.getElementById('stat-blocked-beds');
  if (statBlocked) statBlocked.textContent = blocked;
  document.getElementById('stat-available-beds').textContent = available;
  document.getElementById('stat-today-admissions').textContent = admissions;
  document.getElementById('stat-today-discharges').textContent = discharges;

  const docBadge = document.getElementById('dash-doctor-overall-badge');
  if (docBadge) docBadge.innerHTML = getStatusBadge(h.doctor_status);
}

// 4. Form Populators & Real-Time Client Validation
function populateBedsForm(h) {
  const beds = h.beds || { total: 100, occupied: 50, blocked: 0, today_admissions: 0, today_discharges: 0 };
  const totalInput = document.getElementById('input-total-beds');
  const occupiedInput = document.getElementById('input-occupied-beds');
  const admissionsInput = document.getElementById('input-admissions');
  const dischargesInput = document.getElementById('input-discharges');
  const calcBlockedDisplay = document.getElementById('calc-blocked-display');

  totalInput.value = beds.total;
  occupiedInput.value = beds.occupied;
  if (calcBlockedDisplay) calcBlockedDisplay.textContent = beds.blocked || 0;
  if (admissionsInput) admissionsInput.value = beds.today_admissions || 0;
  if (dischargesInput) dischargesInput.value = beds.today_discharges || 0;
  updateBedCalculations();
}

function updateBedCalculations() {
  const total = parseInt(document.getElementById('input-total-beds').value || '0', 10);
  const occupied = parseInt(document.getElementById('input-occupied-beds').value || '0', 10);
  const blocked = currentHospitalData && currentHospitalData.beds ? (currentHospitalData.beds.blocked || 0) : 0;
  const available = Math.max(0, total - occupied - blocked);

  const display = document.getElementById('calc-available-display');
  const warning = document.getElementById('bed-calc-warning');
  const submitBtn = document.getElementById('btn-save-beds');
  const crowdBadge = document.getElementById('calc-crowd-badge');
  const calcBlockedDisplay = document.getElementById('calc-blocked-display');

  if (calcBlockedDisplay) calcBlockedDisplay.textContent = blocked;

  if (occupied + blocked > total) {
    display.textContent = 'Invalid (Over Capacity)';
    display.style.color = 'var(--status-red)';
    warning.textContent = `⚠️ Occupied (${occupied}) + Blocked (${blocked}) cannot exceed total capacity (${total})`;
    warning.style.display = 'block';
    submitBtn.disabled = true;
    if (crowdBadge) {
      crowdBadge.innerHTML = '<span class="badge badge-red">🔴 Over Capacity</span>';
    }
  } else if (total < 0 || occupied < 0) {
    display.textContent = 'Invalid (Negative)';
    display.style.color = 'var(--status-red)';
    warning.textContent = '⚠️ Bed counts cannot be negative';
    warning.style.display = 'block';
    submitBtn.disabled = true;
  } else {
    display.textContent = `${available} Beds Available`;
    display.style.color = 'var(--status-green)';
    warning.style.display = 'none';
    submitBtn.disabled = false;

    // Auto-calculate crowd status based on bed occupancy %
    const occPct = total > 0 ? (occupied / total) * 100.0 : 0;
    let crowdHtml = '';
    if (occPct <= 40.0) {
      crowdHtml = `<span class="badge badge-green">🟢 Low (${Math.round(occPct)}% Occupied)</span>`;
    } else if (occPct <= 80.0) {
      crowdHtml = `<span class="badge badge-yellow">🟡 Moderate (${Math.round(occPct)}% Occupied)</span>`;
    } else {
      crowdHtml = `<span class="badge badge-red">🔴 High (${Math.round(occPct)}% Occupied)</span>`;
    }
    if (crowdBadge) {
      crowdBadge.innerHTML = crowdHtml;
    }

    // Automatically update top KPI summary cards in real-time
    const statAvail = document.getElementById('stat-available-beds');
    if (statAvail) statAvail.textContent = available;
    const statTotal = document.getElementById('stat-total-beds');
    if (statTotal) statTotal.textContent = total;
    const statOcc = document.getElementById('stat-occupied-beds');
    if (statOcc) statOcc.textContent = occupied;
  }
}

// -------------------------------------------------------------
// Interactive Doctor Management with Specialties & Add Doctor
// -------------------------------------------------------------
let editableDoctorsList = [];

function populateDoctorsForm(h) {
  editableDoctorsList = JSON.parse(JSON.stringify(h.doctors || []));
  if (editableDoctorsList.length === 0) {
    editableDoctorsList = [
      { id: Date.now(), name: 'Dr. Ananya Rao', department: 'Cardiology', specialty: 'Cardiologist', status: 'Available', available_time: '09:00 - 17:00', consultation_capacity: 35 },
      { id: Date.now() + 1, name: 'Dr. Vikram Nair', department: 'Orthopedics', specialty: 'Orthopedic Surgeon', status: 'Available', available_time: '10:00 - 18:00', consultation_capacity: 30 },
      { id: Date.now() + 2, name: 'Dr. Priya Menon', department: 'Pediatrics', specialty: 'Pediatrician', status: 'Available', available_time: '09:00 - 16:00', consultation_capacity: 40 }
    ];
  }
  renderDoctorsList();
}

function renderDoctorsList() {
  const container = document.getElementById('staff-doctors-container');
  if (!container) return;

  if (editableDoctorsList.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 1.5rem; background: var(--bg-subtle); border-radius: var(--radius-md); color: var(--text-muted); border: 1px dashed var(--border-subtle);">
        No doctors registered. Click <strong>"➕ Add Doctor"</strong> above to add a doctor.
      </div>
    `;
    return;
  }

  container.innerHTML = editableDoctorsList.map((d, index) => `
    <div class="doctor-entry-card" data-index="${index}" style="background-color: var(--bg-subtle); border-radius: var(--radius-md); padding: 1rem; border: 1px solid var(--border-subtle);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; gap: 0.5rem; flex-wrap: wrap;">
        <span style="font-weight: 700; font-size: 0.95rem; color: var(--text-main);">
          👨‍⚕️ Doctor #${index + 1}
        </span>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <select class="form-control doctor-status-select" data-index="${index}" style="width: auto; padding: 0.35rem 0.65rem; font-weight: 700; font-size: 0.85rem;">
            <option value="Available" ${d.status === 'Available' ? 'selected' : ''}>🟢 Available</option>
            <option value="Limited" ${d.status === 'Limited' ? 'selected' : ''}>🟡 Limited</option>
            <option value="Unavailable" ${d.status === 'Unavailable' ? 'selected' : ''}>🔴 Unavailable</option>
          </select>
          <button type="button" class="btn btn-sm btn-delete-doctor" data-index="${index}" title="Remove Doctor" style="background: transparent; border: 1px solid var(--border-subtle); color: var(--status-red); padding: 0.3rem 0.55rem; border-radius: var(--radius-sm); cursor: pointer;">
            🗑️ Remove
          </button>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem;">
        <div>
          <label style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Doctor Full Name</label>
          <input type="text" class="form-control doctor-name-input" data-index="${index}" value="${d.name || ''}" placeholder="e.g. Dr. Ananya Rao" required style="padding: 0.4rem 0.6rem; font-size: 0.85rem;">
        </div>
        <div>
          <label style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Medical Department</label>
          <input type="text" class="form-control doctor-dept-input" data-index="${index}" value="${d.department || ''}" placeholder="e.g. Cardiology, Orthopedics" required style="padding: 0.4rem 0.6rem; font-size: 0.85rem;">
        </div>
        <div>
          <label style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Doctor Specialty</label>
          <input type="text" class="form-control doctor-specialty-input" data-index="${index}" value="${d.specialty || ''}" placeholder="e.g. Cardiologist, Orthopedic Surgeon" required style="padding: 0.4rem 0.6rem; font-size: 0.85rem;">
        </div>
        <div>
          <label style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Consultation Hours</label>
          <input type="text" class="form-control doctor-time-input" data-index="${index}" value="${d.available_time || '09:00 - 17:00'}" placeholder="e.g. 09:00 - 17:00, 24x7" style="padding: 0.4rem 0.6rem; font-size: 0.85rem;">
        </div>
        <div>
          <label style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Consultation Capacity</label>
          <input type="number" class="form-control doctor-capacity-input" data-index="${index}" value="${d.consultation_capacity || 30}" min="1" max="200" style="padding: 0.4rem 0.6rem; font-size: 0.85rem;">
        </div>
      </div>
    </div>
  `).join('');

  // Attach delete button listeners
  container.querySelectorAll('.btn-delete-doctor').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.getAttribute('data-index'), 10);
      syncDoctorsFromDOM();
      editableDoctorsList.splice(idx, 1);
      renderDoctorsList();
    });
  });
}

function syncDoctorsFromDOM() {
  const container = document.getElementById('staff-doctors-container');
  if (!container) return;
  const cards = container.querySelectorAll('.doctor-entry-card');
  cards.forEach(card => {
    const idx = parseInt(card.getAttribute('data-index'), 10);
    if (editableDoctorsList[idx]) {
      editableDoctorsList[idx].name = card.querySelector('.doctor-name-input').value.trim();
      editableDoctorsList[idx].department = card.querySelector('.doctor-dept-input').value.trim();
      editableDoctorsList[idx].specialty = card.querySelector('.doctor-specialty-input').value.trim();
      editableDoctorsList[idx].status = card.querySelector('.doctor-status-select').value;
      editableDoctorsList[idx].available_time = card.querySelector('.doctor-time-input').value.trim();
      editableDoctorsList[idx].consultation_capacity = parseInt(card.querySelector('.doctor-capacity-input').value || '30', 10);
      editableDoctorsList[idx].name_or_department = `${editableDoctorsList[idx].name} — ${editableDoctorsList[idx].specialty || editableDoctorsList[idx].department}`;
    }
  });
}

const CANONICAL_RESOURCES = [
  { name: 'ICU Beds', icon: '🛏️' },
  { name: 'Oxygen Support', icon: '💨' },
  { name: 'Pharmacy', icon: '💊' },
  { name: 'Laboratory', icon: '🔬' },
  { name: 'X-ray', icon: '🩻' },
  { name: 'CT Scan', icon: '🖥️' },
  { name: 'Blood Bank', icon: '🩸' },
  { name: 'Emergency Department', icon: '🚨' }
];

function populateResourcesForm(h) {
  const container = document.getElementById('staff-resources-container');
  if (!container) return;

  const currentMap = {};
  (h.resources || []).forEach(r => {
    const raw = (r.resource_type || '').toLowerCase().trim();
    currentMap[raw] = r.status;
  });

  const getStatusFor = (canonName) => {
    const low = canonName.toLowerCase().trim();
    if (currentMap[low]) return currentMap[low];
    if (low === 'icu beds' && (currentMap['icu'] || currentMap['icu beds'])) return currentMap['icu'] || currentMap['icu beds'];
    if (low === 'oxygen support' && (currentMap['oxygen'] || currentMap['oxygen support'])) return currentMap['oxygen'] || currentMap['oxygen support'];
    if (low === 'laboratory' && (currentMap['lab'] || currentMap['laboratory'])) return currentMap['lab'] || currentMap['laboratory'];
    if (low === 'emergency department' && (currentMap['ed'] || currentMap['emergency'] || currentMap['emergency department'])) {
      return currentMap['ed'] || currentMap['emergency'] || currentMap['emergency department'];
    }
    if (low === 'ct scan' && currentMap['ct scan']) return currentMap['ct scan'];
    if (low === 'blood bank' && currentMap['blood bank']) return currentMap['blood bank'];
    return 'Available';
  };

  container.innerHTML = CANONICAL_RESOURCES.map(fac => {
    const stat = getStatusFor(fac.name);
    return `
      <div class="resource-item" style="text-align: left; padding: 0.85rem; background: var(--bg-subtle); border-radius: var(--radius-md); border: 1px solid var(--border-subtle); display: flex; flex-direction: column; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.5rem;">
          <span style="font-size: 1.15rem;">${fac.icon}</span>
          <span class="resource-name" style="font-weight: 700; font-size: 0.85rem; color: var(--text-main);">${fac.name}</span>
        </div>
        <select class="form-control resource-status-select" data-resource="${fac.name}" style="width: 100%; padding: 0.4rem 0.5rem; font-size: 0.82rem; font-weight: 600; cursor: pointer;">
          <option value="Available" ${stat === 'Available' ? 'selected' : ''}>🟢 Available</option>
          <option value="Limited" ${stat === 'Limited' ? 'selected' : ''}>🟡 Limited</option>
          <option value="Unavailable" ${stat === 'Unavailable' ? 'selected' : ''}>🔴 Unavailable</option>
        </select>
      </div>
    `;
  }).join('');
}

// 5. Setup Form Submissions
function setupForms() {
  // Real-time calculation listeners
  document.getElementById('input-total-beds').addEventListener('input', updateBedCalculations);
  document.getElementById('input-occupied-beds').addEventListener('input', updateBedCalculations);

  // 1. Bed Form Submit
  document.getElementById('form-beds').addEventListener('submit', async (e) => {
    e.preventDefault();
    const total = parseInt(document.getElementById('input-total-beds').value, 10);
    const occupied = parseInt(document.getElementById('input-occupied-beds').value, 10);
    const admissions = parseInt(document.getElementById('input-admissions').value || '0', 10);
    const discharges = parseInt(document.getElementById('input-discharges').value || '0', 10);

    const res = await fetchAPI(`/staff/${staffSession.hospital_id}/beds`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${staffSession.token}` },
      body: JSON.stringify({
        total_beds: total,
        occupied_beds: occupied,
        today_admissions: admissions,
        today_discharges: discharges,
        admissions: admissions,
        discharges: discharges,
        staff_id: staffSession.staff_id
      })
    });

    if (res.ok && res.data.success) {
      alert('✅ Bed capacity successfully updated!');
      await loadDashboardData();
    } else {
      alert(`❌ Error: ${res.data.error || 'Failed to update beds.'}`);
    }
  });

  // 2. Add Doctor Button
  const addDocBtn = document.getElementById('btn-add-doctor');
  if (addDocBtn) {
    addDocBtn.addEventListener('click', () => {
      syncDoctorsFromDOM();
      editableDoctorsList.push({
        id: Date.now(),
        name: '',
        department: 'General Medicine',
        specialty: 'General Physician',
        status: 'Available',
        available_time: '09:00 - 17:00',
        consultation_capacity: 35,
        name_or_department: ''
      });
      renderDoctorsList();
      const allNameInputs = document.querySelectorAll('.doctor-name-input');
      if (allNameInputs.length > 0) {
        allNameInputs[allNameInputs.length - 1].focus();
      }
    });
  }

  // 3. Doctor Form Submit (with Specialty & Name)
  document.getElementById('form-doctors').addEventListener('submit', async (e) => {
    e.preventDefault();
    syncDoctorsFromDOM();

    for (let i = 0; i < editableDoctorsList.length; i++) {
      const d = editableDoctorsList[i];
      if (!d.name || d.name.trim() === '') {
        alert(`Please enter a name for Doctor #${i + 1}`);
        return;
      }
    }

    const res = await fetchAPI(`/staff/${staffSession.hospital_id}/doctors`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${staffSession.token}` },
      body: JSON.stringify({
        doctors: editableDoctorsList,
        staff_id: staffSession.staff_id
      })
    });

    if (res.ok && res.data.success) {
      alert('✅ Doctor availability and specialties successfully updated!');
      await loadDashboardData();
    } else {
      alert(`❌ Error: ${res.data.error || 'Failed to update doctors.'}`);
    }
  });

  // 4. Resources Form Submit (8 Key Facilities)
  document.getElementById('form-resources').addEventListener('submit', async (e) => {
    e.preventDefault();
    const selects = document.querySelectorAll('.resource-status-select');
    const resourcesMap = {};

    selects.forEach(sel => {
      const name = sel.getAttribute('data-resource');
      resourcesMap[name] = sel.value;
    });

    const res = await fetchAPI(`/staff/${staffSession.hospital_id}/resources`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${staffSession.token}` },
      body: JSON.stringify({
        resources: resourcesMap,
        staff_id: staffSession.staff_id
      })
    });

    if (res.ok && res.data.success) {
      alert('✅ Medical resources status successfully updated!');
      await loadDashboardData();
    } else {
      alert(`❌ Error: ${res.data.error || 'Failed to update resources.'}`);
    }
  });

  // 5. History Refresh Button
  const refreshBtn = document.getElementById('btn-refresh-history');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      refreshBtn.disabled = true;
      refreshBtn.textContent = 'Refreshing...';
      await loadAuditHistory();
      refreshBtn.textContent = '🔄 Refresh Log';
      refreshBtn.disabled = false;
    });
  }

  // 6. Collapsible Details Toggle
  const auditDetails = document.getElementById('sec-audit-details');
  const auditIndicator = document.getElementById('audit-toggle-indicator');
  if (auditDetails && auditIndicator) {
    auditDetails.addEventListener('toggle', () => {
      if (auditDetails.open) {
        auditIndicator.textContent = 'Click to Hide ▴';
      } else {
        auditIndicator.textContent = 'Click to View ▾';
      }
    });
  }
}

// Format complex values into friendly readable text
function formatHistoryValue(val) {
  if (val === null || val === undefined) return 'None';
  if (typeof val === 'string') return val;
  if (Array.isArray(val)) {
    if (val.length === 0) return 'None';
    // Doctor list format
    if (val[0] && val[0].name) {
      const summary = val.map(d => `${d.name} (${d.status || 'Active'})`).slice(0, 2).join(', ');
      return `${val.length} Doctors: ${summary}${val.length > 2 ? '...' : ''}`;
    }
    // Resource list format
    if (val[0] && val[0].resource_type) {
      const nonAvail = val.filter(r => r.status && r.status !== 'Available');
      if (nonAvail.length > 0) {
        return `${val.length} Facilities (${nonAvail.map(r => `${r.resource_type}: ${r.status}`).join(', ')})`;
      }
      return `${val.length} Facilities (All Available)`;
    }
    return JSON.stringify(val);
  }
  if (typeof val === 'object') {
    if (val.total_beds !== undefined || val.total !== undefined) {
      const tot = val.total_beds !== undefined ? val.total_beds : val.total;
      const occ = val.occupied_beds !== undefined ? val.occupied_beds : val.occupied;
      const avail = val.available_beds !== undefined ? val.available_beds : (val.available !== undefined ? val.available : tot - occ);
      return `Total: ${tot}, Occ: ${occ}, Avail: ${avail}`;
    }
    if (val.current_patients !== undefined) {
      return `Patients: ${val.current_patients}, Waiting: ${val.waiting_patients}`;
    }
    // Resource map format
    const keys = Object.keys(val);
    if (keys.length > 0 && ['Available', 'Limited', 'Unavailable'].includes(val[keys[0]])) {
      return Object.entries(val).map(([k, v]) => `${k}: ${v}`).join(', ');
    }
    return JSON.stringify(val);
  }
  return String(val);
}

// 6. Audit History Log Loader
async function loadAuditHistory() {
  if (!staffSession) return;
  const tbody = document.getElementById('audit-history-tbody');
  if (!tbody) return;

  const res = await fetchAPI(`/staff/${staffSession.hospital_id}/history`, {
    headers: { 'Authorization': `Bearer ${staffSession.token}` }
  });

  if (!res.ok || !res.data.success || !Array.isArray(res.data.data)) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted); padding: 1.5rem;">Unable to load audit history.</td></tr>`;
    return;
  }

  const items = res.data.data;
  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted); padding: 1.5rem;">No updates yet</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(item => {
    const dateStr = item.changed_at ? new Date(item.changed_at).toLocaleString('en-IN', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    }) : 'Just now';
    const oldFormatted = formatHistoryValue(item.old_value);
    const newFormatted = formatHistoryValue(item.new_value);

    let fieldBadge = 'badge-neutral';
    if (item.field_changed === 'beds') fieldBadge = 'badge-blue';
    else if (item.field_changed === 'resources') fieldBadge = 'badge-yellow';
    else if (item.field_changed === 'doctors') fieldBadge = 'badge-green';

    return `
      <tr>
        <td style="white-space: nowrap; font-size: 0.82rem; color: var(--text-muted);">${dateStr}</td>
        <td><strong style="color: var(--primary);">${escapeHtml(item.staff_id || 'staff')}</strong></td>
        <td><span class="badge ${fieldBadge}">${escapeHtml(item.field_changed || 'general')}</span></td>
        <td style="font-size: 0.82rem; color: var(--text-muted); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(oldFormatted)}">${escapeHtml(oldFormatted)}</td>
        <td style="font-size: 0.82rem; color: var(--status-green); font-weight: 600; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(newFormatted)}">${escapeHtml(newFormatted)}</td>
      </tr>
    `;
  }).join('');
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// -------------------------------------------------------------
// Incoming Emergency Requests Management (Features 2 & 3)
// -------------------------------------------------------------
async function loadEmergencyRequests() {
  if (!staffSession) return;

  const res = await fetchAPI(`/staff/${staffSession.hospital_id}/emergency-requests`, {
    headers: { 'Authorization': `Bearer ${staffSession.token}` }
  });

  const tbody = document.getElementById('emergency-requests-tbody');
  const countBadge = document.getElementById('badge-emergency-count');
  if (!tbody) return;

  if (!res.ok || !res.data.success) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--color-danger); padding: 1rem;">
          Failed to load emergency requests.
        </td>
      </tr>
    `;
    return;
  }

  const reqs = res.data.data || [];
  const activeReqs = reqs.filter(r => r.status !== 'Cancelled' && r.status !== 'Patient Admitted');

  // Surface Emergency Requests Immediately: Top-Right Header Alert & Sticky Navbar Indicator
  const headerAlert = document.getElementById('staff-header-emergency-alert');
  const headerAlertText = document.getElementById('staff-header-emergency-text');
  const navAlert = document.getElementById('nav-staff-emergency-indicator');
  const navAlertCount = document.getElementById('nav-staff-emergency-count');

  if (headerAlert && headerAlertText) {
    if (activeReqs.length > 0) {
      headerAlert.className = 'staff-header-emergency-alert alert-active';
      headerAlertText.textContent = `${activeReqs.length} Active Emergency Request${activeReqs.length > 1 ? 's' : ''}`;
      headerAlert.style.display = 'inline-flex';
      headerAlert.title = 'Click to jump directly to Incoming Emergency Requests';
    } else {
      headerAlert.className = 'staff-header-emergency-alert alert-quiet';
      headerAlertText.textContent = 'No active emergencies';
      headerAlert.style.display = 'inline-flex';
      headerAlert.title = 'No active emergency requests';
    }
  }

  if (navAlert && navAlertCount) {
    if (activeReqs.length > 0) {
      navAlert.style.display = 'inline-flex';
      navAlertCount.textContent = `${activeReqs.length} Active`;
    } else {
      navAlert.style.display = 'none';
    }
  }

  if (countBadge) {
    countBadge.textContent = `${activeReqs.length} Active`;
    if (activeReqs.length > 0) {
      countBadge.style.backgroundColor = 'var(--color-danger)';
      countBadge.style.color = '#ffffff';
    } else {
      countBadge.style.backgroundColor = 'var(--color-surface-subtle)';
      countBadge.style.color = 'var(--color-text-muted)';
    }
  }

  if (reqs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--color-text-muted); padding: 1.5rem;">
          No active emergency requests for this hospital at this time.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = reqs.map(r => {
    const timeStr = r.created_at ? new Date(r.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '--';
    
    // Status Badge
    let statusBadge = '<span class="badge badge-yellow">🟡 Ambulance Assigned</span>';
    if (r.status === 'En Route') statusBadge = '<span class="badge badge-blue">🔵 En Route</span>';
    else if (r.status === 'Arrived') statusBadge = '<span class="badge badge-blue">🟣 Arrived</span>';
    else if (r.status === 'Patient Admitted') statusBadge = '<span class="badge badge-green">🟢 Admitted</span>';
    else if (r.status === 'Cancelled') statusBadge = '<span class="badge badge-red">🔴 Cancelled</span>';

    // Action Buttons
    let actionButtons = '';
    if (r.status === 'Ambulance Assigned') {
      actionButtons = `
        <button class="btn btn-sm btn-primary" onclick="handleEmergencyStatusUpdate('${r.request_code}', 'En Route')">Mark En Route</button>
        <button class="btn btn-sm btn-outline btn-danger-subtle" onclick="handleEmergencyCancel('${r.request_code}')">Cancel</button>
      `;
    } else if (r.status === 'En Route') {
      actionButtons = `
        <button class="btn btn-sm btn-primary" onclick="handleEmergencyStatusUpdate('${r.request_code}', 'Arrived')">Confirm Arrival</button>
        <button class="btn btn-sm btn-outline btn-danger-subtle" onclick="handleEmergencyCancel('${r.request_code}')">Cancel</button>
      `;
    } else if (r.status === 'Arrived') {
      actionButtons = `
        <button class="btn btn-sm btn-success" style="background-color: var(--color-primary); color: #fff;" onclick="handleEmergencyStatusUpdate('${r.request_code}', 'Patient Admitted')">Admit Patient (Convert Bed)</button>
        <button class="btn btn-sm btn-outline btn-danger-subtle" onclick="handleEmergencyCancel('${r.request_code}')">Cancel</button>
      `;
    } else if (r.status === 'Patient Admitted') {
      actionButtons = '<span style="color: var(--color-success); font-weight: 700; font-size: 0.82rem;">✅ Bed Secured & Inpatient</span>';
    } else if (r.status === 'Cancelled') {
      actionButtons = '<span style="color: var(--color-text-muted); font-size: 0.82rem;">Released</span>';
    }

    return `
      <tr>
        <td><span class="emergency-code-pill" style="background-color: var(--color-surface-subtle); color: var(--color-text-primary); border: 1px solid var(--color-border); font-size: 0.8rem;">${r.request_code}</span></td>
        <td>${escapeHtml(r.patient_locality || 'Detected Location')}</td>
        <td><strong>${escapeHtml(r.ambulance_code || '--')}</strong><br><span style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(r.driver_name || 'Pilot')} (${escapeHtml(r.driver_contact || '')})</span></td>
        <td>${statusBadge}</td>
        <td>${r.bed_blocked ? '<span class="badge-bed-reserved">🔒 1 Bed Blocked</span>' : (r.status === 'Patient Admitted' ? '<span style="font-size: 0.82rem; color: var(--color-success); font-weight: 700;">🛏️ Occupied</span>' : '<span style="font-size: 0.82rem; color: var(--text-muted);">Released</span>')}</td>
        <td style="font-size: 0.82rem; color: var(--text-muted);">${timeStr}</td>
        <td><div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">${actionButtons}</div></td>
      </tr>
    `;
  }).join('');
}

async function handleEmergencyStatusUpdate(requestCode, newStatus) {
  if (!staffSession) return;

  const res = await fetchAPI(`/emergency/request/${encodeURIComponent(requestCode)}/status`, {
    method: 'PUT',
    headers: { 'Authorization': `Bearer ${staffSession.token}` },
    body: JSON.stringify({ status: newStatus, staff_id: staffSession.staff_id })
  });

  if (res.ok && res.data.success) {
    await loadDashboardData();
    await loadEmergencyRequests();
  } else {
    alert(res.data.error || `Failed to update status to ${newStatus}.`);
  }
}

async function handleEmergencyCancel(requestCode) {
  if (!staffSession) return;

  if (!confirm('Are you sure you want to cancel this emergency request? The blocked bed will be released immediately.')) {
    return;
  }

  const res = await fetchAPI(`/emergency/request/${encodeURIComponent(requestCode)}/cancel`, {
    method: 'PUT',
    headers: { 'Authorization': `Bearer ${staffSession.token}` },
    body: JSON.stringify({ staff_id: staffSession.staff_id })
  });

  if (res.ok && res.data.success) {
    await loadDashboardData();
    await loadEmergencyRequests();
  } else {
    alert(res.data.error || 'Failed to cancel emergency request.');
  }
}

window.handleEmergencyStatusUpdate = handleEmergencyStatusUpdate;
window.handleEmergencyCancel = handleEmergencyCancel;

function setupStaffEmergencyAlertListeners() {
  const jumpToEmergencyQueue = (e) => {
    if (e) e.preventDefault();
    const sec = document.getElementById('sec-emergency-requests');
    if (sec) {
      sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
      sec.style.transition = 'box-shadow 0.3s ease, border-color 0.3s ease';
      sec.style.borderColor = 'var(--color-danger)';
      sec.style.boxShadow = '0 0 0 4px var(--color-danger-border)';
      setTimeout(() => {
        sec.style.boxShadow = '';
        sec.style.borderColor = '';
      }, 2500);
    }
  };

  const headerAlert = document.getElementById('staff-header-emergency-alert');
  if (headerAlert) {
    headerAlert.addEventListener('click', jumpToEmergencyQueue);
  }
  const navAlert = document.getElementById('nav-staff-emergency-indicator');
  if (navAlert) {
    navAlert.addEventListener('click', jumpToEmergencyQueue);
  }
}

