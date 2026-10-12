"""Per-message concern + sentiment tagging.

Model-estimated sentiment (-2..2) is stored on messages; it is kept separate from the self-reported
mood (1..5) on sessions, and the dashboard labels the two differently.
"""
from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError

from .config import CONCERN_CATEGORIES

log = logging.getLogger(__name__)

CONCERN_KEYWORDS: dict[str, list[str]] = {
    "income": ["salary", "earn", "income", "pay", "money", "wage", "how much", "rupee", "₹",
               "ಸಂಬಳ", "ಆದಾಯ", "ಸಂಪಾದ", "ಹಣ", "ಕೂಲಿ", "ವೇತನ", "ಎಷ್ಟು ಸಿಗ"],
    "job_security": ["job", "steady", "permanent", "placement", "security", "unemploy", "stable", "work available",
                     "ಕೆಲಸ", "ಉದ್ಯೋಗ", "ಸ್ಥಿರ", "ಖಾಯಂ", "ನೌಕರಿ"],
    "social_status": ["respect", "status", "society", "relatives", "neighbour", "neighbor", "marriage", "prestige",
                      "people will say", "log kya", "ಗೌರವ", "ಸಮಾಜ", "ಸಂಬಂಧಿಕ", "ಮದುವೆ", "ಮರ್ಯಾದೆ", "ಜನ ಏನು"],
    "safety": ["safe", "danger", "accident", "risk", "harass", "night shift", "injur", "shock",
               "ಸುರಕ್ಷ", "ಅಪಾಯ", "ಅಪಘಾತ", "ಕಿರುಕುಳ", "ರಾತ್ರಿ ಪಾಳಿ"],
    "cost": ["fee", "cost", "afford", "loan", "debt", "expensive", "scholarship", "free", "stipend",
             "ಶುಲ್ಕ", "ಖರ್ಚ", "ಸಾಲ", "ವೆಚ್ಚ", "ವಿದ್ಯಾರ್ಥಿವೇತನ", "ಉಚಿತ", "ಫೀಸ್"],
    "distance_migration": ["far", "away from home", "move to", "city", "hostel", "migrat", "outside", "near home",
                           "nearby", "where", "centre", "center", "ದೂರ", "ಬೇರೆ ಊರು", "ನಗರ", "ಹಾಸ್ಟೆಲ್", "ವಲಸೆ",
                           "ಹತ್ತಿರ", "ಎಲ್ಲಿ", "ಕೇಂದ್ರ"],
    "degree_first": ["degree", "college", "graduat", "engineering", "b.com", "b.sc", "study further", "higher studies",
                     "next step", "future", "grow", "ladder", "diploma",
                     "ಪದವಿ", "ಕಾಲೇಜು", "ಡಿಗ್ರಿ", "ಮುಂದೆ ಓದ", "ಮುಂದಿನ ಹಂತ", "ಡಿಪ್ಲೊಮಾ", "ಬೆಳವಣಿಗೆ"],
}

NEGATIVE = ["worried", "worry", "scared", "afraid", "fear", "not safe", "unsafe", "waste", "useless", "no respect",
            "low pay", "not good", "bad", "don't want", "do not want", "won't", "never", "problem", "difficult",
            "no future", "don't like", "do not like", "not sure", "ashamed", "angry", "against", "not happy", "doubt", "risky",
            "ಚಿಂತೆ", "ಭಯ", "ಹೆದರಿಕೆ", "ಬೇಡ", "ಕಷ್ಟ", "ತೊಂದರೆ", "ವ್ಯರ್ಥ", "ಅನುಮಾನ", "ಇಷ್ಟವಿಲ್ಲ", "ಸಮಸ್ಯೆ"]
STRONG_NEGATIVE = ["very worried", "not at all", "absolutely not", "never allow", "too dangerous", "waste of time",
                   "ತುಂಬಾ ಚಿಂತೆ", "ಖಂಡಿತ ಬೇಡ", "ಸಾಧ್ಯವೇ ಇಲ್ಲ"]
POSITIVE = ["good", "great", "happy", "hopeful", "thank", "helpful", "interested", "like", "sounds fine", "okay",
            "ok", "nice", "confident", "relieved", "makes sense",
            "ಒಳ್ಳೆಯ", "ಧನ್ಯವಾದ", "ಖುಷಿ", "ಇಷ್ಟ", "ಸರಿ", "ಭರವಸೆ", "ಸಮಾಧಾನ"]

SENSITIVE_PATTERNS = [
    r"harass", r"abuse", r"suicid", r"kill (my|him|her)self", r"self[- ]harm", r"depress", r"hopeless",
    r"beat(s|en)? (me|him|her)", r"violen", r"threat", r"loan shark", r"debt", r"can'?t repay", r"fight(ing)? at home",
    r"run away", r"ಕಿರುಕುಳ", r"ಆತ್ಮಹತ್ಯೆ", r"ಸಾಲದ ಹೊರೆ", r"ಸಾಲ ತೀರಿಸ", r"ಹಿಂಸೆ", r"ಮನೆಯಲ್ಲಿ ಜಗಳ", r"ಖಿನ್ನತೆ", r"ಹೊಡೆಯ",
]
CHILD_WORDS = r"(\b(daughter|son|girl|boy|child)\b|ಮಗಳ|ಮಗನ|ಮಗನಿ|ನನ್ನ ಮಗ|ಹುಡುಗಿ|ಹುಡುಗ|ಮಕ್ಕಳ)"
SAFETY_WORDS = r"(safe|safety|danger|night|alone|ಸುರಕ್ಷ|ಅಪಾಯ|ರಾತ್ರಿ|ಒಬ್ಬಳೇ|ಒಬ್ಬನೇ)"

COUNSELLOR_REQUEST = [r"counsel+or", r"talk to (a )?(human|person|someone)", r"real person", r"call me",
                      r"ಸಲಹೆಗಾರ", r"ಮನುಷ್ಯರೊಂದಿಗೆ", r"ಕರೆ ಮಾಡಿ"]


class Tag(BaseModel):
    concern_category: str | None = None
    sentiment: int | None = Field(default=None, ge=-2, le=2)
    confidence: float | None = Field(default=None, ge=0, le=1)


# On a tie, the more specific concern wins ("job" appears in many questions).
TIE_PRIORITY = ["safety", "cost", "degree_first", "social_status", "distance_migration", "income", "job_security"]


def keyword_concern(text: str) -> str | None:
    low = text.lower()
    scores = {c: sum(low.count(k) for k in kws) for c, kws in CONCERN_KEYWORDS.items()}
    best = max(scores, key=lambda c: (scores[c], -TIE_PRIORITY.index(c)))
    return best if scores[best] > 0 else None


def keyword_tag(text: str) -> Tag:
    low = text.lower()
    concern = keyword_concern(text) or "other"
    neg = sum(1 for w in NEGATIVE if w in low)
    strong = sum(1 for w in STRONG_NEGATIVE if w in low)
    pos = sum(1 for w in POSITIVE if re.search(rf"(?<![a-z]){re.escape(w)}", low))
    raw = pos - neg - 2 * strong
    sentiment = max(-2, min(2, raw))
    hits = neg + strong + pos
    confidence = 0.4 if hits == 0 else min(0.85, 0.5 + 0.1 * hits)
    return Tag(concern_category=concern, sentiment=sentiment, confidence=round(confidence, 2))


def is_sensitive(text: str) -> bool:
    low = text.lower()
    if any(re.search(p, low) for p in SENSITIVE_PATTERNS):
        return True
    return bool(re.search(CHILD_WORDS, low) and re.search(SAFETY_WORDS, low))


def wants_counsellor(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in COUNSELLOR_REQUEST)


TAG_SYSTEM = (
    "You label one message from a family talking about vocational training in Karnataka. "
    f"Return only JSON: {{\"concern_category\": one of {CONCERN_CATEGORIES}, "
    "\"sentiment\": integer -2 (very negative/resistant) to 2 (very positive), "
    "\"confidence\": number 0 to 1}. The message may be in Kannada or English. No other text."
)


def parse_tag(raw: str) -> Tag:
    """Strictly validate model output; anything invalid becomes nulls."""
    try:
        mt = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(mt.group(0) if mt else raw)
        tag = Tag.model_validate(data)
        if tag.concern_category not in CONCERN_CATEGORIES:
            return Tag()
        return tag
    except (ValueError, ValidationError, AttributeError):
        return Tag()


def tag_message(text: str, llm=None) -> Tag:
    """Use the fast model when available; keyword tagger in mock mode or on failure."""
    if llm is None or getattr(llm, "is_mock", True):
        return keyword_tag(text)
    try:
        raw = llm.quick_json(TAG_SYSTEM, text)
    except Exception as exc:  # network/API errors must never break the chat
        log.warning("sentiment tagging failed: %s", exc)
        return Tag()
    return parse_tag(raw)
