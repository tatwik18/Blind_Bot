"""
cnn_text.py — TextCNN Proficiency Classifier
=============================================
Convolutional Neural Network on word embeddings that classifies a student's
conversation history as  Beginner / Intermediate / Advanced.

How it works:
  Student messages → tokenize → embed each word → parallel CNN filters
  (bigrams, trigrams, 4-grams) → max-pool → fully-connected → class label

Key design decisions:
  • Falls back silently if PyTorch is not installed
  • Auto-trains on synthetic Hinglish data on first run (no real data needed)
  • Re-trains itself on real session data when you call train_model(extra_sessions)
  • Lightweight: ~50K parameters, runs on CPU in < 5 ms per prediction

Usage:
  from cnn_text import predict_proficiency, ensure_model_trained
  ensure_model_trained()                    # call once at startup
  label, confidence = predict_proficiency(session)
"""

import os
import re
import pickle
import random

BASE_DIR   = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, 'cnn_text_model.pth')
VOCAB_PATH = os.path.join(BASE_DIR, 'cnn_text_vocab.pkl')

# ── Optional PyTorch ──────────────────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    _TORCH = True
except ImportError:
    _TORCH = False

LABEL_MAP   = {0: 'Beginner', 1: 'Intermediate', 2: 'Advanced'}
LABEL_RMAP  = {v: k for k, v in LABEL_MAP.items()}


# ─────────────────────────────────────────────
#  Hinglish-aware tokenizer
# ─────────────────────────────────────────────

def tokenize(text: str) -> list[str]:
    """
    Lowercase + split on non-alpha boundaries.
    Keeps both English and romanised Hindi tokens.
    Drops single-character tokens.
    """
    tokens = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    return [t for t in tokens if len(t) > 1]


# ─────────────────────────────────────────────
#  Vocabulary
# ─────────────────────────────────────────────

class Vocabulary:
    PAD, UNK = '<PAD>', '<UNK>'

    def __init__(self):
        self.word2idx = {self.PAD: 0, self.UNK: 1}
        self.idx2word = {0: self.PAD, 1: self.UNK}
        self.size = 2

    def add(self, word: str):
        if word not in self.word2idx:
            self.word2idx[word] = self.size
            self.idx2word[self.size] = word
            self.size += 1

    def encode(self, tokens: list[str], max_len: int = 60) -> list[int]:
        ids  = [self.word2idx.get(t, 1) for t in tokens[:max_len]]
        ids += [0] * (max_len - len(ids))       # pad to fixed length
        return ids


# ─────────────────────────────────────────────
#  TextCNN architecture
# ─────────────────────────────────────────────

if _TORCH:
    class TextCNN(nn.Module):
        """
        Three parallel Conv1D layers with filter widths 2, 3, 4.
        Each captures different n-gram patterns:
          width-2 → bigrams   ("went to", "very good")
          width-3 → trigrams  ("I went to", "kya matlab hai")
          width-4 → 4-grams   ("what is the meaning")
        Results are max-pooled and concatenated before classification.
        """
        def __init__(self,
                     vocab_size : int,
                     embed_dim  : int = 64,
                     num_filters: int = 64,
                     num_classes: int = 3,
                     max_len    : int = 60):
            super().__init__()
            self.max_len   = max_len
            self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
            # Three CNN heads for different n-gram widths
            self.conv2 = nn.Conv1d(embed_dim, num_filters, kernel_size=2)
            self.conv3 = nn.Conv1d(embed_dim, num_filters, kernel_size=3)
            self.conv4 = nn.Conv1d(embed_dim, num_filters, kernel_size=4)
            self.dropout = nn.Dropout(0.4)
            self.fc      = nn.Linear(num_filters * 3, num_classes)

        def forward(self, x):                       # x: (B, seq_len)
            e = self.embedding(x).permute(0, 2, 1)  # → (B, embed_dim, seq_len)
            # Each conv → relu → max-pool over time
            f2 = torch.relu(self.conv2(e)).max(dim=-1).values  # (B, filters)
            f3 = torch.relu(self.conv3(e)).max(dim=-1).values
            f4 = torch.relu(self.conv4(e)).max(dim=-1).values
            out = torch.cat([f2, f3, f4], dim=1)               # (B, filters*3)
            return self.fc(self.dropout(out))


# ─────────────────────────────────────────────
#  Synthetic Hinglish Training Data
# (covers Beginner / Intermediate / Advanced patterns)
# ─────────────────────────────────────────────

_SYNTH: dict[int, list[str]] = {
    0: [  # ── Beginner ─────────────────────────────
        "hi didi",
        "hello",
        "car ka matlab kya hai",
        "school ka matlab",
        "ok theek hai",
        "haan",
        "kya matlab",
        "ek word batao",
        "mujhe samajh nahi aaya",
        "yeh kya hota hai",
        "I like",
        "my name is Rahul",
        "what is this",
        "book ka matlab kya hai",
        "ok ok",
        "fish ka matlab",
        "water ka matlab kya hai",
        "tree ka matlab",
        "what does happy mean",
        "meaning of sad",
        "yes",
        "no",
        "I am fine",
        "pencil ka matlab",
        "didi ek word",
        "kya hai yeh",
        "table ka matlab kya hai",
        "iska matlab kya hai",
    ],
    1: [  # ── Intermediate ─────────────────────────
        "good morning didi how are you",
        "yesterday I go to market with my friend",
        "I went to school and I study hard",
        "what is difference between has and have",
        "she have a dog is this correct",
        "I buyed a pen from shop",
        "can you tell me about past tense",
        "I am trying to improve my English",
        "today I learned new words from you",
        "my friend told me a story",
        "I wants to learn more vocabulary",
        "can you explain me the grammar rule",
        "I practice English every day",
        "this sentence is correct or not",
        "how to use preposition in sentence",
        "what is plural of child",
        "I did not understood the lesson",
        "can you repeat that more slowly",
        "I am reading English newspaper daily",
        "yesterday we played cricket in ground",
        "my mother is teacher in school",
        "I like to watch English movies",
        "what is meaning of inspire",
        "how to form question in English",
    ],
    2: [  # ── Advanced ─────────────────────────────
        "I think learning English is important because it opens many opportunities",
        "although I was nervous at first I feel more confident now",
        "I have been practicing every day therefore my vocabulary has improved",
        "however I still struggle with pronunciation of some difficult words",
        "despite the difficulty I will not give up because I want to speak fluently",
        "the story was very interesting because it had a great moral lesson",
        "furthermore I believe that consistent practice is the key to success",
        "nevertheless I will continue to work hard and improve my skills",
        "I noticed that whenever I read more my vocabulary improves significantly",
        "consequently I have decided to read English newspapers every morning",
        "I would like to discuss the difference between formal and informal English",
        "whereas spoken English differs from written English both are equally important",
        "I strongly believe that exposure to native speakers helps fluency tremendously",
        "although grammar is important communication skills matter even more",
        "I have realised that confidence is the most important factor in language learning",
        "unless you practice speaking daily you cannot achieve real fluency",
        "otherwise you may learn the rules but still feel nervous while speaking",
        "it is remarkable how quickly one can improve with the right guidance",
        "the comprehension questions in the story were quite challenging however I answered them",
        "I would appreciate it if you could give me more advanced vocabulary words",
    ],
}


def _session_to_text(session: list[dict]) -> str:
    """Concatenate all user messages from a session into one string."""
    msgs = [
        t['content'] for t in session
        if t.get('role') == 'user' and t.get('content', '').strip()
    ]
    return ' '.join(msgs)


# ─────────────────────────────────────────────
#  Dataset
# ─────────────────────────────────────────────

if _TORCH:
    class _SessionDS(Dataset):
        def __init__(self, samples):
            self.samples = samples            # list of (ids_list, int_label)

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            ids, label = self.samples[idx]
            return (torch.tensor(ids, dtype=torch.long),
                    torch.tensor(label, dtype=torch.long))


# ─────────────────────────────────────────────
#  Training
# ─────────────────────────────────────────────

def train_model(extra_sessions: list | None = None,
                epochs: int = 40,
                verbose: bool = True) -> bool:
    """
    Train TextCNN and save model + vocab to disk.

    Args:
        extra_sessions: list of (session_history, label_str) tuples from real data.
                        label_str must be 'Beginner', 'Intermediate', or 'Advanced'.
        epochs:         training epochs (40 is enough for synthetic data).
        verbose:        print progress.

    Returns:
        True on success, False if PyTorch is unavailable.
    """
    if not _TORCH:
        if verbose:
            print('[TextCNN] PyTorch not installed — skipping training.')
        return False

    # ── Build corpus ──────────────────────────────────────────────────────────
    raw: list[tuple[str, int]] = []
    for label_idx, texts in _SYNTH.items():
        for text in texts:
            raw.append((text, label_idx))

    # Augment with real sessions if provided
    if extra_sessions:
        for session, label_str in extra_sessions:
            if label_str in LABEL_RMAP:
                raw.append((_session_to_text(session), LABEL_RMAP[label_str]))

    random.shuffle(raw)

    # ── Build vocabulary ──────────────────────────────────────────────────────
    vocab = Vocabulary()
    for text, _ in raw:
        for token in tokenize(text):
            vocab.add(token)

    # ── Encode ────────────────────────────────────────────────────────────────
    samples = [(vocab.encode(tokenize(text)), label) for text, label in raw]
    dataset    = _SessionDS(samples)
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True)

    # ── Model ─────────────────────────────────────────────────────────────────
    model     = TextCNN(vocab_size=vocab.size)
    optimizer = optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=15, gamma=0.5)

    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for ids, labels in dataloader:
            optimizer.zero_grad()
            loss = criterion(model(ids), labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()
        if verbose and (epoch + 1) % 10 == 0:
            avg = total_loss / len(dataloader)
            print(f'  [TextCNN] Epoch {epoch+1:>3}/{epochs}  loss={avg:.4f}')

    # ── Save ──────────────────────────────────────────────────────────────────
    torch.save(model.state_dict(), MODEL_PATH)
    with open(VOCAB_PATH, 'wb') as f:
        pickle.dump(vocab, f)

    if verbose:
        print(f'  [TextCNN] ✓ Saved model → {MODEL_PATH}')
        print(f'  [TextCNN] ✓ Vocab size  : {vocab.size} tokens')
    return True


# ─────────────────────────────────────────────
#  Inference (lazy model loading)
# ─────────────────────────────────────────────

_model: 'TextCNN | None' = None
_vocab: 'Vocabulary | None' = None


def _load_model() -> bool:
    global _model, _vocab
    if not _TORCH:
        return False
    if _model is not None:
        return True
    if not (os.path.exists(MODEL_PATH) and os.path.exists(VOCAB_PATH)):
        return False
    with open(VOCAB_PATH, 'rb') as f:
        _vocab = pickle.load(f)
    m = TextCNN(vocab_size=_vocab.size)
    m.load_state_dict(torch.load(MODEL_PATH, map_location='cpu', weights_only=True))
    m.eval()
    _model = m
    return True


def predict_proficiency(session: list[dict]) -> tuple[str | None, float]:
    """
    CNN-based proficiency prediction from session history.

    Returns:
        (label, confidence)  where label is 'Beginner'|'Intermediate'|'Advanced'
        (None,  0.0)         if model unavailable or fewer than 4 user messages.
    """
    msgs = [
        t['content'] for t in session
        if t.get('role') == 'user' and t.get('content', '').strip()
    ]
    if len(msgs) < 4:
        return None, 0.0

    if not _load_model():
        return None, 0.0

    text   = _session_to_text(session)
    tokens = tokenize(text)
    ids    = torch.tensor([_vocab.encode(tokens)], dtype=torch.long)

    with torch.no_grad():
        logits = _model(ids)
        probs  = torch.softmax(logits, dim=-1)[0]
        pred   = int(probs.argmax())
        conf   = float(probs[pred])

    return LABEL_MAP[pred], round(conf, 3)


def is_ready() -> bool:
    """Returns True if PyTorch is installed and a trained model exists on disk."""
    return _TORCH and os.path.exists(MODEL_PATH) and os.path.exists(VOCAB_PATH)


def ensure_model_trained(verbose: bool = True):
    """
    Auto-train on synthetic data if no model file exists yet.
    Call once at app startup.
    """
    if not _TORCH:
        if verbose:
            print('  [TextCNN] PyTorch not installed — using rule-based classifier only.')
        return
    if is_ready():
        if verbose:
            print('  [TextCNN] ✓ Trained model found — ready.')
        return
    if verbose:
        print('  [TextCNN] No model found — training on synthetic Hinglish data …')
    train_model(verbose=verbose)
