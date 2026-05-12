"""
lstm_text.py — LSTM Proficiency Classifier
==========================================
Bidirectional LSTM that reads a student's conversation as a TIME SEQUENCE.
Each message = one timestep. The model learns how student language EVOLVES
over the session (early → late messages).

Why LSTM here (not CNN):
  CNN captures WHAT words appear (local n-gram patterns).
  LSTM captures HOW language changes over time (sequential progression).
  Together they form a stronger ensemble.

Architecture:
  [msg_1, msg_2, ..., msg_n]          ← sequence of messages
       ↓  (each message → avg word embedding)
  Embedding layer (per message vector)
       ↓
  Bidirectional LSTM  (forward + backward over the sequence)
       ↓
  Last hidden state (concat fwd + bwd)
       ↓
  Dropout → Linear → Softmax
       ↓
  Beginner / Intermediate / Advanced
"""

import os
import re
import pickle
import random

BASE_DIR    = os.path.dirname(__file__)
MODEL_PATH  = os.path.join(BASE_DIR, 'lstm_model.pth')
VOCAB_PATH  = os.path.join(BASE_DIR, 'lstm_vocab.pkl')

# ── Optional PyTorch ──────────────────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    _TORCH = True
except ImportError:
    _TORCH = False

LABEL_MAP  = {0: 'Beginner', 1: 'Intermediate', 2: 'Advanced'}
LABEL_RMAP = {v: k for k, v in LABEL_MAP.items()}

EMBED_DIM   = 64    # word vector size
HIDDEN_DIM  = 128   # LSTM hidden units
NUM_LAYERS  = 2     # stacked LSTM layers
DROPOUT     = 0.4
MAX_VOCAB   = 3000
MAX_SEQ_LEN = 30    # max messages per session
PAD_IDX     = 0
UNK_IDX     = 1


# ─────────────────────────────────────────────────────────────────────────────
#  Tokenizer
# ─────────────────────────────────────────────────────────────────────────────

def tokenize(text: str) -> list:
    tokens = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    return [t for t in tokens if len(t) > 1]


# ─────────────────────────────────────────────────────────────────────────────
#  Vocabulary
# ─────────────────────────────────────────────────────────────────────────────

class Vocab:
    def __init__(self):
        self.w2i = {'<PAD>': PAD_IDX, '<UNK>': UNK_IDX}
        self.i2w = {PAD_IDX: '<PAD>', UNK_IDX: '<UNK>'}
        self._freq = {}

    def add(self, tokens):
        for t in tokens:
            self._freq[t] = self._freq.get(t, 0) + 1

    def build(self, max_size=MAX_VOCAB):
        top = sorted(self._freq, key=self._freq.get, reverse=True)[:max_size-2]
        for i, w in enumerate(top, start=2):
            self.w2i[w] = i
            self.i2w[i] = w

    def encode(self, tokens):
        return [self.w2i.get(t, UNK_IDX) for t in tokens]

    def __len__(self):
        return len(self.w2i)


# ─────────────────────────────────────────────────────────────────────────────
#  Model Definition
# ─────────────────────────────────────────────────────────────────────────────

_base = nn.Module if _TORCH else object

class LSTMClassifier(_base):
    """
    Bidirectional LSTM over a sequence of messages.
    Each message is represented as the MEAN of its word embeddings.
    The LSTM processes messages in order → captures learning progression.
    """
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_layers, num_classes, dropout):
        super().__init__()
        self.embedding  = nn.Embedding(vocab_size, embed_dim, padding_idx=PAD_IDX)
        self.lstm       = nn.LSTM(
            input_size   = embed_dim,
            hidden_size  = hidden_dim,
            num_layers   = num_layers,
            batch_first  = True,
            bidirectional= True,      # reads session forward AND backward
            dropout      = dropout if num_layers > 1 else 0,
        )
        self.dropout    = nn.Dropout(dropout)
        # bidirectional → hidden_dim * 2
        self.classifier = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x):
        # x: (batch, seq_len, msg_token_len)
        batch, seq_len, token_len = x.shape

        # Embed each word
        x_flat = x.view(batch * seq_len, token_len)        # (B*S, T)
        emb    = self.embedding(x_flat)                    # (B*S, T, E)

        # Mean-pool each message to a single vector
        mask   = (x_flat != PAD_IDX).float().unsqueeze(-1) # (B*S, T, 1)
        msg_vec = (emb * mask).sum(1) / mask.sum(1).clamp(min=1)  # (B*S, E)
        msg_vec = msg_vec.view(batch, seq_len, -1)         # (B, S, E)

        # LSTM over the message sequence
        out, (hn, _) = self.lstm(msg_vec)                  # hn: (layers*2, B, H)

        # Concat last fwd + bwd hidden states
        fwd = hn[-2]   # last forward layer
        bwd = hn[-1]   # last backward layer
        h   = torch.cat([fwd, bwd], dim=1)                 # (B, H*2)
        h   = self.dropout(h)
        return self.classifier(h)                          # (B, num_classes)


# ─────────────────────────────────────────────────────────────────────────────
#  Synthetic Training Data  (Hinglish-aware)
# ─────────────────────────────────────────────────────────────────────────────

_SYNTH = {
    'Beginner': [
        ["hello", "mera naam kya", "namaste", "english nahi aati", "dheere bolo",
         "kya matlab", "samajh nahi", "phir bolo", "ok ok", "haan"],
        ["hi didi", "mujhe help karo", "kya hai yeh", "iska matlab", "nahi samjha",
         "acha", "theek hai", "ok", "haan didi", "shukriya"],
        ["namaste", "shuru karo", "english seekhna hai", "kaise bolte", "matlab kya",
         "arth kya hai", "ok didi", "achha", "thik hai", "bye"],
    ],
    'Intermediate': [
        ["I want to learn", "how do you say this", "kya difference hai",
         "mujhe samajh aa gaya", "can you explain more", "I think I understand",
         "what is the meaning", "I will try", "please repeat", "ok I got it"],
        ["I know some english", "but grammar is difficult", "past tense kaise banate",
         "I tried to speak", "was and were ka difference", "I understand now",
         "can you give example", "I will practice", "thank you didi", "see you"],
        ["hello didi", "I want to practice", "yesterday I went to market",
         "how to say this correctly", "is this sentence right", "I am trying",
         "what about plural", "I learned new word", "very helpful", "thank you"],
    ],
    'Advanced': [
        ["I have been practicing English for months", "the grammar rules are complex",
         "however I find idioms fascinating", "could you explain subjunctive mood",
         "I attempted to write a paragraph", "furthermore the vocabulary is rich",
         "I understand the nuances now", "although it was challenging",
         "nevertheless I persisted", "consequently my skills improved"],
        ["despite the difficulty I enjoy learning", "I wrote an essay yesterday",
         "the structure was introduction body conclusion", "moreover I used transition words",
         "I am comfortable with complex sentences", "therefore I need advanced topics",
         "can we discuss conditionals", "I prefer challenging exercises",
         "my vocabulary has expanded significantly", "I feel confident speaking"],
        ["I have mastered basic grammar", "unless there are exceptions I follow rules",
         "I can construct compound sentences", "furthermore I understand passive voice",
         "the distinction between similar words fascinates me",
         "I analyze sentence structure carefully", "I enjoy sophisticated discussions",
         "my reading comprehension is strong", "I appreciate nuanced feedback",
         "I am ready for advanced conversation practice"],
    ],
}


def _session_to_tensors(messages: list, vocab: Vocab, max_seq=MAX_SEQ_LEN, max_tok=20):
    """
    Convert a list of message strings → (max_seq, max_tok) int tensor.
    Each row = one message tokenized + padded.
    """
    rows = []
    for msg in messages[-max_seq:]:
        toks = tokenize(msg)[:max_tok]
        ids  = vocab.encode(toks)
        ids  += [PAD_IDX] * (max_tok - len(ids))
        rows.append(ids)
    # Pad session to max_seq length
    pad_row = [PAD_IDX] * max_tok
    while len(rows) < max_seq:
        rows.append(pad_row)
    return rows  # list of lists


_ds_base = Dataset if _TORCH else object

class _SessionDataset(_ds_base):
    def __init__(self, samples, vocab):
        self.samples = samples
        self.vocab   = vocab

    def __len__(self): return len(self.samples)

    def __getitem__(self, i):
        messages, label_str = self.samples[i]
        x = _session_to_tensors(messages, self.vocab)
        return torch.tensor(x, dtype=torch.long), torch.tensor(LABEL_RMAP[label_str])


# ─────────────────────────────────────────────────────────────────────────────
#  Training
# ─────────────────────────────────────────────────────────────────────────────

_vocab_cache = None
_model_cache = None


def _build_vocab(samples):
    v = Vocab()
    for messages, _ in samples:
        for msg in messages:
            v.add(tokenize(msg))
    v.build()
    return v


def _make_samples(extra=None):
    samples = []
    for label, sessions in _SYNTH.items():
        for sess in sessions:
            samples.append((sess, label))
    if extra:
        samples.extend(extra)
    random.shuffle(samples)
    return samples


def train_model(extra_sessions=None, epochs=25):
    """Train (or re-train) the LSTM and save to disk."""
    if not _TORCH:
        return False

    samples = _make_samples(extra_sessions)
    vocab   = _build_vocab(samples)
    dataset = _SessionDataset(samples, vocab)
    loader  = DataLoader(dataset, batch_size=4, shuffle=True)

    model = LSTMClassifier(
        vocab_size  = len(vocab),
        embed_dim   = EMBED_DIM,
        hidden_dim  = HIDDEN_DIM,
        num_layers  = NUM_LAYERS,
        num_classes = 3,
        dropout     = DROPOUT,
    )
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(epochs):
        for x, y in loader:
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

    torch.save(model.state_dict(), MODEL_PATH)
    with open(VOCAB_PATH, 'wb') as f:
        pickle.dump(vocab, f)

    global _vocab_cache, _model_cache
    _vocab_cache = vocab
    _model_cache = model
    return True


def _load():
    global _vocab_cache, _model_cache
    if not _TORCH or not os.path.exists(MODEL_PATH):
        return False
    if _model_cache is not None:
        return True
    with open(VOCAB_PATH, 'rb') as f:
        _vocab_cache = pickle.load(f)
    m = LSTMClassifier(len(_vocab_cache), EMBED_DIM, HIDDEN_DIM, NUM_LAYERS, 3, DROPOUT)
    m.load_state_dict(torch.load(MODEL_PATH, map_location='cpu', weights_only=True))
    m.eval()
    _model_cache = m
    return True


def is_ready() -> bool:
    return _TORCH and os.path.exists(MODEL_PATH) and os.path.exists(VOCAB_PATH)


def ensure_model_trained():
    """Call once at startup — trains if no saved model exists."""
    if not _TORCH:
        return
    if not is_ready():
        train_model()


# ─────────────────────────────────────────────────────────────────────────────
#  Inference
# ─────────────────────────────────────────────────────────────────────────────

def predict_proficiency(session: list):
    """
    session: list of {role, content} dicts (same format as chat history)
    Returns (label, confidence) or (None, None) on failure.
    """
    if not _load():
        return None, None

    messages = [
        t['content'] for t in session
        if t.get('role') == 'user' and t.get('content', '').strip()
    ]
    if len(messages) < 3:
        return None, None

    x = _session_to_tensors(messages, _vocab_cache)
    tensor = torch.tensor([x], dtype=torch.long)   # (1, seq, tok)

    with torch.no_grad():
        logits = _model_cache(tensor)               # (1, 3)
        probs  = torch.softmax(logits, dim=1)[0]
        idx    = probs.argmax().item()

    return LABEL_MAP[idx], probs[idx].item()
