"""Match a learner's own words ("bijli mistri", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಆಗಬೇಕು", "drone pilot") to trades in the database.

Only trades that exist in the database can be returned. Below the confidence threshold the result is
`matched: false` — a match is never forced, and the learner's words are kept exactly as said.

Mock mode (and the fallback in real mode): normalise the text, then fuzzy-match (rapidfuzz) every word window
against trade names and synonyms in all four languages. Real mode: the fast model classifies the text and may only
pick slugs from a candidate list the backend supplies (enforced by the JSON schema enum and checked again here).
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from . import lang_text as _lt
from .i18n import norm_lang, tr

log = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.80   # at or above: a confident match
RELATED_MIN = 0.7        # weaker matches are offered only as "related options", never as the goal
MAX_CANDIDATES = 3
CATEGORIES = ("vocational_match", "degree_career", "unknown")


@dataclass
class TradeTerms:
    slug: str
    names: dict
    sector: str
    terms: list[tuple[str, str]] = field(default_factory=list)  # (language, term)


# ---------------------------------------------------------------- normalising
def normalise(text: str) -> str:
    """Lowercase, NFC, punctuation and symbols → spaces (Indic vowel signs and viramas are kept)."""
    text = unicodedata.normalize("NFC", text or "").lower().replace("‌", "").replace("‍", "")
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        out.append(" " if cat[0] in "PSZC" else ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


_LATIN_RULES = [(r"ph", "f"), (r"sh", "s"), (r"ch", "c"), (r"th", "t"), (r"dh", "d"), (r"bh", "b"), (r"kh", "k"),
                (r"gh", "g"), (r"w", "v"), (r"z", "j"), (r"q", "k"), (r"x", "ks"), (r"ee", "i"), (r"oo", "u"),
                (r"aa", "a"), (r"y\b", "i"), (r"(.)\1+", r"\1")]


def phonetic(text: str) -> str:
    """A loose key for romanised Indian-language typing: "bijlee mistry" ≈ "bijli mistri"."""
    if not re.search(r"[a-z]", text):
        return text
    for pat, rep in _LATIN_RULES:
        text = re.sub(pat, rep, text)
    return text


def _is_indic(s: str) -> bool:
    return any(0x0900 <= ord(c) <= 0x0D7F for c in s)


def _windows(words: list[str], n: int) -> list[str]:
    return [" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))]


def term_score(text_key: str, term: str) -> float:
    """How well `term` appears in the (normalised, phonetic) text: 1.0 = whole-word match, else best fuzzy window."""
    t = phonetic(normalise(term))
    if not t:
        return 0.0
    if re.search(rf"(?<!\S){re.escape(t)}(?!\S)", text_key):
        return 1.0
    words, n = text_key.split(), len(t.split())
    if _is_indic(t):
        # Indian scripts attach endings ("ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ಆಗಬೇಕು"), so a long-enough term inside the text counts.
        if len(t) >= 4 and t in text_key:
            return 0.95
    elif len(t) <= 3:
        return 0.0  # short Latin terms ("ev", "gnm") must match a whole word
    best = 0.0
    for k in (n, n + 1):  # never fewer words than the term: "mechanic" is not "ev mechanic"
        for w in _windows(words, k):
            best = max(best, fuzz.ratio(w, t) / 100)
    return best


# ---------------------------------------------------------------- degree careers
def detect_degree_career(text: str) -> tuple[str, str | None] | None:
    """(career key, related sector slug) if the text names a degree career, else None."""
    norm = normalise(text)
    key = phonetic(norm)
    for career, spec in _lt.DEGREE_CAREERS.items():
        for terms in spec["terms"].values():
            for term in terms:
                t = normalise(term)
                if _is_indic(t):
                    if t in norm:
                        return career, spec["related_sector"]
                elif re.search(rf"(?<!\S){re.escape(phonetic(t))}", key):  # word start: engineer → engineering
                    return career, spec["related_sector"]
    return None


# ---------------------------------------------------------------- matching
def _reason(lang: str, term: str | None) -> str:
    texts = _lt.MATCH_REASON.get(lang, _lt.MATCH_REASON["en"])
    return texts["term"].format(term=term) if term else texts["model"]


def _candidate(t: TradeTerms, score: float, lang: str, term: str | None) -> dict:
    return {"slug": t.slug, "name": tr(t.names, lang, f"trade.{t.slug}.names"), "sector": t.sector,
            "score": round(score, 2), "reason": _reason(lang, term)}


def fuzzy_scores(text: str, trades: list[TradeTerms]) -> list[tuple[float, TradeTerms, str]]:
    key = phonetic(normalise(text))
    scored = []
    for t in trades:
        best, best_term = 0.0, ""
        for _lang, term in t.terms:
            s = term_score(key, term)
            if s > best:
                best, best_term = s, term
        scored.append((best, t, best_term))
    # A more specific exact match wins: in "bike mechanic", the trade matching all of it outranks the one matching
    # only "mechanic" (kept, but below the threshold's top so it is listed second).
    exact = [phonetic(normalise(term)) for s, _, term in scored if s == 1.0]
    out = []
    for s, t, term in scored:
        k = phonetic(normalise(term))
        if s == 1.0 and any(len(o) > len(k) and re.search(rf"(?<!\S){re.escape(k)}(?!\S)", o) for o in exact):
            s = 0.85
        out.append((s, t, term))
    out.sort(key=lambda x: (-x[0], x[1].slug))
    return out


def match_fuzzy(text: str, language: str, trades: list[TradeTerms]) -> dict:
    lang = norm_lang(language)
    base = {"text": text, "language": lang, "normalised": normalise(text), "mode": "fuzzy"}
    scored = fuzzy_scores(text, trades)
    degree = detect_degree_career(text)
    if degree:
        career, related_sector = degree
        related = [_candidate(t, 0, lang, None) | {"reason": ""} for _, t, _ in sorted(scored, key=lambda x: x[1].slug)
                   if related_sector and t.sector == related_sector][:MAX_CANDIDATES]
        return base | {"matched": False, "category": "degree_career", "degree_career": career,
                       "related_sector": related_sector, "confidence": 0.0, "candidates": [], "related": related}
    strong = [(s, t, term) for s, t, term in scored if s >= MATCH_THRESHOLD][:MAX_CANDIDATES]
    if strong:
        return base | {"matched": True, "category": "vocational_match", "confidence": round(strong[0][0], 2),
                       "candidates": [_candidate(t, s, lang, term) for s, t, term in strong], "related": []}
    weak = [(s, t, term) for s, t, term in scored if s >= RELATED_MIN][:MAX_CANDIDATES]
    return base | {"matched": False, "category": "unknown", "confidence": round(scored[0][0], 2) if scored else 0.0,
                   "candidates": [], "related": [_candidate(t, s, lang, None) for s, t, _ in weak]}


# ---------------------------------------------------------------- real mode
CLASSIFY_SYSTEM = (
    "You sort a learner's career goal for an Indian vocational-guidance app. The goal may be in English, Kannada, "
    "Hindi or Telugu, or romanised. Decide its category: vocational_match (it is one of the listed trades or an "
    "everyday name for one), degree_career (a career that normally needs a degree or professional course, e.g. "
    "doctor, engineer, teacher, police officer, lawyer), or unknown (anything else, including jobs not in the list). "
    "Only pick slugs from the list, at most 3, each with a score from 0 to 1 for how surely it is the same job. "
    "Never pick a trade just because it is in the same field; if unsure, use unknown with no matches."
)


def classification_schema(slugs: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": list(CATEGORIES)},
            "matches": {"type": "array", "items": {
                "type": "object",
                "properties": {"slug": {"type": "string", "enum": slugs}, "score": {"type": "number"}},
                "required": ["slug", "score"], "additionalProperties": False}},
        },
        "required": ["category", "matches"], "additionalProperties": False,
    }


def candidate_list(text: str, trades: list[TradeTerms], limit: int = 40) -> list[TradeTerms]:
    """The trades the model may choose from: all of them when few, else the closest by fuzzy score."""
    if len(trades) <= limit:
        return trades
    return [t for _, t, _ in fuzzy_scores(text, trades)[:limit]]


def match_with_model(text: str, language: str, trades: list[TradeTerms], llm) -> dict:
    """Ask the fast model; anything outside the candidate list is rejected. Falls back to fuzzy on any failure."""
    lang = norm_lang(language)
    cands = candidate_list(text, trades)
    by_slug = {t.slug: t for t in cands}
    listing = "\n".join(f"- {t.slug}: {tr(t.names, 'en')} (sector: {t.sector})" for t in cands)
    try:
        raw = llm.structured_json(CLASSIFY_SYSTEM, f"Trades:\n{listing}\n\nLearner's goal: {text}",
                                  classification_schema(list(by_slug)))
        data = json.loads(raw)
    except Exception as exc:  # network, refusal, bad JSON — never block onboarding
        log.warning("aspiration classification failed, using fuzzy match: %s", exc)
        return match_fuzzy(text, lang, trades)
    category = data.get("category") if data.get("category") in CATEGORIES else "unknown"
    picks, rejected = [], []
    for item in data.get("matches") or []:
        slug, score = item.get("slug"), item.get("score")
        if slug not in by_slug:
            rejected.append(slug)
            continue
        if isinstance(score, (int, float)) and min(1.0, float(score)) >= MATCH_THRESHOLD and slug not in [p[1].slug for p in picks]:
            picks.append((min(1.0, float(score)), by_slug[slug]))
    if rejected:
        log.warning("model returned trades outside the candidate list (rejected): %s", rejected)
    base = {"text": text, "language": lang, "normalised": normalise(text), "mode": "model",
            "rejected_slugs": rejected}
    if category == "degree_career":
        fuzzy = match_fuzzy(text, lang, trades)
        return fuzzy | base | {"matched": False, "category": "degree_career", "candidates": [], "confidence": 0.0,
                               "degree_career": fuzzy.get("degree_career"), "related_sector": fuzzy.get("related_sector"),
                               "related": fuzzy.get("related", [])}
    picks.sort(key=lambda p: -p[0])
    picks = picks[:MAX_CANDIDATES]
    if category == "vocational_match" and picks:
        return base | {"matched": True, "category": "vocational_match", "confidence": round(picks[0][0], 2),
                       "candidates": [_candidate(t, s, lang, None) for s, t in picks], "related": []}
    return base | {"matched": False, "category": "unknown", "confidence": round(picks[0][0], 2) if picks else 0.0,
                   "candidates": [], "related": []}
