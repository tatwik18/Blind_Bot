"""
eval_classifier.py — Evaluation of the Proficiency Classifier
==============================================================
Computes Accuracy, Precision, Recall, F1, and ROC-AUC
for the CNN + LSTM ensemble classifier.

Run:  python eval_classifier.py
"""

import random
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, roc_auc_score,
    ConfusionMatrixDisplay, confusion_matrix,
)
from sklearn.preprocessing import label_binarize
import matplotlib.pyplot as plt

# ── Ensure models are trained before we evaluate ────────────────────────────
from lstm_text import ensure_model_trained as _lstm_init
from cnn_text  import ensure_model_trained as _cnn_init
print("Checking / training models (first run may take ~30s)…")
_cnn_init()
_lstm_init()
print("Models ready.\n")

# ── Import the classifier pipeline ──────────────────────────────────────────
from classifier import classify_proficiency

# ── All synthetic sessions (same data LSTM/CNN train on) ────────────────────
# In a real deployment you'd collect real labeled sessions here.
from lstm_text import _SYNTH   # {label: [[msg, msg, ...], ...]}

LABELS = ['Beginner', 'Intermediate', 'Advanced']

# ── Build session dicts (same format as app chat history) ───────────────────
def _make_session(messages):
    return [{'role': 'user', 'content': m} for m in messages]

all_samples = []
for label, sessions in _SYNTH.items():
    for sess in sessions:
        all_samples.append((_make_session(sess), label))

random.seed(42)
random.shuffle(all_samples)

# Dataset is small (9 synthetic sessions) so evaluate on all samples.
# In production you would use real labeled sessions as test data.
test_samples = all_samples

# ── Collect predictions ─────────────────────────────────────────────────────
y_true, y_pred = [], []
for session, true_label in test_samples:
    pred = classify_proficiency(session)
    if pred is None:
        pred = 'Beginner'   # fewer than 4 msgs → default
    y_true.append(true_label)
    y_pred.append(pred)

# ── Core metrics ─────────────────────────────────────────────────────────────
acc  = accuracy_score(y_true, y_pred)
prec = precision_score(y_true, y_pred, average='macro', zero_division=0)
rec  = recall_score(y_true, y_pred, average='macro', zero_division=0)
f1   = f1_score(y_true, y_pred, average='macro', zero_division=0)

print("=" * 52)
print("  PROFICIENCY CLASSIFIER — EVALUATION RESULTS")
print("=" * 52)
print(f"  Test samples : {len(y_true)}")
print(f"  Accuracy     : {acc:.4f}  ({acc*100:.1f}%)")
print(f"  Precision    : {prec:.4f}  (macro avg)")
print(f"  Recall       : {rec:.4f}  (macro avg)")
print(f"  F1-Score     : {f1:.4f}  (macro avg)")
print()

# ── Per-class breakdown ──────────────────────────────────────────────────────
print(classification_report(y_true, y_pred, labels=LABELS, zero_division=0))

# ── ROC-AUC (One-vs-Rest for multi-class) ───────────────────────────────────
try:
    y_bin = label_binarize(y_true, classes=LABELS)
    y_pred_bin = label_binarize(y_pred, classes=LABELS)
    roc_auc = roc_auc_score(y_bin, y_pred_bin, average='macro', multi_class='ovr')
    print(f"  ROC-AUC (OvR macro): {roc_auc:.4f}")
except Exception as e:
    print(f"  ROC-AUC: could not compute ({e})")

# ── Confusion matrix plot ────────────────────────────────────────────────────
cm = confusion_matrix(y_true, y_pred, labels=LABELS)
fig, ax = plt.subplots(figsize=(6, 5))
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=LABELS)
disp.plot(ax=ax, cmap='Blues', values_format='d')
ax.set_title('Proficiency Classifier — Confusion Matrix')
plt.tight_layout()
plt.savefig('confusion_matrix.png', dpi=150)
print("\n  Confusion matrix saved → confusion_matrix.png")
plt.show()
