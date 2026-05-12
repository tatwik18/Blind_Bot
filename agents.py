"""
agents.py — Agentic AI layer for Didi Hinglish tutor bot

Four specialised agents that enhance the core conversation loop:
  PlannerAgent    — creates a structured 5-step session plan at login
  MemoryAgent     — compresses old conversation turns into a memory summary
  ReflectionAgent — validates responses for accessibility (blind student, voice-only)
  IntentAgent     — classifies student intent for smarter context injection

Plus a parallel executor that runs proficiency classification and intent
detection concurrently to reduce per-turn latency.

All agents accept a get_response_fn parameter so they remain decoupled from
app.py and can be called with any LLM backend (neutral or Didi-persona).
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="didi_agent")


# ─────────────────────────────────────────────────────────────────────────────
#  PlannerAgent
# ─────────────────────────────────────────────────────────────────────────────

_PLANNER_PROMPT = """\
You are Didi's lesson planner for a Hinglish English tutor bot for blind students in India.

Student: {name}  |  Proficiency: {proficiency}  |  Weak words: {weak_words}  |  Has prior session: {has_history}

Create a 5-step session plan. Return ONLY a valid JSON array — no explanation, no markdown.

Each element: {{"step": int, "type": str, "instruction": str, "context_injection": str}}

"type" must be one of: warm_up, vocabulary, grammar, story, quiz, pronunciation, conversation, confidence_boost
"instruction": one Hinglish sentence telling Didi what to focus on this step
"context_injection": short English phrase injected into Didi's system prompt for that step

Example (output this format exactly):
[
  {{"step":1,"type":"warm_up","instruction":"Student ka dil se swagat karo.","context_injection":"Warm-up step. Be very welcoming. Ask one gentle opening question."}},
  {{"step":2,"type":"vocabulary","instruction":"Aaj ka ek naya word sikhao.","context_injection":"Teach one vocabulary word: give Hindi meaning, syllable breakdown, example sentence."}},
  {{"step":3,"type":"conversation","instruction":"English mein baat karo.","context_injection":"Natural two-way conversation. One question at a time."}},
  {{"step":4,"type":"quiz","instruction":"Aaj ka quick quiz lo.","context_injection":"Gently quiz on today's lesson. Celebrate every answer."}},
  {{"step":5,"type":"confidence_boost","instruction":"Warmly close the session.","context_injection":"Closing step. Specific genuine praise. End with warm encouragement."}}
]"""


def run_planner(name: str, proficiency: str, weak_words: list,
                has_history: bool, get_response_fn) -> list:
    """
    Generate a personalised 5-step lesson plan.
    Falls back to a sensible default if the LLM returns invalid JSON.
    """
    weak_str = ", ".join(w["word"] for w in weak_words[:3]) if weak_words else "none yet"
    prompt = _PLANNER_PROMPT.format(
        name=name,
        proficiency=proficiency or "Beginner",
        weak_words=weak_str,
        has_history=has_history,
    )
    try:
        reply, _ = get_response_fn(prompt, [], "")
        match = re.search(r'\[[\s\S]*?\]', reply)
        if match:
            plan = json.loads(match.group())
            if isinstance(plan, list) and len(plan) >= 3:
                return plan
    except Exception:
        pass
    return _default_plan(proficiency, bool(weak_words))


def _default_plan(proficiency: str, has_weak_words: bool) -> list:
    step3_type = "pronunciation" if has_weak_words else "story"
    step3_inst = (
        "Pehle miss kiye gaye words phir practice karo."
        if has_weak_words else
        "Ek choti bilingual story sunao."
    )
    step3_ctx = (
        "Help the student practice words they previously mispronounced. Be very encouraging."
        if has_weak_words else
        "Tell a short bilingual story. After each English sentence give its Hindi meaning."
    )
    return [
        {
            "step": 1, "type": "warm_up",
            "instruction": "Student ka warmly swagat karo aur puchho aaj kya seekhna hai.",
            "context_injection": "Warm-up step. Be very warm and welcoming. Ask one gentle opening question.",
        },
        {
            "step": 2, "type": "vocabulary",
            "instruction": "Aaj ka ek naya English word sikhao with Hindi meaning.",
            "context_injection": "Teach one vocabulary word: Hindi meaning, syllable breakdown, simple example sentence.",
        },
        {
            "step": 3, "type": step3_type,
            "instruction": step3_inst,
            "context_injection": step3_ctx,
        },
        {
            "step": 4, "type": "quiz",
            "instruction": "Aaj jo seekha usse 2 sawaal se check karo.",
            "context_injection": "Gently quiz on today's content. Ask only one question at a time. Celebrate every answer.",
        },
        {
            "step": 5, "type": "confidence_boost",
            "instruction": "Student ki sachchi tarif karo aur agle session ke liye inspire karo.",
            "context_injection": "Closing step. Give specific genuine praise about today. End with warm encouragement.",
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  MemoryAgent
# ─────────────────────────────────────────────────────────────────────────────

_MEMORY_PROMPT = """\
Summarize this English tutoring conversation between Didi and {name} in 2-3 Hinglish sentences. Be concise.
Include: key words or concepts taught, a strength the student showed, one area needing more work.
Output ONLY the summary sentences. No labels. No formatting.

Conversation:
{convo}"""


def compress_history(history: list, student_name: str, get_response_fn) -> str | None:
    """
    Compress old conversation turns into a compact memory string.
    Returns None when history is too short to be worth compressing.
    """
    if len(history) < 10:
        return None
    convo = "\n".join(
        f"{'Didi' if t.get('role') == 'assistant' else student_name}: {t.get('content', '').strip()}"
        for t in history
        if t.get("content", "").strip()
    )
    try:
        summary, _ = get_response_fn(
            _MEMORY_PROMPT.format(name=student_name, convo=convo), [], ""
        )
        return summary.strip() or None
    except Exception:
        return None


def build_memory_addon(summary: str) -> str:
    """Convert a memory summary into a system-prompt addon for Didi."""
    return (
        f"\n\n[MEMORY — EARLIER THIS SESSION]: {summary}"
        "\nDo NOT re-teach what the memory says was already covered. Continue naturally."
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ReflectionAgent
# ─────────────────────────────────────────────────────────────────────────────

_REFLECTION_PROMPT = """\
Review this Didi response. The student is BLIND — this is voice-only. Check for violations:
1. Visual language (dekho / dekhiye / see this / look here / watch this)
2. More than 4 sentences
3. Bullet points, numbered lists, or dashes used as lists
4. More than one question asked at once

Response to check:
"{response}"

If ANY violation found: rewrite the response fixing only the violations. Output ONLY the fixed response.
If NO violations: output exactly the word PASS"""

_VISUAL_RE = re.compile(
    r'\b(dekho|dekhiye|see\s+this|look\s+here|look\s+at\s+this|watch\s+this|yahan\s+dekh)\b',
    re.I,
)
_LIST_RE = re.compile(r'(?m)^\s*[-•*]|\b\d+\.\s')


def reflect(response: str, get_response_fn) -> str:
    """
    Accessibility check on a Didi response.
    Fast pre-check first — only calls the LLM when a violation is actually likely.
    """
    has_visual = bool(_VISUAL_RE.search(response))
    has_list   = bool(_LIST_RE.search(response))
    too_long   = len(re.split(r'[.!?।]+', response.strip())) > 6

    if not (has_visual or has_list or too_long):
        return response  # fast-path — no LLM call needed

    try:
        result, _ = get_response_fn(
            _REFLECTION_PROMPT.format(response=response), [], ""
        )
        result = result.strip()
        if result.upper() == "PASS" or not result:
            return response
        if (
            len(result) > 20
            and not result.startswith("1.")
            and not result.startswith("Violation")
            and not result.lower().startswith("the response")
        ):
            return result
    except Exception:
        pass
    return response


# ─────────────────────────────────────────────────────────────────────────────
#  IntentAgent
# ─────────────────────────────────────────────────────────────────────────────

_INTENT_LABELS = frozenset([
    "story", "quiz", "pronunciation", "vocabulary", "grammar",
    "conversation", "confidence", "progress", "summary", "general",
])

_INTENT_RE: dict[str, re.Pattern] = {
    "story":         re.compile(r'\b(story|kahani|kissa|sunao|suniye)\b', re.I),
    "quiz":          re.compile(r'\b(quiz|test|sawaal|exam)\b', re.I),
    "pronunciation": re.compile(r'\b(pronunciation|ucharan|pronounce|bolna\s*seekh)\b', re.I),
    "vocabulary":    re.compile(r'\b(matlab|meaning|arth|ka\s+matlab|what\s+does|meaning\s+of)\b', re.I),
    "grammar":       re.compile(r'\b(grammar|noun|verb|tense|pronoun|preposition|adjective)\b', re.I),
    "conversation":  re.compile(r'\b(conversation|baat\s*karo|let\s*us\s*talk|english\s*mein\s*baat)\b', re.I),
    "confidence":    re.compile(r'\b(dar|scared|nervous|dar\s*lag|sharm|afraid|darr)\b', re.I),
}

_INTENT_LLM_PROMPT = """\
Classify this student message into ONE word from this list:
story, quiz, pronunciation, vocabulary, grammar, conversation, confidence, progress, summary, general

Message: "{message}"

Output ONLY the one category word. Nothing else."""


def classify_intent(message: str, get_response_fn) -> str:
    """
    Classify student intent. Uses keyword patterns first (fast path),
    falls back to LLM only for ambiguous messages.
    """
    for intent, pattern in _INTENT_RE.items():
        if pattern.search(message):
            return intent
    if len(message.split()) <= 5:
        return "general"
    try:
        label, _ = get_response_fn(
            _INTENT_LLM_PROMPT.format(message=message), [], ""
        )
        label = label.strip().lower().split()[0]
        if label in _INTENT_LABELS:
            return label
    except Exception:
        pass
    return "general"


_INTENT_INJECTIONS: dict[str, str] = {
    "story":         "\n[INTENT: STORY] Tell a story immediately in the standard bilingual format with Matlab after each sentence. Do not ask permission first.",
    "quiz":          "\n[INTENT: QUIZ] Ask ONE quiz question now. Wait for the answer before asking another.",
    "pronunciation": "\n[INTENT: PRONUNCIATION] Focus on pronunciation. Give syllable breakdown. Be very encouraging.",
    "vocabulary":    "\n[INTENT: VOCABULARY] Give Hindi meaning + simple example sentence. Break the word syllable by syllable.",
    "grammar":       "\n[INTENT: GRAMMAR] Explain ONLY in Hindi or Hinglish. Never explain grammar concepts in English.",
    "conversation":  "\n[INTENT: CONVERSATION] This is English speaking practice. Ask your question IN ENGLISH — simple and short. If the student replies in Hindi/Hinglish, warmly acknowledge then ask them to try saying the same thing in English before moving on.",
    "confidence":    "\n[INTENT: CONFIDENCE] Student needs emotional comfort first. Be warm and reassuring before any teaching.",
    "progress":      "\n[INTENT: PROGRESS] Briefly celebrate the student's progress with specific, genuine praise.",
    "summary":       "\n[INTENT: SUMMARY] Give a warm spoken summary of what was covered today.",
    "general":       "",
}


def get_intent_context(intent: str, plan_step: dict | None = None) -> str:
    """Build a context string combining intent injection and current plan step."""
    ctx = _INTENT_INJECTIONS.get(intent, "")
    if plan_step:
        step_ctx = plan_step.get("context_injection", "")
        if step_ctx:
            ctx += (
                f"\n[SESSION PLAN — STEP {plan_step.get('step', '')} "
                f"({plan_step.get('type', '')})]: {step_ctx}"
            )
    return ctx


# ─────────────────────────────────────────────────────────────────────────────
#  Parallel executor
# ─────────────────────────────────────────────────────────────────────────────

def parallel_classify(history: list, message: str,
                      get_response_fn) -> tuple[str | None, str]:
    """
    Run proficiency classification and intent detection concurrently.

    Proficiency classification (especially the CNN tier) can be slow.
    Running it in parallel with intent detection cuts per-turn overhead.

    Returns (proficiency_label_or_None, intent_label).
    """
    from classifier import classify_proficiency

    prof_future   = _pool.submit(classify_proficiency, history)
    intent_future = _pool.submit(classify_intent, message, get_response_fn)

    proficiency = prof_future.result()
    intent      = intent_future.result()
    return proficiency, intent
