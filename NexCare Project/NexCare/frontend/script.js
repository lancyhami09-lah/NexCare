/**
 * NexCare Universal JavaScript Module
 * Multi-Language i18n Engine (6 Languages: en, ta, te, kn, hi, ml),
 * Web Speech API Voice Assistant & Accessibility Management
 */

const API_BASE = '/api';
const SUPPORTED_LANGS = ['en', 'ta', 'te', 'kn', 'hi', 'ml'];
const SPEECH_LANG_MAP = {
  'en': 'en-IN',
  'ta': 'ta-IN',
  'te': 'te-IN',
  'kn': 'kn-IN',
  'hi': 'hi-IN',
  'ml': 'ml-IN'
};

// Cached translation dictionaries
const loadedTranslations = {};
let currentLanguage = localStorage.getItem('nexcare_lang') || 'en';
if (!SUPPORTED_LANGS.includes(currentLanguage)) {
  currentLanguage = 'en';
}

let isLargeText = localStorage.getItem('nexcare_large_text') === 'true';

// Locality voice recognition keyword mapping
const LOCALITY_SYNONYMS = {
  'adyar': 'Adyar',
  'adayar': 'Adyar',
  'அடையாறு': 'Adyar',
  'అడయార్': 'Adyar',
  'ಅಡ್ಯಾರ್': 'Adyar',
  'अडयार': 'Adyar',
  'അഡയാർ': 'Adyar',

  'anna nagar': 'Anna Nagar',
  'annanagar': 'Anna Nagar',
  'அண்ணா நகர்': 'Anna Nagar',
  'అన్నా నగర్': 'Anna Nagar',
  'ಅಣ್ಣಾ ನಗರ': 'Anna Nagar',
  'अन्ना नगर': 'Anna Nagar',
  'അണ്ണാ നഗർ': 'Anna Nagar',

  'egmore': 'Egmore',
  'எழும்பூர்': 'Egmore',
  'ఎగ్మోర్': 'Egmore',
  'ಎಗ್ಮೋರ್': 'Egmore',
  'एग्मोर': 'Egmore',
  'എഗ്മോർ': 'Egmore',

  'guindy': 'Guindy',
  'கிண்டி': 'Guindy',
  'గిండి': 'Guindy',
  'ಗಿಂಡಿ': 'Guindy',
  'गिंडी': 'Guindy',
  'ഗിണ്ടി': 'Guindy',

  'manapakkam': 'Manapakkam',
  'மணப்பாக்கம்': 'Manapakkam',
  'మణపాక్కం': 'Manapakkam',
  'ಮಣಪಾಕ್ಕಂ': 'Manapakkam',
  'मनापक्कम': 'Manapakkam',
  'മണപ്പാക്കം': 'Manapakkam',

  'mogappair': 'Mogappair',
  'முகப்பேர்': 'Mogappair',
  'మొగప్పైర్': 'Mogappair',
  'ಮೊಗಪ್ಪೈರ್': 'Mogappair',
  'मोगप्पेयर': 'Mogappair',
  'മൊഗപ്പെയർ': 'Mogappair',

  'perambur': 'Perambur',
  'பெரம்பூர்': 'Perambur',
  'పెరంబూర్': 'Perambur',
  'ಪೆರಂಬೂರ್': 'Perambur',
  'पेरंबूर': 'Perambur',
  'പെരമ്പൂർ': 'Perambur',

  'porur': 'Porur',
  'போரூர்': 'Porur',
  'పోరూర్': 'Porur',
  'ಪೋರೂರ್': 'Porur',
  'पोरूर': 'Porur',
  'പോരൂർ': 'Porur',

  'sholinganallur': 'Sholinganallur',
  'சோழிங்கநல்லூர்': 'Sholinganallur',
  'షోలింగనల్లూర్': 'Sholinganallur',
  'ಶೋಲಿಂಗನಲ್ಲೂರ್': 'Sholinganallur',
  'शोलिंगनल्लूर': 'Sholinganallur',
  'ഷോളിംഗനല്ലൂർ': 'Sholinganallur',

  't. nagar': 'T. Nagar',
  't nagar': 'T. Nagar',
  'தி நகர்': 'T. Nagar',
  'టి నగర్': 'T. Nagar',
  'ಟಿ ನಗರ': 'T. Nagar',
  'टी नगर': 'T. Nagar',
  'ടി നഗർ': 'T. Nagar',

  'tambaram': 'Tambaram',
  'தாம்பரம்': 'Tambaram',
  'తాంబరం': 'Tambaram',
  'ತಾಂಬರಂ': 'Tambaram',
  'तांबरम': 'Tambaram',
  'താംബരം': 'Tambaram',

  'velachery': 'Velachery',
  'வேளச்சேரி': 'Velachery',
  'వేలచేరి': 'Velachery',
  'ವೇಲಚೇರಿ': 'Velachery',
  'वेलाचेरी': 'Velachery',
  'വേളച്ചേരി': 'Velachery'
};

// ====================================================================
// 1. MULTI-LANGUAGE I18N ENGINE
// ====================================================================

async function loadLanguage(lang) {
  if (!SUPPORTED_LANGS.includes(lang)) lang = 'en';

  if (!loadedTranslations[lang]) {
    try {
      const res = await fetch(`/i18n/${lang}.json?v=${Date.now()}`);
      if (res.ok) {
        loadedTranslations[lang] = await res.json();
      } else {
        // Fallback to English if file fetch fails
        if (lang !== 'en' && !loadedTranslations['en']) {
          const fb = await fetch('/i18n/en.json');
          loadedTranslations['en'] = await fb.json();
        }
        loadedTranslations[lang] = loadedTranslations['en'] || {};
      }
    } catch (e) {
      console.warn(`Failed to fetch i18n file for ${lang}`, e);
      loadedTranslations[lang] = loadedTranslations['en'] || {};
    }
  }

  currentLanguage = lang;
  localStorage.setItem('nexcare_lang', lang);
  document.documentElement.lang = lang;

  applyTranslations(loadedTranslations[lang]);

  // Update language selector dropdowns
  const langSelect = document.getElementById('lang-select');
  if (langSelect) {
    langSelect.value = lang;
  }

  // Keep Voice Assistant language immediately in sync and cancel previous language speech
  if (typeof voiceAssistant !== 'undefined' && voiceAssistant) {
    if (voiceAssistant.isSpeaking && voiceAssistant.synth) {
      voiceAssistant.synth.cancel();
      voiceAssistant.isSpeaking = false;
    }
    if (voiceAssistant.recognition) {
      voiceAssistant.recognition.lang = SPEECH_LANG_MAP[lang] || 'en-IN';
    }
  }

  // Notify any active page controller (e.g. patient.js)
  if (typeof window.onLanguageChanged === 'function') {
    window.onLanguageChanged(lang);
  }
}

function t(key, fallback = '') {
  const dict = loadedTranslations[currentLanguage] || loadedTranslations['en'] || {};
  return dict[key] || fallback || key;
}

function applyTranslations(dict) {
  if (!dict) return;

  // 1. Standard text nodes
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) {
      el.textContent = dict[key];
    }
  });

  // 2. HTML text nodes (for text with icons or bold tags)
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    if (dict[key]) {
      el.innerHTML = dict[key];
    }
  });

  // 3. Placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (dict[key]) {
      el.placeholder = dict[key];
    }
  });

  // 4. ARIA and Titles
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    if (dict[key]) {
      el.title = dict[key];
    }
  });

  // Update text size toggle button label
  const btn = document.getElementById('toggle-text-size');
  if (btn) {
    btn.textContent = isLargeText ? t('text_standard_btn', '🔤 A- Standard Text') : t('text_large_btn', '🔤 A+ Large Text');
  }
}

// Translate Status Words paired with text
function getTranslatedStatusBadge(status) {
  const s = (status || '').toLowerCase();
  if (s === 'available') {
    return `<span class="badge badge-green">🟢 ${t('status_available', 'Available')}</span>`;
  }
  if (s === 'low') {
    return `<span class="badge badge-green">🟢 ${t('crowd_low', 'Low Crowd')}</span>`;
  }
  if (s === 'limited') {
    return `<span class="badge badge-yellow">🟡 ${t('status_limited', 'Limited')}</span>`;
  }
  if (s === 'moderate') {
    return `<span class="badge badge-yellow">🟡 ${t('crowd_moderate', 'Moderate Crowd')}</span>`;
  }
  if (s === 'high') {
    return `<span class="badge badge-red">🔴 ${t('crowd_high', 'High Crowd')}</span>`;
  }
  return `<span class="badge badge-red">🔴 ${t('status_unavailable', 'Unavailable')}</span>`;
}

// ====================================================================
// 2. WEB SPEECH API VOICE ASSISTANT
// ====================================================================

class NexCareVoiceAssistant {
  constructor() {
    this.recognition = null;
    this.isListening = false;
    this.isSpeaking = false;
    this.synth = window.speechSynthesis || null;
    this.hasSpeechSupport = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    this.initRecognition();
    this.createToastElement();
  }

  initRecognition() {
    if (!this.hasSpeechSupport) {
      console.warn('SpeechRecognition not supported in this browser.');
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = false;
    this.recognition.maxAlternatives = 3;

    this.recognition.onstart = () => {
      this.isListening = true;
      this.updateUIState();
      this.showToast(t('voice_status_listening', '🎙️ Listening... Speak locality or command'), 'listening');
    };

    this.recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript.trim();
      console.log('Voice Recognized:', transcript);
      this.showToast(`🗣️ "${transcript}"`, 'processing');
      this.handleVoiceCommand(transcript);
    };

    this.recognition.onerror = (event) => {
      console.warn('SpeechRecognition Error:', event.error);
      this.isListening = false;
      this.updateUIState();
      if (event.error === 'not-allowed') {
        this.showToast('Microphone access denied. Please allow microphone permission.', 'error', 4000);
      } else if (event.error === 'no-speech') {
        this.showToast('No speech detected. Please try again.', 'idle', 3000);
      } else {
        this.showToast(`Voice recognition: ${event.error}`, 'idle', 3000);
      }
    };

    this.recognition.onend = () => {
      this.isListening = false;
      this.updateUIState();
    };
  }

  createToastElement() {
    if (document.getElementById('voice-toast')) return;
    const toast = document.createElement('div');
    toast.id = 'voice-toast';
    toast.className = 'voice-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.innerHTML = `
      <div class="voice-toast-icon">🎙️</div>
      <div class="voice-toast-text" id="voice-toast-text">Voice Assistant Active</div>
      <button class="voice-toast-close" id="voice-toast-close" aria-label="Close">&times;</button>
    `;
    document.body.appendChild(toast);

    document.getElementById('voice-toast-close').addEventListener('click', () => {
      toast.classList.remove('show');
    });
  }

  showToast(message, state = 'idle', duration = 4000) {
    const toast = document.getElementById('voice-toast');
    const text = document.getElementById('voice-toast-text');
    if (!toast || !text) return;

    text.textContent = message;
    toast.classList.add('show');

    if (state === 'speaking') {
      toast.classList.add('speaking');
    } else {
      toast.classList.remove('speaking');
    }

    if (this._toastTimer) clearTimeout(this._toastTimer);
    if (duration > 0) {
      this._toastTimer = setTimeout(() => {
        toast.classList.remove('show');
      }, duration);
    }
  }

  toggle() {
    if (!this.hasSpeechSupport) {
      alert(t('voice_not_supported', 'Speech recognition is not supported in this browser. You can still use all buttons.'));
      return;
    }
    if (this.isListening) {
      this.stopListening();
    } else {
      this.startListening();
    }
  }

  startListening() {
    if (!this.recognition) return;
    // Set speech recognition language matching interface language
    const langCode = SPEECH_LANG_MAP[currentLanguage] || 'en-IN';
    this.recognition.lang = langCode;

    try {
      this.recognition.start();
    } catch (e) {
      console.warn('SpeechRecognition start error:', e);
    }
  }

  stopListening() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
    }
    this.isListening = false;
    this.updateUIState();
  }

  stopAll() {
    // 1. Immediately cancel any active speech playback
    if (this.synth) {
      this.synth.cancel();
      this.isSpeaking = false;
    }
    // 2. Immediately abort active speech recognition listening
    if (this.recognition && this.isListening) {
      try {
        this.recognition.abort();
      } catch (e) {
        console.warn('SpeechRecognition abort error:', e);
      }
      this.isListening = false;
    }
    // 3. Reset UI & Toast
    this.updateUIState();
    const toast = document.getElementById('voice-toast');
    if (toast) {
      toast.classList.remove('show');
      toast.classList.remove('speaking');
    }
    // 4. Reset read aloud buttons
    document.querySelectorAll('.btn-read-aloud.playing').forEach(btn => {
      btn.classList.remove('playing');
      btn.textContent = `🔊 ${t('btn_read_aloud', 'Read Aloud')}`;
    });
    this.showToast(t('voice_status_stopped', '⏹️ Voice stopped'), 'idle', 2000);
  }

  updateUIState() {
    const btn = document.getElementById('voice-assist-btn');
    if (btn) {
      if (this.isListening) {
        btn.classList.add('listening');
        btn.setAttribute('aria-pressed', 'true');
        btn.textContent = '🔴 Listening...';
      } else {
        btn.classList.remove('listening');
        btn.setAttribute('aria-pressed', 'false');
        btn.textContent = '🎙️ Voice';
      }
    }
  }

  handleVoiceCommand(rawTranscript) {
    const text = rawTranscript.toLowerCase().trim();

    // 1. Check for Locality names
    for (const [key, localityName] of Object.entries(LOCALITY_SYNONYMS)) {
      if (text.includes(key)) {
        this.selectLocality(localityName);
        return;
      }
    }

    // 2. Check for Announce Nearby Hospitals command
    if (
      text.includes('nearby') ||
      text.includes('tell me nearby') ||
      text.includes('announce') ||
      text.includes('hospital details') ||
      text.includes('அருகிலுள்ள') ||
      text.includes('மருத்துவமனை விவரங்கள்') ||
      text.includes('సమీప') ||
      text.includes('దగ్గరి') ||
      text.includes('ಹತ್ತಿರದ') ||
      text.includes('पास के') ||
      text.includes('नज़दीकी') ||
      text.includes('അടുത്തുള്ള') ||
      text.includes('സമീപത്തുള്ള') ||
      text.includes('ആശുപത്രി വിവരങ്ങൾ')
    ) {
      this.announceNearbyHospitals();
      return;
    }

    // 3. Check for Search command
    if (
      text.includes('search') ||
      text.includes('find') ||
      text.includes('show all') ||
      text.includes('all hospitals') ||
      text.includes('தேடு') ||
      text.includes('வெతుకు') ||
      text.includes('ಹುಡುಕು') ||
      text.includes('खोज') ||
      text.includes('തിരയുക') ||
      text.includes('കണ്ടെത്തുക')
    ) {
      this.triggerSearch();
      return;
    }

    // 4. Check for Recommendations command
    if (
      text.includes('recommend') ||
      text.includes('best') ||
      text.includes('smart') ||
      text.includes('top') ||
      text.includes('பரிந்துரை') ||
      text.includes('సిఫార్సు') ||
      text.includes('ಶಿಫಾರಸು') ||
      text.includes('अनुशंसा') ||
      text.includes('सिफारिश') ||
      text.includes('ശുപാർശ') ||
      text.includes('മികച്ച')
    ) {
      this.triggerRecommendations();
      return;
    }

    // 5. Check for Read aloud command
    if (
      text.includes('read') ||
      text.includes('speak') ||
      text.includes('வாசி') ||
      text.includes('చదువు') ||
      text.includes('ಓದು') ||
      text.includes('पढ़ो') ||
      text.includes('വായിക്കുക') ||
      text.includes('പറയുക')
    ) {
      this.readTopHospital();
      return;
    }

    // Unrecognized command
    this.speak(`Heard: ${rawTranscript}. You can say a locality like Adyar, or say Search, Recommend, or Tell me nearby hospitals.`);
    this.showToast(`❓ Unrecognized. Try saying "Adyar", "Search", or "Tell me nearby hospitals"`, 'idle', 4000);
  }

  selectLocality(localityName) {
    this.showToast(`📍 Selected: ${localityName}`, 'idle', 3500);

    // Update patient portal selector if on patient.html
    const patientLocSelect = document.getElementById('patient-locality');
    if (patientLocSelect) {
      patientLocSelect.value = localityName;
      patientLocSelect.dispatchEvent(new Event('change'));
    }

    // Update home quick selector if on index.html
    const quickLocSelect = document.getElementById('quick-locality');
    if (quickLocSelect) {
      quickLocSelect.value = localityName;
    }

    this.speak(`${t('voice_selected_area', 'Selected locality:')} ${localityName}`);
  }

  triggerSearch() {
    this.showToast('🔍 Searching hospitals...', 'idle', 3000);
    this.speak(t('voice_searching', 'Searching all hospitals in Chennai.'));

    const tabAll = document.getElementById('tab-all');
    if (tabAll) {
      tabAll.click();
    } else {
      const btnQuickSearch = document.getElementById('btn-quick-search');
      if (btnQuickSearch) btnQuickSearch.click();
    }
  }

  triggerRecommendations() {
    this.showToast('✨ Showing top recommendations...', 'idle', 3000);
    this.speak(t('voice_showing_rec', 'Showing top recommended hospitals.'));

    const tabRec = document.getElementById('tab-recommended');
    if (tabRec) {
      tabRec.click();
    } else {
      const btnQuickRec = document.getElementById('btn-quick-recommend');
      if (btnQuickRec) btnQuickRec.click();
    }
  }

  readTopHospital() {
    if (typeof window.readFirstHospitalCard === 'function') {
      window.readFirstHospitalCard();
    } else {
      this.speak('Please open the patient search to hear hospital summaries.');
    }
  }

  announceNearbyHospitals(hospitalsList = null) {
    let list = hospitalsList;
    if (!list || !Array.isArray(list) || list.length === 0) {
      if (window.currentHospitals && window.currentHospitals.length > 0) {
        list = window.currentHospitals;
      } else if (window.recommendedHospitals && window.recommendedHospitals.length > 0) {
        list = window.recommendedHospitals;
      }
    }

    if (!list || list.length === 0) {
      this.showToast('📢 Fetching nearby hospitals to announce...', 'processing', 3000);
      fetch(`${API_BASE}/hospitals/recommendations?limit=3`)
        .then(res => res.json())
        .then(data => {
          if (data && data.data && data.data.length > 0) {
            this.announceNearbyHospitals(data.data);
          } else {
            this.speak(t('voice_no_hospitals', 'No hospital information available to announce. Please select your location first.'));
          }
        })
        .catch(() => {
          this.speak(t('voice_no_hospitals', 'No hospital information available to announce.'));
        });
      return;
    }

    const topHospitals = list.slice(0, 3);
    const intro = t('voice_announce_intro', 'Here are the top nearby hospital details for your location:');
    this.showToast(t('voice_announcing_toast', '📢 Announcing nearby hospital details...'), 'speaking', 8000);

    const summaries = topHospitals.map((h, idx) => {
      const beds = h.beds ? h.beds.available : 'several';
      const dist = h.distance_km != null ? `${h.distance_km} kilometers away` : '';
      const doctor = h.doctor_status || 'Available';
      const crowd = h.crowd_status || 'Low';
      return `Hospital ${idx + 1}: ${h.name}, located in ${h.locality}, ${dist}. Beds available: ${beds}. Doctors: ${doctor}. Crowd level: ${crowd}.`;
    });

    const fullAnnouncement = `${intro} ${summaries.join(' ')}`;
    this.speak(fullAnnouncement);
  }

  speak(text, onComplete = null) {
    if (!this.synth) return;

    // Cancel ongoing speech to avoid overlapping
    this.synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    const targetLang = SPEECH_LANG_MAP[currentLanguage] || 'en-IN';
    utterance.lang = targetLang;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Select suitable voice if available
    const voices = this.synth.getVoices();
    let voice = voices.find(v => v.lang === targetLang || v.lang.startsWith(targetLang.split('-')[0]));
    if (!voice && currentLanguage !== 'en') {
      // Fallback voice to English
      voice = voices.find(v => v.lang.startsWith('en'));
      if (this.isListening) {
        this.showToast(t('voice_lang_fallback', 'Voice active in English.'), 'idle', 3000);
      }
    }
    if (voice) {
      utterance.voice = voice;
    }

    utterance.onstart = () => {
      this.isSpeaking = true;
      this.showToast(`🔊 Speaking: ${text.substring(0, 45)}...`, 'speaking', 0);
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      const toast = document.getElementById('voice-toast');
      if (toast && toast.classList.contains('speaking')) {
        toast.classList.remove('show');
      }
      if (typeof onComplete === 'function') onComplete();
    };

    utterance.onerror = (e) => {
      console.warn('SpeechSynthesis Error:', e);
      this.isSpeaking = false;
      const toast = document.getElementById('voice-toast');
      if (toast) toast.classList.remove('show');
    };

    this.synth.speak(utterance);
  }
}

// Global Voice Assistant instance
let voiceAssistant = null;

// ====================================================================
// 3. READ ALOUD HELPER FOR HOSPITAL CARDS
// ====================================================================

function readHospitalSummary(h, btnElement = null) {
  if (!voiceAssistant) return;

  const beds = h.beds || { total: 100, available: 50 };
  const distText = h.distance_km != null ? `${h.distance_km} kilometers away` : '';
  const doctorStat = h.doctor_status || 'Available';
  const crowdStat = h.crowd_status || 'Low';

  // Construct readable summary sentence
  const speechText = `${h.name}, located in ${h.locality}, ${distText}. ${beds.available} beds currently available out of ${beds.total}. Doctors are ${doctorStat}. Crowd status is ${crowdStat}.`;

  if (btnElement) {
    btnElement.classList.add('playing');
    btnElement.textContent = '🔊 Reading...';
  }

  voiceAssistant.speak(speechText, () => {
    if (btnElement) {
      btnElement.classList.remove('playing');
      btnElement.textContent = `🔊 ${t('btn_read_aloud', 'Read Aloud')}`;
    }
  });
}

// ====================================================================
// 4. ACCESSIBILITY & INITIALIZATION
// ====================================================================

function applyTextSize() {
  if (isLargeText) {
    document.body.classList.add('large-text');
  } else {
    document.body.classList.remove('large-text');
  }
  const btn = document.getElementById('toggle-text-size');
  if (btn) {
    btn.textContent = isLargeText ? t('text_standard_btn', '🔤 A- Standard Text') : t('text_large_btn', '🔤 A+ Large Text');
    btn.setAttribute('aria-pressed', isLargeText);
  }
}

// Reusable Fetch Wrapper
async function fetchAPI(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      },
      ...options
    });
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    console.error('API Error:', err);
    return { ok: false, status: 0, data: { error: 'Network error connecting to NexCare server.' } };
  }
}

// Initial Bootstrapping
document.addEventListener('DOMContentLoaded', async () => {
  // 1. Initialize Voice Assistant
  voiceAssistant = new NexCareVoiceAssistant();

  // 2. Wire Voice button
  const voiceBtn = document.getElementById('voice-assist-btn');
  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      voiceAssistant.toggle();
    });
  }

  // 2b. Wire Voice Stop button
  const voiceStopBtn = document.getElementById('voice-stop-btn');
  if (voiceStopBtn) {
    voiceStopBtn.addEventListener('click', () => {
      if (voiceAssistant) {
        voiceAssistant.stopAll();
      }
    });
  }

  // 3. Setup Large Text Toggle button
  const textToggleBtn = document.getElementById('toggle-text-size');
  if (textToggleBtn) {
    textToggleBtn.addEventListener('click', () => {
      isLargeText = !isLargeText;
      localStorage.setItem('nexcare_large_text', isLargeText);
      applyTextSize();
    });
  }

  // 4. Setup 5-Language Selector
  const langSelect = document.getElementById('lang-select');
  if (langSelect) {
    langSelect.value = currentLanguage;
    langSelect.addEventListener('change', async (e) => {
      await loadLanguage(e.target.value);
    });
  }

  // 5. Load active language dictionary and apply
  await loadLanguage(currentLanguage);
  applyTextSize();
});
