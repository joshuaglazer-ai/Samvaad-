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


def pct(x: float | None) -> str:
    if x is None:
        return "—"
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


T = {
    "en": {
        "ack": "That is an important question.",
        "acks": ["Thank you for asking.", "That is worth knowing.", "Good question.", "That is an important question."],
        "ack_parent": "That is an important question, and it is right to ask it.",
        "demo": " This is demo data, for testing only.",
        "state_fb": " District data is not available. This is the state-level figure.",
        "national_fb": " District and state data are not available. This is the national figure.",
        "older": " The latest year is not available here, so this is an earlier year.",
        "card": " See the card below.",
        "nodata": "I don't have verified data for this yet. A counsellor can help you with it. Would you like to talk to one?",
        "offer": "A counsellor can help you with it. Would you like to talk to one?",
        "outcome": "For {trade}{place}, {rate}% of trained learners got a job ({period}). Typical monthly earnings were ₹{median}, from ₹{lo} to ₹{hi}, based on {n} learners. Source: {source}.",
        "outcome_noearn": "For {trade}{place}, {rate}% of trained learners got a job ({period}), based on {n} learners. Source: {source}.",
        "status_line": " Skilled work is recognised on NSQF, a national ladder of skill levels, and it can grow step by step.",
        "ladder": "Here is the career ladder for {trade}. It starts with: {first}. It can lead to: {last}.",
        "can_start": " The learner can start this training now.",
        "cannot_start": " This training needs: {req}.",
        "nsqf": " NSQF is a national ladder of skill levels.",
        "degree_honest": " A degree can also be a good path. It depends on the learner's goals.",
        "costs_free": "For {trade}, some courses are free and fees go up to ₹{hi}.",
        "costs_range": "For {trade}, course fees are from ₹{lo} to ₹{hi}.",
        "costs_none": "For {trade}, I could not find a fee figure.",
        "support": " Support: {items}",
        "providers": "In {district}, these centres offer {trade} training: {names}. You can visit and ask about placements and safety.",
        "providers_none": "I don't have verified data for this yet. I could not find a {trade} centre in {district} in our data.",
        "providers_other": " Centres for this trade are listed in: {other}.",
        "safety": "Your concern for safety matters. Training centres teach safe work practices, and you can visit one to see it yourself. I don't have verified workplace safety data yet; a counsellor can talk this through with you.",
        "options": "Here are the options in our pilot: {names}.",
        "escalate": "Thank you for telling us. This matters, and a counsellor is the right person to help. A counsellor will join shortly. You can wait here or ask for a call back.",
        "escalate_request": "Of course. A counsellor will join shortly. You can wait here or ask for a call back.",
        "disagree": " You both want what is best. You see {value} a little differently. Let's look at both views.",
        "q_outcome": " Would you like to see the next steps after this training?",
        "q_ladder": " Would you like to know about fees and support?",
        "q_costs": " Would you like to see training centres near you?",
        "q_providers": " Would you like to know about earnings after this training?",
        "q_options": " Which one would you like to know more about?",
        "q_safety": " Would you like to talk to a counsellor about this?",
        "in_place": " in {district}",
    },
    "kn": {
        "ack": "ಇದು ಮುಖ್ಯವಾದ ಪ್ರಶ್ನೆ.",
        "acks": ["ಕೇಳಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದ.", "ಇದನ್ನು ತಿಳಿಯುವುದು ಮುಖ್ಯ.", "ಒಳ್ಳೆಯ ಪ್ರಶ್ನೆ.", "ಇದು ಮುಖ್ಯವಾದ ಪ್ರಶ್ನೆ."],
        "ack_parent": "ಇದು ಮುಖ್ಯವಾದ ಪ್ರಶ್ನೆ, ಇದನ್ನು ಕೇಳುವುದು ಸರಿಯಾಗಿದೆ.",
        "demo": " ಇದು ಡೆಮೊ ಮಾಹಿತಿ, ಪರೀಕ್ಷೆಗೆ ಮಾತ್ರ.",
        "state_fb": " ಜಿಲ್ಲಾ ಮಟ್ಟದ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. ಇದು ರಾಜ್ಯ ಮಟ್ಟದ ಅಂಕಿ.",
        "national_fb": " ಜಿಲ್ಲಾ ಮತ್ತು ರಾಜ್ಯ ಮಟ್ಟದ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. ಇದು ರಾಷ್ಟ್ರ ಮಟ್ಟದ ಅಂಕಿ.",
        "older": " ಇತ್ತೀಚಿನ ವರ್ಷದ ಮಾಹಿತಿ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಹಿಂದಿನ ವರ್ಷದ ಅಂಕಿ ತೋರಿಸಲಾಗಿದೆ.",
        "card": " ಕೆಳಗಿನ ಕಾರ್ಡ್ ನೋಡಿ.",
        "nodata": "ಇದಕ್ಕೆ ಇನ್ನೂ ಪರಿಶೀಲಿತ ಮಾಹಿತಿ ನನ್ನ ಬಳಿ ಇಲ್ಲ. ಸಲಹೆಗಾರರು ಇದರಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಹುದು. ಅವರೊಂದಿಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಾ?",
        "offer": "ಸಲಹೆಗಾರರು ಇದರಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಹುದು. ಅವರೊಂದಿಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಾ?",
        "outcome": "{place}{trade} ತರಬೇತಿ ಪಡೆದವರಲ್ಲಿ ಶೇ. {rate} ಜನರಿಗೆ ಕೆಲಸ ಸಿಕ್ಕಿದೆ ({period}). ಸಾಮಾನ್ಯ ತಿಂಗಳ ಸಂಪಾದನೆ ₹{median}; ₹{lo} ರಿಂದ ₹{hi} ವರೆಗೆ. ಇದು {n} ಕಲಿಯುವವರ ಆಧಾರದಲ್ಲಿ. ಮೂಲ: {source}.",
        "outcome_noearn": "{place}{trade} ತರಬೇತಿ ಪಡೆದವರಲ್ಲಿ ಶೇ. {rate} ಜನರಿಗೆ ಕೆಲಸ ಸಿಕ್ಕಿದೆ ({period}), {n} ಕಲಿಯುವವರ ಆಧಾರದಲ್ಲಿ. ಮೂಲ: {source}.",
        "status_line": " ಕೌಶಲದ ಕೆಲಸಕ್ಕೆ NSQF ಎಂಬ ಕೌಶಲ ಮಟ್ಟಗಳ ರಾಷ್ಟ್ರೀಯ ಏಣಿಯಲ್ಲಿ ಮಾನ್ಯತೆ ಇದೆ, ಮತ್ತು ಹಂತ ಹಂತವಾಗಿ ಬೆಳೆಯಬಹುದು.",
        "ladder": "{trade} ವೃತ್ತಿ ಏಣಿ ಇಲ್ಲಿದೆ. ಮೊದಲ ಹಂತ: {first}. ಮುಂದೆ ತಲುಪಬಹುದಾದದ್ದು: {last}.",
        "can_start": " ಕಲಿಯುವವರು ಈಗಲೇ ಈ ತರಬೇತಿ ಪ್ರಾರಂಭಿಸಬಹುದು.",
        "cannot_start": " ಈ ತರಬೇತಿಗೆ ಬೇಕಾದದ್ದು: {req}.",
        "nsqf": " NSQF ಎಂದರೆ ಕೌಶಲ ಮಟ್ಟಗಳ ರಾಷ್ಟ್ರೀಯ ಏಣಿ.",
        "degree_honest": " ಪದವಿಯೂ ಒಳ್ಳೆಯ ದಾರಿ ಆಗಬಹುದು. ಅದು ಕಲಿಯುವವರ ಗುರಿಯನ್ನು ಅವಲಂಬಿಸಿದೆ.",
        "costs_free": "{trade} ತರಬೇತಿಗೆ ಕೆಲವು ಕೋರ್ಸ್‌ಗಳು ಉಚಿತ; ಶುಲ್ಕ ₹{hi} ವರೆಗೆ ಇರಬಹುದು.",
        "costs_range": "{trade} ತರಬೇತಿಗೆ ಶುಲ್ಕ ₹{lo} ರಿಂದ ₹{hi} ವರೆಗೆ.",
        "costs_none": "{trade} ತರಬೇತಿಯ ಶುಲ್ಕದ ಅಂಕಿ ಸಿಗಲಿಲ್ಲ.",
        "support": " ನೆರವು: {items}",
        "providers": "{district} ಜಿಲ್ಲೆಯಲ್ಲಿ ಈ ಕೇಂದ್ರಗಳಲ್ಲಿ {trade} ತರಬೇತಿ ಸಿಗುತ್ತದೆ: {names}. ಅಲ್ಲಿಗೆ ಭೇಟಿ ನೀಡಿ ಕೆಲಸ ಮತ್ತು ಸುರಕ್ಷತೆ ಬಗ್ಗೆ ಕೇಳಬಹುದು.",
        "providers_none": "ಇದಕ್ಕೆ ಇನ್ನೂ ಪರಿಶೀಲಿತ ಮಾಹಿತಿ ನನ್ನ ಬಳಿ ಇಲ್ಲ. {district} ಜಿಲ್ಲೆಯಲ್ಲಿ {trade} ಕೇಂದ್ರ ನಮ್ಮ ಮಾಹಿತಿಯಲ್ಲಿ ಸಿಗಲಿಲ್ಲ.",
        "providers_other": " ಈ ತರಬೇತಿಯ ಕೇಂದ್ರಗಳು ಇಲ್ಲಿವೆ: {other}.",
        "safety": "ಸುರಕ್ಷತೆಯ ಬಗ್ಗೆ ನಿಮ್ಮ ಕಾಳಜಿ ಮುಖ್ಯ. ತರಬೇತಿ ಕೇಂದ್ರಗಳು ಸುರಕ್ಷಿತ ಕೆಲಸದ ವಿಧಾನಗಳನ್ನು ಕಲಿಸುತ್ತವೆ; ನೀವೇ ಭೇಟಿ ನೀಡಿ ನೋಡಬಹುದು. ಕೆಲಸದ ಸ್ಥಳದ ಸುರಕ್ಷತೆಯ ಪರಿಶೀಲಿತ ಮಾಹಿತಿ ಇನ್ನೂ ಇಲ್ಲ; ಸಲಹೆಗಾರರು ಇದರ ಬಗ್ಗೆ ನಿಮ್ಮೊಂದಿಗೆ ಮಾತನಾಡಬಹುದು.",
        "options": "ನಮ್ಮ ಪ್ರಾಯೋಗಿಕ ಯೋಜನೆಯಲ್ಲಿರುವ ಆಯ್ಕೆಗಳು: {names}.",
        "escalate": "ನಮಗೆ ತಿಳಿಸಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದ. ಇದು ಮುಖ್ಯ ವಿಷಯ, ಇದಕ್ಕೆ ಸಲಹೆಗಾರರೇ ಸರಿಯಾದ ಸಹಾಯ ಮಾಡಬಲ್ಲರು. ಸಲಹೆಗಾರರು ಸ್ವಲ್ಪ ಸಮಯದಲ್ಲಿ ಸೇರುತ್ತಾರೆ. ಇಲ್ಲೇ ಕಾಯಬಹುದು ಅಥವಾ ಮರಳಿ ಕರೆ ಕೇಳಬಹುದು.",
        "escalate_request": "ಖಂಡಿತ. ಸಲಹೆಗಾರರು ಸ್ವಲ್ಪ ಸಮಯದಲ್ಲಿ ಸೇರುತ್ತಾರೆ. ಇಲ್ಲೇ ಕಾಯಬಹುದು ಅಥವಾ ಮರಳಿ ಕರೆ ಕೇಳಬಹುದು.",
        "disagree": " ನೀವಿಬ್ಬರೂ ಉತ್ತಮವಾದದ್ದನ್ನೇ ಬಯಸುತ್ತೀರಿ. {value} ಬಗ್ಗೆ ನಿಮ್ಮ ನೋಟ ಸ್ವಲ್ಪ ಬೇರೆ. ಎರಡೂ ನೋಟಗಳನ್ನು ನೋಡೋಣ.",
        "q_outcome": " ಈ ತರಬೇತಿಯ ನಂತರದ ಮುಂದಿನ ಹಂತಗಳನ್ನು ನೋಡಲು ಬಯಸುತ್ತೀರಾ?",
        "q_ladder": " ಶುಲ್ಕ ಮತ್ತು ನೆರವಿನ ಬಗ್ಗೆ ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಾ?",
        "q_costs": " ನಿಮ್ಮ ಹತ್ತಿರದ ತರಬೇತಿ ಕೇಂದ್ರಗಳನ್ನು ನೋಡಲು ಬಯಸುತ್ತೀರಾ?",
        "q_providers": " ಈ ತರಬೇತಿಯ ನಂತರದ ಸಂಪಾದನೆಯ ಬಗ್ಗೆ ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಾ?",
        "q_options": " ಯಾವುದರ ಬಗ್ಗೆ ಹೆಚ್ಚು ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಿ?",
        "q_safety": " ಇದರ ಬಗ್ಗೆ ಸಲಹೆಗಾರರೊಂದಿಗೆ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಾ?",
        "in_place": "{district} ಜಿಲ್ಲೆಯಲ್ಲಿ ",
    },
}


def _limits(result: dict, t: dict) -> str:
    codes = result.get("limitation_codes", [])
    out = ""
    if "state_fallback" in codes:
        out += t["state_fb"]
    if "national_fallback" in codes:
        out += t["national_fb"]
    if "older_year" in codes:
        out += t["older"]
    if "demo" in codes:
        out += t["demo"]
    return out


def _district_name(d: str | None, lang: str) -> str:
    return DISTRICT_KN.get(d or "", d or "") if lang == "kn" else (d or "")


def compose(user_text: str, ctx: dict, results: list[tuple[str, dict]]) -> str:
    lang = "kn" if ctx.get("language") == "kn" else "en"
    t = T[lang]
    concern = keyword_concern(user_text) or "other"
    turn = ctx.get("turn", 0)
    if turn == 0:
        ack = t["ack_parent"] if ctx.get("speaker") == "parent" else t["ack"]
    else:  # vary the acknowledgement so long sessions do not sound repetitive
        ack = t["acks"][(turn - 1) % len(t["acks"])]

    for name, res in results:
        if name == "escalate":
            return t["escalate_request"] if res.get("trigger") == "user_request" else t["escalate"]

    if not results:
        return ack + t["nodata"]
    name, res = results[0]
    if not res.get("found"):
        if name == "get_providers" and res.get("trade_name"):
            text = ack + " " + t["providers_none"].format(trade=res["trade_name"],
                                                          district=_district_name(ctx.get("district"), lang))
            if res.get("other_districts"):
                text += t["providers_other"].format(other=", ".join(_district_name(d, lang) for d in res["other_districts"]))
            return f"{text} {t['offer']}"
        return ack + " " + t["nodata"]

    text, question = "", ""
    if name == "get_trade_outcomes":
        rec = res["records"][0]
        place = ""
        if res.get("geo_level_used") == "district" and rec.get("district"):
            place = t["in_place"].format(district=_district_name(rec["district"], lang))
        fields = dict(trade=res["trade_name"], place=place, rate=pct(rec.get("placement_rate")),
                      period=rec["reporting_period"], median=inr(rec.get("earnings_median")),
                      lo=inr(rec.get("earnings_min")), hi=inr(rec.get("earnings_max")),
                      n=rec.get("sample_size"), source=(res.get("source") or {}).get("title", ""))
        tpl = t["outcome"] if rec.get("earnings_median") is not None else t["outcome_noearn"]
        text = tpl.format(**fields) + _limits(res, t)
        if concern == "social_status":
            text += t["status_line"]
        question = t["q_outcome"]
    elif name == "get_progression":
        recs = res["records"]
        text = t["ladder"].format(trade=res["trade_name"], first=recs[0]["title"], last=recs[-1]["title"])
        if res.get("can_start_training") is True:
            text += t["can_start"]
        elif res.get("can_start_training") is False:
            text += t["cannot_start"].format(req=res.get("trade_entry_requirement", ""))
        text += t["nsqf"]
        if concern == "degree_first" or (any(r["kind"] == "degree" for r in recs) and "degree" in user_text.lower()):
            text += t["degree_honest"]
        text += t["demo"]
        question = t["q_ladder"]
    elif name == "get_costs_and_support":
        rec = res["records"][0]
        lo, hi = rec.get("fee_min"), rec.get("fee_max")
        if hi is None:
            text = t["costs_none"].format(trade=res["trade_name"])
        elif lo == 0:
            text = t["costs_free"].format(trade=res["trade_name"], hi=inr(hi))
        else:
            text = t["costs_range"].format(trade=res["trade_name"], lo=inr(lo), hi=inr(hi))
        supports = [s["description"] for s in rec.get("supports", [])]
        if supports:
            text += t["support"].format(items=" ".join(supports))
        text += _limits(res, t)
        question = t["q_costs"]
    elif name == "get_providers":
        names = ", ".join(p["name"] for p in res["records"])
        base = t["providers"].format(district=_district_name(ctx.get("district"), lang),
                                     trade=res["trade_name"], names=names)
        if concern == "safety":
            text = t["safety"] + " " + base
            question = t["q_safety"]
        else:
            text = base
            question = t["q_providers"]
        text += t["demo"]
    elif name == "list_trades":
        text = t["options"].format(names=", ".join(r["name"] for r in res["records"]))
        question = t["q_options"]

    # Acknowledge differing alignment priorities when this concern touches one of them.
    al = ctx.get("alignment") or {}
    value = ALIGN_FOR_CONCERN.get(concern)
    if al.get("complete") and value and al.get("biggest_difference") == value:
        text += t["disagree"].format(value=ALIGN_LABEL[lang][value])

    return f"{ack} {text.strip()}{t['card'] if name != 'list_trades' else ''}{question}"
