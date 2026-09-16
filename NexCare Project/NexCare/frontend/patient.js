/**
 * NexCare Patient Portal Controller
 * Search, filtering, AI recommendations, all-India geolocation, modal view, and voice read-aloud integration
 */

let allHospitalsData = [];
let rankedHospitalsData = [];
let currentView = 'all'; // 'all' or 'recommended'
let currentPatientLocality = '';
let currentCoordinates = null; // { lat, lng }
let allIndiaLocations = {};

document.addEventListener('DOMContentLoaded', async () => {
  // Parse URL query parameters
  const urlParams = new URLSearchParams(window.location.search);
  const initialLocality = urlParams.get('locality') || '';
  const initialView = urlParams.get('view') || 'all';
  const initialLat = urlParams.get('lat');
  const initialLng = urlParams.get('lng');

  if (initialView === 'recommended') {
    currentView = 'recommended';
  }

  if (initialLat && initialLng) {
    currentCoordinates = {
      lat: parseFloat(initialLat),
      lng: parseFloat(initialLng)
    };
  }

  // Load all-India states and cities
  await loadLocations(initialLocality);

  // Setup Live Geolocation Button
  setupLiveLocation();

  // Setup Spoken Announcements Button
  setupAnnounceButton();

  // Setup View Switcher Tabs
  setupTabs();

  // Setup Filter and Search Listeners
  setupFilters();

  // Setup Modal Listeners
  setupModal();

  // Setup Floating SOS Emergency Modal
  setupSOSModal();

  // Auto-open SOS modal if triggered via query param
  if (urlParams.get('sos') === 'open') {
    openEmergencyConfirmation();
  }

  // Initial Data Fetch
  await refreshData();
});

// 1. Load All-India States and Cities (Two-Step Cascading Selector)
async function loadLocations(preselectCity) {
  const stateSelect = document.getElementById('patient-state');
  const citySelect = document.getElementById('patient-city');
  const legacySelect = document.getElementById('patient-locality');

  const res = await fetchAPI('/locations');
  if (res.ok && res.data && res.data.data) {
    allIndiaLocations = res.data.data;
  } else {
    // Fallback if endpoint fails
    allIndiaLocations = {
      "Tamil Nadu": [
        "Chennai - Adyar", "Chennai - Anna Nagar", "Chennai - Egmore", "Chennai - Guindy",
        "Chennai - Manapakkam", "Chennai - Mogappair", "Chennai - Perambur", "Chennai - Porur",
        "Chennai - Sholinganallur", "Chennai - T. Nagar", "Chennai - Tambaram", "Chennai - Velachery"
      ]
    };
  }

  if (stateSelect) {
    stateSelect.innerHTML = `<option value="">${t('select_state_placeholder', 'Choose State...')}</option>`;
    
    // Always put Tamil Nadu at the top, then others alphabetically
    const states = Object.keys(allIndiaLocations).sort((a, b) => {
      if (a === 'Tamil Nadu') return -1;
      if (b === 'Tamil Nadu') return 1;
      return a.localeCompare(b);
    });

    // Detect which state contains preselectCity
    let detectedState = 'Tamil Nadu';
    if (preselectCity) {
      for (const [st, cities] of Object.entries(allIndiaLocations)) {
        if (cities.some(c => c.toLowerCase() === preselectCity.toLowerCase() || c.toLowerCase().includes(preselectCity.toLowerCase()))) {
          detectedState = st;
          break;
        }
      }
    }

    states.forEach(st => {
      const opt = document.createElement('option');
      opt.value = st;
      opt.textContent = st;
      if (st === detectedState) {
        opt.selected = true;
      }
      stateSelect.appendChild(opt);
    });

    // Populate cities for default/detected state
    populateCities(detectedState, preselectCity);

    // State change event
    stateSelect.addEventListener('change', (e) => {
      const selectedState = e.target.value;
      currentCoordinates = null; // Clear live GPS when manually picking state
      populateCities(selectedState);
      refreshData();
    });
  }

  if (citySelect) {
    citySelect.addEventListener('change', (e) => {
      currentCoordinates = null; // Clear live GPS when manually picking city
      currentPatientLocality = e.target.value;
      if (legacySelect) legacySelect.value = currentPatientLocality;
      refreshData();
    });
  }
}

function populateCities(stateName, preselectCity = '') {
  const citySelect = document.getElementById('patient-city');
  const legacySelect = document.getElementById('patient-locality');
  if (!citySelect) return;

  citySelect.innerHTML = `<option value="">${t('select_city_placeholder', 'Choose City or Locality...')}</option>`;
  const cities = allIndiaLocations[stateName] || [];

  cities.forEach(city => {
    const opt = document.createElement('option');
    opt.value = city;
    opt.textContent = city;
    if (
      (preselectCity && (city.toLowerCase() === preselectCity.toLowerCase() || city.toLowerCase().includes(preselectCity.toLowerCase()))) ||
      (!preselectCity && stateName === 'Tamil Nadu' && city === 'Chennai - Adyar')
    ) {
      opt.selected = true;
      currentPatientLocality = city;
    }
    citySelect.appendChild(opt);
  });

  if (!currentPatientLocality && cities.length > 0) {
    currentPatientLocality = cities[0];
    citySelect.value = cities[0];
  }

  if (legacySelect) {
    legacySelect.innerHTML = citySelect.innerHTML;
    legacySelect.value = currentPatientLocality;
  }
}

// 2. Setup Live Geolocation Button
function setupLiveLocation() {
  const liveBtn = document.getElementById('btn-live-loc');
  if (!liveBtn) return;

  liveBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
      alert(t('live_loc_denied', 'Location access was not granted or not supported in this browser.'));
      return;
    }

    liveBtn.textContent = t('live_loc_detecting', '📍 Detecting your live location...');
    liveBtn.disabled = true;

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        currentCoordinates = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude
        };
        currentPatientLocality = ''; // GPS coordinates take precedence

        liveBtn.textContent = t('live_loc_success', '✅ Live location acquired');
        liveBtn.disabled = false;

        // Reset button text after 3 seconds
        setTimeout(() => {
          liveBtn.textContent = t('btn_live_location', '📍 Use My Current Location');
        }, 3500);

        refreshData();
      },
      (err) => {
        console.warn('Geolocation error:', err);
        liveBtn.textContent = t('btn_live_location', '📍 Use My Current Location');
        liveBtn.disabled = false;
        alert(t('live_loc_denied', 'Location access was not granted. Please select your State and City below.'));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000
      }
    );
  });
}

// 3. Setup Spoken Announcements Button
function setupAnnounceButton() {
  const announceBtn = document.getElementById('btn-announce-hospitals');
  if (!announceBtn) return;

  announceBtn.addEventListener('click', () => {
    const list = (currentView === 'recommended') ? rankedHospitalsData : allHospitalsData;
    if (voiceAssistant && typeof voiceAssistant.announceNearbyHospitals === 'function') {
      voiceAssistant.announceNearbyHospitals(list);
    } else {
      alert('Voice assistant is loading. Please try again in a moment.');
    }
  });
}

// 4. View Tab Setup
function setupTabs() {
  const tabAll = document.getElementById('tab-all');
  const tabRec = document.getElementById('tab-recommended');
  const recBanner = document.getElementById('recommendation-info-banner');

  tabAll.addEventListener('click', () => {
    currentView = 'all';
    tabAll.classList.add('active');
    tabAll.setAttribute('aria-selected', 'true');
    tabRec.classList.remove('active');
    tabRec.setAttribute('aria-selected', 'false');
    if (recBanner) recBanner.style.display = 'none';
    renderHospitals();
  });

  tabRec.addEventListener('click', () => {
    currentView = 'recommended';
    tabRec.classList.add('active');
    tabRec.setAttribute('aria-selected', 'true');
    tabAll.classList.remove('active');
    tabAll.setAttribute('aria-selected', 'false');
    if (recBanner) recBanner.style.display = 'block';
    renderHospitals();
  });

  if (currentView === 'recommended') {
    tabRec.click();
  }
}

// 5. Setup Filter Listeners
function setupFilters() {
  const searchInput = document.getElementById('filter-search');
  const typeSelect = document.getElementById('filter-type');
  const crowdSelect = document.getElementById('filter-crowd');
  const bedsSelect = document.getElementById('filter-beds');

  const onFilterChange = () => renderHospitals();

  if (searchInput) searchInput.addEventListener('input', onFilterChange);
  if (typeSelect) typeSelect.addEventListener('change', onFilterChange);
  if (crowdSelect) crowdSelect.addEventListener('change', onFilterChange);
  if (bedsSelect) bedsSelect.addEventListener('change', onFilterChange);
}

// 6. Refresh Hospital Data from Server
async function refreshData() {
  const container = document.getElementById('hospitals-list');
  if (!container) return;

  container.innerHTML = `
    <div style="grid-column: 1 / -1; text-align: center; padding: 2.5rem;">
      <p style="color: var(--text-muted); font-size: 1.05rem;">Fetching hospital availability indicators...</p>
    </div>
  `;

  const stateSelect = document.getElementById('patient-state');
  const selectedState = stateSelect ? stateSelect.value : '';

  let listUrl = '/hospitals';
  let recUrl = '/hospitals/recommendations?limit=10';
  const queryParts = [];

  if (currentCoordinates) {
    queryParts.push(`lat=${currentCoordinates.lat}&lng=${currentCoordinates.lng}`);
  } else if (currentPatientLocality) {
    queryParts.push(`patient_locality=${encodeURIComponent(currentPatientLocality)}`);
    queryParts.push(`locality=${encodeURIComponent(currentPatientLocality)}`);
  }

  if (selectedState) {
    queryParts.push(`state=${encodeURIComponent(selectedState)}`);
  }

  if (queryParts.length > 0) {
    const qs = queryParts.join('&');
    listUrl += `?${qs}`;
    recUrl += `&${qs}`;
  }

  const [listRes, recRes] = await Promise.all([
    fetchAPI(listUrl),
    fetchAPI(recUrl)
  ]);

  if (listRes.ok && listRes.data.data) {
    allHospitalsData = listRes.data.data;
  } else {
    allHospitalsData = [];
  }
  if (recRes.ok && recRes.data.data) {
    rankedHospitalsData = recRes.data.data;
  } else {
    rankedHospitalsData = [];
  }

  // Update global accessible references for Voice Assistant
  window.currentHospitals = allHospitalsData;
  window.recommendedHospitals = rankedHospitalsData;

  // Notice Banner for locations outside Chennai/Bengaluru
  const noticeBanner = document.getElementById('non-chennai-notice-banner');
  const noticeText = document.getElementById('non-chennai-notice-text');
  const locationNote = (listRes.data && listRes.data.location_note) || (recRes.data && recRes.data.location_note);

  if (noticeBanner) {
    if (locationNote) {
      noticeBanner.style.display = 'block';
      if (noticeText) noticeText.textContent = locationNote;
    } else {
      noticeBanner.style.display = 'none';
    }
  }

  renderHospitals();
}

// 5. Render Filtered Hospital Cards
function renderHospitals() {
  const container = document.getElementById('hospitals-list');
  if (!container) return;

  const dataset = (currentView === 'recommended') ? rankedHospitalsData : allHospitalsData;

  const searchInput = document.getElementById('filter-search');
  const typeSelect = document.getElementById('filter-type');
  const crowdSelect = document.getElementById('filter-crowd');
  const bedsSelect = document.getElementById('filter-beds');

  const searchQuery = (searchInput ? searchInput.value : '').toLowerCase().trim();
  const selectedType = typeSelect ? typeSelect.value : '';
  const selectedCrowd = crowdSelect ? crowdSelect.value : '';
  const minBeds = parseInt(bedsSelect ? bedsSelect.value : '0', 10) || 0;

  const filtered = dataset.filter(h => {
    // Search keyword
    if (searchQuery) {
      const matchName = (h.name || '').toLowerCase().includes(searchQuery);
      const matchLoc = (h.locality || '').toLowerCase().includes(searchQuery);
      const matchAddr = (h.address || '').toLowerCase().includes(searchQuery);
      if (!matchName && !matchLoc && !matchAddr) return false;
    }

    // Type filter
    if (selectedType && h.type !== selectedType) {
      return false;
    }

    // Crowd filter
    if (selectedCrowd && h.crowd_status !== selectedCrowd) {
      return false;
    }

    // Bed availability filter
    const availableBeds = h.beds ? h.beds.available : 0;
    if (availableBeds < minBeds) {
      return false;
    }

    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle);">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🔍</div>
        <h3 style="margin-bottom: 0.5rem;">${t('no_hospitals_found', 'No hospitals found')}</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem; max-width: 540px; margin: 0 auto;">
          ${t('adjust_filters_hint', 'Try adjusting your filters or clearing the search query to see more results.')}
        </p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(h => createHospitalCardHTML(h, currentView === 'recommended')).join('');

  // Attach Details Button Event Listeners
  document.querySelectorAll('.btn-view-details').forEach(btn => {
    btn.addEventListener('click', () => {
      const hid = parseInt(btn.getAttribute('data-id'), 10);
      const hospital = allHospitalsData.find(item => item.id === hid) || rankedHospitalsData.find(item => item.id === hid);
      if (hospital) {
        openHospitalModal(hospital);
      }
    });
  });

  // Attach Read Aloud Button Event Listeners
  document.querySelectorAll('.btn-speak-card').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const hid = parseInt(btn.getAttribute('data-id'), 10);
      const hospital = allHospitalsData.find(item => item.id === hid) || rankedHospitalsData.find(item => item.id === hid);
      if (hospital && typeof readHospitalSummary === 'function') {
        readHospitalSummary(hospital, btn);
      }
    });
  });
}

// 6. Template for Single Hospital Card with i18n & Voice Support
function createHospitalCardHTML(h, isRecommendedView) {
  const beds = h.beds || { total: 100, occupied: 50, available: 50 };
  const occPct = beds.total > 0 ? Math.round((beds.occupied / beds.total) * 100) : 0;
  const availPct = 100 - occPct;
  const dist = h.distance_km != null ? `${h.distance_km} km` : 'Simulated';
  const typeLabel = h.type === 'Government' ? t('facility_govt', 'Government') : t('facility_private', 'Private');

  let recommendationBannerHTML = '';
  let scoreHTML = '';

  if (isRecommendedView && h.score != null) {
    scoreHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.6rem;">
          <div class="score-badge" title="Overall Weighted Recommendation Score">${Math.round(h.score)}</div>
          <div>
            <div style="font-size: 0.85rem; font-weight: 700; color: var(--primary);">${t('match_score_title', 'NexCare Match Score')}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${t('match_score_subtitle', 'Out of 100 points')}</div>
          </div>
        </div>
        <span class="badge badge-green">${t('recommended_badge', 'Recommended')}</span>
      </div>
    `;

    if (h.recommendation_reason) {
      recommendationBannerHTML = `
        <div class="rec-reason-box" role="note">
          <strong>${t('why_hospital_label', 'Why this hospital:')}</strong> ${h.recommendation_reason}
        </div>
      `;
    }
  }

  return `
    <article class="hospital-card" aria-label="${h.name}">
      <div>
        ${scoreHTML}
        <div class="card-header">
          <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;">
            <span class="card-locality-badge">📍 ${h.locality} (${dist})</span>
            <span class="badge badge-neutral">${typeLabel}</span>
          </div>
          <h3 class="card-title">${h.name}</h3>
          <p class="card-address">${h.address}</p>
        </div>

        ${recommendationBannerHTML}

        <!-- Bed Availability Bar -->
        <div class="bed-stat-wrap">
          <div class="bed-stat-header">
            <span>${t('beds_available_label', 'Beds Available:')} <strong style="color: var(--status-green);">${beds.available}</strong> / ${beds.total}</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">${availPct}% ${t('beds_free_label', 'free')}</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${availPct}%;"></div>
          </div>
        </div>

        <!-- Specialty Tags & Indicators -->
        ${renderCardSpecialties(h)}

        <!-- Indicators -->
        <div class="card-indicators">
          ${getTranslatedStatusBadge(h.doctor_status)}
          ${getTranslatedStatusBadge(h.crowd_status)}
        </div>
      </div>

      <div class="card-action-bar">
        <button class="btn-speak-card" data-id="${h.id}" title="Read hospital status aloud">
          🔊 ${t('btn_read_aloud', 'Read Aloud')}
        </button>

        <button class="btn btn-primary btn-sm btn-view-details" data-id="${h.id}">
          ${t('btn_view_details', 'View Details ➔')}
        </button>
      </div>
    </article>
  `;
}

// 7. Modal Handlers
function setupModal() {
  const modal = document.getElementById('hospital-modal');
  const closeBtn = document.getElementById('modal-close-btn');

  if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.remove('open'));
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('open');
      }
    });
  }

  // ESC key to close
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && modal.classList.contains('open')) {
      modal.classList.remove('open');
    }
  });
}

function openHospitalModal(h) {
  const modal = document.getElementById('hospital-modal');
  if (!modal) return;

  const beds = h.beds || { total: 0, occupied: 0, available: 0 };
  const crowd = h.crowd || { current_patients: 0, waiting_patients: 0 };
  const dist = h.distance_km != null ? `${h.distance_km} km` : 'Simulated';
  const typeLabel = h.type === 'Government' ? t('facility_govt', 'Government') : t('facility_private', 'Private');

  document.getElementById('modal-hospital-name').textContent = h.name;
  document.getElementById('modal-type-badge').textContent = typeLabel;
  document.getElementById('modal-hospital-address').textContent = h.address;
  document.getElementById('modal-hospital-contact').textContent = `${t('contact_desk_label', '📞 Inquiries / Emergency Desk:')} ${h.contact_number}`;
  document.getElementById('modal-distance').textContent = `${dist} ${t('modal_from_selected', 'from selected location')}`;

  // Directions Link
  const mapQuery = encodeURIComponent(`${h.name}, ${h.address}`);
  document.getElementById('modal-map-link').href = `https://www.google.com/maps/search/?api=1&query=${mapQuery}`;

  // Beds
  document.getElementById('modal-beds-total').textContent = beds.total;
  document.getElementById('modal-beds-occupied').textContent = beds.occupied;
  document.getElementById('modal-beds-available').textContent = beds.available;
  const availPct = beds.total > 0 ? Math.round((beds.available / beds.total) * 100) : 0;
  document.getElementById('modal-bed-progress').style.width = `${availPct}%`;

  // Doctors with Name, Specialty & Status
  const doctorsList = document.getElementById('modal-doctors-list');
  if (h.doctors && h.doctors.length > 0) {
    doctorsList.innerHTML = h.doctors.map(d => {
      const docName = d.name || (d.name_or_department ? d.name_or_department.split(' — ')[0] : 'Dr. Specialist');
      const docSpec = d.specialty || d.department || 'Specialist';
      return `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0.9rem; background: var(--bg-subtle); border-radius: var(--radius-sm); border-left: 4px solid var(--primary); margin-bottom: 0.4rem; gap: 0.5rem; flex-wrap: wrap;">
          <div>
            <div style="font-size: 0.95rem; font-weight: 700; color: var(--text-main); margin-bottom: 0.25rem;">
              <span>${docName}</span>
              <span style="color: var(--text-muted); font-weight: 400;"> — </span>
              <span class="badge badge-specialty" style="font-size: 0.8rem;">${docSpec}</span>
              <span style="color: var(--text-muted); font-weight: 400;"> — </span>
              <span>${getTranslatedStatusBadge(d.status)}</span>
            </div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">Dept: ${d.department || docSpec} • Available: ${d.available_time || '09:00 - 17:00'} • Capacity: ${d.consultation_capacity || 30} pts/day</div>
          </div>
        </div>
      `;
    }).join('');
  } else {
    doctorsList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.88rem;">Doctor status: ${getTranslatedStatusBadge(h.doctor_status)}</div>`;
  }

  // Resources
  const resGrid = document.getElementById('modal-resources-grid');
  const resIcons = {
    'icu beds': '🛏️',
    'oxygen support': '💨',
    'oxygen': '💨',
    'pharmacy': '💊',
    'laboratory': '🔬',
    'lab': '🔬',
    'x-ray': '🩻',
    'ct scan': '🖥️',
    'blood bank': '🩸',
    'emergency department': '🚨',
    'ed': '🚨'
  };

  if (h.resources && h.resources.length > 0) {
    resGrid.innerHTML = h.resources.map(r => {
      const icon = resIcons[(r.resource_type || '').toLowerCase().trim()] || '🏥';
      return `
        <div class="resource-item">
          <div class="resource-name">${icon} ${r.resource_type}</div>
          <div>${getTranslatedStatusBadge(r.status)}</div>
        </div>
      `;
    }).join('');
  } else {
    resGrid.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">Standard resources available.</div>';
  }

  // Crowd
  document.getElementById('modal-crowd-current').textContent = crowd.current_patients;
  document.getElementById('modal-crowd-waiting').textContent = crowd.waiting_patients;
  document.getElementById('modal-crowd-status-badge').innerHTML = getTranslatedStatusBadge(h.crowd_status);

  // Last Updated
  const updatedText = h.last_updated ? new Date(h.last_updated).toLocaleString('en-IN') : 'Recent';
  document.getElementById('modal-last-updated').textContent = updatedText;

  modal.classList.add('open');
}

// 8. Helper to Read First Card (Triggered by Voice Assistant)
window.readFirstHospitalCard = function() {
  const dataset = (currentView === 'recommended') ? rankedHospitalsData : allHospitalsData;
  if (dataset && dataset.length > 0) {
    readHospitalSummary(dataset[0]);
  } else {
    if (voiceAssistant) {
      voiceAssistant.speak('No hospitals available to read.');
    }
  }
};

// 9. React to Language Selector toggle in script.js
window.onLanguageChanged = function(lang) {
  renderHospitals();
};

// 10. Render Specialty badges for hospital card
function renderCardSpecialties(h) {
  if (!h.doctors || h.doctors.length === 0) return '';
  const specialties = [...new Set(h.doctors.map(d => d.specialty).filter(Boolean))];
  if (specialties.length === 0) return '';

  return `
    <div class="card-specialties-row">
      ${specialties.slice(0, 3).map(s => `<span class="badge badge-specialty">🩺 ${s}</span>`).join(' ')}
      ${specialties.length > 3 ? `<span style="font-size: 0.75rem; color: var(--text-muted);">+${specialties.length - 3}</span>` : ''}
    </div>
  `;
}

// 11. Floating SOS Emergency Modal & Simulated Workflow Handler
let activeEmergencyPollingTimer = null;

function showSOSModal() {
  const sosModal = document.getElementById('sos-modal');
  if (!sosModal) return;
  sosModal.style.display = 'flex';
  sosModal.classList.add('open');
  sosModal.setAttribute('aria-hidden', 'false');
}

function hideSOSModal() {
  const sosModal = document.getElementById('sos-modal');
  if (!sosModal) return;
  sosModal.classList.remove('open');
  sosModal.style.display = 'none';
  sosModal.setAttribute('aria-hidden', 'true');
}

function setupSOSModal() {
  const sosBtn = document.getElementById('btn-sos-floating');
  const sosModal = document.getElementById('sos-modal');
  const closeBtn = document.getElementById('btn-close-sos');
  const cancelModalBtn = document.getElementById('btn-sos-cancel-modal');
  const confirmBtn = document.getElementById('btn-sos-confirm');
  const cancelReqBtn = document.getElementById('btn-emergency-cancel');
  const viewActiveBtn = document.getElementById('btn-view-active-emergency');

  if (!sosBtn || !sosModal) return;

  // Check on load if active emergency exists in localStorage
  checkActiveEmergencyOnLoad();

  // Floating SOS Button click
  sosBtn.addEventListener('click', () => {
    const activeCode = localStorage.getItem('nexcare_active_emergency');
    if (activeCode) {
      // Direct to live tracking screen
      openEmergencyTracking(activeCode);
    } else {
      // Open confirmation screen
      openEmergencyConfirmation();
    }
  });

  // Top active emergency banner "View Tracking" click
  if (viewActiveBtn) {
    viewActiveBtn.addEventListener('click', () => {
      const activeCode = localStorage.getItem('nexcare_active_emergency');
      if (activeCode) {
        openEmergencyTracking(activeCode);
      }
    });
  }

  // Close modal button (X)
  if (closeBtn) {
    closeBtn.addEventListener('click', hideSOSModal);
  }

  // Cancel modal button (inside confirm view)
  if (cancelModalBtn) {
    cancelModalBtn.addEventListener('click', hideSOSModal);
  }

  // Click outside modal
  sosModal.addEventListener('click', (e) => {
    if (e.target === sosModal) {
      hideSOSModal();
    }
  });

  // Escape key closes modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sosModal.classList.contains('open')) {
      hideSOSModal();
    }
  });

  // Confirm emergency button click
  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      await initiateEmergencyRequest();
    });
  }

  // Cancel emergency request button (inside tracking view)
  if (cancelReqBtn) {
    cancelReqBtn.addEventListener('click', async () => {
      const activeCode = localStorage.getItem('nexcare_active_emergency');
      if (!activeCode) return;

      const confirmMsg = t(
        'sos_cancel_confirm',
        'Are you sure you want to cancel this emergency request? The reserved bed will be released immediately.'
      );
      if (confirm(confirmMsg)) {
        await cancelEmergencyRequest(activeCode);
      }
    });
  }
}

async function checkActiveEmergencyOnLoad() {
  const activeCode = localStorage.getItem('nexcare_active_emergency');
  if (!activeCode) return;

  try {
    const res = await fetchAPI(`/emergency/request/${encodeURIComponent(activeCode)}`);
    if (res.ok && res.data && res.data.success && res.data.data) {
      const req = res.data.data;
      if (req.status !== 'Cancelled' && req.status !== 'Patient Admitted') {
        showActiveEmergencyBanner(req);
      } else {
        localStorage.removeItem('nexcare_active_emergency');
        hideActiveEmergencyBanner();
      }
    } else {
      localStorage.removeItem('nexcare_active_emergency');
      hideActiveEmergencyBanner();
    }
  } catch (err) {
    console.error('Error verifying active emergency:', err);
  }
}

function openEmergencyConfirmation() {
  const viewConfirm = document.getElementById('sos-view-confirm');
  const viewFinding = document.getElementById('sos-view-finding');
  const viewTracking = document.getElementById('sos-view-tracking');
  const locPill = document.getElementById('sos-detected-loc-text');

  if (viewConfirm) viewConfirm.style.display = 'block';
  if (viewFinding) viewFinding.style.display = 'none';
  if (viewTracking) viewTracking.style.display = 'none';

  // Update detected location text with solid fallbacks
  const stateSelect = document.getElementById('patient-state');
  const citySelect = document.getElementById('patient-city');
  const state = (stateSelect && stateSelect.value) ? stateSelect.value : 'Tamil Nadu';
  const city = (citySelect && citySelect.value) ? citySelect.value : (currentPatientLocality || 'Chennai - Adyar');

  if (locPill) {
    locPill.textContent = `${state} • ${city}`;
  }

  populateSOSNearestHospitals();
  showSOSModal();
}

async function openEmergencyTracking(requestCode) {
  const viewConfirm = document.getElementById('sos-view-confirm');
  const viewFinding = document.getElementById('sos-view-finding');
  const viewTracking = document.getElementById('sos-view-tracking');

  if (viewConfirm) viewConfirm.style.display = 'none';
  if (viewFinding) viewFinding.style.display = 'none';
  if (viewTracking) viewTracking.style.display = 'block';

  showSOSModal();
  await pollEmergencyStatus(requestCode);

  // Start polling interval every 4 seconds while modal is open
  if (activeEmergencyPollingTimer) clearInterval(activeEmergencyPollingTimer);
  activeEmergencyPollingTimer = setInterval(async () => {
    const code = localStorage.getItem('nexcare_active_emergency');
    const sosModal = document.getElementById('sos-modal');
    if (code && sosModal && sosModal.classList.contains('open')) {
      await pollEmergencyStatus(code);
    } else if (!code) {
      clearInterval(activeEmergencyPollingTimer);
    }
  }, 4000);
}

async function initiateEmergencyRequest() {
  const viewConfirm = document.getElementById('sos-view-confirm');
  const viewFinding = document.getElementById('sos-view-finding');
  const viewTracking = document.getElementById('sos-view-tracking');

  if (viewConfirm) viewConfirm.style.display = 'none';
  if (viewFinding) viewFinding.style.display = 'block';

  const stateSelect = document.getElementById('patient-state');
  const citySelect = document.getElementById('patient-city');
  const state = (stateSelect && stateSelect.value) ? stateSelect.value : 'Tamil Nadu';
  const patientLocality = (citySelect && citySelect.value) ? citySelect.value : (currentPatientLocality || 'Chennai - Adyar');

  const payload = {
    patient_locality: patientLocality,
    state: state,
    lat: currentCoordinates ? currentCoordinates.lat : null,
    lng: currentCoordinates ? currentCoordinates.lng : null
  };

  try {
    const res = await fetchAPI('/emergency/request', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res.ok && res.data && res.data.success && res.data.data) {
      const req = res.data.data;
      localStorage.setItem('nexcare_active_emergency', req.request_code);
      showActiveEmergencyBanner(req);
      renderTrackingView(req);

      if (viewFinding) viewFinding.style.display = 'none';
      if (viewTracking) viewTracking.style.display = 'block';

      // Refresh background hospital list to reflect updated bed counts!
      refreshData();

      // Start polling
      if (activeEmergencyPollingTimer) clearInterval(activeEmergencyPollingTimer);
      activeEmergencyPollingTimer = setInterval(async () => {
        const code = localStorage.getItem('nexcare_active_emergency');
        const sosModal = document.getElementById('sos-modal');
        if (code && sosModal && sosModal.classList.contains('open')) {
          await pollEmergencyStatus(code);
        } else if (!code) {
          clearInterval(activeEmergencyPollingTimer);
        }
      }, 4000);
    } else {
      const errorMsg = (res.data && (res.data.error || res.data.message)) || 'Unable to allocate emergency hospital at this time.';
      alert(errorMsg);
      if (viewFinding) viewFinding.style.display = 'none';
      if (viewConfirm) viewConfirm.style.display = 'block';
    }
  } catch (err) {
    console.error('Failed to dispatch emergency request:', err);
    alert('Connection error while contacting emergency dispatch service.');
    if (viewFinding) viewFinding.style.display = 'none';
    if (viewConfirm) viewConfirm.style.display = 'block';
  }
}

async function pollEmergencyStatus(requestCode) {
  try {
    const res = await fetchAPI(`/emergency/request/${encodeURIComponent(requestCode)}`);
    if (res.ok && res.data && res.data.success && res.data.data) {
      const req = res.data.data;
      renderTrackingView(req);

      if (req.status === 'Patient Admitted') {
        localStorage.removeItem('nexcare_active_emergency');
        hideActiveEmergencyBanner();
        if (activeEmergencyPollingTimer) clearInterval(activeEmergencyPollingTimer);
        refreshData();
      } else if (req.status === 'Cancelled') {
        localStorage.removeItem('nexcare_active_emergency');
        hideActiveEmergencyBanner();
        if (activeEmergencyPollingTimer) clearInterval(activeEmergencyPollingTimer);
        refreshData();
      }
    }
  } catch (err) {
    console.error('Polling error:', err);
  }
}

function renderTrackingView(req) {
  const codeEl = document.getElementById('sos-track-code');
  const hospEl = document.getElementById('sos-track-hospital');
  const ambEl = document.getElementById('sos-track-ambulance');
  const driverEl = document.getElementById('sos-track-driver');
  const etaEl = document.getElementById('sos-track-eta');
  const statusPill = document.getElementById('sos-track-status-pill');
  const cancelBtn = document.getElementById('btn-emergency-cancel');

  if (codeEl) codeEl.textContent = req.request_code;
  if (hospEl) hospEl.textContent = `${req.hospital_name} (${req.hospital_locality})`;
  if (ambEl) ambEl.textContent = req.ambulance_code || 'Assigned';
  if (driverEl) driverEl.textContent = `${req.driver_name || 'Pilot'} • ${req.driver_contact || '+91 98000 00000'}`;
  if (etaEl) etaEl.textContent = req.status === 'Arrived' ? 'Arrived at Facility' : (req.status === 'Patient Admitted' ? 'Admitted' : `~${req.estimated_eta_mins || 12} mins`);
  if (statusPill) statusPill.textContent = req.status;

  // Update Timeline Steps
  const steps = ['assigned', 'enroute', 'arrived', 'admitted'];
  const statusMap = {
    'Pending': 0,
    'Ambulance Assigned': 0,
    'En Route': 1,
    'Arrived': 2,
    'Patient Admitted': 3
  };
  const activeIdx = statusMap[req.status] !== undefined ? statusMap[req.status] : 0;

  steps.forEach((s, idx) => {
    const el = document.getElementById(`step-${s}`);
    if (!el) return;
    el.classList.remove('completed', 'current');
    if (idx < activeIdx) {
      el.classList.add('completed');
    } else if (idx === activeIdx) {
      el.classList.add('current');
    }
  });

  if (cancelBtn) {
    if (req.status === 'Patient Admitted' || req.status === 'Cancelled') {
      cancelBtn.style.display = 'none';
    } else {
      cancelBtn.style.display = 'inline-block';
    }
  }
}

async function cancelEmergencyRequest(requestCode) {
  try {
    const res = await fetchAPI(`/emergency/request/${encodeURIComponent(requestCode)}/cancel`, {
      method: 'PUT',
      body: JSON.stringify({ staff_id: 'patient-ui' })
    });
    if (res.ok && res.data && res.data.success) {
      localStorage.removeItem('nexcare_active_emergency');
      hideActiveEmergencyBanner();
      if (activeEmergencyPollingTimer) clearInterval(activeEmergencyPollingTimer);
      alert('Emergency request cancelled. The blocked bed has been released back into availability.');
      hideSOSModal();
      refreshData();
    } else {
      alert((res.data && (res.data.error || res.data.message)) || 'Failed to cancel emergency request.');
    }
  } catch (err) {
    console.error('Failed to cancel emergency:', err);
    alert('Connection error while cancelling emergency request.');
  }
}

function showActiveEmergencyBanner(req) {
  const banner = document.getElementById('patient-active-emergency-banner');
  const codePill = document.getElementById('active-emergency-code');
  if (banner) {
    banner.style.display = 'flex';
    if (codePill) codePill.textContent = req.request_code;
  }
}

function hideActiveEmergencyBanner() {
  const banner = document.getElementById('patient-active-emergency-banner');
  if (banner) {
    banner.style.display = 'none';
  }
}

function populateSOSNearestHospitals() {
  const container = document.getElementById('sos-nearest-list');
  if (!container) return;

  let list = [...allHospitalsData];
  list.sort((a, b) => (a.distance_km || 999) - (b.distance_km || 999));
  const top3 = list.slice(0, 3);

  if (top3.length === 0) {
    container.innerHTML = `
      <p style="font-size: 0.88rem; color: var(--text-muted); margin: 0.5rem 0;">
        ${t('sos_no_hospitals', 'Dial 108 immediately for urgent ambulance and emergency dispatch.')}
      </p>
    `;
    return;
  }

  container.innerHTML = top3.map(h => {
    const dist = h.distance_km != null ? `${h.distance_km} km` : 'Near';
    const phone = h.contact_number || '108';
    const cleanPhone = phone.replace(/[^0-9+]/g, '');
    return `
      <div class="sos-hospital-item">
        <div>
          <div style="font-weight: 700; font-size: 0.92rem; color: var(--text-primary);">${h.name}</div>
          <div style="font-size: 0.78rem; color: var(--text-muted);">📍 ${h.locality} • ${dist}</div>
        </div>
        <a href="tel:${cleanPhone}" class="btn btn-sm btn-danger" style="display: inline-flex; align-items: center; gap: 0.35rem; font-weight: 700; padding: 0.4rem 0.75rem;">
          📞 ${phone}
        </a>
      </div>
    `;
  }).join('');
}
