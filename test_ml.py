"""
Quick test for classifier.py and clustering.py
Run with:  python test_ml.py
"""

from classifier import classify_proficiency, get_proficiency_prompt_addon
from clustering import cluster_students

# ─────────────────────────────────────────────
#  Fake session histories
# ─────────────────────────────────────────────

# Beginner: very short answers, often asks for meanings
beginner_session = [
    {"role": "user",      "content": "hello didi"},
    {"role": "assistant", "content": "Hello! Kya seekhna hai aaj?"},
    {"role": "user",      "content": "car ka matlab kya hai"},
    {"role": "assistant", "content": "Car matlab gaadi hoti hai."},
    {"role": "user",      "content": "ok"},
    {"role": "assistant", "content": "Chalo ek sentence banao — I have a car."},
    {"role": "user",      "content": "I have car"},
    {"role": "assistant", "content": "Almost! 'I have a car' — article 'a' lagana hota hai."},
    {"role": "user",      "content": "school ka matlab kya hai"},
    {"role": "assistant", "content": "School matlab paathshala."},
]

# Intermediate: longer answers, some grammar attempts
intermediate_session = [
    {"role": "user",      "content": "good morning didi how are you"},
    {"role": "assistant", "content": "Good morning! Main bilkul theek hoon."},
    {"role": "user",      "content": "yesterday I go to market with my friend"},
    {"role": "assistant", "content": "Almost! Past mein 'went' use hota hai — I went to market."},
    {"role": "user",      "content": "I went to market and I buyed vegetables"},
    {"role": "assistant", "content": "'Bought' use hota hai — I bought vegetables."},
    {"role": "user",      "content": "ok I bought vegetables and fruits from market"},
    {"role": "assistant", "content": "Bahut acha! Perfect sentence."},
    {"role": "user",      "content": "what is difference between has and have"},
    {"role": "assistant", "content": "Has — he she it ke saath. Have — I you we they ke saath."},
    {"role": "user",      "content": "she have a dog — is this correct"},
    {"role": "assistant", "content": "Nahi — she HAS a dog."},
]

# Advanced: long sentences, complex conjunctions, no meaning-asking
advanced_session = [
    {"role": "user",      "content": "I think learning English is important because it opens many opportunities"},
    {"role": "assistant", "content": "Absolutely! That was a perfect sentence."},
    {"role": "user",      "content": "although I was nervous at first I feel more confident now"},
    {"role": "assistant", "content": "Wonderful use of 'although'!"},
    {"role": "user",      "content": "I have been practicing every day therefore my vocabulary has improved a lot"},
    {"role": "assistant", "content": "Excellent! 'Therefore' is used perfectly here."},
    {"role": "user",      "content": "however I still struggle with pronunciation of some words"},
    {"role": "assistant", "content": "That is very common. Let us practice together."},
    {"role": "user",      "content": "despite the difficulty I will not give up because I want to speak fluently"},
    {"role": "assistant", "content": "That determination will take you far!"},
]

# ─────────────────────────────────────────────
#  Test 1 — Classifier
# ─────────────────────────────────────────────
print("=" * 55)
print("  TEST 1 — Proficiency Classifier")
print("=" * 55)

cases = [
    ("Beginner  session", beginner_session,     "Beginner"),
    ("Intermediate session", intermediate_session, "Intermediate"),
    ("Advanced  session", advanced_session,     "Advanced"),
    ("Too short session", [{"role":"user","content":"hi"}], None),
]

all_passed = True
for label, session, expected in cases:
    result = classify_proficiency(session)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        all_passed = False
    print(f"  [{status}] {label:<28} expected={str(expected):<15} got={result}")

print()
print("Prompt addon (Intermediate):")
print(get_proficiency_prompt_addon("Intermediate"))

# ─────────────────────────────────────────────
#  Test 2 — Clustering
# ─────────────────────────────────────────────
print()
print("=" * 55)
print("  TEST 2 — Student Clustering")
print("=" * 55)

fake_db = {
    "1": {"name": "Arjun",   "last_session": beginner_session},
    "2": {"name": "Priya",   "last_session": intermediate_session},
    "3": {"name": "Rahul",   "last_session": advanced_session},
    "4": {"name": "Simran",  "last_session": beginner_session},
    "5": {"name": "Dev",     "last_session": intermediate_session},
    "6": {"name": "Kavya",   "last_session": advanced_session},
}

clusters = cluster_students(fake_db, k=3)

if clusters:
    for c in clusters:
        names = [s["name"] for s in c["students"]]
        print(f"\n  Group {c['id']} ({c['size']} students)  {c['color']}")
        print(f"  Description : {c['description']}")
        print(f"  Students    : {', '.join(names)}")
else:
    print("  No clusters returned (need at least 2 students with session data)")

# ─────────────────────────────────────────────
#  Test 3 — Edge cases
# ─────────────────────────────────────────────
print()
print("=" * 55)
print("  TEST 3 — Edge Cases")
print("=" * 55)

# Only 1 student — clustering should return []
one_student_db = {"1": {"name": "Solo", "last_session": beginner_session}}
result = cluster_students(one_student_db)
print(f"  [{'PASS' if result == [] else 'FAIL'}] 1 student → clusters=[]  got={result}")

# Empty session — classifier returns None
result = classify_proficiency([])
print(f"  [{'PASS' if result is None else 'FAIL'}] Empty session → None  got={result}")

# Student with no session data — excluded from clustering
no_session_db = {
    "1": {"name": "Active", "last_session": advanced_session},
    "2": {"name": "New",    "last_session": []},
    "3": {"name": "Also",   "last_session": intermediate_session},
}
result = cluster_students(no_session_db)
names_in_clusters = [s["name"] for c in result for s in c["students"]]
print(f"  [{'PASS' if 'New' not in names_in_clusters else 'FAIL'}] Student with no history excluded from clusters")

print()
print("Done!")
