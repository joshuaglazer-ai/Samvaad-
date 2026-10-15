"""Numeric guardrail (Rule 2): every number in a reply must come from this turn's tool outputs.

How a claim is checked
  1. Numbers are extracted from the reply: Western and Kannada digits, ₹/Rs amounts, %, "k",
     "thousand"/"ಸಾವಿರ", "lakh"/"ಲಕ್ಷ", "crore"/"ಕೋಟಿ". In a range like "12–18 thousand", the unit
     applies to both ends.
  2. Allowed values are every number found anywhere in the tool outputs (numeric fields and numbers
     inside strings, e.g. "FY 2024-25" → 2024 and 25; "Passed Class 12" → 12).
  3. A claim matches if an allowed value equals it after formatting: 12000 = "12,000" = "₹12k" =
     "12 thousand"; 118000 ≈ "1.2 lakh" (rounded to the precision the reply uses).

Documented exceptions (not treated as statistics)
  * Plain integers ≤ 10 with no unit (₹, %, k, lakh …) — step numbers, counts ("3 options"),
    ordinals ("2nd"), NSQF levels.
  * School classes 8, 10 and 12 when written as a class ("Class 12", "12th", "12ನೇ", "SSLC/PUC" context),
    because families describe education this way.
  Derived figures (e.g. monthly × 12) are NOT allowed — the reply must quote the tool's own figure.

Spoken rounding rule (Update 2, decision D25)
  Replies may round amounts for easy listening ONLY when the number is introduced by an approximation word
  ("about", "around", "nearly", "roughly", "ಸುಮಾರು", "लगभग", "करीब", "సుమారు", "దాదాపు" …). Such a claim matches a
  tool value v ≥ 1,000 if it equals v rounded (half up) to the nearest 500 or the nearest 1,000.
  Example: tool 14,250 → "about ₹14,000" or "about ₹14,500" pass; "₹14,000" without "about" fails;
  "about ₹15,000" fails. Percentages may be rounded to a whole number. Exact figures always stay on the card.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Kannada, Devanagari (Hindi) and Telugu digits → Western digits.
KANNADA_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯०१२३४५६७८९౦౧౨౩౪౫౬౭౮౯", "0123456789" * 3)
SMALL_INT_MAX = 10
SCHOOL_CLASSES = {8, 10, 12}

UNIT_MULT = {
    "k": 1_000, "thousand": 1_000, "ಸಾವಿರ": 1_000,
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000, "ಲಕ್ಷ": 100_000,
    "crore": 10_000_000, "crores": 10_000_000, "ಕೋಟಿ": 10_000_000,
    # Hindi
    "हज़ार": 1_000, "हजार": 1_000, "लाख": 100_000, "करोड़": 10_000_000,
    # Telugu
    "వేలు": 1_000, "వేల": 1_000, "హజార్": 1_000, "లక్షలు": 100_000, "లక్ష": 100_000, "కోట్లు": 10_000_000, "కోటి": 10_000_000,
}
PCT_UNITS = {"%", "percent", "per cent", "ಶೇಕಡಾ", "ಶೇ", "प्रतिशत", "फ़ीसदी", "फीसदी", "శాతం"}

NUM = r"\d[\d,]*(?:\.\d+)?"
UNIT = (r"%|per\s?cent|k(?![a-z])|thousand|ಸಾವಿರ|lakhs?|lacs?|ಲಕ್ಷ|crores?|ಕೋಟಿ"
        r"|प्रतिशत|फ़ीसदी|फीसदी|हज़ार|हजार|लाख|करोड़|శాతం|వేలు|వేల|హజార్|లక్షలు|లక్ష|కోట్లు|కోటి")
CLAIM_RE = re.compile(
    rf"(?P<pct_pre>ಶೇಕಡಾ|ಶೇ\.?)?\s*(?P<cur>₹|rs\.?|inr)?\s*(?P<num>{NUM})"
    rf"(?:\s*(?P<dash>-|–|—|to|ರಿಂದ|से|నుండి)\s*(?:₹|rs\.?)?\s*(?P<num2>{NUM}))?"
    rf"\s*(?P<unit>{UNIT})?",
    re.IGNORECASE,
)
CLASS_CONTEXT_RE = re.compile(r"(class|std\.?|standard|grade|ತರಗತಿ|कक्षा|क्लास|తరగతి)\s*$", re.IGNORECASE)
CLASS_SUFFIX_RE = re.compile(r"^\s*(th|st|nd|rd|ನೇ|ನೆಯ|वीं|वी|వ)", re.IGNORECASE)
PLAIN_NUM_RE = re.compile(NUM)
APPROX_RE = re.compile(
    r"(about|around|approx\.?|approximately|roughly|nearly|close to|almost|"
    r"ಸುಮಾರು|ಅಂದಾಜು|ಹೆಚ್ಚು ಕಡಿಮೆ|लगभग|करीब|क़रीब|तकरीबन|क़रीबन|సుమారు|సుమారుగా|దాదాపు)\s*(of\s*)?(₹|rs\.?|inr|ಶೇ\.?|ಶೇಕಡಾ)?\s*$",
    re.IGNORECASE,
)
ROUNDING_STEPS = (500, 1000)
ROUNDING_MIN = 1000


@dataclass
class Claim:
    raw: str
    value: float          # value in base units (rupees, percent points, plain count)
    shown: float          # the number as written (before the unit multiplier)
    decimals: int         # decimals as written
    mult: int             # unit multiplier (1 if none)
    is_percent: bool
    has_unit: bool        # ₹ / % / k / lakh / thousand …
    approx: bool = False  # introduced by "about"/"ಸುಮಾರು"/… → spoken rounding rule applies
    exempt: str | None = None


@dataclass
class GuardrailResult:
    passed: bool
    claims: list[Claim] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)


def _to_float(s: str) -> tuple[float, int]:
    s = s.replace(",", "")
    decimals = len(s.split(".")[1]) if "." in s else 0
    return float(s), decimals


def _normalise_unit(u: str | None) -> str | None:
    if not u:
        return None
    u = u.lower().replace(" ", "")
    return "%" if u in {"percent", "percent.", "प्रतिशत", "फ़ीसदी", "फीसदी", "శాతం"} else u


def extract_claims(text: str) -> list[Claim]:
    text = text.translate(KANNADA_DIGITS)
    claims: list[Claim] = []
    for mt in CLAIM_RE.finditer(text):
        unit = _normalise_unit(mt.group("unit"))
        pct = bool(mt.group("pct_pre")) or unit == "%"
        mult = UNIT_MULT.get(unit or "", 1)
        has_unit = bool(mt.group("cur")) or pct or mult != 1
        nums = [mt.group("num")] + ([mt.group("num2")] if mt.group("num2") else [])
        for idx, n in enumerate(nums):
            shown, dec = _to_float(n)
            claim = Claim(raw=mt.group(0).strip(), value=shown * mult, shown=shown, decimals=dec,
                          mult=mult, is_percent=pct, has_unit=has_unit,
                          approx=bool(APPROX_RE.search(text[max(0, mt.start() - 30):mt.start() + (mt.start("num") - mt.start())])))
            # exemptions
            before = text[: mt.start("num") if idx == 0 else mt.start("num2")]
            after = text[(mt.end("num") if idx == 0 else mt.end("num2")):]
            if not has_unit and shown.is_integer():
                if shown <= SMALL_INT_MAX:
                    claim.exempt = "small_integer"
                elif int(shown) in SCHOOL_CLASSES and (CLASS_CONTEXT_RE.search(before[-12:]) or CLASS_SUFFIX_RE.match(after)):
                    claim.exempt = "school_class"
            claims.append(claim)
    return claims


def allowed_values(tool_outputs: list[Any]) -> set[float]:
    vals: set[float] = set()

    def walk(x: Any) -> None:
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            vals.add(float(x))
        elif isinstance(x, str):
            for n in PLAIN_NUM_RE.findall(x.translate(KANNADA_DIGITS)):
                try:
                    vals.add(_to_float(n)[0])
                except ValueError:
                    pass
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)

    walk(tool_outputs)
    return vals


def _round_half_up(v: float, step: int) -> float:
    return ((v + step / 2) // step) * step


def _matches(claim: Claim, allowed: set[float]) -> bool:
    tol = 0.5 * 10 ** (-claim.decimals) + 1e-9
    for v in allowed:
        if claim.approx and v >= ROUNDING_MIN and not claim.is_percent and                 any(_round_half_up(v, step) == claim.value for step in ROUNDING_STEPS):
            return True
        if claim.value == v:
            return True
        # Same number at the precision the reply used: 118000 → "1.2 lakh", 73.6 → "74%".
        if abs(v / claim.mult - claim.shown) <= tol and (claim.mult != 1 or claim.decimals > 0 or claim.is_percent):
            return True
    return False


def check(reply: str, tool_outputs: list[Any]) -> GuardrailResult:
    claims = extract_claims(reply)
    allowed = allowed_values(tool_outputs)
    unmatched = [c.raw for c in claims if not c.exempt and not _matches(c, allowed)]
    return GuardrailResult(passed=not unmatched, claims=claims, unmatched=unmatched)


# ------------------------------------------------------------------------------------------ claim check
# Beyond numbers (Update 4): words that make a factual promise about a centre or course. A reply may use one only when
# this turn's tool results support it — the same word (in any language) appears in the tool data, or a field says so
# (e.g. a fee of 0 supports "free"; a non-empty `accreditation` supports "accredited"). A flag is treated exactly like
# an unsupported number: regenerate once, then the safe fallback message.
CLAIM_TERMS: dict[str, str] = {
    "government": r"\bgovernment\b|\bgovt\b|\bsarkari\b|ಸರ್ಕಾರ|सरकार|ప్రభుత్వ",
    "free": r"\bfree\b(?!\s+to\b)|\bmuft\b|ಉಚಿತ|मुफ़्त|मुफ्त|फ़्री|फ्री|ఉచిత",
    "guaranteed": r"guarantee|ಖಾತರಿ|ಗ್ಯಾರಂಟಿ|गारंटी|गारण्टी|గ్యారంటీ|హామీ",
    "certified": r"\bcertified\b|ಪ್ರಮಾಣೀಕೃತ|प्रमाणित|సర్టిఫైడ్",
    "accredited": r"\baccredited\b|ಮಾನ್ಯತೆ ಪಡೆದ|मान्यता प्राप्त|గుర్తింపు పొందిన",
}
CLAIM_RE_BY_TERM = {k: re.compile(v, re.IGNORECASE) for k, v in CLAIM_TERMS.items()}


def _walk(value: Any):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk(v)


def claim_check(reply: str, tool_outputs: list[Any]) -> list[str]:
    """Claim words in the reply that this turn's tool results do not support (empty list = fine)."""
    found = [k for k, rx in CLAIM_RE_BY_TERM.items() if rx.search(reply or "")]
    if not found:
        return []
    import json

    text = json.dumps(tool_outputs, ensure_ascii=False, default=str)
    pairs = list(_walk(tool_outputs))
    fields = {
        "free": any(k in ("fee_min", "fee_max") and v == 0 for k, v in pairs),
        "accredited": any(k == "accreditation" and v for k, v in pairs),
        "government": any(k == "provider_type" and str(v).startswith("government") for k, v in pairs),
    }
    return [k for k in found if not (fields.get(k) or CLAIM_RE_BY_TERM[k].search(text))]


CLAIM_NAMES = {"government": "who runs a centre (government)", "free": "free / no fee", "guaranteed": "a guarantee",
               "certified": "certification", "accredited": "accreditation"}
LANGUAGE_NAMES = {"en": "English", "kn": "Kannada", "hi": "Hindi", "te": "Telugu"}


def correction_note(unmatched: list[str], language: str, claims: list[str] | None = None) -> str:
    parts = []
    if unmatched:
        parts.append("Your reply contained numbers that are not in this turn's tool results: "
                     f"{', '.join(dict.fromkeys(unmatched))}. Use only figures exactly as they appear in the tool "
                     "results (you may call a tool again). Do not estimate, convert or calculate new numbers.")
    if claims:
        parts.append("Your reply stated things the tool results do not say: "
                     f"{', '.join(CLAIM_NAMES.get(c, c) for c in claims)}. Only state facts that appear in the tool "
                     "results; do not add who runs a centre, government status, quality, guarantees or eligibility.")
    return ("[Guardrail correction] " + " ".join(parts) + " Rewrite the reply. If the data is not available, say so "
            f"and offer a counsellor. Reply in {LANGUAGE_NAMES.get(language, 'English')}.")


FALLBACK_TEXT = {
    "en": "I want to be careful with numbers, and I couldn't confirm this one. Please see the card below. "
          "A counsellor can help — would you like that?",
    "kn": "ಅಂಕಿಅಂಶಗಳಲ್ಲಿ ನಾನು ಎಚ್ಚರಿಕೆಯಿಂದ ಇರಬೇಕು; ಇದನ್ನು ಖಚಿತಪಡಿಸಲು ಆಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಕೆಳಗಿನ ಕಾರ್ಡ್ ನೋಡಿ. "
          "ಸಲಹೆಗಾರರು ಸಹಾಯ ಮಾಡಬಹುದು — ಬೇಕೇ?",
}

from .lang_text import FALLBACK_TEXT as _FB  # noqa: E402

FALLBACK_TEXT.update(_FB)
