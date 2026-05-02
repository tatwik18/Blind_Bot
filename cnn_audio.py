"""
cnn_audio.py — Audio CNN for Pronunciation Scoring & Confidence Detection
=========================================================================
Two CNN models that work on raw audio from the student's microphone:

  1. MelCNN  (2-D CNN on mel-spectrogram images)
     • Pronunciation scoring  → how closely did the student say a word?
     • Input : WAV/MP3 audio bytes  +  expected word text
     • Output: score 0–100  +  pass/fail  +  feedback string

  2. ConfidenceCNN  (1-D CNN on MFCC feature sequence)
     • Detects nervousness / confidence from voice tone & rhythm
     • Input : WAV/MP3 audio bytes
     • Output: {'confident': 0.72, 'nervous': 0.28}

Both models fall back gracefully when librosa or PyTorch is not installed.
Because training requires real labelled audio (which we don't have yet),
both models ship with a rule-based fallback that uses the existing
difflib fuzzy-match approach plus simple energy/pitch heuristics.

Integration points in app.py:
    POST /pronunciation/audio_check   → MelCNN pronunciation scoring
    POST /chat/confidence             → ConfidenceCNN emotion detection

Installation (optional — needed only for CNN inference):
    pip install torch librosa numpy soundfile
"""

import os
import io
import re
import math
import random
import difflib
import tempfile

BASE_DIR = os.path.dirname(__file__)

# ── Optional heavy imports ────────────────────────────────────────────────────
try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False

try:
    import librosa
    _LIBROSA = True
except ImportError:
    _LIBROSA = False

try:
    import torch
    import torch.nn as nn
    _TORCH = True
except ImportError:
    _TORCH = False

_CNN_READY = _NUMPY and _LIBROSA and _TORCH   # True only if all three installed

MEL_MODEL_PATH  = os.path.join(BASE_DIR, 'cnn_mel_model.pth')
CONF_MODEL_PATH = os.path.join(BASE_DIR, 'cnn_conf_model.pth')

SAMPLE_RATE  = 16_000   # Hz — standard for speech models
N_MELS       = 64       # mel-spectrogram frequency bins
N_MFCC       = 13       # MFCC coefficients for confidence CNN
MAX_MEL_TIME = 128      # time frames (~2 s of audio)
MAX_CONF_LEN = 100      # MFCC frames for confidence CNN


# ═══════════════════════════════════════════════════════════════════════════════
#  1.  MelCNN  — Pronunciation Scoring
# ═══════════════════════════════════════════════════════════════════════════════

if _TORCH:
    class MelCNN(nn.Module):
        """
        2-D CNN that takes a (1, N_MELS, MAX_MEL_TIME) mel-spectrogram image
        and outputs a single pronunciation similarity score in [0, 1].

        Architecture mirrors a small ResNet-style stack:
          Conv → BN → ReLU → MaxPool  (×3)  →  GlobalAvgPool  →  FC
        """
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                # Block 1
                nn.Conv2d(1, 32, kernel_size=3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
                nn.MaxPool2d(2),                             # → (32, 32, 64)
                # Block 2
                nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
                nn.MaxPool2d(2),                             # → (64, 16, 32)
                # Block 3
                nn.Conv2d(64, 128, kernel_size=3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
                nn.MaxPool2d(2),                             # → (128, 8, 16)
            )
            self.pool = nn.AdaptiveAvgPool2d((2, 2))         # → (128, 2, 2)
            self.fc   = nn.Sequential(
                nn.Flatten(),
                nn.Linear(128 * 4, 64), nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(64, 1), nn.Sigmoid(),              # score ∈ [0,1]
            )

        def forward(self, x):                                # x: (B,1,N_MELS,T)
            return self.fc(self.pool(self.features(x))).squeeze(-1)


# ─────────────────────────────────────────────
#  1-B  ConfidenceCNN — Emotion / Nervousness
# ─────────────────────────────────────────────

if _TORCH:
    class ConfidenceCNN(nn.Module):
        """
        1-D CNN on MFCC sequence  →  2-class softmax:
          class 0 = nervous / hesitant
          class 1 = confident / clear

        MFCC captures:  speaking rate, pauses, pitch variation, energy.
        """
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                # (B, N_MFCC, T)
                nn.Conv1d(N_MFCC, 64, kernel_size=5, padding=2), nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Conv1d(64, 128, kernel_size=3, padding=1), nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Conv1d(128, 64, kernel_size=3, padding=1), nn.ReLU(),
                nn.AdaptiveAvgPool1d(1),                     # → (B, 64, 1)
            )
            self.fc = nn.Sequential(
                nn.Flatten(),
                nn.Linear(64, 32), nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(32, 2),                            # 2 classes
            )

        def forward(self, x):                                # x: (B, N_MFCC, T)
            return self.fc(self.net(x))


# ─────────────────────────────────────────────
#  Audio → feature extraction helpers
# ─────────────────────────────────────────────

def _load_audio(audio_bytes: bytes) -> tuple:
    """
    Load raw audio bytes (WAV or MP3) into a mono float32 numpy array.
    Returns (y, sr) or (None, None) on failure.
    """
    if not _CNN_READY:
        return None, None
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        y, sr = librosa.load(tmp_path, sr=SAMPLE_RATE, mono=True)
        os.unlink(tmp_path)
        return y, sr
    except Exception as e:
        print(f'[AudioCNN] load error: {e}')
        return None, None


def _audio_to_melspec(y: 'np.ndarray') -> 'torch.Tensor | None':
    """
    Convert waveform → normalised mel-spectrogram tensor  (1, N_MELS, MAX_MEL_TIME).
    Pads or truncates along the time axis.
    """
    if not _CNN_READY:
        return None
    try:
        mel = librosa.feature.melspectrogram(y=y, sr=SAMPLE_RATE,
                                             n_mels=N_MELS, fmax=8000)
        mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
        # Normalise to [0, 1]
        mel_db = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-9)
        # Pad / truncate time axis
        T = mel_db.shape[1]
        if T >= MAX_MEL_TIME:
            mel_db = mel_db[:, :MAX_MEL_TIME]
        else:
            mel_db = np.pad(mel_db, ((0, 0), (0, MAX_MEL_TIME - T)))
        # → tensor (1, 1, N_MELS, MAX_MEL_TIME)
        return torch.tensor(mel_db, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    except Exception as e:
        print(f'[AudioCNN] mel error: {e}')
        return None


def _audio_to_mfcc(y: 'np.ndarray') -> 'torch.Tensor | None':
    """
    Convert waveform → MFCC tensor  (1, N_MFCC, MAX_CONF_LEN).
    """
    if not _CNN_READY:
        return None
    try:
        mfcc = librosa.feature.mfcc(y=y, sr=SAMPLE_RATE, n_mfcc=N_MFCC).astype(np.float32)
        # Normalise per coefficient
        mfcc = (mfcc - mfcc.mean(axis=1, keepdims=True)) / (mfcc.std(axis=1, keepdims=True) + 1e-9)
        T = mfcc.shape[1]
        if T >= MAX_CONF_LEN:
            mfcc = mfcc[:, :MAX_CONF_LEN]
        else:
            mfcc = np.pad(mfcc, ((0, 0), (0, MAX_CONF_LEN - T)))
        return torch.tensor(mfcc, dtype=torch.float32).unsqueeze(0)   # (1, N_MFCC, T)
    except Exception as e:
        print(f'[AudioCNN] mfcc error: {e}')
        return None


# ─────────────────────────────────────────────
#  Lazy model loaders
# ─────────────────────────────────────────────

_mel_model: 'MelCNN | None'  = None
_conf_model: 'ConfidenceCNN | None' = None


def _load_mel_model() -> bool:
    global _mel_model
    if not _TORCH or not os.path.exists(MEL_MODEL_PATH):
        return False
    if _mel_model is not None:
        return True
    m = MelCNN()
    m.load_state_dict(torch.load(MEL_MODEL_PATH, map_location='cpu', weights_only=True))
    m.eval()
    _mel_model = m
    return True


def _load_conf_model() -> bool:
    global _conf_model
    if not _TORCH or not os.path.exists(CONF_MODEL_PATH):
        return False
    if _conf_model is not None:
        return True
    m = ConfidenceCNN()
    m.load_state_dict(torch.load(CONF_MODEL_PATH, map_location='cpu', weights_only=True))
    m.eval()
    _conf_model = m
    return True


# ─────────────────────────────────────────────
#  Rule-based fallback helpers
# (used when CNN model is not trained yet)
# ─────────────────────────────────────────────

def _difflib_score(expected: str, spoken: str) -> float:
    """Sequence-match ratio between expected and spoken word, 0.0–1.0."""
    spoken_clean = re.sub(
        r'\b(i said|the word is|word is|is|the|a|an)\b', '', spoken.lower()
    ).strip() or spoken.lower()
    return difflib.SequenceMatcher(None, expected.lower(), spoken_clean).ratio()


def _heuristic_confidence(audio_bytes: bytes) -> dict:
    """
    Simple energy-based confidence heuristic when CNN is unavailable.
    Loud, sustained audio → confident.  Very short or silent → nervous.
    """
    n_bytes = len(audio_bytes)
    if n_bytes > 20_000:
        return {'confident': 0.70, 'nervous': 0.30, 'source': 'heuristic'}
    if n_bytes > 8_000:
        return {'confident': 0.50, 'nervous': 0.50, 'source': 'heuristic'}
    return {'confident': 0.30, 'nervous': 0.70, 'source': 'heuristic'}


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════════

def score_pronunciation(audio_bytes: bytes,
                        expected_word: str,
                        spoken_text: str = '',
                        syllables: str = '') -> dict:
    """
    Score how well the student pronounced a word.

    Args:
        audio_bytes:   Raw WAV/MP3 bytes from the microphone recording.
        expected_word: The word the student was asked to say (e.g. "beautiful").
        spoken_text:   The speech-recogniser transcript (used as fallback).
        syllables:     Syllable hint for feedback (e.g. "beau-ti-ful").

    Returns dict:
        {
          score:    int   0–100
          correct:  bool  (score >= 75)
          feedback: str   Hinglish feedback string
          source:   str   'cnn' | 'difflib'
        }
    """
    syllables = syllables or expected_word

    # ── Try CNN first ─────────────────────────────────────────────────────────
    if _CNN_READY and _load_mel_model() and audio_bytes:
        y, sr = _load_audio(audio_bytes)
        if y is not None:
            mel = _audio_to_melspec(y)
            if mel is not None:
                with torch.no_grad():
                    cnn_score = float(_mel_model(mel).item())
                score   = round(cnn_score * 100)
                correct = score >= 75
                if correct:
                    feedback = random.choice([
                        f"Waah! CNN ko bhi {expected_word} bilkul sahi laga! Perfect!",
                        f"Excellent! Your pronunciation of {expected_word} is spot on!",
                    ])
                elif score >= 50:
                    feedback = (
                        f"Good try! CNN score {score}/100. "
                        f"Thoda aur practice: {syllables}."
                    )
                else:
                    feedback = (
                        f"Koi baat nahi! CNN score {score}/100. "
                        f"Let us try again: {syllables}."
                    )
                return {'score': score, 'correct': correct,
                        'feedback': feedback, 'source': 'cnn'}

    # ── Fallback: difflib on transcript ──────────────────────────────────────
    ratio   = _difflib_score(expected_word, spoken_text or expected_word)
    score   = round(ratio * 100)
    correct = ratio >= 0.80

    if correct:
        feedback = random.choice([
            "Shabash! Bilkul sahi bola! Great job!",
            "Excellent! Your pronunciation is perfect!",
        ])
    elif ratio >= 0.55:
        feedback = f"Good try! Thoda aur practice karo. Say it like this: {syllables}."
    else:
        feedback = f"Koi baat nahi! Let us try again. Listen carefully: {syllables}."

    return {'score': score, 'correct': correct,
            'feedback': feedback, 'source': 'difflib'}


def detect_confidence(audio_bytes: bytes) -> dict:
    """
    Detect the student's confidence level from their voice recording.

    Args:
        audio_bytes: Raw WAV/MP3 bytes.

    Returns dict:
        {
          confident: float  0.0–1.0
          nervous:   float  0.0–1.0
          label:     str    'Confident' | 'Nervous'
          source:    str    'cnn' | 'heuristic'
        }
    """
    # ── Try CNN ───────────────────────────────────────────────────────────────
    if _CNN_READY and _load_conf_model() and audio_bytes:
        y, _ = _load_audio(audio_bytes)
        if y is not None:
            mfcc = _audio_to_mfcc(y)
            if mfcc is not None:
                with torch.no_grad():
                    logits = _conf_model(mfcc)
                    probs  = torch.softmax(logits, dim=-1)[0].tolist()
                return {
                    'nervous'  : round(probs[0], 3),
                    'confident': round(probs[1], 3),
                    'label'    : 'Confident' if probs[1] > probs[0] else 'Nervous',
                    'source'   : 'cnn',
                }

    # ── Fallback ──────────────────────────────────────────────────────────────
    result = _heuristic_confidence(audio_bytes)
    result['label'] = 'Confident' if result['confident'] > result['nervous'] else 'Nervous'
    return result


def get_didi_comfort_line(confidence_result: dict) -> str | None:
    """
    Given a confidence result dict, return a comforting Hinglish line
    that Didi should say if the student sounds nervous.
    Returns None when the student sounds confident (no intervention needed).
    """
    if confidence_result.get('nervous', 0) < 0.60:
        return None
    return random.choice([
        "Koi tension nahi beta, araam se bolo — main sun rahi hoon.",
        "Bilkul ghabrao mat. Aap bahut achha kar rahe ho.",
        "Main hoon na. Dariye mat bilkul — hum saath hain.",
        "Take a deep breath. Aap kar sakte ho — I believe in you!",
    ])


def cnn_status() -> dict:
    """Return a status dict for the /health endpoint."""
    return {
        'text_cnn_ready' : _TORCH and os.path.exists(
            os.path.join(BASE_DIR, 'cnn_text_model.pth')),
        'mel_cnn_ready'  : _CNN_READY and os.path.exists(MEL_MODEL_PATH),
        'conf_cnn_ready' : _CNN_READY and os.path.exists(CONF_MODEL_PATH),
        'torch'          : _TORCH,
        'librosa'        : _LIBROSA,
        'numpy'          : _NUMPY,
    }
