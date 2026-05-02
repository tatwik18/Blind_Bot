"""
Student Proficiency Level Classifier
=====================================
Two-tier classification pipeline:

  Tier 1 — TextCNN (cnn_text.py)
    Deep learning model that reads all user messages as a sequence and
    classifies them via parallel convolutional filters (bigrams, trigrams,
    4-grams).  Requires PyTorch.  Auto-trains on first run.

  Tier 2 — Rule-based scoring (this file, always available)
    Extracts 4 linguistic features with threshold scoring.
    No dependencies — always works as a fallback.

classify_proficiency() transparently tries Tier 1 first, then Tier 2.
"""

import re

# ── Optional CNN tier ─────────────────────────────────────────────────────────
try:
    from cnn_text import predict_proficiency as _cnn_predict, is_ready as _cnn_ready
    _CNN_AVAILABLE = True
except Exception:
    _CNN_AVAILABLE = False

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
    Returns None when there are fewer than 4 user messages (not enough data).

    Pipeline:
      1. TextCNN (cnn_text.py) — if PyTorch installed and model trained
      2. Rule-based scoring     — always available, no dependencies
    """
    msgs = _user_messages(session)
    if len(msgs) < 4:
        return None

    # ── Tier 1: TextCNN ───────────────────────────────────────────────────────
    if _CNN_AVAILABLE and _cnn_ready():
        label, confidence = _cnn_predict(session)
        if label is not None:
            return label

    # ── Tier 2: Rule-based fallback ───────────────────────────────────────────
    return _rule_based(session)


def classify_proficiency_with_source(session):
    """
    Same as classify_proficiency() but also returns the source.
    Returns (label, source)  where source is 'cnn' or 'rules'.
    """
    msgs = _user_messages(session)
    if len(msgs) < 4:
        return None, None

    if _CNN_AVAILABLE and _cnn_ready():
        label, confidence = _cnn_predict(session)
        if label is not None:
            return label, f'cnn ({confidence:.0%})'

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
