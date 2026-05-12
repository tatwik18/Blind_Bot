"""
Student Proficiency Level Classifier
=====================================
Three-tier classification pipeline:

  Tier 1 — Ensemble: TextCNN + LSTM
    CNN  (cnn_text.py):  parallel conv filters capture WHAT words appear
    LSTM (lstm_text.py): bidirectional LSTM captures HOW language evolves
    If both available → majority vote; if they disagree → LSTM wins
    (LSTM has sequential context CNN lacks)

  Tier 2 — TextCNN only (if LSTM unavailable)
    Requires PyTorch. Auto-trains on first run.

  Tier 3 — Rule-based scoring (always available, no dependencies)
    Extracts 4 linguistic features with threshold scoring.

classify_proficiency() transparently tries Tier 1 → 2 → 3.
"""

import re

# ── Optional CNN tier ─────────────────────────────────────────────────────────
try:
    from cnn_text import predict_proficiency as _cnn_predict, is_ready as _cnn_ready
    _CNN_AVAILABLE = True
except Exception:
    _CNN_AVAILABLE = False

# ── Optional LSTM tier ────────────────────────────────────────────────────────
try:
    from lstm_text import predict_proficiency as _lstm_predict, is_ready as _lstm_ready
    _LSTM_AVAILABLE = True
except Exception:
    _LSTM_AVAILABLE = False

_MEANING_PATTERNS = [
    r'ka matlab', r'kya matlab', r'matlab kya', r'what does',
    r'meaning of', r'ka arth', r'iska matlab', r'mujhe samajh',
    r'kya hota hai', r'kya hai yeh', r'what is',
]

_COMPLEX_CONJUNCTIONS = [
    'because', 'although', 'however', 'therefore', 'whereas',
    'unless', 'despite', 'furthermore', 'nevertheless', 'moreover',
    'consequently', 'otherwise', 'nevertheless',
]


def _user_messages(session):
    return [
        t['content'] for t in session
        if t.get('role') == 'user' and t.get('content', '').strip()
    ]


def _avg_word_count(messages):
    if not messages:
        return 0.0
    return sum(len(m.split()) for m in messages) / len(messages)


def _vocab_richness(messages):
    """Type-token ratio across all user messages (unique / total English words)."""
    all_words = re.findall(r'\b[a-zA-Z]+\b', ' '.join(messages).lower())
    if len(all_words) < 5:
        return 0.0
    return len(set(all_words)) / len(all_words)


def _meaning_ask_rate(messages):
    """Fraction of messages where the student asks for a word's meaning."""
    if not messages:
        return 0.0
    count = sum(
        1 for m in messages
        if any(re.search(p, m.lower()) for p in _MEANING_PATTERNS)
    )
    return count / len(messages)


def _complex_sentence_rate(messages):
    """Fraction of messages containing complex English conjunctions."""
    if not messages:
        return 0.0
    count = sum(
        1 for m in messages
        if any(c in m.lower() for c in _COMPLEX_CONJUNCTIONS)
    )
    return count / len(messages)


def _rule_based(session):
    """
    Pure-Python rule-based proficiency scoring (Tier 2 fallback).
    Scoring (max 7, min -1):
      +2 avg words >=8,  +1 >=4
      +2 vocab richness >=0.65,  +1 >=0.4
      -1 meaning-ask rate >0.3,  +1 <0.1
      +2 complex-conjunction rate >=0.2,  +1 >=0.08
    """
    msgs = _user_messages(session)
    if len(msgs) < 4:
        return None

    avg_wc       = _avg_word_count(msgs)
    vocab_rich   = _vocab_richness(msgs)
    meaning_rate = _meaning_ask_rate(msgs)
    complex_rate = _complex_sentence_rate(msgs)

    score = 0
    if avg_wc >= 8:      score += 2
    elif avg_wc >= 4:    score += 1
    if vocab_rich >= 0.65:   score += 2
    elif vocab_rich >= 0.4:  score += 1
    if meaning_rate > 0.3:   score -= 1
    elif meaning_rate < 0.1: score += 1
    if complex_rate >= 0.2:  score += 2
    elif complex_rate >= 0.08: score += 1

    if score >= 5: return 'Advanced'
    if score >= 2: return 'Intermediate'
    return 'Beginner'


def classify_proficiency(session):
    """
    Returns 'Beginner', 'Intermediate', or 'Advanced'.
    Returns None when there are fewer than 4 user messages.

    Pipeline:
      Tier 1 — CNN + LSTM ensemble (majority vote; LSTM wins on tie)
      Tier 2 — CNN only
      Tier 3 — Rule-based fallback
    """
    msgs = _user_messages(session)
    if len(msgs) < 4:
        return None

    cnn_label  = None
    lstm_label = None

    # ── Tier 1: Ensemble CNN + LSTM ───────────────────────────────────────────
    if _CNN_AVAILABLE and _cnn_ready():
        cnn_label, _ = _cnn_predict(session)

    if _LSTM_AVAILABLE and _lstm_ready():
        lstm_label, _ = _lstm_predict(session)

    if cnn_label and lstm_label:
        # Both available — majority vote (agree → use it; disagree → LSTM wins)
        return cnn_label if cnn_label == lstm_label else lstm_label

    # ── Tier 2: Single model ──────────────────────────────────────────────────
    if lstm_label:
        return lstm_label
    if cnn_label:
        return cnn_label

    # ── Tier 3: Rule-based fallback ───────────────────────────────────────────
    return _rule_based(session)


def classify_proficiency_with_source(session):
    """
    Same as classify_proficiency() but also returns the source string.
    Returns (label, source).
    """
    msgs = _user_messages(session)
    if len(msgs) < 4:
        return None, None

    cnn_label, cnn_conf   = None, None
    lstm_label, lstm_conf = None, None

    if _CNN_AVAILABLE and _cnn_ready():
        cnn_label, cnn_conf = _cnn_predict(session)

    if _LSTM_AVAILABLE and _lstm_ready():
        lstm_label, lstm_conf = _lstm_predict(session)

    if cnn_label and lstm_label:
        if cnn_label == lstm_label:
            return cnn_label, f'ensemble-agree cnn={cnn_conf:.0%} lstm={lstm_conf:.0%}'
        else:
            return lstm_label, f'ensemble-disagree lstm={lstm_conf:.0%} wins'

    if lstm_label:
        return lstm_label, f'lstm ({lstm_conf:.0%})'
    if cnn_label:
        return cnn_label, f'cnn ({cnn_conf:.0%})'

    return _rule_based(session), 'rules'


def get_proficiency_prompt_addon(level):
    """Returns a system-prompt suffix that tells Didi how to pitch her teaching."""
    if level == 'Beginner':
        return (
            "\n\n[STUDENT PROFILE — AUTO DETECTED: BEGINNER] "
            "Is student ne abhi English seekhna shuru kiya hai. "
            "Bahut simple words use karo, short sentences mein baat karo, "
            "aur har English word ka Hindi matlab zaroor batao. "
            "Celebrate even tiny efforts enthusiastically."
        )
    if level == 'Intermediate':
        return (
            "\n\n[STUDENT PROFILE — AUTO DETECTED: INTERMEDIATE] "
            "Is student ko basic English aati hai. "
            "Thoda challenging vocabulary introduce karo, "
            "simple grammar concepts Hindi mein explain karo, "
            "aur longer sentences banane ke liye encourage karo."
        )
    if level == 'Advanced':
        return (
            "\n\n[STUDENT PROFILE — AUTO DETECTED: ADVANCED] "
            "Is student ki English kaafi achhi hai. "
            "Advanced vocabulary aur idioms freely use karo, "
            "complex grammar structures naturally discuss karo, "
            "aur nuanced conversation mein engage karo."
        )
    return ""
