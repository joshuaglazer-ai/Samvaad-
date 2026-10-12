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

KANNADA_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")
SMALL_INT_MAX = 10
SCHOOL_CLASSES = {8, 10, 12}

UNIT_MULT = {
    "k": 1_000, "thousand": 1_000, "ಸಾವಿರ": 1_000,
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000, "ಲಕ್ಷ": 100_000,
    "crore": 10_000_000, "crores": 10_000_000, "ಕೋಟಿ": 10_000_000,
}
PCT_UNITS = {"%", "percent", "per cent", "ಶೇಕಡಾ", "ಶೇ"}

NUM = r"\d[\d,]*(?:\.\d+)?"
UNIT = r"%|per\s?cent|k(?![a-z])|thousand|ಸಾವಿರ|lakhs?|lacs?|ಲಕ್ಷ|crores?|ಕೋಟಿ"
CLAIM_RE = re.compile(
    rf"(?P<pct_pre>ಶೇಕಡಾ|ಶೇ\.?)?\s*(?P<cur>₹|rs\.?|inr)?\s*(?P<num>{NUM})"
    rf"(?:\s*(?P<dash>-|–|—|to|ರಿಂದ)\s*(?:₹|rs\.?)?\s*(?P<num2>{NUM}))?"
    rf"\s*(?P<unit>{UNIT})?",
    re.IGNORECASE,
)
CLASS_CONTEXT_RE = re.compile(r"(class|std\.?|standard|grade|ತರಗತಿ)\s*$", re.IGNORECASE)
CLASS_SUFFIX_RE = re.compile(r"^\s*(th|st|nd|rd|ನೇ|ನೆಯ)", re.IGNORECASE)
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
    return {"percent": "%", "percent.": "%"}.get(u, u)


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


def correction_note(unmatched: list[str], language: str) -> str:
    listed = ", ".join(dict.fromkeys(unmatched))
    return (
        "[Guardrail correction] Your reply contained numbers that are not in this turn's tool results: "
        f"{listed}. Rewrite the reply. Use only figures exactly as they appear in the tool results "
        "(you may call a tool again). Do not estimate, convert or calculate new numbers. If the data is "
        f"not available, say so and offer a counsellor. Reply in {'Kannada' if language == 'kn' else 'English'}."
    )


FALLBACK_TEXT = {
    "en": "I want to be careful with numbers, and I couldn't confirm this one. Please see the card below. "
          "A counsellor can help — would you like that?",
    "kn": "ಅಂಕಿಅಂಶಗಳಲ್ಲಿ ನಾನು ಎಚ್ಚರಿಕೆಯಿಂದ ಇರಬೇಕು; ಇದನ್ನು ಖಚಿತಪಡಿಸಲು ಆಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಕೆಳಗಿನ ಕಾರ್ಡ್ ನೋಡಿ. "
          "ಸಲಹೆಗಾರರು ಸಹಾಯ ಮಾಡಬಹುದು — ಬೇಕೇ?",
}
