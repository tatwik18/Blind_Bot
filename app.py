"""
=============================================================
  Didi — Hinglish English Tutor  v5  (AI-Only Edition)
=============================================================
  Backend   : Python Flask
  TTS       : gTTS  (Google Text-to-Speech, free online)
  STT       : Web Speech API / Chrome (en-IN Hinglish)
  AI Brain  : Grok (primary) → Gemini (fallback)

  Setup:
    1. Add keys to .env:
         GROK_API_KEY=your_key
         GEMINI_API_KEY=your_key
    2. python app.py
=============================================================
"""

import os
import re
import sys
import json
import random
import hashlib
import difflib
import datetime
import tempfile
import threading
import requests

from classifier import classify_proficiency, get_proficiency_prompt_addon
from clustering  import cluster_students
import database  as db
from quiz_data   import QUIZ_QUESTIONS, PRONUNCIATION_WORDS
from story_data  import STORIES
from cnn_text    import ensure_model_trained as _cnn_text_init
from cnn_audio   import score_pronunciation as cnn_score_pronunciation
from cnn_audio   import detect_confidence, get_didi_comfort_line, cnn_status

# Force UTF-8 output on Windows to avoid cp1252 encoding errors with Unicode chars
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from gtts import gTTS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from google import genai as _genai
    from google.genai import types as _gtypes
    _GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
except ImportError:
    _genai      = None
    _gtypes     = None
    _GEMINI_KEY = ""

_gemini_client = None

_GROQ_KEY   = os.getenv("GROQ_API_KEY", "").strip()
_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"


# ─────────────────────────────────────────────
#  Didi's Teaching System Prompt
# ─────────────────────────────────────────────
DIDI_SYSTEM_PROMPT = """You are a gentle English learning voice chatbot designed especially for blind students in India who may feel shy, scared, or nervous while learning. Your name is Didi. You speak in Hinglish — a natural and warm mix of Hindi and English, like a caring elder sister.

━━━ CORE MISSION ━━━
Help students learn English confidently from zero to advanced level through stories, real conversations, vocabulary building, simple grammar, listening skills, speaking confidence, sentence formation, daily life English, fluency development, and confidence building.

━━━ ABSOLUTE TOP PRIORITY — STORY OR LISTENING REQUEST ━━━
If the student's message contains __STORY_NOW__, or they say anything like:
"mujhe story sunao", "kahani sunao", "main bas sunna chahta hu", "aaj aap bolo", "koi story sunao", "kissa sunao", "story chahiye" —
YOU MUST tell a story IMMEDIATELY. No asking them to repeat. No finishing a lesson first. No conditions.
The student is BLIND. What they ask for RIGHT NOW is what matters most.

HOW TO TELL THE STORY — smooth, natural flow, no forced repetition:
Start with: "Ek choti si story suno."
Then tell 3 to 4 sentences in simple English. After each sentence, say "Matlab:" and give the Hindi meaning.
End with a one-line moral: "Moral: [lesson]."
Do NOT say "Mere saath boliye" or ask for repetition during a story unless the student asks to practise.

Example story:
"Ek choti si story suno. Once there was a little bird. Matlab: Ek chidiya thi. She wanted to fly high. Matlab: Woh ooncha udna chahti thi. Every day she learned something new. Matlab: Woh roz kuch naya seekhti thi. One day she touched the clouds. Matlab: Ek din woh badlon tak pahunch gayi. Moral: Small steps create big success."

Always tell a fresh, different story each time. Never repeat the same story.

━━━ UNDERSTAND INTENT BEFORE REPLYING ━━━
Read what the student actually wants before responding.

LISTENING MODE — if they say "main bas sunna chahta hu", "aaj aap bolo", "story sunao":
Tell stories smoothly. Explain meanings gently. No interruptions. No forced repetition. Keep the flow natural.

CONVERSATION LEARNING MODE — if they say "mujhe English seekhni hai", "mere saath baat karo", "conversation karo", "mujhe improve karna hai":
Talk naturally in two-way conversation. Ask simple questions and wait for the reply. Improve sentences softly. Explain mistakes kindly. Slowly increase the level from beginner to advanced. Keep it natural, never like an exam.

━━━ LEARNING PATH ━━━
Beginner: basic words, greetings, self-introduction, yes and no answers, simple daily sentences.
Intermediate: longer sentences, tense basics, daily conversations, question answering, confidence speaking.
Advanced: fluent conversation, sharing opinions, storytelling, professional English, grammar refinement, natural speaking style.

━━━ CONVERSATION MODE — WHEN STUDENT WANTS TO TALK IN ENGLISH ━━━
If student says anything like "chalo english mein baat karte hain", "let us talk", "english mein bolna hai", "conversation karo":
Start a real two-way English conversation IMMEDIATELY.
Ask natural questions like a friend would. Examples:
"Great! What is your name and where are you from?"
"Wonderful! Tell me — what do you like to do in your free time?"
"Nice! Do you have any brothers or sisters?"
"Interesting! What is your favourite subject in school?"
Keep the conversation flowing naturally. One question at a time. Wait for their answer. Then respond to what they said and ask the next question.
Do NOT go back to drilling sentences. This is free conversation time.

━━━ AUTO-CORRECT — WHATSAPP STYLE ━━━
When the student makes a small English mistake during conversation, correct it INLINE without stopping the conversation flow. Like WhatsApp autocorrect — smooth and quick.

HOW TO DO IT (always in this order):
1. First acknowledge what they said positively
2. Slip in the correction naturally in ONE short line
3. Immediately continue the conversation — ask the next question or respond to their answer

Examples:

Student says: "I goes to school every day."
Didi says: "Nice! Small tip — we say I go, not I goes. I go to school every day. So, which subject do you like most in school?"

Student says: "She don't like mango."
Didi says: "Good try! We say she does not like — she does not like mango. Anyway, what about you — what is your favourite fruit?"

Student says: "Yesterday I go to market."
Didi says: "Almost! Past mein went use hota hai — yesterday I went to market. What did you buy there?"

The key rule: correction is ONE line, then the conversation MUST continue. Never stop and drill. Never ask them to repeat unless they ask for it.

━━━ GRAMMAR CONCEPTS — HINDI ONLY (CRITICAL) ━━━
If the student asks about ANY grammar term — noun, pronoun, verb, adjective, adverb, preposition, conjunction, tense, article, sentence, subject, object, plural, singular — ALWAYS explain it in Hindi or Hinglish. NEVER explain grammar in English. These students are learning English; they do not know English grammar terms yet. Give the Hindi/Hinglish explanation, then one simple example.

Example: Student asks "preposition kya hota hai?"
WRONG: "A preposition is a word that shows the relationship between a noun and other words."
RIGHT: "Preposition do cheezein ke beech ka rishta batata hai. Jaise: in, on, at, under, above. Example: The book is on the table. Yahan 'on' ek preposition hai."

━━━ MISTAKE HANDLING ━━━
When student makes a mistake:
Acknowledge warmly, correct in one line, then move forward immediately. Never stop the conversation. Never make the student feel ashamed.

━━━ IF STUDENT IS NERVOUS ━━━
Say: "Koi tension nahi. Hum araam se seekhenge." or "Galti karna learning ka part hai." or "Aap bahut accha kar rahe ho. Main aapke saath hoon." or "Main hoon na, dariye mat bilkul."

━━━ VOICE INPUT — CRITICAL RULE ━━━
This student speaks through a microphone. Voice recognition NEVER produces punctuation marks.
So "good morning how are you" is IDENTICAL to "Good morning, how are you?" — they are the same.
"i am fine thank you" is IDENTICAL to "I am fine, thank you." — they are the same.
NEVER penalize, correct, or ask the student to repeat because of missing:
- question marks (?)
- commas (,)
- full stops (.)
- capital letters
- exclamation marks (!)
These do not exist in spoken voice. Treat the words alone as the answer.
If the words are correct, the answer is correct. Praise immediately and move forward.

━━━ LANGUAGE AND FORMAT RULES ━━━
Speak 65% Hinglish or Hindi and 35% English. Never sound like a textbook.
Keep responses to 3 to 4 short sentences maximum. The student is blind and hears this, not reads it.
Never use bullet points, dashes, or visual lists in your reply.
Never say "look here", "see this", or anything that requires vision.
When teaching a new English word, break it gently: Beau-ti-ful, Com-for-ta-ble.
If student says "__nudge__", gently re-prompt with exactly what they were practising last from the conversation history.
Tone always: patient, supportive, calm, friendly. Never strict. Never scary. Never like a school teacher forcing answers.

━━━ MAIN GOAL ━━━
Make the student fearless, confident, and fluent in English through simple two-way communication. Always behave like a caring teacher-friend. This student cannot see. Your voice is their window to the world.

━━━ SESSION TRACKING (SILENT) ━━━
Throughout every session, silently track in your memory:
1. Every new English word introduced, its Hindi meaning, and the example sentence used.
2. Every sentence the student attempted — was it correct, partially correct, or needed help.
3. Any grammar or language concept explained (e.g., pronoun, tense, preposition).
4. Moments the student got something right confidently — these are praise points.
5. Words or sentences the student struggled with more than once — these are gentle focus points.
Never mention this tracking to the student during the session.

━━━ SUMMARY — WHEN YOU SEE __SUMMARY_NOW__ [name] ━━━
Generate a warm, spoken 3-part summary for [name]. Rules:
- NEVER use bullet points, numbers, or lists — speak in flowing sentences only.
- Keep the full summary under 60 seconds of speaking time.
- Always begin with genuine, specific praise. End with one encouraging line.
- Never mention mistakes, failures, or how many times something was wrong.
- Never ask a question during the summary.
- Speak slowly and warmly throughout.

PART 1 — CELEBRATION (5 sec): Warm specific praise referencing something real from the session.
Hindi: "[Name], aaj tumne bahut achha kaam kiya! Tumne itni himmat se seekha, mujhe bahut khushi hui."

PART 2 — WHAT WE LEARNED (30 sec): Story-style recap of words, sentences, concepts. Repeat each word and its Hindi meaning slowly so the child hears it again.
Hindi example: "Aaj humne ek nayi word seekhi — 'Inspire'. Hindi mein iska matlab hota hai 'prerit karna'. Humne yeh bhi seekha ki pronoun kya hota hai — jaise 'Rahul' ki jagah hum 'vah' bolte hain."

PART 3 — GENTLE FOCUS (15 sec): Pick ONE thing that needs more practice, frame it as exciting not as weakness, then warm goodbye.
Hindi: "Agli baar hum '...' aur practice karenge — yeh bahut maza aayega. Bahut bahut shabash [name]! Kal phir milenge!"

━━━ LAST SESSION SUMMARY — WHEN YOU SEE __LAST_CLASS__ [name] ━━━
Summarize the conversation history provided as context. Use the same 3-part warm format but say "pichli baar" or "last time" instead of "aaj". Help the student remember what they learned in the previous session before starting today.

━━━ STUDENT WELCOME — WHEN YOU SEE __NEW_STUDENT__ [name] ━━━
Welcome [name] warmly as a brand new student. Express excitement about meeting them. Make them feel safe and comfortable. Ask what they would like to learn or practice today.
Example: "Namaste [name]! Main bahut khush hoon aapse milke! Main aapki Didi hoon, aapki English teacher. Aap bilkul tension mat lo — hum saath milke seekhenge. Toh batao, aaj kya seekhna hai?"

━━━ RETURNING STUDENT WELCOME — WHEN YOU SEE __RETURNING_STUDENT__ [name] ━━━
Greet [name] warmly by name. Express genuine happiness they came back. Make them feel remembered and valued. Ask what they want to continue or start.
Example: "Arre [name]! Wapas aaye, bahut achha kiya! Main aapka intezaar kar rahi thi. Chalo aaj phir kuch naya seekhte hain — kya bolna hai aaj?"

━━━ IMPORTANT — SUMMARY RULE ━━━
NEVER offer, suggest, or start a summary on your own. Only generate a summary when you receive the __SUMMARY_NOW__ or __LAST_CLASS__ tags. During a normal session, continue teaching naturally. """


# ─────────────────────────────────────────────
#  Gemini model init
# ─────────────────────────────────────────────
def _init_gemini():
    global _gemini_client
    if _genai and _GEMINI_KEY:
        try:
            _gemini_client = _genai.Client(api_key=_GEMINI_KEY)
            print("  [Gemini] Client ready ✓  (gemini-2.5-flash)")
        except Exception as e:
            print(f"  [Gemini] Init failed: {e}")

_init_gemini()


# ─────────────────────────────────────────────
#  Student Database  (students.json, 20 slots)
# ─────────────────────────────────────────────
STUDENT_DB_PATH = os.path.join(os.path.dirname(__file__), 'students.json')
_db_lock = threading.Lock()


def _load_students() -> dict:
    with _db_lock:
        if os.path.exists(STUDENT_DB_PATH):
            try:
                with open(STUDENT_DB_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}


def _save_students(db: dict):
    with _db_lock:
        with open(STUDENT_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
#  App Setup
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)


# ─────────────────────────────────────────────
#  TTS Cache
# ─────────────────────────────────────────────
TTS_CACHE_DIR = os.path.join(tempfile.gettempdir(), "didi_tts_cache")
os.makedirs(TTS_CACHE_DIR, exist_ok=True)
MAX_CACHE_FILES = 300


def _cleanup_cache():
    try:
        files = [
            (os.path.getmtime(os.path.join(TTS_CACHE_DIR, f)),
             os.path.join(TTS_CACHE_DIR, f))
            for f in os.listdir(TTS_CACHE_DIR)
            if f.endswith(".mp3")
        ]
        if len(files) > MAX_CACHE_FILES:
            files.sort()
            for _, path in files[:len(files) - MAX_CACHE_FILES]:
                os.remove(path)
    except Exception:
        pass


def _cache_path(text: str, lang: str, slow: bool) -> str:
    key = hashlib.md5(f"{text}|{lang}|{slow}".encode()).hexdigest()
    return os.path.join(TTS_CACHE_DIR, f"{key}.mp3")


def clean_for_tts(text: str) -> str:
    text = text.replace('...', ', ')
    text = text.replace('…',   ', ')
    text = text.replace(':', ', ')
    text = text.replace('!', '. ')
    text = text.replace(';', ', ')
    text = re.sub(r'[*_""`~]', '', text)
    text = re.sub(r'[\[\]{}]', '', text)
    text = re.sub(r',\s*,', ', ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def generate_audio(text: str, lang: str, tld: str, slow: bool, path: str):
    tts = gTTS(text=clean_for_tts(text), lang=lang, tld=tld, slow=slow)
    tts.save(path)


# ─────────────────────────────────────────────
#  gTTS Language Selector
# ─────────────────────────────────────────────
def gtts_params(detected_lang: str, slow: bool) -> tuple[str, str, bool]:
    if detected_lang == "english":
        return "en", "co.in", slow
    return "hi", "com", slow


# ─────────────────────────────────────────────
#  Language Detection (for TTS voice selection)
# ─────────────────────────────────────────────
HINDI_MARKERS = {
    "mujhe", "main", "hoon", "hai", "hain", "kya", "karo", "beta",
    "didi", "bolo", "seekhna", "sikhna", "chahiye", "nahi", "aap",
    "tum", "ek", "aaj", "kal", "yahan", "wahan", "matlab", "boliye",
    "suniye", "achha", "acha", "theek", "shukriya", "namaste",
    "namaskar", "alvida", "phir", "dobara", "baat", "galti", "koi",
    "bahut", "thoda", "zyada", "mere", "saath", "shabd", "rang",
    "ginti", "dheere", "dhire", "slowly", "repeat", "practice",
    "vocab", "aur", "lekin", "kyun", "kyunki", "woh", "yeh", "isse",
    "usse", "hame", "humko", "tumhe", "apna", "apni", "mera", "meri",
}

def detect_language(text: str) -> str:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return "hinglish"
    h = sum(1 for w in words if w in HINDI_MARKERS)
    r = h / len(words)
    if r > 0.45:
        return "hindi"
    if r > 0.12:
        return "hinglish"
    return "english"


# ─────────────────────────────────────────────
#  Gemini AI Response
# ─────────────────────────────────────────────
def gemini_response(message: str, history: list, extra_prompt: str = "") -> str:
    gem_history = []
    for turn in history[-14:]:
        role    = turn.get("role", "user")
        content = turn.get("content", "").strip()
        if not content:
            continue
        if role == "assistant":
            role = "model"
        if role in ("user", "model"):
            gem_history.append(
                _gtypes.Content(role=role, parts=[_gtypes.Part(text=content)])
            )

    contents = gem_history + [
        _gtypes.Content(role="user", parts=[_gtypes.Part(text=message)])
    ]
    config = _gtypes.GenerateContentConfig(
        system_instruction=DIDI_SYSTEM_PROMPT + extra_prompt,
        max_output_tokens=600,
        temperature=0.75,
    )
    response = _gemini_client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=contents,
        config=config,
    )
    return response.text.strip()


# ─────────────────────────────────────────────
#  Groq (GroqCloud) Response
# ─────────────────────────────────────────────
def groq_response(message: str, history: list, extra_prompt: str = "") -> str:
    messages = [{"role": "system", "content": DIDI_SYSTEM_PROMPT + extra_prompt}]
    for turn in history[-14:]:
        role    = turn.get("role", "user")
        content = turn.get("content", "").strip()
        if content and role in ("user", "assistant"):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    resp = requests.post(
        _GROQ_URL,
        headers={
            "Authorization": f"Bearer {_GROQ_KEY}",
            "Content-Type" : "application/json",
        },
        json={
            "model"      : _GROQ_MODEL,
            "messages"   : messages,
            "max_tokens" : 600,
            "temperature": 0.75,
        },
        timeout=25,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Groq API {resp.status_code}: {resp.text[:200]}")
    return resp.json()["choices"][0]["message"]["content"].strip()


# ─────────────────────────────────────────────
#  Main Response Dispatcher
# ─────────────────────────────────────────────
def get_response(message: str, history: list, extra_prompt: str = "") -> tuple[str, str]:
    """Return (reply_text, source_label). Priority: Groq → Gemini."""
    if _GROQ_KEY:
        try:
            reply = groq_response(message, history, extra_prompt)
            return reply, "groq"
        except Exception as e:
            print(f"[Groq error] {type(e).__name__}: {e}")

    if _gemini_client:
        try:
            reply = gemini_response(message, history, extra_prompt)
            return reply, "gemini"
        except Exception as e:
            print(f"[Gemini error] {type(e).__name__}: {e}")

    return "Beta, abhi network slow hai. Thodi der mein phir try karo.", "error"


# ─────────────────────────────────────────────
#  Daily Vocab
# ─────────────────────────────────────────────
DAILY_VOCAB = [
    {"word": "Courage",      "hindi": "Himmat",          "example": "You have the courage to learn English."},
    {"word": "Patience",     "hindi": "Sabr",            "example": "Learning needs patience."},
    {"word": "Brilliant",    "hindi": "Bahut smart",     "example": "You are a brilliant student."},
    {"word": "Resilient",    "hindi": "Mazboot",         "example": "You are resilient and strong."},
    {"word": "Grateful",     "hindi": "Shukarguza",      "example": "I am grateful for my teacher."},
    {"word": "Determined",   "hindi": "Pakka iraada",    "example": "I am determined to learn English."},
    {"word": "Perseverance", "hindi": "Lage rehna",      "example": "Perseverance is the key to success."},
    {"word": "Inspire",      "hindi": "Prerit karna",    "example": "You inspire me every day."},
    {"word": "Achieve",      "hindi": "Hasil karna",     "example": "I will achieve my goals."},
    {"word": "Confident",    "hindi": "Atma-vishwas",    "example": "I feel confident when I practice."},
    {"word": "Honest",       "hindi": "Imaandar",        "example": "An honest person is respected by all."},
    {"word": "Curious",      "hindi": "Jigyaasu",        "example": "Be curious and keep learning."},
    {"word": "Humble",       "hindi": "Vineet",          "example": "Great people are always humble."},
    {"word": "Generous",     "hindi": "Udaar",           "example": "She is very generous and kind."},
    {"word": "Dedication",   "hindi": "Mehnat",          "example": "Dedication will take you far in life."},
]


# ─────────────────────────────────────────────
#  Pre-cache common startup phrases
# ─────────────────────────────────────────────
PRECACHE_PHRASES = [
    ("Namaste beta! Main hoon aapki Didi, aapki English teacher. Chalo shuru karte hain!", "hinglish"),
    ("Koi baat nahi beta! Galti se hi toh seekhte hain. Wapas try karo!", "hinglish"),
    ("Bahut acha beta! Shabash! Chalo aur aage badhte hain.", "hinglish"),
    ("Bye bye beta! Aaj bahut acha practice kiya. Kal phir aana!", "hinglish"),
]

def _precache_worker():
    for text, lang_hint in PRECACHE_PHRASES:
        path = _cache_path(text, lang_hint, False)
        if not os.path.exists(path):
            try:
                g_lang, tld, slow = gtts_params(detect_language(text), False)
                generate_audio(text, g_lang, tld, slow, path)
            except Exception as e:
                print(f"  [TTS pre-cache] FAIL: {e}")


# ─────────────────────────────────────────────
#  Flask Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    today_idx  = datetime.date.today().toordinal() % len(DAILY_VOCAB)
    daily_word = DAILY_VOCAB[today_idx]
    return render_template("index.html", daily_word=daily_word)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if not data or not data.get("message", "").strip():
        return jsonify({"error": "No message provided"}), 400

    msg      = data["message"].strip()
    history  = data.get("history", [])
    language = detect_language(msg)

    level       = classify_proficiency(history)
    extra_prompt = get_proficiency_prompt_addon(level) if level else ""
    reply, source = get_response(msg, history, extra_prompt)

    return jsonify({
        "response"   : reply,
        "source"     : source,
        "language"   : language,
        "proficiency": level,
    })


@app.route("/tts")
def tts_endpoint():
    text      = request.args.get("text", "").strip()[:2000]
    lang_hint = request.args.get("lang", "hinglish")
    slow_raw  = request.args.get("slow", "false").lower()
    slow      = slow_raw == "true"

    if not text:
        return jsonify({"error": "No text"}), 400

    path = _cache_path(text, lang_hint, slow)

    if not os.path.exists(path):
        try:
            g_lang, tld, is_slow = gtts_params(lang_hint, slow)
            generate_audio(text, g_lang, tld, is_slow, path)
            threading.Thread(target=_cleanup_cache, daemon=True).start()
        except Exception as e:
            print(f"[gTTS error] {e}")
            return jsonify({"error": f"TTS generation failed: {e}"}), 500

    return send_file(
        path,
        mimetype="audio/mpeg",
        as_attachment=False,
        conditional=True,
    )


@app.route("/health")
def health():
    if _GROQ_KEY:
        brain = "groq"
    elif _gemini_client:
        brain = "gemini"
    else:
        brain = "none"
    return jsonify({
        "status"  : "ok",
        "tts"     : "google-gtts-online",
        "brain"   : brain,
        "fallback": "web-speech-api",
        "cnn"     : cnn_status(),
    })


@app.route("/vocab/daily")
def vocab_daily():
    idx = datetime.date.today().toordinal() % len(DAILY_VOCAB)
    return jsonify(DAILY_VOCAB[idx])


@app.route("/vocab/random")
def vocab_random():
    return jsonify(random.choice(DAILY_VOCAB))


# ─────────────────────────────────────────────
#  Student Routes
# ─────────────────────────────────────────────

@app.route("/student/check")
def student_check():
    """Check if a student ID (1–20) exists. Returns name + last_session if found."""
    sid = request.args.get("id", "").strip()
    if not sid.isdigit() or not (1 <= int(sid) <= 20):
        return jsonify({"error": "Invalid ID — must be 1 to 20"}), 400
    db = _load_students()
    if sid in db:
        return jsonify({
            "exists"      : True,
            "name"        : db[sid]["name"],
            "last_session": db[sid].get("last_session", []),
        })
    return jsonify({"exists": False})


@app.route("/student/register", methods=["POST"])
def student_register():
    """Register a new student for an unclaimed ID."""
    data = request.get_json(silent=True) or {}
    sid  = str(data.get("id",   "")).strip()
    name = str(data.get("name", "")).strip()[:60]

    if not sid.isdigit() or not (1 <= int(sid) <= 20):
        return jsonify({"error": "Invalid ID"}), 400
    if not name:
        return jsonify({"error": "Name required"}), 400

    db = _load_students()
    if sid in db:
        return jsonify({"error": "ID already taken", "name": db[sid]["name"]}), 409

    db[sid] = {
        "name"        : name,
        "created_at"  : str(datetime.date.today()),
        "last_session": [],
    }
    _save_students(db)
    return jsonify({"success": True, "name": name})


@app.route("/student/save_session", methods=["POST"])
def save_session():
    """Persist the last 20 chat turns for a student."""
    data    = request.get_json(silent=True) or {}
    sid     = str(data.get("id",      "")).strip()
    history = data.get("history", [])

    db = _load_students()
    if sid in db:
        db[sid]["last_session"] = history[-20:]
        db[sid]["last_seen"]    = str(datetime.date.today())
        level = classify_proficiency(history)
        if level:
            db[sid]["proficiency"] = level
        _save_students(db)
    return jsonify({"success": True})


@app.route("/teacher")
def teacher_dashboard():
    """Teacher-facing page — shows all student accounts and their saved histories."""
    db = _load_students()
    # Build a list of all 20 slots, filled or empty
    slots = []
    for i in range(1, 21):
        sid = str(i)
        if sid in db:
            s       = db[sid]
            session = s.get("last_session", [])
            # Use stored proficiency or compute it on-the-fly
            proficiency = s.get("proficiency") or classify_proficiency(session)
            slots.append({
                "id"          : i,
                "occupied"    : True,
                "name"        : s.get("name", "—"),
                "created_at"  : s.get("created_at", "—"),
                "last_seen"   : s.get("last_seen", "—"),
                "msg_count"   : len(session),
                "last_session": session,
                "proficiency" : proficiency,
            })
        else:
            slots.append({"id": i, "occupied": False})

    clusters = cluster_students(db)
    return render_template("teacher.html", slots=slots, clusters=clusters)


@app.route("/teacher/delete/<sid>", methods=["POST"])
def teacher_delete(sid):
    """Delete a student account (teacher action)."""
    db = _load_students()
    if sid in db:
        del db[sid]
        _save_students(db)
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404


@app.route("/summary", methods=["POST"])
def generate_summary():
    """
    Generate a spoken summary using AI.
    Body: { student_name, history, type }
    type = 'current'  → today's session summary
    type = 'last'     → last stored session summary
    """
    data         = request.get_json(silent=True) or {}
    student_name = str(data.get("student_name", "beta")).strip()[:60] or "beta"
    history      = data.get("history", [])
    stype        = data.get("type", "current")

    if stype == "last":
        tag = f"__LAST_CLASS__ {student_name}"
    else:
        tag = f"__SUMMARY_NOW__ {student_name}"

    reply, source = get_response(tag, history)
    return jsonify({"response": reply, "source": source, "language": "hinglish"})


# ─────────────────────────────────────────────
#  Progress Routes
# ─────────────────────────────────────────────

@app.route("/progress/<sid>")
def get_progress(sid):
    """Return lifetime + weekly stats for a student (used by front-end on login)."""
    data = db.get_progress_summary(sid.strip())
    return jsonify(data)


@app.route("/progress/update", methods=["POST"])
def update_progress():
    """
    Called at session end.
    Body: { student_id, name, speaking_attempts, words_practiced, session_minutes }
    """
    data     = request.get_json(silent=True) or {}
    sid      = str(data.get("student_id", "")).strip()
    name     = str(data.get("name", "")).strip()
    speaking = int(data.get("speaking_attempts", 0))
    words    = int(data.get("words_practiced",   0))
    minutes  = int(data.get("session_minutes",   0))

    if not sid or not name:
        return jsonify({"error": "Missing student_id or name"}), 400

    db.ensure_student(sid, name)
    streak = db.update_streak(sid)
    db.add_session_stats(sid, speaking, words, minutes)
    return jsonify({"success": True, "streak": streak})


# ─────────────────────────────────────────────
#  Quiz Routes
# ─────────────────────────────────────────────

@app.route("/quiz/question")
def quiz_question():
    """
    Return one quiz question dict.
    Query params: sid (student id), type (optional: opposite/meaning/grammar/spelling)
    The response includes the accepted answers list so the client can check locally.
    """
    sid    = request.args.get("sid",  "").strip()
    qtype  = request.args.get("type", "").strip()

    difficulty = db.get_adaptive_difficulty(sid) if sid else 'medium'

    # 30 % chance: inject a weak-word spelling question for spaced repetition
    if sid and not qtype:
        weak = db.get_weak_words(sid, limit=3)
        if weak and random.random() < 0.30:
            word = weak[0]['word']
            return jsonify({
                "type"      : "spelling",
                "question"  : f"Let us practise a word you found tricky. How do you spell '{word}'?",
                "answers"   : [word],
                "hint"      : "Spell it letter by letter: " + " ".join(word.upper()),
                "difficulty": difficulty,
                "weak_word" : True,
            })

    # Difficulty pool: harder levels also include easier questions
    diff_pool = {
        'easy'  : ['easy'],
        'medium': ['easy', 'medium'],
        'hard'  : ['medium', 'hard'],
    }.get(difficulty, ['easy', 'medium'])

    all_types    = ['opposite', 'meaning', 'grammar', 'spelling']
    chosen_type  = qtype if qtype in all_types else random.choice(all_types)
    type_pool    = QUIZ_QUESTIONS.get(chosen_type, {})

    candidates = []
    for d in diff_pool:
        candidates.extend(type_pool.get(d, []))

    if not candidates:
        return jsonify({"error": "No questions available"}), 404

    q = random.choice(candidates)
    return jsonify({
        "type"      : chosen_type,
        "question"  : q['q'],
        "answers"   : q['a'],
        "hint"      : q.get('hint', ''),
        "difficulty": difficulty,
    })


@app.route("/quiz/record", methods=["POST"])
def quiz_record():
    """Persist a single quiz answer. Body: { student_id, quiz_type, question, correct }"""
    data    = request.get_json(silent=True) or {}
    sid     = str(data.get("student_id", "")).strip()
    qtype   = str(data.get("quiz_type",  "")).strip()
    question= str(data.get("question",   "")).strip()
    correct = bool(data.get("correct",   False))

    if sid:
        db.record_quiz_answer(sid, qtype, question, correct)
    return jsonify({"success": True})


# ─────────────────────────────────────────────
#  Pronunciation Routes
# ─────────────────────────────────────────────

@app.route("/pronunciation/word")
def pronunciation_word():
    """
    Return the next word to practise.
    Prioritises weak words due for spaced repetition (not tried in 2+ days).
    Query param: sid
    """
    sid        = request.args.get("sid", "").strip()
    difficulty = db.get_adaptive_difficulty(sid) if sid else 'medium'

    # Spaced-repetition: surface weak words overdue for review
    if sid:
        weak   = db.get_weak_words(sid, limit=5)
        cutoff = str(datetime.date.today() - datetime.timedelta(days=2))
        due    = [w for w in weak if w.get('last_tried', '') <= cutoff]
        if due:
            # Match word to PRONUNCIATION_WORDS for syllables
            all_pw = [w for d in ['easy','medium','hard'] for w in PRONUNCIATION_WORDS.get(d, [])]
            match  = next((pw for pw in all_pw if pw['word'] == due[0]['word']), None)
            if match:
                return jsonify({
                    "word"      : match['word'],
                    "syllables" : match['syllables'],
                    "difficulty": difficulty,
                    "revision"  : True,
                })

    diff_pool  = {
        'easy'  : ['easy'],
        'medium': ['easy', 'medium'],
        'hard'  : ['medium', 'hard'],
    }.get(difficulty, ['easy', 'medium'])

    candidates = [w for d in diff_pool for w in PRONUNCIATION_WORDS.get(d, [])]
    entry      = random.choice(candidates) if candidates else {"word": "school", "syllables": "sc-hool"}

    return jsonify({
        "word"      : entry['word'],
        "syllables" : entry['syllables'],
        "difficulty": difficulty,
        "revision"  : False,
    })


@app.route("/pronunciation/check", methods=["POST"])
def pronunciation_check():
    """
    Fuzzy-match expected word vs what the speech recogniser heard.
    Body: { expected, spoken, student_id, syllables }
    Returns: { correct, score, feedback }
    """
    data      = request.get_json(silent=True) or {}
    expected  = str(data.get("expected",   "")).strip().lower()
    spoken    = str(data.get("spoken",     "")).strip().lower()
    sid       = str(data.get("student_id", "")).strip()
    syllables = str(data.get("syllables",  expected)).strip()

    if not expected or not spoken:
        return jsonify({"error": "Missing expected or spoken"}), 400

    # Strip common filler phrases that the recogniser might add
    spoken_clean = re.sub(
        r'\b(i\s+said|the\s+word\s+is|word\s+is|is|the|a|an)\b', '', spoken
    ).strip() or spoken

    ratio   = difflib.SequenceMatcher(None, expected, spoken_clean).ratio()
    correct = ratio >= 0.80

    if correct:
        feedback = random.choice([
            "Excellent! Your pronunciation is perfect!",
            "Shabash! Bilkul sahi bola! Great job!",
            "Waah! Bahut acha bola! Well done!",
        ])
    elif ratio >= 0.55:
        feedback = (
            f"Good try! Thoda aur practice karo. "
            f"Say it like this: {syllables}."
        )
    else:
        feedback = (
            f"Koi baat nahi! Let us try again. "
            f"Listen carefully: {syllables}."
        )

    if sid:
        db.record_pronunciation_attempt(sid, expected, correct)

    return jsonify({"correct": correct, "score": round(ratio * 100), "feedback": feedback})


# ─────────────────────────────────────────────
#  CNN Routes
# ─────────────────────────────────────────────

@app.route("/pronunciation/audio_check", methods=["POST"])
def pronunciation_audio_check():
    """
    CNN-powered pronunciation scoring from raw audio.

    Accepts multipart/form-data:
      audio        : audio file (WAV/MP3/WebM)
      expected     : the target word (str)
      spoken       : speech-recogniser transcript (str, optional)
      syllables    : syllable hint  (str, optional)
      student_id   : student ID     (str, optional — for DB logging)

    Returns: { score, correct, feedback, source }

    If PyTorch / librosa are not installed, falls back to difflib scoring
    on the spoken transcript (same behaviour as /pronunciation/check).
    """
    expected  = request.form.get("expected",   "").strip().lower()
    spoken    = request.form.get("spoken",     "").strip().lower()
    syllables = request.form.get("syllables",  expected).strip()
    sid       = request.form.get("student_id", "").strip()

    if not expected:
        return jsonify({"error": "Missing expected word"}), 400

    audio_bytes = b""
    if "audio" in request.files:
        audio_bytes = request.files["audio"].read()

    result = cnn_score_pronunciation(
        audio_bytes   = audio_bytes,
        expected_word = expected,
        spoken_text   = spoken,
        syllables     = syllables,
    )

    # Persist to DB
    if sid:
        db.record_pronunciation_attempt(sid, expected, result["correct"])

    return jsonify(result)


@app.route("/chat/confidence", methods=["POST"])
def chat_confidence():
    """
    Detect student nervousness from a short voice clip.

    Accepts multipart/form-data:
      audio : audio file (WAV/MP3/WebM) — the student's last recording

    Returns:
      {
        confident : float,
        nervous   : float,
        label     : 'Confident' | 'Nervous',
        source    : 'cnn' | 'heuristic',
        comfort   : str | null   (Hinglish comfort line if nervous)
      }

    Frontend can call this after each speech result and, if comfort is
    non-null, ask Didi to say it before the main reply.
    """
    audio_bytes = b""
    if "audio" in request.files:
        audio_bytes = request.files["audio"].read()

    result         = detect_confidence(audio_bytes)
    result["comfort"] = get_didi_comfort_line(result)
    return jsonify(result)


# ─────────────────────────────────────────────
#  Story Route
# ─────────────────────────────────────────────

@app.route("/story/interactive")
def story_interactive():
    """Return a random story with comprehension questions."""
    return jsonify(random.choice(STORIES))


# ─────────────────────────────────────────────
#  Weak Words Route
# ─────────────────────────────────────────────

@app.route("/words/weak/<sid>")
def weak_words(sid):
    """Return up to 5 words a student most often mispronounces."""
    return jsonify({"words": db.get_weak_words(sid.strip())})


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import os

    PORT = int(os.environ.get("PORT", 5000))

    if _GROQ_KEY:
        brain_label = f"Groq AI ✓  ({_GROQ_MODEL})"
    elif _gemini_client:
        brain_label = "Gemini AI ✓  (gemini-2.5-flash)"
    else:
        brain_label = "No AI keys found — add GROQ_API_KEY or GEMINI_API_KEY to .env"

    print("=" * 62)
    print("  Didi — Hinglish Tutor Bot  v5  (AI-Only)")
    print("=" * 62)
    print(f"  Open this in Chrome → http://localhost:{PORT}")
    print(f"  Brain  : {brain_label}")
    print(f"  Voice  : Google TTS (Indian female voice)")
    print("=" * 62)

    threading.Thread(target=_precache_worker, daemon=True).start()
    # Auto-train TextCNN on synthetic data (skipped if already trained)
    threading.Thread(target=_cnn_text_init, kwargs={"verbose": True}, daemon=True).start()
    app.run(debug=False, host="0.0.0.0", port=PORT)
