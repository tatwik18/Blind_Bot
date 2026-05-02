"""
SQLite progress tracker for Didi tutor bot.
Handles: student progress, quiz scores, pronunciation attempts, streaks.
"""

import sqlite3
import os
import datetime
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), 'didi_progress.db')
_lock   = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS student_progress (
    student_id        TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    streak            INTEGER DEFAULT 0,
    last_active       TEXT    DEFAULT '',
    speaking_attempts INTEGER DEFAULT 0,
    words_practiced   INTEGER DEFAULT 0,
    session_minutes   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quiz_scores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    date       TEXT NOT NULL,
    quiz_type  TEXT NOT NULL,
    question   TEXT,
    correct    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pronunciation_log (
    student_id TEXT NOT NULL,
    word       TEXT NOT NULL,
    correct    INTEGER DEFAULT 0,
    wrong      INTEGER DEFAULT 0,
    last_tried TEXT    DEFAULT '',
    PRIMARY KEY (student_id, word)
);
"""


def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _lock:
        with _conn() as c:
            c.executescript(_SCHEMA)


def ensure_student(sid: str, name: str):
    """Create a progress row for the student if it doesn't exist."""
    with _lock:
        with _conn() as c:
            c.execute(
                "INSERT INTO student_progress (student_id, name) VALUES (?,?) "
                "ON CONFLICT(student_id) DO UPDATE SET name=excluded.name",
                (sid, name)
            )


def update_streak(sid: str) -> int:
    """Increment streak if student was active yesterday, reset if gap > 1 day."""
    today     = str(datetime.date.today())
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
    with _lock:
        with _conn() as c:
            row = c.execute(
                "SELECT streak, last_active FROM student_progress WHERE student_id=?",
                (sid,)
            ).fetchone()
            if not row:
                return 0
            last, streak = row['last_active'], row['streak']
            if last == today:
                return streak
            streak = (streak + 1) if (last == yesterday) else 1
            c.execute(
                "UPDATE student_progress SET streak=?, last_active=? WHERE student_id=?",
                (streak, today, sid)
            )
            return streak


def add_session_stats(sid: str, speaking: int = 0, words: int = 0, minutes: int = 0):
    """Accumulate session counts into the lifetime totals."""
    with _lock:
        with _conn() as c:
            c.execute(
                "UPDATE student_progress SET "
                "speaking_attempts = speaking_attempts + ?, "
                "words_practiced   = words_practiced   + ?, "
                "session_minutes   = session_minutes   + ? "
                "WHERE student_id = ?",
                (speaking, words, minutes, sid)
            )


def record_quiz_answer(sid: str, quiz_type: str, question: str, correct: bool):
    """Persist one quiz attempt."""
    with _lock:
        with _conn() as c:
            c.execute(
                "INSERT INTO quiz_scores (student_id, date, quiz_type, question, correct) "
                "VALUES (?,?,?,?,?)",
                (sid, str(datetime.date.today()), quiz_type, question, 1 if correct else 0)
            )


def record_pronunciation_attempt(sid: str, word: str, correct: bool):
    """Upsert a pronunciation attempt for the (student, word) pair."""
    today = str(datetime.date.today())
    word  = word.lower().strip()
    with _lock:
        with _conn() as c:
            c.execute(
                "INSERT INTO pronunciation_log "
                "(student_id, word, correct, wrong, last_tried) VALUES (?,?,?,?,?) "
                "ON CONFLICT(student_id, word) DO UPDATE SET "
                "correct    = correct    + ?, "
                "wrong      = wrong      + ?, "
                "last_tried = ?",
                (
                    sid, word,
                    1 if correct else 0,
                    0 if correct else 1,
                    today,
                    1 if correct else 0,
                    0 if correct else 1,
                    today,
                )
            )


def get_weak_words(sid: str, limit: int = 5) -> list:
    """Return words where wrong > correct, sorted by most-wrong first."""
    with _conn() as c:
        rows = c.execute(
            "SELECT word, wrong, correct, last_tried FROM pronunciation_log "
            "WHERE student_id=? AND wrong > correct "
            "ORDER BY wrong DESC, last_tried ASC LIMIT ?",
            (sid, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def get_adaptive_difficulty(sid: str) -> str:
    """
    Derive 'easy' / 'medium' / 'hard' from the last 7 days of quiz scores.
    Defaults to 'medium' when there is no quiz history yet.
    """
    cutoff = str(datetime.date.today() - datetime.timedelta(days=7))
    with _conn() as c:
        row = c.execute(
            "SELECT COUNT(*) AS total, SUM(correct) AS right_count FROM quiz_scores "
            "WHERE student_id=? AND date >= ?",
            (sid, cutoff)
        ).fetchone()
    if row and row['total'] > 0:
        pct = (row['right_count'] or 0) / row['total'] * 100
        if pct < 50:
            return 'easy'
        if pct > 80:
            return 'hard'
    return 'medium'


def get_progress_summary(sid: str) -> dict:
    """Return a dict of lifetime + last-7-day stats for one student."""
    week = str(datetime.date.today() - datetime.timedelta(days=7))
    with _conn() as c:
        prog = c.execute(
            "SELECT * FROM student_progress WHERE student_id=?", (sid,)
        ).fetchone()
        quiz = c.execute(
            "SELECT COUNT(*) AS total, SUM(correct) AS right_count FROM quiz_scores "
            "WHERE student_id=? AND date >= ?", (sid, week)
        ).fetchone()
        pron = c.execute(
            "SELECT COUNT(DISTINCT word) AS cnt FROM pronunciation_log "
            "WHERE student_id=?", (sid,)
        ).fetchone()

    out: dict = {}
    if prog:
        out.update(dict(prog))
    qt = int(quiz['total'])                  if quiz and quiz['total']       else 0
    qr = int(quiz['right_count'] or 0)       if quiz                         else 0
    out['quiz_total']   = qt
    out['quiz_correct'] = qr
    out['quiz_pct']     = round(qr / qt * 100) if qt > 0 else 0
    out['words_tried']  = int(pron['cnt']) if pron else 0
    return out


# Initialise schema on import.
init_db()
