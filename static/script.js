/**
 * ═══════════════════════════════════════════════════════════
 *  Didi — Hinglish Tutor Bot  v6  (Voice-Only Edition)
 * ═══════════════════════════════════════════════════════════
 *
 *  Full voice flow:
 *  ┌──────────────────────────────────────────────────────┐
 *  │  [Page loads]  Tap overlay shown                     │
 *  │       ↓  User taps/clicks anywhere                   │
 *  │  Chrome audio autoplay UNLOCKED                      │
 *  │       ↓                                              │
 *  │  PASSIVE MODE — waiting for "shuru karo"             │
 *  │       ↓  Student says "shuru karo"                   │
 *  │  IDENTIFYING — "apna student ID boliye (1–20)"       │
 *  │       ↓  Student says a number                       │
 *  │    New student → REGISTERING → ask name              │
 *  │    Old student → ACTIVE (history loaded)             │
 *  │       ↓                                              │
 *  │  ACTIVE MODE — full conversation loop                │
 *  │    sub-modes: quiz / story / pronunciation           │
 *  │    summary trigger → AI summary → back to ACTIVE     │
 *  │       ↓  "Band karo"                                 │
 *  │  session saved → PASSIVE MODE                        │
 *  └──────────────────────────────────────────────────────┘
 */

'use strict';

/* ══════════════════════════════════════════
   MODE CONSTANTS
══════════════════════════════════════════ */
const Mode = {
  LOCKED      : 'locked',      // before tap overlay dismissed
  PASSIVE     : 'passive',     // waiting for "shuru karo"
  IDENTIFYING : 'identifying', // waiting for student ID number
  REGISTERING : 'registering', // new student — waiting for name
  ACTIVE      : 'active',      // full conversation
};

/* Sub-modes within ACTIVE (null = normal chat) */
const SubMode = {
  NONE         : null,
  QUIZ         : 'quiz',
  STORY        : 'story',
  PRONUNCIATION: 'pronunciation',
};

/* ══════════════════════════════════════════
   STATE
══════════════════════════════════════════ */
const State = {
  mode        : Mode.LOCKED,
  isListening : false,
  isSpeaking  : false,
  isLoading   : false,
  isProcessing: false,

  lastBotText : '',
  lastBotLang : 'hinglish',
  slowMode    : false,

  history         : [],
  fullHistory     : [],   // uncompressed complete log — never trimmed
  sentencesSpoken : 0,
  wordsLearned    : 0,
  sessionSeconds  : 0,

  silenceTimer    : null,

  // Student account
  studentId         : null,
  studentName       : null,
  lastSessionHistory: [],
  _pendingId        : null,

  // Progress (from SQLite)
  streak     : 0,
  totalWords : 0,
  weekQuizPct: 0,

  // ── Sub-mode: Quiz ─────────────────────────
  subMode       : SubMode.NONE,
  quizSession   : { questions: [], index: 0, correct: 0, total: 0 },

  // ── Sub-mode: Story ────────────────────────
  storySession  : { story: null, phase: 'none', qIdx: 0, correct: 0 },

  // ── Sub-mode: Pronunciation ────────────────
  pronSession   : { word: null, syllables: '', count: 0, correct: 0 },

  // ── Confidence scoring ─────────────────────
  confidence    : { silenceCount: 0, retryCount: 0, responseTimes: [], questionStartedAt: 0 },

  // ── Agentic session state ───────────────────
  sessionPlan   : [],     // 5-step plan from PlannerAgent
  planStepIdx   : 0,      // current step index
  memoryNote    : '',     // compressed memory from MemoryAgent
  isCompressing : false,  // lock to prevent concurrent compressions
};

/* ══════════════════════════════════════════
   ELEMENT CACHE
══════════════════════════════════════════ */
const El = {
  overlay      : document.getElementById('tap-overlay'),
  chatLog      : document.getElementById('chat-log'),
  liveTx       : document.getElementById('live-tx'),
  statusWrap   : document.querySelector('.status-wrap'),
  statusRing   : document.getElementById('status-ring'),
  statusEmoji  : document.getElementById('status-emoji'),
  statusMsg    : document.getElementById('status-msg'),
  srLive       : document.getElementById('sr-live'),
  ttsLabel     : document.getElementById('tts-label'),
  ttsDot       : document.getElementById('tts-dot'),
  statSentences: document.getElementById('stat-sentences'),
  statWords    : document.getElementById('stat-words'),
  statMins     : document.getElementById('stat-mins'),
  // New elements (added in index.html)
  statStreak     : document.getElementById('stat-streak'),
  statQuizPct    : document.getElementById('stat-quiz-pct'),
  statTotalWords : document.getElementById('stat-total-words'),
  dbProgress     : document.getElementById('db-progress'),
  modeIndicator  : document.getElementById('mode-indicator'),
  modeLabel      : document.getElementById('mode-label'),
};

/* ══════════════════════════════════════════
   TAP OVERLAY — audio unlock
══════════════════════════════════════════ */
const SILENT_WAV =
  'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwA' +
  'AIhYAQACABAAZGF0YQAAAAA=';

let _audioUnlocked = false;

async function handleOverlayTap(e) {
  if (e) { e.preventDefault(); e.stopPropagation(); }
  El.overlay.removeEventListener('click',    handleOverlayTap);
  El.overlay.removeEventListener('touchend', handleOverlayTap);
  document.removeEventListener('keydown',    _overlayKeyHandler);

  if (!_audioUnlocked) {
    try {
      const silence = new Audio(SILENT_WAV);
      silence.volume = 0.001;
      await silence.play();
      silence.pause();
      _audioUnlocked = true;
    } catch (_) {}
  }

  El.overlay.classList.add('fade-out');
  setTimeout(() => {
    El.overlay.hidden = true;
    El.overlay.setAttribute('aria-hidden', 'true');
  }, 520);

  enterPassiveMode();
}

function _overlayKeyHandler(e) {
  if (e.key === 'Enter' || e.key === ' ') handleOverlayTap(e);
}

El.overlay.addEventListener('click',    handleOverlayTap);
El.overlay.addEventListener('touchend', handleOverlayTap, { passive: false });
document.addEventListener('keydown',    _overlayKeyHandler);


/* ══════════════════════════════════════════
   GOOGLE TTS  (gTTS → Flask /tts → MP3)
══════════════════════════════════════════ */
let _currentAudio = null;

function _ttsUrl(text, lang) {
  return `/tts?text=${encodeURIComponent(text)}&lang=${encodeURIComponent(lang)}&slow=${State.slowMode}`;
}

function speak(text, lang = 'hinglish', onDone) {
  if (!text) { if (onDone) onDone(); return; }
  _clearSilenceTimer();
  _stopAudio();
  abortRecognition();

  State.isSpeaking = true;
  State.isLoading  = true;
  document.body.classList.add('tts-loading');
  document.body.classList.remove('tts-done');
  setStatus('loading', '⏳', 'Bol rahi hoon…');

  const audio = new Audio(_ttsUrl(text, lang));
  _currentAudio = audio;
  audio.preload = 'auto';

  audio.addEventListener('canplaythrough', () => {
    State.isLoading = false;
    document.body.classList.remove('tts-loading');
    document.body.classList.add('tts-done');
    setStatus('speaking', '🔊', 'Bol rahi hoon…');
  }, { once: true });

  audio.addEventListener('ended', () => {
    _onAudioFinished();
    if (onDone) onDone();
    else _restartMicAfterSpeaking();
  }, { once: true });

  audio.addEventListener('error', () => {
    _onAudioFinished();
    _fallbackSpeak(text, lang, onDone);
  }, { once: true });

  audio.play().catch(() => {
    _onAudioFinished();
    _fallbackSpeak(text, lang, onDone);
  });
}

function _onAudioFinished() {
  State.isSpeaking = false;
  State.isLoading  = false;
  _currentAudio    = null;
  document.body.classList.remove('tts-loading', 'tts-done');
}

function _stopAudio() {
  if (_currentAudio) {
    try { _currentAudio.pause(); _currentAudio.src = ''; } catch (_) {}
    _currentAudio = null;
  }
  State.isSpeaking = false;
  State.isLoading  = false;
  document.body.classList.remove('tts-loading', 'tts-done');
}

function _restartMicAfterSpeaking() {
  if (State.mode !== Mode.LOCKED) {
    scheduleRestart(380);
    if (State.mode === Mode.ACTIVE) _startSilenceTimer();
  }
}

/* ── Silence timer ──────────────────────── */
const SILENCE_DELAY_MS = 9000;
const NUDGE_PHRASES = [
  "Haan beta, main sun rahi hoon! Dariye mat. Wapas boliye mere saath!",
  "Koi baat nahi beta. Dheere dheere boliye, main intezaar kar rahi hoon!",
  "Main yahaan hoon beta! Galti hogi toh bhi theek hai. Ek baar try karo!",
  "Suno beta — aap bahut achhe ho. Sirf ek baar try karo, main hoon na!",
  "Beta, ek chhota sa try karo. Boliye: I am learning English!",
];

function _startSilenceTimer() {
  _clearSilenceTimer();
  State.silenceTimer = setTimeout(() => {
    if (State.mode === Mode.ACTIVE && !State.isSpeaking &&
        !State.isProcessing && !State.isLoading) {
      State.confidence.silenceCount++;
      const nudge = NUDGE_PHRASES[Math.floor(Math.random() * NUDGE_PHRASES.length)];
      _botSay(nudge, 'hinglish');
    }
  }, SILENCE_DELAY_MS);
}

function _clearSilenceTimer() {
  if (State.silenceTimer) { clearTimeout(State.silenceTimer); State.silenceTimer = null; }
}

function _fallbackSpeak(text, lang, onDone) {
  State.isSpeaking = true;
  setStatus('speaking', '🔊', 'Bol rahi hoon (fallback)…');
  const synth = window.speechSynthesis;
  synth.cancel();
  const utt  = new SpeechSynthesisUtterance(text);
  utt.lang   = (lang === 'english') ? 'en-IN' : 'hi-IN';
  utt.rate   = State.slowMode ? 0.63 : 0.88;
  utt.pitch  = 1.06;
  utt.volume = 1.0;
  const voices = synth.getVoices();
  const pick   = voices.find(v => v.name === 'Google हिन्दी')
              || voices.find(v => v.lang === 'hi-IN')
              || voices.find(v => v.name.toLowerCase().includes('veena'))
              || voices.find(v => v.lang === 'en-IN') || null;
  if (pick) utt.voice = pick;
  utt.onend  = () => { State.isSpeaking = false; if (onDone) onDone(); else _restartMicAfterSpeaking(); };
  utt.onerror= () => { State.isSpeaking = false; if (onDone) onDone(); else _restartMicAfterSpeaking(); };
  synth.speak(utt);
}

function prewarm(text, lang = 'hinglish') {
  fetch(_ttsUrl(text, lang), { method: 'HEAD' }).catch(() => {});
}


/* ══════════════════════════════════════════
   SPEECH RECOGNITION
══════════════════════════════════════════ */
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition   = null;
let _restartTimer = null;

function _buildRecognition() {
  if (!SpeechRecognition) return null;
  const rec = new SpeechRecognition();
  rec.lang            = 'en-US';
  rec.continuous      = false;
  rec.interimResults  = true;
  rec.maxAlternatives = 3;

  rec.onstart = () => {
    State.isListening = true;
    if (State.mode === Mode.PASSIVE) {
      setStatus('passive', '👂', '"Shuru karo" boliye shuru karne ke liye…');
    } else if (State.mode === Mode.IDENTIFYING) {
      setStatus('passive', '🔢', 'Apna student ID boliye…');
    } else if (State.mode === Mode.REGISTERING) {
      setStatus('passive', '✏️', 'Apna naam boliye…');
    } else {
      setStatus('listening', '🎤', 'Sun rahi hoon… bolo beta!');
    }
  };

  rec.onresult = (event) => {
    let interim = '', final = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      if (res.isFinal) {
        let best = res[0];
        for (let a = 1; a < res.length; a++) {
          if (res[a].confidence > best.confidence) best = res[a];
        }
        final += best.transcript;
      } else {
        interim += res[0].transcript;
      }
    }
    El.liveTx.textContent = final || interim;

    if (final.trim()) {
      switch (State.mode) {
        case Mode.PASSIVE:     _handlePassive(final.trim());     break;
        case Mode.IDENTIFYING: _handleIdentifying(final.trim()); break;
        case Mode.REGISTERING: _handleRegistering(final.trim()); break;
        case Mode.ACTIVE:      handleUserSpeech(final.trim());   break;
      }
    }
  };

  rec.onerror = (ev) => {
    State.isListening = false;
    if (ev.error === 'no-speech') {
      if (State.mode !== Mode.LOCKED && !State.isSpeaking) scheduleRestart(650);
    } else if (ev.error === 'not-allowed' || ev.error === 'service-not-allowed') {
      setStatus('idle', '🚫', 'Microphone allow karo — Chrome → Settings → Privacy → Microphone');
      announceToSR('Microphone permission denied. Allow mic access and reload the page.');
    } else if (ev.error === 'network') {
      setStatus('idle', '🌐', 'Network error. Internet check karo…');
      if (State.mode !== Mode.LOCKED) scheduleRestart(2500);
    } else if (ev.error !== 'aborted') {
      if (State.mode !== Mode.LOCKED && !State.isSpeaking) scheduleRestart(1400);
    }
  };

  rec.onend = () => {
    State.isListening = false;
    El.liveTx.textContent = '';
    if (State.mode !== Mode.LOCKED &&
        !State.isSpeaking && !State.isProcessing && !State.isLoading) {
      scheduleRestart(420);
    }
  };

  return rec;
}

function startRecognition() {
  if (!recognition) recognition = _buildRecognition();
  if (!recognition) return;
  if (State.isListening || State.isSpeaking ||
      State.isProcessing || State.isLoading) return;
  try { recognition.start(); } catch (_) {}
}

function abortRecognition() {
  if (recognition && State.isListening) {
    try { recognition.abort(); } catch (_) {}
    State.isListening = false;
  }
}

function scheduleRestart(ms) {
  clearTimeout(_restartTimer);
  _restartTimer = setTimeout(() => {
    if (State.mode !== Mode.LOCKED &&
        !State.isSpeaking && !State.isProcessing && !State.isLoading) {
      startRecognition();
    }
  }, ms);
}


/* ══════════════════════════════════════════
   VOICE COMMAND PATTERNS
══════════════════════════════════════════ */

const RE_START = new RegExp(
  [
    '\\b(shuru|shuroo|shuro|suroo|suru|start|begin|chalu|chalo\\s*start|helo\\s*didi|hello\\s*didi|namaste\\s*didi|activate|open)\\b',
    'शुरू|शुरु|चालू|शुरूआत',
  ].join('|'), 'i'
);

const RE_END = new RegExp(
  [
    '\\b(band\\s*karo|bandh\\s*karo|bund\\s*karo|stop\\b|end\\b|bye\\b|goodbye|good\\s*bye|alvida|band\\s*ho|khatam|khatm|rukao|ruk\\s*jao|finish|close|deactivate)\\b',
    'बंद|रुको|बंद\\s*करो|खत्म',
  ].join('|'), 'i'
);

const RE_REPEAT = new RegExp(
  [
    '\\b(phir\\s*bolo|dobara\\s*bolo|again\\s*bolo|again\\b|repeat\\b|suna\\s*nahi|nahi\\s*suna|sunai\\s*nahi|ek\\s*baar\\s*aur|once\\s*more|say\\s*again)\\b',
    'फिर\\s*बोलो|दोबारा\\s*बोलो',
  ].join('|'), 'i'
);

const RE_SLOW = new RegExp(
  [
    '\\b(dheere\\s*bolo|dheere|dhire|slowly\\b|slow\\b|slow\\s*karo|speak\\s*slow|aaram\\s*se|dhire\\s*bolo|slowly\\s*please)\\b',
    'धीरे|आराम\\s*से',
  ].join('|'), 'i'
);

const RE_FAST = new RegExp(
  [
    '\\b(tez\\s*bolo|tez\\b|fast\\s*bolo|fast\\b|speak\\s*fast|jaldi\\s*bolo|jaldi\\b|tez\\s*karo|faster\\b|speed\\s*up)\\b',
    'तेज़|तेज|जल्दी',
  ].join('|'), 'i'
);

const RE_STORY = new RegExp(
  [
    '\\b(story|kahani|kissa|tale|sunao|suniye|ek\\s*kahani|ek\\s*story|story\\s*sunao|kahani\\s*sunao|story\\s*chahiye|kahani\\s*chahiye|wanna\\s*hear|want\\s*to\\s*hear|hear\\s*a\\s*story|mujhe\\s*story|story\\s*suno|kahani\\s*suno)\\b',
    'कहानी|किस्सा',
  ].join('|'), 'i'
);

const RE_SUMMARY = new RegExp(
  [
    '\\b(summary|recap|revision|revise|remind\\s*me|what\\s*did\\s*we\\s*learn|what\\s*did\\s*we\\s*do|tell\\s*me\\s*what\\s*we\\s*did|summary\\s*batao|summary\\s*please|recap\\s*karo|revision\\s*karo|aaj\\s*kya\\s*seekha|humne\\s*kya\\s*seekha|mujhe\\s*yaad\\s*dilao|aaj\\s*ka\\s*summary|kya\\s*kiya\\s*humne|phir\\s*se\\s*batao)\\b',
  ].join('|'), 'i'
);

const RE_LAST_CLASS = new RegExp(
  [
    '\\b(last\\s*class|last\\s*time|pichle\\s*class|pichli\\s*baar|previous\\s*class|kal\\s*kya\\s*seekha|last\\s*session|pichla\\s*session)\\b',
  ].join('|'), 'i'
);

// ── New patterns for v6 features ────────────────────────────────────────────

const RE_QUIZ_START = new RegExp(
  '\\b(quiz|test|exam|sawaal|question\\s*karo|questions|quiz\\s*shuru|quiz\\s*do|quiz\\s*chahiye|quiz\\s*mode|test\\s*lo|mujhe\\s*test|practice\\s*test)\\b', 'i'
);

const RE_PRONUNCIATION_START = new RegExp(
  '\\b(pronounce|pronunciation|ucharan|word\\s*practice|bolna\\s*seekho|bolna\\s*sikhao|shabdon\\s*ki\\s*practice|speak\\s*words|practice\\s*words)\\b', 'i'
);

const RE_INTERACTIVE_STORY = new RegExp(
  '\\b(interactive\\s*story|samajh\\s*wali\\s*story|story\\s*with\\s*questions|comprehension|story\\s*quiz|kahani\\s*aur\\s*sawaal)\\b', 'i'
);

const RE_PROGRESS = new RegExp(
  '\\b(meri\\s*progress|my\\s*progress|progress\\s*batao|streak|kitna\\s*seekha|how\\s*many\\s*words|kitni\\s*practice|mera\\s*score)\\b', 'i'
);

const RE_EXIT_SUBMODE = new RegExp(
  '\\b(wapas\\s*jao|back\\s*to\\s*chat|normal\\s*mode|regular\\s*mode|chat\\s*karo|mode\\s*band\\s*karo|exit\\s*quiz|exit\\s*mode|stop\\s*quiz)\\b', 'i'
);


/* ══════════════════════════════════════════
   STUDENT ID HELPERS
══════════════════════════════════════════ */

const HINDI_NUM_MAP = {
  ek:1, do:2, teen:3, tin:3, char:4, chaar:4,
  paanch:5, panch:5, chheh:6, chhe:6, chhah:6, chai:6,
  saat:7, sat:7, aath:8, ath:8, nau:9, noh:9,
  das:10, gyarah:11, barah:12, terah:13, chaudah:14, chawdah:14,
  pandrah:15, pandara:15, solah:16, satrah:17, satara:17,
  atharah:18, athara:18, unnis:19, unis:19, bees:20,
};

function extractStudentId(text) {
  const lower = text.toLowerCase().trim();
  const digitMatch = lower.match(/\b(\d+)\b/);
  if (digitMatch) {
    const n = parseInt(digitMatch[1], 10);
    return { num: n, valid: n >= 1 && n <= 20 };
  }
  const EN_WORDS = [
    '', 'one','two','three','four','five','six','seven','eight','nine','ten',
    'eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen',
    'eighteen','nineteen','twenty',
  ];
  for (let n = 1; n <= 20; n++) {
    if (new RegExp(`\\b${EN_WORDS[n]}\\b`).test(lower)) return { num: n, valid: true };
  }
  for (const [word, num] of Object.entries(HINDI_NUM_MAP)) {
    if (new RegExp(`\\b${word}\\b`).test(lower)) return { num, valid: true };
  }
  return null;
}

function sanitiseName(raw) {
  const noise = /\b(mera|naam|hai|my|name|is|aapka|apka|mein|hoon|bolta|bolti)\b/gi;
  return raw.replace(noise, '').replace(/\s{2,}/g, ' ').trim()
    .split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}


/* ══════════════════════════════════════════
   AGENTIC HELPERS
══════════════════════════════════════════ */

/* PlannerAgent — fetch a 5-step session plan after login */
async function _fetchSessionPlan(name, proficiency, weakWords, hasHistory) {
  try {
    const res = await fetch('/session/plan', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({
        student_name: name,
        proficiency : proficiency || 'Beginner',
        weak_words  : weakWords  || [],
        has_history : hasHistory,
      }),
      signal: AbortSignal.timeout(20_000),
    });
    const data = await res.json();
    if (data.plan && data.plan.length) {
      State.sessionPlan  = data.plan;
      State.planStepIdx  = 0;
      _updatePlanUI();
      console.log('[Didi Agent] Plan:', data.plan.map(s => s.type).join(' → '));
    }
  } catch (_) {
    /* plan is optional — silently continue without it */
  }
}

/* MemoryAgent — compress history when it gets too long */
async function _tryCompressHistory() {
  if (State.history.length < 14 || State.isCompressing) return;
  State.isCompressing = true;
  try {
    const res = await fetch('/session/compress', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({
        history     : State.history,
        student_name: State.studentName || 'beta',
        keep_recent : 6,
      }),
      signal: AbortSignal.timeout(15_000),
    });
    const data = await res.json();
    if (data.compressed) {
      State.history    = data.history;
      State.memoryNote = data.memory_summary;
      console.log('[Didi Agent] Memory compressed:', data.memory_summary);
    }
  } catch (_) {
    /* silently skip — history will just stay full */
  } finally {
    State.isCompressing = false;
  }
}

/* Advance the plan step every 3 user turns */
function _advancePlanStep() {
  if (!State.sessionPlan.length) return;
  const userTurns = State.history.filter(t => t.role === 'user').length;
  const newIdx    = Math.min(Math.floor(userTurns / 3), State.sessionPlan.length - 1);
  if (newIdx !== State.planStepIdx) {
    State.planStepIdx = newIdx;
    _updatePlanUI();
  }
}

/* Auto-save session history to backend (silent, best-effort) */
function _autoSaveSession() {
  if (!State.studentId || !State.fullHistory.length) return;
  navigator.sendBeacon(
    '/student/save_session',
    new Blob(
      [JSON.stringify({ id: String(State.studentId), history: State.fullHistory })],
      { type: 'application/json' }
    )
  );
}

/* Show current plan step in the mode indicator */
function _updatePlanUI() {
  if (!El.modeIndicator || !El.modeLabel) return;
  const step = State.sessionPlan[State.planStepIdx];
  if (!step || State.subMode) return;   // sub-mode label takes priority
  const emojis = {
    warm_up: '👋', vocabulary: '📚', grammar: '📖', story: '📖',
    quiz: '📝', pronunciation: '🎙️', conversation: '💬', confidence_boost: '⭐',
  };
  const emoji = emojis[step.type] || '📚';
  El.modeLabel.textContent   = `${emoji} Step ${step.step}: ${step.type.replace(/_/g, ' ')}`;
  El.modeIndicator.hidden    = false;
  El.modeIndicator.className = 'mode-indicator mode-plan';
}


/* ══════════════════════════════════════════
   MODE TRANSITIONS
══════════════════════════════════════════ */

function enterPassiveMode() {
  State.mode       = Mode.PASSIVE;
  State.studentId  = null;
  State.studentName= null;
  setStatus('passive', '👂', 'Sun rahi hoon… "Shuru karo" boliye');
  _setSubMode(SubMode.NONE);

  const msg = 'Namaste beta! Main sun rahi hoon. Shuru karo boliye, aur hum English practice karenge!';
  _botSay(msg, 'hinglish', () => { startRecognition(); });
}

function enterIdentifyingMode() {
  State.mode = Mode.IDENTIFYING;
  setStatus('passive', '🔢', 'Apna student ID boliye…');

  const msg = 'Bahut achha! Ab apna student ID boliye.';
  _botSay(msg, 'hinglish', () => { startRecognition(); });
}

async function enterActiveMode(name, isNew, lastHistory) {
  State.mode        = Mode.ACTIVE;
  State.studentName = name;
  if (lastHistory && lastHistory.length) {
    // lastHistory = today's existing messages — continue from where left off
    State.history     = [...lastHistory];
    State.fullHistory = [...lastHistory];
    // lastSessionHistory is already set from the check response (previous day)
    // Only set it here for new-student path where check didn't run
    if (!State.lastSessionHistory.length) State.lastSessionHistory = [];
  }
  startSessionTimer();
  _resetConfidence();

  // Reset agentic state for new session
  State.sessionPlan  = [];
  State.planStepIdx  = 0;
  State.memoryNote   = '';
  State.isCompressing= false;

  // Load SQLite progress from backend (streak, quiz %)
  // Then use the loaded data to kick off the PlannerAgent in background
  if (State.studentId) {
    const sid = String(State.studentId);
    _loadProgressStats(sid, name);
    // Fetch plan in background — non-blocking, session works fine without it
    fetch(`/progress/${encodeURIComponent(sid)}`)
      .then(r => r.json())
      .then(d => {
        const prof = d.proficiency || 'Beginner';
        return fetch(`/words/weak/${encodeURIComponent(sid)}`)
          .then(r => r.json())
          .then(w => _fetchSessionPlan(name, prof, w.words || [], lastHistory.length > 0));
      })
      .catch(() => {});
  }

  let welcome = isNew
    ? `__NEW_STUDENT__ ${name}`
    : `__RETURNING_STUDENT__ ${name}`;

  setStatus('thinking', '🤔', 'Soch rahi hoon…');
  State.isProcessing = true;

  try {
    const res = await fetch('/chat', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ message: welcome, history: State.history }),
      signal : AbortSignal.timeout(25_000),
    });
    const data  = await res.json();
    const reply = data.response || `Namaste ${name}! Chalo aaj English seekhte hain!`;
    State.history.push({ role: 'assistant', content: reply });
    _botSay(reply, 'hinglish');
  } catch (_) {
    const fallback = isNew
      ? `Namaste ${name}! Main bahut khush hoon aapse milke! Chalo English seekhna shuru karte hain!`
      : `Arre ${name}! Wapas aaye, bahut achha kiya! Chalo aaj phir kuch naya seekhte hain!`;
    _botSay(fallback, 'hinglish');
  } finally {
    State.isProcessing = false;
  }
}

function enterEndMode() {
  stopSessionTimer();
  _clearSilenceTimer();
  _setSubMode(SubMode.NONE);

  // Save session data (both systems)
  _autoSaveSession();
  if (State.studentId && State.studentName) {
    const minutes = Math.floor(State.sessionSeconds / 60);
    fetch('/progress/update', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({
        student_id        : String(State.studentId),
        name              : State.studentName,
        speaking_attempts : State.sentencesSpoken,
        words_practiced   : State.wordsLearned,
        session_minutes   : minutes,
      }),
    })
    .then(r => r.json())
    .then(d => { if (d.streak) State.streak = d.streak; })
    .catch(() => {});
  }

  const name       = State.studentName || 'beta';
  const confidence = _computeConfidenceScore();
  const bye        = `Bye bye ${name}! Aaj bahut achha practice kiya. Jab chahein wapas aana — phir "Shuru karo" boliye!`;

  function _resetAndReturn() {
    State.mode        = Mode.PASSIVE;
    State.studentId   = null;
    State.studentName = null;
    State.history     = [];
    State.fullHistory = [];
    State.lastSessionHistory = [];
    State.sentencesSpoken    = 0;
    State.wordsLearned       = 0;
    State.sessionSeconds     = 0;
    State.sessionPlan        = [];
    State.planStepIdx        = 0;
    State.memoryNote         = '';
    State.isCompressing      = false;
    updateStats();
    _updateDbStats(0, 0, 0);
    setStatus('passive', '👂', '"Shuru karo" boliye dobara shuru karne ke liye…');
    scheduleRestart(600);
  }

  // Build confidence message (may be empty)
  let confMsg = '';
  if      (confidence >= 80) confMsg = 'Aaj aapne bahut tez aur confident jawab diye! Great confidence!';
  else if (confidence >= 60) confMsg = 'Aapka confidence badh raha hai! Roz practice karo!';
  else if (confidence >= 40) confMsg = 'Aap seekh rahe ho. Har din thoda aur confident hoge!';

  // Chain: confidence message (if any) → bye → reset
  // This guarantees only ONE voice plays at a time
  if (confMsg) {
    _botSay(confMsg, 'hinglish', () => {
      _botSay(bye, 'hinglish', _resetAndReturn);
    });
  } else {
    _botSay(bye, 'hinglish', _resetAndReturn);
  }
}


/* ══════════════════════════════════════════
   PASSIVE MODE HANDLER
══════════════════════════════════════════ */
function _handlePassive(text) {
  if (State.isProcessing || State.isSpeaking) return;
  if (RE_START.test(text)) {
    enterIdentifyingMode();
  } else {
    scheduleRestart(300);
  }
}


/* ══════════════════════════════════════════
   IDENTIFYING MODE HANDLER
══════════════════════════════════════════ */
async function _handleIdentifying(text) {
  if (State.isProcessing || State.isSpeaking) return;

  const result = extractStudentId(text);

  if (!result) {
    const again = 'Maafi karo, samajh nahi aaya. Apna student ID boliye.';
    _botSay(again, 'hinglish', () => { startRecognition(); });
    return;
  }

  if (!result.valid) {
    const noExist = `Student ID ${result.num} exist nahi karta. Kripya sahi student ID boliye.`;
    _botSay(noExist, 'hinglish', () => { startRecognition(); });
    return;
  }

  const id = result.num;
  State._pendingId   = id;
  State.isProcessing = true;

  try {
    const res  = await fetch(`/student/check?id=${id}`, { signal: AbortSignal.timeout(8000) });
    const data = await res.json();

    if (data.exists) {
      State.studentId          = id;
      State.lastSessionHistory = data.last_session || [];   // previous day — for recap
      State.isProcessing       = false;
      await enterActiveMode(data.name, false, data.today_history || []);
    } else {
      State.isProcessing = false;
      State.mode = Mode.REGISTERING;
      setStatus('passive', '✏️', 'Apna naam boliye…');
      const ask = `ID number ${id} — yeh pehli baar hai! Swagat hai! Ab apna naam boliye.`;
      _botSay(ask, 'hinglish', () => { startRecognition(); });
    }
  } catch (_) {
    State.isProcessing = false;
    const err = 'Network mein thodi dikkat aayi. Kripya dobara apna ID boliye.';
    _botSay(err, 'hinglish', () => { startRecognition(); });
  }
}


/* ══════════════════════════════════════════
   REGISTERING MODE HANDLER
══════════════════════════════════════════ */
async function _handleRegistering(text) {
  if (State.isProcessing || State.isSpeaking) return;

  const name = sanitiseName(text);
  if (!name || name.length < 2) {
    const again = 'Kripya apna naam boliye — sirf apna naam.';
    _botSay(again, 'hinglish', () => { startRecognition(); });
    return;
  }

  State.isProcessing = true;

  try {
    const res = await fetch('/student/register', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ id: State._pendingId, name }),
      signal : AbortSignal.timeout(8000),
    });
    const data = await res.json();

    if (data.error === 'ID already taken') {
      State.isProcessing = false;
      State.mode = Mode.IDENTIFYING;
      const taken = `ID ${State._pendingId} abhi kisi aur ne le liya! Koi aur number boliye.`;
      _botSay(taken, 'hinglish', () => { startRecognition(); });
      return;
    }

    State.studentId    = State._pendingId;
    State._pendingId   = null;
    State.isProcessing = false;
    await enterActiveMode(data.name || name, true, []);

  } catch (_) {
    State.isProcessing = false;
    const err = 'Account banana mein dikkat aayi. Dobara apna naam boliye.';
    _botSay(err, 'hinglish', () => { startRecognition(); });
  }
}


/* ══════════════════════════════════════════
   SUMMARY HANDLER
══════════════════════════════════════════ */
async function _handleSummary(type) {
  abortRecognition();
  State.isProcessing = true;
  setStatus('thinking', '🤔', 'Summary taiyaar kar rahi hoon…');

  const history = type === 'last'
    ? State.lastSessionHistory
    : State.history;

  try {
    const res = await fetch('/summary', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({
        student_name: State.studentName || 'beta',
        history,
        type,
      }),
      signal: AbortSignal.timeout(30_000),
    });
    const data  = await res.json();
    const reply = data.response || 'Aaj bahut achha kiya! Chalo kal aur seekhenge!';
    _botSay(reply, 'hinglish');
  } catch (_) {
    _botSay('Summary abhi nahi aa payi. Ek baar phir try karo!', 'hinglish');
  } finally {
    State.isProcessing = false;
  }
}


/* ══════════════════════════════════════════
   MAIN CONVERSATION HANDLER  (ACTIVE mode)
══════════════════════════════════════════ */
async function handleUserSpeech(text) {
  if (!text || State.isProcessing) return;

  _clearSilenceTimer();
  abortRecognition();

  // ── Record response time for confidence scoring ─────────────────────────
  if (State.confidence.questionStartedAt > 0) {
    const elapsed = (Date.now() - State.confidence.questionStartedAt) / 1000;
    State.confidence.responseTimes.push(elapsed);
    State.confidence.questionStartedAt = 0;
  }

  State.isProcessing = true;

  /* ── Route to sub-mode handler if active ──────────────────────────────── */
  if (State.subMode === SubMode.QUIZ) {
    _handleQuizAnswer(text);
    return;
  }
  if (State.subMode === SubMode.STORY) {
    _handleStoryAnswer(text);
    return;
  }
  if (State.subMode === SubMode.PRONUNCIATION) {
    _handlePronunciationAnswer(text);
    return;
  }

  /* ── Client-side instant commands ──────────────────────────────────────── */

  if (RE_END.test(text)) {
    addBubble('user', text);
    State.isProcessing = false;
    enterEndMode();
    return;
  }

  if (RE_REPEAT.test(text)) {
    addBubble('user', text);
    State.confidence.retryCount++;
    State.isProcessing = false;
    if (State.lastBotText) speak(State.lastBotText, State.lastBotLang);
    else speak('Main hoon na beta! Kuch pucho.', 'hinglish');
    return;
  }

  if (RE_SLOW.test(text)) {
    addBubble('user', text);
    State.slowMode = true;
    _botSay('Bilkul beta! Main ab dheere dheere bolungi. Aaram se suniye!', 'hinglish');
    State.isProcessing = false;
    return;
  }

  if (RE_FAST.test(text)) {
    addBubble('user', text);
    State.slowMode = false;
    _botSay('Theek hai beta! Ab thoda tez bolungi!', 'hinglish');
    State.isProcessing = false;
    return;
  }

  // Last class summary
  if (RE_LAST_CLASS.test(text)) {
    addBubble('user', text);
    if (!State.lastSessionHistory.length) {
      State.isProcessing = false;
      const noHist = State.studentName
        ? `${State.studentName}, pichli class ka koi record nahi mila. Yeh shayad tumhara pehla session hai!`
        : 'Pichli class ka koi record nahi mila. Yeh shayad pehla session hai!';
      _botSay(noHist, 'hinglish');
      return;
    }
    State.isProcessing = false;
    _handleSummary('last');
    return;
  }

  // Current session summary
  if (RE_SUMMARY.test(text)) {
    addBubble('user', text);
    State.isProcessing = false;
    _handleSummary('current');
    return;
  }

  // ── New v6 triggers ────────────────────────────────────────────────────

  // Progress report
  if (RE_PROGRESS.test(text)) {
    addBubble('user', text);
    State.isProcessing = false;
    _speakProgressReport();
    return;
  }

  // Interactive story (with comprehension questions)
  if (RE_INTERACTIVE_STORY.test(text)) {
    addBubble('user', text);
    State.isProcessing = false;
    startInteractiveStory();
    return;
  }

  // Quiz mode
  if (RE_QUIZ_START.test(text)) {
    addBubble('user', text);
    State.isProcessing = false;
    startQuizMode();
    return;
  }

  // Pronunciation practice
  if (RE_PRONUNCIATION_START.test(text)) {
    addBubble('user', text);
    State.isProcessing = false;
    startPronunciationMode();
    return;
  }

  /* ── Normal message → Flask /chat ────────────────────────────────────── */
  addBubble('user', text);
  setStatus('thinking', '🤔', 'Soch rahi hoon…');

  const msgToSend = RE_STORY.test(text) ? `__STORY_NOW__ ${text}` : text;

  State.history.push({ role: 'user', content: text });
  State.fullHistory.push({ role: 'user', content: text });
  // History length is now managed by MemoryAgent compression instead of hard shift

  State.sentencesSpoken++;
  updateStats();

  try {
    const res = await fetch('/chat', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({
        message    : msgToSend,
        history    : State.history,
        plan_step  : State.sessionPlan[State.planStepIdx] || null,
        memory_note: State.memoryNote || '',
      }),
      signal : AbortSignal.timeout(25_000),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data  = await res.json();
    const reply = data.response || 'Koi baat nahi beta, ek baar phir boliye!';
    const lang  = data.language  || 'hinglish';

    State.history.push({ role: 'assistant', content: reply });
    State.fullHistory.push({ role: 'assistant', content: reply });
    if (/word|vocab|matlab|meaning/i.test(text)) State.wordsLearned++;
    updateStats();

    // Advance plan step + trigger memory compression if history is growing
    _advancePlanStep();
    _tryCompressHistory();
    _autoSaveSession();   // persist after every turn

    _botSay(reply, lang);

  } catch (err) {
    console.error('[/chat]', err);
    _botSay('Thodi si dikkat aayi beta, koi baat nahi! Ek baar phir boliye!', 'hinglish');
  } finally {
    State.isProcessing = false;
  }
}

function _botSay(text, lang, onDone) {
  addBubble('bot', text);
  State.lastBotText = text;
  State.lastBotLang = lang;
  speak(text, lang, onDone);
}


/* ══════════════════════════════════════════
   ── QUIZ MODE ──
══════════════════════════════════════════ */

const QUIZ_TOTAL_QUESTIONS = 5;

async function startQuizMode() {
  _setSubMode(SubMode.QUIZ);
  State.quizSession = { questions: [], index: 0, correct: 0, total: 0 };

  const sid = State.studentId ? String(State.studentId) : '';
  const intro = 'Quiz time! Main aapko ' + QUIZ_TOTAL_QUESTIONS +
    ' sawaal puchungi. Dhyan se suno aur jawab dena. Chalo shuru karte hain!';
  _botSay(intro, 'hinglish', () => _fetchAndAskQuizQuestion(sid));
}

async function _fetchAndAskQuizQuestion(sid) {
  if (State.quizSession.total >= QUIZ_TOTAL_QUESTIONS) {
    _endQuizMode();
    return;
  }

  State.isProcessing = true;
  try {
    const res = await fetch(`/quiz/question?sid=${encodeURIComponent(sid)}`, {
      signal: AbortSignal.timeout(8000),
    });
    const q = await res.json();
    if (q.error) { _botSay('Quiz mein kuch dikkat aayi. Wapas chat mein aate hain.', 'hinglish'); _setSubMode(SubMode.NONE); return; }

    // Store question on session state so the answer handler can check it
    State.quizSession.questions.push(q);
    State.quizSession.index = State.quizSession.questions.length - 1;

    const num = State.quizSession.total + 1;
    const prompt = `Sawaal number ${num}: ${q.question}`;
    _botSay(prompt, 'english', () => {
      State.confidence.questionStartedAt = Date.now();
      State.isProcessing = false;
      startRecognition();
    });
  } catch (_) {
    _botSay('Network issue. Quiz thodi der mein try karo.', 'hinglish');
    _setSubMode(SubMode.NONE);
    State.isProcessing = false;
  }
}

function _handleQuizAnswer(text) {
  const q   = State.quizSession.questions[State.quizSession.index];
  if (!q) { State.isProcessing = false; return; }

  addBubble('user', text);
  State.quizSession.total++;

  const correct = _answerMatches(text, q.answers);
  if (correct) State.quizSession.correct++;

  // Record in backend
  const sid = State.studentId ? String(State.studentId) : '';
  if (sid) {
    fetch('/quiz/record', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ student_id: sid, quiz_type: q.type, question: q.question, correct }),
    }).catch(() => {});
  }

  const feedback = correct
    ? _pickMotivation('correct')
    : `${_pickMotivation('wrong')} Sahi jawab tha: ${q.answers[0]}. ${q.hint}`;

  _botSay(feedback, 'hinglish', () => {
    State.isProcessing = false;
    _fetchAndAskQuizQuestion(sid);
  });
}

function _endQuizMode() {
  const { correct, total } = State.quizSession;
  const pct   = Math.round((correct / total) * 100);
  const score = `Quiz khatam! Aapne ${correct} mein se ${total} sawaal sahi kiye — ${pct} percent!`;

  let comment = '';
  if (pct >= 80) comment = 'Waah! Bahut badhiya! Aap bade expert ban rahe ho!';
  else if (pct >= 50) comment = 'Achha kiya! Thoda aur practice se aur improve karoge!';
  else comment = 'Koi baat nahi! Har galti se seekhte hain. Kal aur practice karte hain!';

  State.weekQuizPct = pct;
  _updateDbStats(State.streak, pct, State.totalWords);
  _setSubMode(SubMode.NONE);
  _botSay(`${score} ${comment}`, 'hinglish', () => {
    State.isProcessing = false;
    startRecognition();
  });
}

/* Simple fuzzy answer checker used by quiz and story */
function _answerMatches(spoken, expectedList) {
  const s = spoken.toLowerCase().replace(/[.,!?']/g, '').trim();
  for (const ans of expectedList) {
    const a = ans.toLowerCase().trim();
    if (s.includes(a) || a.includes(s)) return true;
    // All words in expected appear in spoken
    const sWords = s.split(/\s+/);
    const aWords = a.split(/\s+/);
    if (aWords.length > 0 && aWords.every(w => sWords.includes(w))) return true;
  }
  return false;
}


/* ══════════════════════════════════════════
   ── INTERACTIVE STORY MODE ──
══════════════════════════════════════════ */

async function startInteractiveStory() {
  _setSubMode(SubMode.STORY);
  State.storySession = { story: null, phase: 'none', qIdx: 0, correct: 0 };

  State.isProcessing = true;
  try {
    const res   = await fetch('/story/interactive', { signal: AbortSignal.timeout(8000) });
    const story = await res.json();
    State.storySession.story = story;
    State.storySession.phase = 'listening';

    const intro = 'Story time! Main ek kahani sunaungi. Dhyan se suno — phir main 2 sawaal puchungi. Toh shuru karte hain.';
    _botSay(intro, 'hinglish', () => {
      _botSay(story.story, 'english', () => {
        State.storySession.phase = 'questions';
        State.storySession.qIdx  = 0;
        State.isProcessing = false;
        _askStoryQuestion();
      });
    });
  } catch (_) {
    _botSay('Story abhi load nahi hui. Thodi der mein try karo.', 'hinglish');
    _setSubMode(SubMode.NONE);
    State.isProcessing = false;
  }
}

function _askStoryQuestion() {
  const story = State.storySession.story;
  if (!story) return;
  const q = story.questions[State.storySession.qIdx];
  if (!q) { _endStoryMode(); return; }

  const num = State.storySession.qIdx + 1;
  _botSay(`Sawaal number ${num}: ${q.q}`, 'english', () => {
    State.confidence.questionStartedAt = Date.now();
    startRecognition();
  });
}

function _handleStoryAnswer(text) {
  const story = State.storySession.story;
  if (!story) { State.isProcessing = false; return; }

  const q = story.questions[State.storySession.qIdx];
  if (!q) { State.isProcessing = false; return; }

  addBubble('user', text);

  const correct = _answerMatches(text, q.a);
  if (correct) State.storySession.correct++;

  const feedback = correct
    ? _pickMotivation('correct')
    : `${_pickMotivation('wrong')} Hint: ${q.hint}`;

  State.storySession.qIdx++;
  _botSay(feedback, 'hinglish', () => {
    State.isProcessing = false;
    if (State.storySession.qIdx < story.questions.length) {
      _askStoryQuestion();
    } else {
      _endStoryMode();
    }
  });
}

function _endStoryMode() {
  const { correct } = State.storySession;
  const total = State.storySession.story?.questions?.length || 2;
  const comment = correct === total
    ? 'Waah! Dono sawaal bilkul sahi! Story bahut achhi samjhi tumne!'
    : correct === 1
      ? 'Ek sawaal sahi kiya! Achha effort! Aur baar baar practice karo.'
      : 'Koi baat nahi! Story phir se suno aur dobara try karo.';

  _setSubMode(SubMode.NONE);
  _botSay(comment, 'hinglish', () => {
    State.isProcessing = false;
    startRecognition();
  });
}


/* ══════════════════════════════════════════
   ── PRONUNCIATION MODE ──
══════════════════════════════════════════ */

const PRONUNCIATION_WORDS_PER_SESSION = 5;

async function startPronunciationMode() {
  _setSubMode(SubMode.PRONUNCIATION);
  State.pronSession = { word: null, syllables: '', count: 0, correct: 0 };

  const intro = 'Pronunciation practice shuru karte hain! Main ek word bolungi — aap uss word ko bolna hai. Tayaar ho?';
  _botSay(intro, 'hinglish', () => {
    _fetchAndAskPronunciationWord();
  });
}

async function _fetchAndAskPronunciationWord() {
  if (State.pronSession.count >= PRONUNCIATION_WORDS_PER_SESSION) {
    _endPronunciationMode();
    return;
  }

  const sid = State.studentId ? String(State.studentId) : '';
  State.isProcessing = true;
  try {
    const res   = await fetch(`/pronunciation/word?sid=${encodeURIComponent(sid)}`, {
      signal: AbortSignal.timeout(8000),
    });
    const data  = await res.json();
    State.pronSession.word      = data.word;
    State.pronSession.syllables = data.syllables;

    const revisionNote = data.revision ? 'Yeh word tumne pehle miss kiya tha. Ek baar aur try karo. ' : '';
    const prompt = `${revisionNote}Yeh word bolo: ${data.word}. ${data.syllables}.`;
    _botSay(prompt, 'english', () => {
      State.confidence.questionStartedAt = Date.now();
      State.isProcessing = false;
      startRecognition();
    });
  } catch (_) {
    _botSay('Word load nahi hua. Thodi der mein try karo.', 'hinglish');
    _setSubMode(SubMode.NONE);
    State.isProcessing = false;
  }
}

async function _handlePronunciationAnswer(text) {
  if (!State.pronSession.word) { State.isProcessing = false; return; }

  addBubble('user', text);
  State.pronSession.count++;

  const sid = State.studentId ? String(State.studentId) : '';

  try {
    const res = await fetch('/pronunciation/check', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({
        expected  : State.pronSession.word,
        spoken    : text,
        student_id: sid,
        syllables : State.pronSession.syllables,
      }),
      signal: AbortSignal.timeout(8000),
    });
    const data = await res.json();

    if (data.correct) State.pronSession.correct++;

    _botSay(data.feedback, 'hinglish', () => {
      State.isProcessing = false;
      _fetchAndAskPronunciationWord();
    });
  } catch (_) {
    _botSay('Check nahi ho paya. Dobara try karo!', 'hinglish');
    State.isProcessing = false;
    _fetchAndAskPronunciationWord();
  }
}

function _endPronunciationMode() {
  const { correct, count } = State.pronSession;
  const pct  = Math.round((correct / count) * 100);
  const msg  = `Pronunciation practice khatam! Aapne ${correct} mein se ${count} words sahi bole — ${pct} percent! ` +
    (pct >= 80 ? 'Excellent pronunciation!' : pct >= 50 ? 'Bahut achha! Keep practising!' : 'Koi baat nahi! Roz practice se improve hoga!');

  _setSubMode(SubMode.NONE);
  State.wordsLearned += correct;
  updateStats();
  _botSay(msg, 'hinglish', () => {
    State.isProcessing = false;
    startRecognition();
  });
}


/* ══════════════════════════════════════════
   ── MOTIVATION COACH ──
══════════════════════════════════════════ */

const _MOTIVATION = {
  correct: [
    'Excellent! Bilkul sahi! You are doing great!',
    'Shabash! Waah! Perfect answer!',
    'Brilliant! You are improving every day!',
    'Amazing! Keep going like this!',
    'Bahut acha! I am so proud of you!',
  ],
  wrong: [
    'Nice try! Koi baat nahi, hum seekhenge.',
    'Good effort! Galti se hi toh seekhte hain.',
    'Almost there! Ek baar aur try karo.',
  ],
  repeated_wrong: [
    'Dariye mat! We will learn slowly together.',
    'Koi tension nahi. Hum araam se seekhenge.',
    'Aap bahut achha kar rahe ho. Main aapke saath hoon.',
  ],
};

function _pickMotivation(type) {
  const arr = _MOTIVATION[type] || _MOTIVATION.wrong;
  return arr[Math.floor(Math.random() * arr.length)];
}


/* ══════════════════════════════════════════
   ── CONFIDENCE SCORING ──
══════════════════════════════════════════ */

function _resetConfidence() {
  State.confidence = { silenceCount: 0, retryCount: 0, responseTimes: [], questionStartedAt: 0 };
}

function _computeConfidenceScore() {
  const { silenceCount, retryCount, responseTimes } = State.confidence;
  let score = 100;
  score -= silenceCount * 8;
  score -= retryCount   * 4;
  if (responseTimes.length > 0) {
    const avg = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
    if (avg < 5)  score += 10;   // fast responses → bonus
    if (avg > 20) score -= 10;   // very slow → deduction
  }
  return Math.max(0, Math.min(100, score));
}

function _speakConfidenceFeedback(score) {
  let msg = '';
  if (score >= 80) {
    msg = 'Aaj aapne bahut tez aur confident jawab diye! Great confidence!';
  } else if (score >= 60) {
    msg = 'Aapka confidence badh raha hai! Roz practice karo!';
  } else if (score >= 40) {
    msg = 'Aap seekh rahe ho. Har din thoda aur confident hoge!';
  }
  // Only say something meaningful — skip low score (the bye message covers it)
  if (msg && score >= 40) _botSay(msg, 'hinglish');
}


/* ══════════════════════════════════════════
   ── PROGRESS REPORT ──
══════════════════════════════════════════ */

async function _loadProgressStats(sid, name) {
  try {
    // Ensure a row exists in SQLite for new students
    await fetch('/progress/update', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ student_id: sid, name, speaking_attempts: 0, words_practiced: 0, session_minutes: 0 }),
    });

    const res  = await fetch(`/progress/${encodeURIComponent(sid)}`, { signal: AbortSignal.timeout(6000) });
    const data = await res.json();

    State.streak      = data.streak      || 0;
    State.weekQuizPct = data.quiz_pct    || 0;
    State.totalWords  = data.words_tried || 0;

    if (El.dbProgress) El.dbProgress.hidden = false;
    _updateDbStats(State.streak, State.weekQuizPct, State.totalWords);
  } catch (_) {}
}

function _updateDbStats(streak, quizPct, totalWords) {
  if (El.statStreak)      El.statStreak.textContent      = streak;
  if (El.statQuizPct)     El.statQuizPct.textContent     = quizPct + '%';
  if (El.statTotalWords)  El.statTotalWords.textContent  = totalWords;
}

function _speakProgressReport() {
  const sid  = State.studentId ? String(State.studentId) : '';
  const name = State.studentName || 'beta';

  fetch(`/progress/${encodeURIComponent(sid)}`, { signal: AbortSignal.timeout(6000) })
    .then(r => r.json())
    .then(d => {
      const streak = d.streak      || 0;
      const words  = d.words_tried || 0;
      const qPct   = d.quiz_pct    || 0;
      const spk    = d.speaking_attempts || 0;
      const mins   = d.session_minutes   || 0;

      let msg = `${name}, yeh rahi tumhari progress! `;
      if (streak > 1) msg += `Tumhara streak ${streak} din ka hai — bahut achha! `;
      if (words  > 0) msg += `Tumne ${words} words practice kiye hain. `;
      if (qPct   > 0) msg += `Is hafte quiz mein ${qPct} percent sahi kiye. `;
      if (spk    > 0) msg += `Tumne kul ${spk} baar bolne ki koshish ki — great! `;
      if (!streak && !words && !qPct) msg += 'Yeh tumhara pehla session hai! Chalo milke seekhte hain!';

      _botSay(msg, 'hinglish');
    })
    .catch(() => {
      _botSay(`${name}, progress data abhi load nahi ho paya. Thodi der mein try karo!`, 'hinglish');
    })
    .finally(() => { State.isProcessing = false; });
}


/* ══════════════════════════════════════════
   ── SUB-MODE UI HELPER ──
══════════════════════════════════════════ */

const _SUBMODE_LABELS = {
  [SubMode.QUIZ]         : '📝 Quiz Mode',
  [SubMode.STORY]        : '📖 Story Mode',
  [SubMode.PRONUNCIATION]: '🎙️ Pronunciation Mode',
};

function _setSubMode(sm) {
  State.subMode = sm;
  if (!El.modeIndicator || !El.modeLabel) return;

  if (sm && _SUBMODE_LABELS[sm]) {
    El.modeLabel.textContent     = _SUBMODE_LABELS[sm];
    El.modeIndicator.hidden      = false;
    El.modeIndicator.className   = `mode-indicator mode-${sm}`;
  } else {
    El.modeIndicator.hidden = true;
  }
}


/* ══════════════════════════════════════════
   UI HELPERS
══════════════════════════════════════════ */
const RING_CLASSES = {
  idle     : '',
  passive  : 'ring-passive',
  listening: 'ring-listening',
  speaking : 'ring-speaking',
  thinking : 'ring-thinking',
  loading  : 'ring-loading',
};
const WRAP_CLASSES = {
  idle     : '',
  passive  : 'state-passive',
  listening: 'state-listening',
  speaking : 'state-speaking',
  thinking : 'state-thinking',
  loading  : 'state-loading',
};

function setStatus(type, emoji, msg) {
  El.statusRing.className = `status-ring ${RING_CLASSES[type] || ''}`;
  El.statusWrap.className = `status-wrap ${WRAP_CLASSES[type] || ''}`;
  El.statusEmoji.textContent = emoji;
  El.statusMsg.textContent   = msg;
  announceToSR(msg);
}

function addBubble(sender, text) {
  const isBot = sender === 'bot';
  const art   = document.createElement('article');
  art.className = `bubble ${isBot ? 'bot-bubble' : 'user-bubble'}`;
  art.setAttribute('aria-label', isBot ? `Didi says: ${text}` : `You said: ${text}`);

  const now  = new Date();
  const time = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  art.innerHTML = `
    <span class="bbl-who" aria-hidden="true">${isBot ? '🧕 Didi' : '👤 Aap'}</span>
    <p class="bbl-text">${escapeHTML(text)}</p>
    <time class="bubble-time" datetime="${now.toISOString()}">${time}</time>
  `;
  El.chatLog.appendChild(art);
  El.chatLog.scrollTop = El.chatLog.scrollHeight;
}

function announceToSR(text) {
  El.srLive.textContent = '';
  requestAnimationFrame(() => { El.srLive.textContent = text; });
}

function escapeHTML(str) {
  return str
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}


/* ══════════════════════════════════════════
   SESSION TIMER + STATS
══════════════════════════════════════════ */
let _timerHandle = null;

function startSessionTimer() {
  clearInterval(_timerHandle);
  _timerHandle = setInterval(() => {
    State.sessionSeconds++;
    if (El.statMins) El.statMins.textContent = Math.floor(State.sessionSeconds / 60);
  }, 1000);
}

function stopSessionTimer() { clearInterval(_timerHandle); }

function updateStats() {
  if (El.statSentences) El.statSentences.textContent = State.sentencesSpoken;
  if (El.statWords)     El.statWords.textContent     = State.wordsLearned;
}


/* ══════════════════════════════════════════
   KEYBOARD SHORTCUTS
══════════════════════════════════════════ */
document.addEventListener('keydown', (e) => {
  if (['BUTTON','INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;

  // R = repeat last bot message
  if (e.code === 'KeyR' && State.mode !== Mode.LOCKED) {
    e.preventDefault();
    if (State.lastBotText && !State.isSpeaking) {
      _stopAudio();
      speak(State.lastBotText, State.lastBotLang);
    }
  }

  // Escape = exit sub-mode (keyboard accessibility)
  if (e.code === 'Escape' && State.subMode !== SubMode.NONE) {
    e.preventDefault();
    _setSubMode(SubMode.NONE);
    _botSay('Sub-mode se wapas aa gayi. Normal chat mein hoon ab!', 'hinglish');
  }
});


/* ══════════════════════════════════════════
   PAGE UNLOAD — save session before tab closes
══════════════════════════════════════════ */
window.addEventListener('beforeunload', () => { _autoSaveSession(); });
window.addEventListener('pagehide',     () => { _autoSaveSession(); });


/* ══════════════════════════════════════════
   HEALTH CHECK
══════════════════════════════════════════ */
async function checkHealth() {
  try {
    const d = await fetch('/health', { signal: AbortSignal.timeout(4000) }).then(r => r.json());
    const ttsOk = d.tts === 'google-gtts-online';
    const brainLabels = { groq: 'Google TTS · Groq AI ✓', gemini: 'Google TTS · Gemini AI ✓' };
    El.ttsLabel.textContent = ttsOk ? (brainLabels[d.brain] || 'Google TTS ✓') : 'TTS Ready ✓';
    El.ttsDot.className = 'tts-dot online';
  } catch (_) {
    El.ttsLabel.textContent = 'Connecting…';
  }
}


/* ══════════════════════════════════════════
   BROWSER SUPPORT CHECK
══════════════════════════════════════════ */
function checkBrowserSupport() {
  if (!SpeechRecognition) {
    El.overlay.innerHTML = `
      <div class="overlay-card">
        <div class="overlay-emoji">🚫</div>
        <h1 class="overlay-title" style="color:#f85149">Chrome Required</h1>
        <p class="overlay-hint">Voice features sirf Google Chrome mein kaam karti hain.</p>
        <p class="overlay-hint-en">Please open this page in Google Chrome browser.</p>
      </div>`;
    return false;
  }
  return true;
}


/* ══════════════════════════════════════════
   INIT
══════════════════════════════════════════ */
(function init() {
  if (!checkBrowserSupport()) return;
  checkHealth();
  prewarm('Namaste beta! Main sun rahi hoon. Shuru karo boliye, aur hum English practice karenge!', 'hinglish');
  prewarm('Bahut achha! Ab apna student ID number boliye. Ek se bees tak koi bhi number boliye.', 'hinglish');
  announceToSR('Didi tutor bot tayaar hai. Screen tap karo shuru karne ke liye.');
  console.log(
    '%c🎓 Didi v6 — Voice-Only + Quiz + Story + Pronunciation\n%cTap → "Shuru karo" → ID → talk freely',
    'color:#56d364;font-size:14px;font-weight:bold;',
    'color:#8b949e;font-size:12px;'
  );
})();
