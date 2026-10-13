"""The learner's own goal and the parent's hope for the child (Update 3): save, describe, compare.

The words are always stored exactly as given. Matched trades come only from the database (match_aspiration or the
family's own pick from Browse / "Not sure yet"); a goal with no match is still saved, and logged as an evidence gap.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import lang_text as _lt
from . import models as m
from .aspiration import normalise
from .data_tools import DataTools
from .i18n import norm_lang, tr

WHO_PREFIX = {"learner": "aspiration_", "parent": "parent_hope_"}
TRAITS = ("hands", "people", "machines", "outdoors", "computers")


def _set(s: m.SessionRow, who: str, field: str, value) -> None:
    if field in ("matched_trade_slugs", "match_confidence") and who == "learner":
        setattr(s, field, value)
    else:
        setattr(s, f"{WHO_PREFIX[who]}{field}", value)


def _get(s: m.SessionRow, who: str, field: str):
    if field in ("matched_trade_slugs", "match_confidence") and who == "learner":
        return getattr(s, field)
    return getattr(s, f"{WHO_PREFIX[who]}{field}")


def save_goal(db: Session, s: m.SessionRow, who: str, text: str | None, language: str, source: str,
              selected_slugs: list[str], confirmed: bool) -> dict:
    """Store one person's goal. Raises ValueError for trade slugs that are not in the database."""
    lang = norm_lang(language)
    known = set(db.scalars(select(m.Trade.slug)))
    bad = [x for x in selected_slugs if x not in known]
    if bad:
        raise ValueError(f"unknown trades {bad}")
    selected = list(dict.fromkeys(selected_slugs))[:3]
    text = (text or "").strip()[:300] or None
    tools = DataTools(db, session_id=s.id, language=lang)
    confidence: float | None = 1.0 if selected else None
    if source in ("voice", "text") and text:
        r = tools.match_aspiration(text, lang, district=s.district)  # logs a gap itself when nothing matches
        category = r["category"]
        if selected:
            category = "vocational_match"
            scores = {c["slug"]: c["score"] for c in r["candidates"]}
            confidence = max((scores.get(x, 0.0) for x in selected), default=0.0) or r["confidence"]
        elif r["matched"]:
            # "None of these": the closest trades were not what they meant — respect that, and note the gap.
            category = "unknown"
            confidence = None
            tools._gap("match_aspiration", None, s.district,
                       {"aspiration_text": text, "language": lang, "category": "rejected_matches"})
    else:
        category = "vocational_match" if selected else "unknown"
    for field, value in (("text", text), ("language", lang), ("source", source), ("matched_trade_slugs", selected),
                         ("match_confidence", confidence), ("category", category), ("confirmed", confirmed)):
        _set(s, who, field, value)
    db.add(m.Event(session_id=s.id, event_type="aspiration_saved",
                   payload={"who": who, "source": source, "category": category, "matched": len(selected)}))
    return goal_view(db, s, who, lang)


def goal_view(db: Session, s: m.SessionRow, who: str, lang: str) -> dict | None:
    text = _get(s, who, "text")
    slugs = _get(s, who, "matched_trade_slugs") or []
    if not text and not slugs:
        return None
    rows = {t.slug: t for t in db.scalars(select(m.Trade).where(m.Trade.slug.in_(slugs)))} if slugs else {}
    trades = [{"slug": x, "name": tr(rows[x].names, lang, f"trade.{x}.names")} for x in slugs if x in rows]
    return {
        "who": who, "text": text, "language": _get(s, who, "language"), "source": _get(s, who, "source"),
        "category": _get(s, who, "category"), "confirmed": bool(_get(s, who, "confirmed")),
        "confidence": _get(s, who, "match_confidence"), "trades": trades,
        # What to show: the chosen trade's name when there is one, otherwise the family's own words.
        "label": trades[0]["name"] if trades else text,
    }


def goals_differ(learner: dict | None, parent: dict | None) -> bool:
    if not learner or not parent:
        return False
    ls, ps = {t["slug"] for t in learner["trades"]}, {t["slug"] for t in parent["trades"]}
    if ls and ps:
        return ls.isdisjoint(ps)
    if ls or ps:
        return True
    return normalise(learner["text"] or "") != normalise(parent["text"] or "")


def compare_goals(db: Session, s: m.SessionRow, language: str | None = None) -> dict:
    lang = norm_lang(language or s.language)
    learner, parent = goal_view(db, s, "learner", lang), goal_view(db, s, "parent", lang)
    return {"learner": learner, "parent": parent, "differ": goals_differ(learner, parent)}


def suggest_trades(db: Session, likes: list[str], near_home: bool | None, district: str | None,
                   language: str) -> list[dict]:
    """'Not sure yet': up to 3 database trades whose work styles fit the answers, each with a short reason."""
    lang = norm_lang(language)
    likes = [x for x in TRAITS if x in likes]
    if not likes:
        return []
    scored = []
    for t in db.scalars(select(m.Trade).order_by(m.Trade.slug)):
        hits = [x for x in (t.traits or []) if x in likes]
        if hits:
            scored.append((len(hits), (t.traits or [])[0] in likes, t, hits[0]))
    scored.sort(key=lambda x: (-x[0], not x[1], x[2].slug))
    if near_home and district:
        offered = {slug for p in db.scalars(select(m.Provider).where(m.Provider.district == district))
                   for slug in (p.trades or [])}
        local = [x for x in scored if x[2].slug in offered]
        scored = local or scored  # never leave the family with nothing
    reasons = _lt.QUIZ_REASON.get(lang, _lt.QUIZ_REASON["en"])
    return [{"slug": t.slug, "name": tr(t.names, lang, f"trade.{t.slug}.names"), "sector": t.sector,
             "icon": t.icon, "reason": reasons[trait]} for _, _, t, trait in scored[:3]]
