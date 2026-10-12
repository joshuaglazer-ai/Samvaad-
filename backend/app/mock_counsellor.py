"""Deterministic counsellor used when LLM_MODE=mock or no API key is set.

It behaves like the real model at the message level: first it emits tool_use blocks (real data tools),
then it composes a template answer ONLY from the tool results. All numbers come from tool output.
"""
from __future__ import annotations

import re

from .sentiment import is_sensitive, keyword_concern, wants_counsellor

# Order matters: more specific phrases first.
TRADE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("ev-service-technician", [r"\bev\b", "electric vehicle", "battery", "ವಿದ್ಯುತ್ ವಾಹನ", "ಇವಿ"]),
    ("home-health-aide", ["home health", "elder care", "home care", "ಮನೆ ಆರೋಗ್ಯ", "ಹಿರಿಯರ ಆರೈಕೆ", "ಮನೆ ಆರೈಕೆ"]),
    ("general-duty-assistant", ["general duty", r"\bgda\b", "hospital", "nurs", "patient", "health",
                                "ಆಸ್ಪತ್ರೆ", "ನರ್ಸ್", "ರೋಗಿ", "ಜನರಲ್ ಡ್ಯೂಟಿ", "ಆರೋಗ್ಯ"]),
    ("two-wheeler-service-technician", ["two-wheeler", "two wheeler", "bike", "scooter", "motorcycle",
                                       "ದ್ವಿಚಕ್ರ", "ಬೈಕ್", "ಸ್ಕೂಟರ್"]),
    ("solar-pv-installer", ["solar", "ಸೌರ", "ಸೋಲಾರ್"]),
    ("wireman", ["wireman", "wiring", "ವೈರ್‌ಮ್ಯಾನ್", "ವೈರ್ಮ್ಯಾನ್", "ವೈರಿಂಗ್"]),
    ("automotive-service-technician", [r"\bcar\b", "automotive", "mechanic", "ಕಾರು", "ಮೆಕ್ಯಾನಿಕ್"]),
    ("electrician", ["electrician", "electric", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "ವಿದ್ಯುತ್"]),
]
# Trades outside the pilot: passed to the tools as-is so the honest "no data" path is exercised.
OTHER_TRADES = {
    "plumber": ["plumb", "ಪ್ಲಂಬ"], "tailor": ["tailor", "ಟೈಲರ್", "ದರ್ಜಿ"], "welder": ["weld", "ವೆಲ್ಡ"],
    "beautician": ["beauti", "ಬ್ಯೂಟಿ"], "carpenter": ["carpent", "ಬಡಗಿ"], "data-entry-operator": ["data entry"],
    "drone-technician": ["drone", "ಡ್ರೋನ್"], "chef": ["chef", "cook", "ಅಡುಗೆ"],
}
INTEREST_TO_TRADE = {
    "electricity": "electrician", "nature_solar": "solar-pv-installer", "vehicles": "two-wheeler-service-technician",
    "machines": "automotive-service-technician", "helping": "general-duty-assistant", "computers": "ev-service-technician",
}

INTENT_PATTERNS = {
    "progression": ["next step", "ladder", "future", "grow", "diploma",
                    "degree", "higher stud", "study further", "career path", "ಮುಂದಿನ", "ಏಣಿ", "ಪದವಿ", "ಡಿಪ್ಲೊಮಾ",
                    "ಮುಂದೆ ಓದ", "ಮುಂದಿನ ಹಂತ"],
    "providers": ["where", "centre", "center", "institute", "near", "nearby", "visit", "ಎಲ್ಲಿ", "ಕೇಂದ್ರ", "ಹತ್ತಿರ"],
    "costs": ["fee", "cost", "afford", "scholarship", "stipend", "loan", "free", "ಶುಲ್ಕ", "ಖರ್ಚ", "ವೆಚ್ಚ",
              "ವಿದ್ಯಾರ್ಥಿವೇತನ", "ಉಚಿತ", "ಸಾಲ"],
    "options": ["options", "which course", "what courses", "which trade", "what trades", "other option", "choices",
                "ಆಯ್ಕೆ", "ಯಾವ ಕೋರ್ಸ್", "ಬೇರೆ"],
}
CONCERN_TO_INTENT = {
    "income": "outcomes", "job_security": "outcomes", "social_status": "outcomes", "other": "outcomes",
    "degree_first": "progression", "cost": "costs", "distance_migration": "providers", "safety": "safety",
}
ALIGN_FOR_CONCERN = {"degree_first": "study_further", "income": "earning_soon", "distance_migration": "near_home",
                     "social_status": "respect", "safety": "safety"}

ALIGN_LABEL = {
    "en": {"earning_soon": "Earning soon", "near_home": "Staying near home", "respect": "Respect in the community",
           "study_further": "Studying further", "safety": "Safety"},
    "kn": {"earning_soon": "ಬೇಗ ಸಂಪಾದನೆ", "near_home": "ಮನೆಯ ಹತ್ತಿರ ಇರುವುದು", "respect": "ಊರಿನಲ್ಲಿ ಗೌರವ",
           "study_further": "ಮುಂದೆ ಓದುವುದು", "safety": "ಸುರಕ್ಷತೆ"},
}
DISTRICT_KN = {"Bengaluru Urban": "ಬೆಂಗಳೂರು ನಗರ", "Mysuru": "ಮೈಸೂರು", "Kalaburagi": "ಕಲಬುರಗಿ", "Dharwad": "ಧಾರವಾಡ"}


def _has(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) if p.startswith(r"\b") else p in text for p in patterns)


def detect_trade(text: str) -> str | None:
    low = text.lower()
    for slug, kws in TRADE_KEYWORDS:
        if _has(low, kws):
            return slug
    for slug, kws in OTHER_TRADES.items():
        if _has(low, kws):
            return slug
    return None


def detect_intent(text: str) -> str:
    low = text.lower()
    for intent in ("options", "costs", "providers", "progression"):
        if _has(low, INTENT_PATTERNS[intent]):
            return intent
    return CONCERN_TO_INTENT.get(keyword_concern(text) or "other", "outcomes")


def plan(text: str, ctx: dict) -> list[tuple[str, dict]]:
    """Decide which tools to call for a user message. Returns [(tool_name, input), ...]."""
    if is_sensitive(text):
        return [("escalate", {"reason": "Sensitive topic raised by the family", "trigger": "sensitive_topic"})]
    if wants_counsellor(text):
        return [("escalate", {"reason": "Family asked to talk to a counsellor", "trigger": "user_request"})]
    intent = detect_intent(text)
    trade = detect_trade(text) or ctx.get("last_trade") or ctx.get("suggested_trade")
    district = ctx.get("district")
    if intent == "options" or not trade:
        return [("list_trades", {"language": ctx.get("language", "en")})]
    if intent == "progression":
        return [("get_progression", {"trade_slug": trade, "education_level": ctx.get("learner_education")})]
    if intent == "costs":
        args = {"trade_slug": trade, "district": district}
        if ctx.get("income_bracket"):
            args["income_bracket"] = ctx["income_bracket"]
        return [("get_costs_and_support", args)]
    if intent in ("providers", "safety"):
        return [("get_providers", {"trade_slug": trade, "district": district})]
    return [("get_trade_outcomes", {"trade_slug": trade, "district": district})]


# ------------------------------------------------------------------------------------------ composing
# Answer shape (Update 2): reassure (varied) → one simple fact → one gentle next step. ≤ ~50 words.
# Exact figures stay on the card; the text uses "about" + the rounding rule in guardrail.py.


def inr(n: float | int | None) -> str:
    """Indian digit grouping: 118000 → 1,18,000."""
    if n is None:
        return "—"
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = f"{head},{tail}"
    return ("-" if n < 0 else "") + s


def approx_amount(v: float | int) -> int:
    """Spoken rounding (documented in guardrail.py): nearest ₹1,000 from ₹10,000 up, else nearest ₹500."""
    step = 1000 if v >= 10000 else 500
    return int((v + step / 2) // step * step)


def pct(x: float | None) -> str:
    if x is None:
        return "—"
    return str(int(round(x)))


REASSURE = {
    "en": {
        "income": ["It's natural to think about earnings first.", "Earnings matter to every family.", "That's a fair thing to ask."],
        "job_security": ["Wanting a steady job is a fair hope.", "Every family wants some security.", "That's an important worry."],
        "social_status": ["Many families have this question.", "Respect matters to every family.", "That's a very common worry."],
        "safety": ["Your child's safety matters most.", "It's right to think about safety.", "Safety comes first for every family."],
        "cost": ["Cost is an important part of this decision.", "It's wise to plan for costs early.", "Many families worry about fees."],
        "distance_migration": ["Staying close to family matters.", "It's natural to want training near home.", "Being near home is important to many families."],
        "degree_first": ["Many families think about a degree first.", "Studying further is a good thought.", "That's a thoughtful question."],
        "other": ["Thank you for asking.", "Good question.", "Happy to help with that."],
    },
    "kn": {
        "income": ["ಮೊದಲು ಸಂಪಾದನೆಯ ಬಗ್ಗೆ ಯೋಚಿಸುವುದು ಸಹಜ.", "ಸಂಪಾದನೆ ಪ್ರತಿಯೊಂದು ಕುಟುಂಬಕ್ಕೂ ಮುಖ್ಯ.", "ಇದು ಕೇಳಬೇಕಾದ ಪ್ರಶ್ನೆ."],
        "job_security": ["ಸ್ಥಿರ ಕೆಲಸದ ಆಸೆ ಸಹಜ.", "ಪ್ರತಿಯೊಂದು ಕುಟುಂಬಕ್ಕೂ ಭದ್ರತೆ ಬೇಕು.", "ಇದು ಮುಖ್ಯವಾದ ಚಿಂತೆ."],
        "social_status": ["ಹಲವು ಕುಟುಂಬಗಳಿಗೆ ಈ ಪ್ರಶ್ನೆ ಇರುತ್ತದೆ.", "ಗೌರವ ಎಲ್ಲರಿಗೂ ಮುಖ್ಯ.", "ಇದು ತುಂಬಾ ಸಾಮಾನ್ಯ ಚಿಂತೆ."],
        "safety": ["ನಿಮ್ಮ ಮಗುವಿನ ಸುರಕ್ಷತೆ ಎಲ್ಲಕ್ಕಿಂತ ಮುಖ್ಯ.", "ಸುರಕ್ಷತೆಯ ಬಗ್ಗೆ ಯೋಚಿಸುವುದು ಸರಿ.", "ಪ್ರತಿ ಕುಟುಂಬಕ್ಕೂ ಸುರಕ್ಷತೆ ಮೊದಲು."],
        "cost": ["ಖರ್ಚು ಈ ನಿರ್ಧಾರದ ಮುಖ್ಯ ಭಾಗ.", "ಖರ್ಚಿನ ಬಗ್ಗೆ ಮೊದಲೇ ಯೋಚಿಸುವುದು ಜಾಣತನ.", "ಹಲವು ಕುಟುಂಬಗಳಿಗೆ ಶುಲ್ಕದ ಚಿಂತೆ ಇರುತ್ತದೆ."],
        "distance_migration": ["ಕುಟುಂಬದ ಹತ್ತಿರ ಇರುವುದು ಮುಖ್ಯ.", "ಮನೆಯ ಹತ್ತಿರ ತರಬೇತಿ ಬೇಕೆನ್ನುವುದು ಸಹಜ.", "ಹಲವು ಕುಟುಂಬಗಳಿಗೆ ಮನೆಯ ಹತ್ತಿರ ಇರುವುದು ಮುಖ್ಯ."],
        "degree_first": ["ಹಲವು ಕುಟುಂಬಗಳು ಮೊದಲು ಪದವಿಯ ಬಗ್ಗೆ ಯೋಚಿಸುತ್ತವೆ.", "ಮುಂದೆ ಓದುವ ಯೋಚನೆ ಒಳ್ಳೆಯದು.", "ಇದು ಯೋಚಿಸಿ ಕೇಳಿದ ಪ್ರಶ್ನೆ."],
        "other": ["ಕೇಳಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದ.", "ಒಳ್ಳೆಯ ಪ್ರಶ್ನೆ.", "ಸಹಾಯ ಮಾಡಲು ಸಂತೋಷ."],
    },
}

T = {
    "en": {
        "src_demo": "from demo data, {period}",
        "src": "from {source}, {period}",
        "state_fb": " District data isn't available, so this is the state figure.",
        "national_fb": " District and state data aren't available, so this is the national figure.",
        "nodata": "I don't have reliable data on this yet. A counsellor can help — would you like that?",
        "earn": "This data shows {trade} learners{place} usually earn about ₹{amount} a month ({src}).",
        "placed": "This data shows about {rate}% of {trade} learners{place} found work after training ({src}).",
        "valued": "Skilled work like {trade} is valued and needed everywhere.",
        "ladder": "{trade} has a clear growth path, from {first} up to {last}.",
        "can_start": " Your child can start now.",
        "cannot_start": " It needs: {req}.",
        "degree_honest": " For some learners a degree is also a good path.",
        "costs_free": "For {trade}, some courses are free and others cost up to about ₹{hi}.",
        "costs_range": "For {trade}, fees are about ₹{lo} to ₹{hi}.",
        "costs_none": "I couldn't find a fee figure for {trade}.",
        "scheme": " Eligible families may get free training under a scheme.",
        "scheme_maybe": " Support may be available, depending on family income.",
        "providers": "In {district}, you can visit {name}.",
        "providers_more": " There are {n} more centres on the card.",
        "providers_none": "I couldn't find a {trade} centre in {district} in our data.",
        "safety": "Training centres follow safety rules, and learners are taught protective practices.",
        "options": "Some options are {names}.",
        "escalate": "Thank you for telling us. A counsellor is the right person to help and will join shortly. You can wait here or ask for a call back.",
        "escalate_request": "Of course. A counsellor will join shortly. You can wait here or ask for a call back.",
        "both_views": "You both want what is best. Let's look at {value} from both sides.",
        "q_earn": " Would you like to see how this can grow?",
        "q_placed": " Would you like to see training centres near you?",
        "q_valued": " Shall I show you the growth path?",
        "q_ladder": " Would you like to know about fees?",
        "q_costs": " Shall I show training centres near you?",
        "q_providers": " Would you like to know about earnings?",
        "q_options": " Which one interests you?",
        "q_safety": " Would you like to talk to a counsellor about this?",
        "in_place": " in {district}",
    },
    "kn": {
        "src_demo": "ಡೆಮೊ ಮಾಹಿತಿ, {period}",
        "src": "{source}, {period}",
        "state_fb": " ಜಿಲ್ಲಾ ಮಾಹಿತಿ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಇದು ರಾಜ್ಯ ಮಟ್ಟದ ಅಂಕಿ.",
        "national_fb": " ಜಿಲ್ಲಾ ಮತ್ತು ರಾಜ್ಯ ಮಾಹಿತಿ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಇದು ರಾಷ್ಟ್ರ ಮಟ್ಟದ ಅಂಕಿ.",
        "nodata": "ಇದರ ಬಗ್ಗೆ ಇನ್ನೂ ವಿಶ್ವಾಸಾರ್ಹ ಮಾಹಿತಿ ನನ್ನ ಬಳಿ ಇಲ್ಲ. ಸಲಹೆಗಾರರು ಸಹಾಯ ಮಾಡಬಹುದು — ಬೇಕೇ?",
        "earn": "ಈ ಮಾಹಿತಿಯ ಪ್ರಕಾರ {place}{trade} ಕಲಿತವರು ಸಾಮಾನ್ಯವಾಗಿ ತಿಂಗಳಿಗೆ ಸುಮಾರು ₹{amount} ಸಂಪಾದಿಸುತ್ತಾರೆ ({src}).",
        "placed": "ಈ ಮಾಹಿತಿಯ ಪ್ರಕಾರ {place}{trade} ಕಲಿತವರಲ್ಲಿ ಸುಮಾರು ಶೇ. {rate} ಜನರಿಗೆ ಕೆಲಸ ಸಿಕ್ಕಿದೆ ({src}).",
        "valued": "{trade} ನಂತಹ ಕೌಶಲದ ಕೆಲಸಕ್ಕೆ ಎಲ್ಲೆಡೆ ಮೌಲ್ಯ ಮತ್ತು ಬೇಡಿಕೆ ಇದೆ.",
        "ladder": "{trade} ನಲ್ಲಿ ಬೆಳೆಯುವ ಸ್ಪಷ್ಟ ದಾರಿ ಇದೆ: {first} ರಿಂದ {last} ವರೆಗೆ.",
        "can_start": " ನಿಮ್ಮ ಮಗು ಈಗಲೇ ಪ್ರಾರಂಭಿಸಬಹುದು.",
        "cannot_start": " ಇದಕ್ಕೆ ಬೇಕಾದದ್ದು: {req}.",
        "degree_honest": " ಕೆಲವರಿಗೆ ಪದವಿಯೂ ಒಳ್ಳೆಯ ದಾರಿ.",
        "costs_free": "{trade} ತರಬೇತಿಗೆ ಕೆಲವು ಕೋರ್ಸ್‌ಗಳು ಉಚಿತ; ಕೆಲವಕ್ಕೆ ಸುಮಾರು ₹{hi} ವರೆಗೆ ಶುಲ್ಕ ಇದೆ.",
        "costs_range": "{trade} ತರಬೇತಿ ಶುಲ್ಕ ಸುಮಾರು ₹{lo} ರಿಂದ ₹{hi}.",
        "costs_none": "{trade} ತರಬೇತಿಯ ಶುಲ್ಕದ ಅಂಕಿ ಸಿಗಲಿಲ್ಲ.",
        "scheme": " ಅರ್ಹ ಕುಟುಂಬಗಳಿಗೆ ಯೋಜನೆಯಡಿ ಉಚಿತ ತರಬೇತಿ ಸಿಗಬಹುದು.",
        "scheme_maybe": " ಕುಟುಂಬದ ಆದಾಯವನ್ನು ಅವಲಂಬಿಸಿ ನೆರವು ಸಿಗಬಹುದು.",
        "providers": "{district} ಜಿಲ್ಲೆಯಲ್ಲಿ ನೀವು {name} ಗೆ ಭೇಟಿ ನೀಡಬಹುದು.",
        "providers_more": " ಇನ್ನೂ {n} ಕೇಂದ್ರಗಳು ಕಾರ್ಡ್‌ನಲ್ಲಿವೆ.",
        "providers_none": "{district} ಜಿಲ್ಲೆಯಲ್ಲಿ {trade} ಕೇಂದ್ರ ನಮ್ಮ ಮಾಹಿತಿಯಲ್ಲಿ ಸಿಗಲಿಲ್ಲ.",
        "safety": "ತರಬೇತಿ ಕೇಂದ್ರಗಳು ಸುರಕ್ಷತಾ ನಿಯಮಗಳನ್ನು ಪಾಲಿಸುತ್ತವೆ, ಮತ್ತು ಕಲಿಯುವವರಿಗೆ ರಕ್ಷಣೆಯ ವಿಧಾನಗಳನ್ನು ಕಲಿಸಲಾಗುತ್ತದೆ.",
        "options": "ಕೆಲವು ಆಯ್ಕೆಗಳು: {names}.",
        "escalate": "ನಮಗೆ ತಿಳಿಸಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದ. ಇದಕ್ಕೆ ಸಲಹೆಗಾರರೇ ಸರಿಯಾದ ಸಹಾಯ; ಅವರು ಸ್ವಲ್ಪ ಸಮಯದಲ್ಲಿ ಸೇರುತ್ತಾರೆ. ಇಲ್ಲೇ ಕಾಯಬಹುದು ಅಥವಾ ಮರಳಿ ಕರೆ ಕೇಳಬಹುದು.",
        "escalate_request": "ಸರಿ. ಸಲಹೆಗಾರರು ಸ್ವಲ್ಪ ಸಮಯದಲ್ಲಿ ಸೇರುತ್ತಾರೆ. ಇಲ್ಲೇ ಕಾಯಬಹುದು ಅಥವಾ ಮರಳಿ ಕರೆ ಕೇಳಬಹುದು.",
        "both_views": "ನೀವಿಬ್ಬರೂ ಉತ್ತಮವಾದದ್ದನ್ನೇ ಬಯಸುತ್ತೀರಿ. {value} ಬಗ್ಗೆ ಎರಡೂ ನೋಟಗಳನ್ನು ನೋಡೋಣ.",
        "q_earn": " ಇದು ಹೇಗೆ ಬೆಳೆಯಬಹುದು ಎಂದು ನೋಡೋಣವೇ?",
        "q_placed": " ಹತ್ತಿರದ ತರಬೇತಿ ಕೇಂದ್ರಗಳನ್ನು ನೋಡೋಣವೇ?",
        "q_valued": " ಬೆಳವಣಿಗೆಯ ದಾರಿಯನ್ನು ತೋರಿಸಲೇ?",
        "q_ladder": " ಶುಲ್ಕದ ಬಗ್ಗೆ ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಾ?",
        "q_costs": " ಹತ್ತಿರದ ತರಬೇತಿ ಕೇಂದ್ರಗಳನ್ನು ತೋರಿಸಲೇ?",
        "q_providers": " ಸಂಪಾದನೆಯ ಬಗ್ಗೆ ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಾ?",
        "q_options": " ಯಾವುದು ನಿಮಗೆ ಇಷ್ಟ?",
        "q_safety": " ಇದರ ಬಗ್ಗೆ ಸಲಹೆಗಾರರೊಂದಿಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಾ?",
        "in_place": "{district} ಜಿಲ್ಲೆಯಲ್ಲಿ ",
    },
}


def _district_name(d: str | None, lang: str) -> str:
    return DISTRICT_KN.get(d or "", d or "") if lang == "kn" else (d or "")


def _fallback_note(res: dict, t: dict) -> str:
    codes = res.get("limitation_codes", [])
    if "state_fallback" in codes:
        return t["state_fb"]
    if "national_fallback" in codes:
        return t["national_fb"]
    return ""


def _src(res: dict, rec: dict, t: dict) -> str:
    period = rec.get("reporting_period", "")
    if rec.get("data_status", res.get("data_status")) == "demo":
        return t["src_demo"].format(period=period)
    return t["src"].format(source=(res.get("source") or {}).get("title", ""), period=period)


def reassure(concern: str, ctx: dict, lang: str) -> str:
    options = REASSURE[lang].get(concern) or REASSURE[lang]["other"]
    return options[ctx.get("turn", 0) % len(options)]


def compose(user_text: str, ctx: dict, results: list[tuple[str, dict]]) -> str:
    lang = "kn" if ctx.get("language") == "kn" else "en"
    t = T[lang]
    concern = keyword_concern(user_text) or "other"

    for name, res in results:
        if name == "escalate":
            return t["escalate_request"] if res.get("trigger") == "user_request" else t["escalate"]

    # When learner and parent ranked this concern's value differently, the reassurance acknowledges both views.
    al = ctx.get("alignment") or {}
    value = ALIGN_FOR_CONCERN.get(concern)
    if al.get("complete") and value and al.get("biggest_difference") == value:
        opener = t["both_views"].format(value=ALIGN_LABEL[lang][value])
    else:
        opener = reassure(concern, ctx, lang)

    if not results:
        return f"{opener} {t['nodata']}"
    name, res = results[0]
    if not res.get("found"):
        if name == "get_providers" and res.get("trade_name"):
            miss = t["providers_none"].format(trade=res["trade_name"], district=_district_name(ctx.get("district"), lang))
            return f"{opener} {miss} {t['nodata']}"
        return f"{opener} {t['nodata']}"

    fact, question = "", ""
    if name == "get_trade_outcomes":
        rec = res["records"][0]
        place = ""
        if res.get("geo_level_used") == "district" and rec.get("district"):
            place = t["in_place"].format(district=_district_name(rec["district"], lang))
        fields = dict(trade=res["trade_name"], place=place, src=_src(res, rec, t))
        if concern == "social_status":
            fact, question = t["valued"].format(trade=res["trade_name"]), t["q_valued"]
        elif concern == "job_security" and rec.get("placement_rate") is not None:
            fact, question = t["placed"].format(rate=pct(rec["placement_rate"]), **fields), t["q_placed"]
        elif rec.get("earnings_median") is not None:
            fact, question = t["earn"].format(amount=inr(approx_amount(rec["earnings_median"])), **fields), t["q_earn"]
        else:
            fact, question = t["placed"].format(rate=pct(rec.get("placement_rate")), **fields), t["q_placed"]
        if concern != "social_status":
            fact += _fallback_note(res, t)
    elif name == "get_progression":
        recs = res["records"]
        fact = t["ladder"].format(trade=res["trade_name"], first=recs[0]["title"], last=recs[-1]["title"])
        if res.get("can_start_training") is True:
            fact += t["can_start"]
        elif res.get("can_start_training") is False:
            fact += t["cannot_start"].format(req=res.get("trade_entry_requirement", ""))
        if concern == "degree_first":
            fact += t["degree_honest"]
        question = t["q_ladder"]
    elif name == "get_costs_and_support":
        rec = res["records"][0]
        lo, hi = rec.get("fee_min"), rec.get("fee_max")
        if hi is None:
            fact = t["costs_none"].format(trade=res["trade_name"])
        elif lo == 0:
            fact = t["costs_free"].format(trade=res["trade_name"], hi=inr(approx_amount(hi)))
        else:
            fact = t["costs_range"].format(trade=res["trade_name"], lo=inr(approx_amount(lo)), hi=inr(approx_amount(hi)))
        schemes = [s for s in rec.get("supports", []) if s["support_type"] in ("scheme", "scholarship")]
        if any(s["depends_on_income"] for s in schemes):
            fact += t["scheme_maybe"]
        elif schemes:
            fact += t["scheme"]
        question = t["q_costs"]
    elif name == "get_providers":
        recs = res["records"]
        base = t["providers"].format(district=_district_name(ctx.get("district"), lang), name=recs[0]["name"])
        if len(recs) > 1:
            base += t["providers_more"].format(n=len(recs) - 1)
        if concern == "safety":
            fact, question = t["safety"], t["q_safety"]
        else:
            fact, question = base, t["q_providers"]
    elif name == "list_trades":
        names = [r["name"] for r in res["records"]][:4]
        fact, question = t["options"].format(names=", ".join(names)), t["q_options"]

    return f"{opener} {fact.strip()}{question}"
