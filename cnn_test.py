"""
cnn_test.py — Standalone CNN Test Script
=========================================
Tests all three CNN components without running Flask.
No API keys needed. Just:

    python cnn_test.py

Results show PASS / FAIL for each assertion.
"""

import sys

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

total = passed = 0

def check(condition, message):
    global total, passed
    total += 1
    if condition:
        passed += 1
        print(f"  {PASS} {message}")
    else:
        print(f"  {FAIL} {message}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ─────────────────────────────────────────────────────────────
#  Fake session histories
# ─────────────────────────────────────────────────────────────

beginner_session = [
    {"role": "user",      "content": "hi didi"},
    {"role": "assistant", "content": "Hello beta!"},
    {"role": "user",      "content": "car ka matlab kya hai"},
    {"role": "assistant", "content": "Car matlab gaadi."},
    {"role": "user",      "content": "ok"},
    {"role": "assistant", "content": "Chalo ek sentence banao."},
    {"role": "user",      "content": "school ka matlab"},
    {"role": "assistant", "content": "School matlab paathshala."},
    {"role": "user",      "content": "iska matlab kya hai"},
    {"role": "assistant", "content": "Matlab: meaning."},
]

intermediate_session = [
    {"role": "user",      "content": "good morning didi how are you today"},
    {"role": "assistant", "content": "Good morning! Main theek hoon."},
    {"role": "user",      "content": "yesterday I go to market with my friend"},
    {"role": "assistant", "content": "Almost — 'went', not 'go'."},
    {"role": "user",      "content": "I went to market and I buyed vegetables"},
    {"role": "assistant", "content": "'Bought', not 'buyed'."},
    {"role": "user",      "content": "what is difference between has and have"},
    {"role": "assistant", "content": "Has for he/she/it. Have for I/you/we/they."},
    {"role": "user",      "content": "I am trying to improve my English every day"},
    {"role": "assistant", "content": "Bahut acha! Keep it up!"},
    {"role": "user",      "content": "can you explain me present tense"},
    {"role": "assistant", "content": "Sure! Present tense..."},
]

advanced_session = [
    {"role": "user",      "content": "I think learning English is important because it opens many opportunities"},
    {"role": "assistant", "content": "Excellent sentence!"},
    {"role": "user",      "content": "although I was nervous at first I feel more confident now"},
    {"role": "assistant", "content": "Wonderful use of although!"},
    {"role": "user",      "content": "I have been practicing every day therefore my vocabulary has improved"},
    {"role": "assistant", "content": "Perfect use of therefore!"},
    {"role": "user",      "content": "however I still struggle with pronunciation of some difficult words"},
    {"role": "assistant", "content": "Let us practice together."},
    {"role": "user",      "content": "despite the difficulty I will not give up because I want to speak fluently"},
    {"role": "assistant", "content": "That determination is wonderful!"},
    {"role": "user",      "content": "furthermore I believe consistent practice is the key to success"},
    {"role": "assistant", "content": "Absolutely right!"},
]

too_short_session = [
    {"role": "user",      "content": "hi"},
    {"role": "assistant", "content": "Hello!"},
]


# ═════════════════════════════════════════════════════════════
#  TEST 1 — Rule-based classifier (always works, no PyTorch)
# ═════════════════════════════════════════════════════════════
section("TEST 1 — Rule-based Classifier (no dependencies)")

from classifier import _rule_based

check(_rule_based(beginner_session)     == 'Beginner',     "Beginner session → Beginner")
check(_rule_based(intermediate_session) == 'Intermediate', "Intermediate session → Intermediate")
check(_rule_based(advanced_session)     == 'Advanced',     "Advanced session → Advanced")
check(_rule_based(too_short_session)    is None,           "Too short session → None")


# ═════════════════════════════════════════════════════════════
#  TEST 2 — TextCNN (requires PyTorch)
# ═════════════════════════════════════════════════════════════
section("TEST 2 — TextCNN Proficiency Classifier")

try:
    import torch
    torch_ok = True
    print(f"  {INFO} PyTorch {torch.__version__} found ✓")
except ImportError:
    torch_ok = False
    print(f"  {INFO} PyTorch not installed — CNN tests will show expected skips")

from cnn_text import ensure_model_trained, predict_proficiency, is_ready

if torch_ok:
    print(f"  {INFO} Training TextCNN on synthetic data …")
    ensure_model_trained(verbose=True)
    check(is_ready(), "Model file exists after training")

    label_b, conf_b = predict_proficiency(beginner_session)
    label_i, conf_i = predict_proficiency(intermediate_session)
    label_a, conf_a = predict_proficiency(advanced_session)
    label_s, conf_s = predict_proficiency(too_short_session)

    check(label_b == 'Beginner',     f"CNN: beginner session → {label_b} ({conf_b:.0%})")
    check(label_i == 'Intermediate', f"CNN: intermediate session → {label_i} ({conf_i:.0%})")
    check(label_a == 'Advanced',     f"CNN: advanced session → {label_a} ({conf_a:.0%})")
    check(label_s is None,           f"CNN: too short session → {label_s}")
else:
    print(f"  {INFO} Skipping CNN tests (PyTorch not installed)")


# ═════════════════════════════════════════════════════════════
#  TEST 3 — Two-tier classify_proficiency()
# ═════════════════════════════════════════════════════════════
section("TEST 3 — Two-tier classify_proficiency() pipeline")

from classifier import classify_proficiency, classify_proficiency_with_source

for label, session, name in [
    ('Beginner',     beginner_session,     'beginner'),
    ('Intermediate', intermediate_session, 'intermediate'),
    ('Advanced',     advanced_session,     'advanced'),
]:
    result = classify_proficiency(session)
    source_result, source = classify_proficiency_with_source(session)
    check(result == label, f"{name} → {result}  (source: {source})")

check(classify_proficiency(too_short_session) is None, "Too short → None")


# ═════════════════════════════════════════════════════════════
#  TEST 4 — cnn_audio (pronunciation + confidence)
# ═════════════════════════════════════════════════════════════
section("TEST 4 — Audio CNN (pronunciation scoring + confidence)")

from cnn_audio import score_pronunciation, detect_confidence, get_didi_comfort_line, cnn_status

status = cnn_status()
print(f"  {INFO} torch={status['torch']}  librosa={status['librosa']}  numpy={status['numpy']}")
print(f"  {INFO} mel_cnn_ready={status['mel_cnn_ready']}  conf_cnn_ready={status['conf_cnn_ready']}")

# ── Pronunciation: difflib fallback (no audio bytes) ──────────────────────────
result = score_pronunciation(b"", "beautiful", spoken_text="beautiful", syllables="beau-ti-ful")
check(result['correct'] == True,        f"Exact match → correct=True  score={result['score']}  source={result['source']}")

result = score_pronunciation(b"", "beautiful", spoken_text="beatiful")
check(result['score'] >= 50,            f"Close match → score={result['score']} (>=50)")

result = score_pronunciation(b"", "elephant", spoken_text="hello")
check(result['correct'] == False,       f"No match → correct=False  score={result['score']}")

# ── Confidence: heuristic fallback (no audio bytes) ───────────────────────────
result_empty = detect_confidence(b"")
check('confident' in result_empty,      "detect_confidence returns 'confident' key")
check('nervous'   in result_empty,      "detect_confidence returns 'nervous' key")
check('label'     in result_empty,      "detect_confidence returns 'label' key")
check(abs(result_empty['confident'] + result_empty['nervous'] - 1.0) < 0.01,
                                        "confident + nervous ≈ 1.0")

# Large audio → confident heuristic
result_big  = detect_confidence(b"x" * 30_000)
check(result_big['confident'] > result_big['nervous'],
                                        "Large audio → more confident than nervous")

result_tiny = detect_confidence(b"x" * 500)
check(result_tiny['nervous'] > result_tiny['confident'],
                                        "Tiny audio → more nervous than confident")

# ── Comfort line ──────────────────────────────────────────────────────────────
nervous_result    = {'confident': 0.20, 'nervous': 0.80}
confident_result  = {'confident': 0.80, 'nervous': 0.20}
check(get_didi_comfort_line(nervous_result)   is not None, "Nervous → comfort line returned")
check(get_didi_comfort_line(confident_result) is None,     "Confident → no comfort line (None)")


# ═════════════════════════════════════════════════════════════
#  TEST 5 — get_proficiency_prompt_addon
# ═════════════════════════════════════════════════════════════
section("TEST 5 — Proficiency Prompt Addons")

from classifier import get_proficiency_prompt_addon

for level in ['Beginner', 'Intermediate', 'Advanced']:
    addon = get_proficiency_prompt_addon(level)
    check(len(addon) > 20,      f"{level} addon is non-empty ({len(addon)} chars)")
    check('STUDENT PROFILE' in addon, f"{level} addon contains [STUDENT PROFILE] tag")

check(get_proficiency_prompt_addon(None) == "",  "None level → empty string")


# ─────────────────────────────────────────────────────────────
#  Summary
# ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  Results: {passed}/{total} passed", end="  ")
if passed == total:
    print("\033[92m✓ All tests passed!\033[0m")
else:
    print(f"\033[91m✗ {total - passed} test(s) failed\033[0m")
print('='*60)

sys.exit(0 if passed == total else 1)
