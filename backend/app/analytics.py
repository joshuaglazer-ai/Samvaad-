"""Dashboard aggregations. Every number comes from logged data, with counts and denominators.

Small-cell rule: any group based on fewer than MIN_CELL (5) sessions is suppressed
(`suppressed: true`, values null) — to avoid over-reading tiny samples and to protect privacy.
Model-estimated sentiment (messages.sentiment, -2..2) and self-reported mood (sessions.mood_*, 1..5)
are always reported separately.

All parent data is SELF-IDENTIFIED (someone tapped "Parent" or joined as the parent). Sessions where the parent
joined on their own phone (participation_mode = two_devices) are the strongest signal; the dashboard can filter
by participation mode and labels parent metrics accordingly.
"""
from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .aspiration import normalise
from .config import ALIGNMENT_VALUES, CONCERN_CATEGORIES, DISTRICT_COORDS, DISTRICTS, get_settings


def min_cell() -> int:
    return get_settings().min_cell_size


class Filters:
    def __init__(self, district: str | None = None, income_bracket: str | None = None, period: str | None = None,
                 include_simulated: bool = True, participation_mode: str | None = None):
        self.participation_mode = participation_mode or None
        self.district = district or None
        self.income_bracket = income_bracket or None
        self.period = period or "all"
        self.include_simulated = include_simulated

    def since(self) -> datetime | None:
        days = {"7d": 7, "30d": 30, "90d": 90}.get(self.period)
        return datetime.now(timezone.utc) - timedelta(days=days) if days else None


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def sessions(db: Session, f: Filters) -> list[m.SessionRow]:
    q = select(m.SessionRow)
    if f.district:
        q = q.where(m.SessionRow.district == f.district)
    if f.income_bracket:
        q = q.where(m.SessionRow.income_bracket == f.income_bracket)
    if not f.include_simulated:
        q = q.where(m.SessionRow.simulated.is_(False))
    if f.participation_mode:
        q = q.where(m.SessionRow.participation_mode == f.participation_mode)
    rows = list(db.scalars(q))
    since = f.since()
    return [s for s in rows if not since or _aware(s.created_at) >= since]


def _messages(db: Session, ids: set[str], role: str = "user") -> list[m.Message]:
    if not ids:
        return []
    out: list[m.Message] = []
    idl = list(ids)
    for i in range(0, len(idl), 500):  # keep IN() lists small
        out += db.scalars(select(m.Message).where(m.Message.session_id.in_(idl[i:i + 500]), m.Message.role == role,
                                                  m.Message.live.is_(False)).order_by(m.Message.id))
    return out


def _by_session(db: Session, model, ids: set[str]) -> list:
    idl = list(ids)
    out: list = []
    for i in range(0, len(idl), 500):
        out += db.scalars(select(model).where(model.session_id.in_(idl[i:i + 500])))
    return out


def suppress(cell: dict, n_sessions: int) -> dict:
    if n_sessions < min_cell():
        return {**{k: None for k in cell}, "sessions": n_sessions, "suppressed": True}
    return {**cell, "sessions": n_sessions, "suppressed": False}


def data_flags(db: Session, ss: list[m.SessionRow]) -> dict:
    demo = db.scalar(select(m.Outcome.id).where(m.Outcome.data_status == "demo").limit(1)) is not None
    return {"includes_demo_data": demo, "includes_simulated_sessions": any(s.simulated for s in ss),
            "simulated_sessions": sum(1 for s in ss if s.simulated), "min_cell_size": min_cell(),
            "parent_data_note": "Self-identified parent responses"}


# ---------------------------------------------------------------------------------------------- endpoints
def overview(db: Session, f: Filters) -> dict:
    ss = sessions(db, f)
    ids = {s.id for s in ss}
    cases = _by_session(db, m.Escalation, ids)
    open_cases = sum(1 for c in cases if c.status != "resolved")
    shifts_p = [s.mood_post_parent - s.mood_pre_parent for s in ss if s.mood_pre_parent and s.mood_post_parent]
    shifts_l = [s.mood_post_learner - s.mood_pre_learner for s in ss if s.mood_pre_learner and s.mood_post_learner]
    calls = [c for msg in _messages(db, ids, "assistant") for c in (msg.tool_calls or []) if c.get("name") != "escalate"]
    found = sum(1 for c in calls if c.get("found"))
    statuses = Counter(msg.guardrail_status for msg in _messages(db, ids, "assistant"))
    return {
        "sessions": len(ss),
        "open_cases": open_cases, "cases": len(cases),
        "escalation_rate": {"numerator": sum(1 for s in ss if s.escalated), "denominator": len(ss)},
        "mood_shift_parent": {"mean": round(sum(shifts_p) / len(shifts_p), 2) if len(shifts_p) >= min_cell() else None,
                              "n": len(shifts_p)},
        "mood_shift_learner": {"mean": round(sum(shifts_l) / len(shifts_l), 2) if len(shifts_l) >= min_cell() else None,
                               "n": len(shifts_l)},
        "evidence_coverage": {"numerator": found, "denominator": len(calls)},
        "guardrail": dict(statuses),
        "participation_modes": {mode: sum(1 for s in ss if s.participation_mode == mode)
                                for mode in ("together", "two_devices", "learner_only")},
        **data_flags(db, ss),
    }


def concerns(db: Session, f: Filters) -> dict:
    """Concern categories of user messages, by district and by income bracket."""
    ss = sessions(db, f)
    by_id = {s.id: s for s in ss}
    msgs = [x for x in _messages(db, set(by_id)) if x.concern_category]

    def group(key) -> list[dict]:
        out = []
        groups: dict[str, list[m.Message]] = defaultdict(list)
        for x in msgs:
            groups[key(by_id[x.session_id]) or "unknown"].append(x)
        for g, items in sorted(groups.items()):
            n_sess = len({x.session_id for x in items})
            counts = Counter(x.concern_category for x in items)
            cell = {"group": g, "total_messages": len(items), "counts": {c: counts.get(c, 0) for c in CONCERN_CATEGORIES}}
            sup = suppress({"total_messages": cell["total_messages"], "counts": cell["counts"]}, n_sess)
            out.append({"group": g, **sup})
        return out

    return {"by_district": group(lambda s: s.district),
            "by_income_bracket": group(lambda s: s.income_bracket or "not_given"),
            "categories": CONCERN_CATEGORIES, **data_flags(db, ss)}


def resistance_by_district(db: Session, f: Filters) -> dict:
    """Share of parent messages with model-estimated sentiment ≤ -1, per district."""
    ss = sessions(db, f)
    by_id = {s.id: s for s in ss}
    parent = [x for x in _messages(db, set(by_id)) if x.speaker == "parent" and x.sentiment is not None]
    rows = []
    for d in DISTRICTS:
        items = [x for x in parent if by_id[x.session_id].district == d]
        n_sess = len({s.id for s in ss if s.district == d})
        neg = sum(1 for x in items if x.sentiment <= -1)
        top = Counter(x.concern_category for x in items if x.sentiment <= -1 and x.concern_category).most_common(3)
        cell = {"negative_parent_messages": neg, "parent_messages": len(items),
                "share": round(neg / len(items), 3) if items else None, "top_negative_concerns": [c for c, _ in top]}
        rows.append({"district": d, "lat": DISTRICT_COORDS[d][0], "lng": DISTRICT_COORDS[d][1], **suppress(cell, n_sess)})
    return {"districts": rows, "measure": "model-estimated sentiment ≤ -1 on self-identified parent messages",
            **data_flags(db, ss)}


def sentiment_shift(db: Session, f: Filters) -> dict:
    """Two separate series (never on one axis): model sentiment by parent turn, and self-reported mood pre/post."""
    ss = sessions(db, f)
    ids = {s.id for s in ss}
    turns: dict[int, list[int]] = defaultdict(list)
    sess_by_turn: dict[int, set] = defaultdict(set)
    counters: dict[str, int] = defaultdict(int)
    for x in _messages(db, ids):
        if x.speaker != "parent" or x.sentiment is None:
            continue
        counters[x.session_id] += 1
        k = min(counters[x.session_id], 5)  # 5 = "5th or later"
        turns[k].append(x.sentiment)
        sess_by_turn[k].add(x.session_id)
    model = [{"turn": k, **suppress({"mean_sentiment": round(sum(v) / len(v), 2), "messages": len(v)},
                                     len(sess_by_turn[k]))} for k, v in sorted(turns.items())]

    def mood(attr_pre: str, attr_post: str) -> dict:
        pairs = [(getattr(s, attr_pre), getattr(s, attr_post)) for s in ss if getattr(s, attr_pre) and getattr(s, attr_post)]
        cell = {"pre_mean": round(sum(p for p, _ in pairs) / len(pairs), 2) if pairs else None,
                "post_mean": round(sum(q for _, q in pairs) / len(pairs), 2) if pairs else None,
                "improved": sum(1 for p, q in pairs if q > p), "same": sum(1 for p, q in pairs if q == p),
                "worse": sum(1 for p, q in pairs if q < p)}
        return suppress(cell, len(pairs))

    return {"model_sentiment_by_parent_turn": model,
            "self_reported_mood": {"parent": mood("mood_pre_parent", "mood_post_parent"),
                                   "learner": mood("mood_pre_learner", "mood_post_learner")},
            "labels": {"model": "Model-estimated sentiment (−2 to +2), parent messages",
                       "mood": "Self-reported mood (1 to 5), before vs after"},
            **data_flags(db, ss)}


def funnel(db: Session, f: Filters) -> dict:
    ss = sessions(db, f)
    ids = {s.id for s in ss}
    events = _by_session(db, m.Event, ids)
    with_event = lambda t: {e.session_id for e in events if e.event_type == t}  # noqa: E731
    steps = [
        ("started", len(ss)),
        ("alignment_completed", len(with_event("alignment_completed"))),
        ("outcome_viewed", len(with_event("outcome_viewed"))),
        ("mood_post", sum(1 for s in ss if s.mood_post_parent or s.mood_post_learner)),
        ("escalated", sum(1 for s in ss if s.escalated)),
    ]
    total = len(ss) or 1
    return {"steps": [{"step": k, "sessions": v, "denominator": len(ss), "share": round(v / total, 3)} for k, v in steps],
            **data_flags(db, ss)}


def alignment_gaps(db: Session, f: Filters) -> dict:
    """Most common learner–parent priority differences, by district."""
    ss = sessions(db, f)
    by_id = {s.id: s for s in ss}
    events = [e for e in _by_session(db, m.Event, set(by_id)) if e.event_type == "alignment_completed"]
    rows = []
    for d in DISTRICTS:
        evs = [e for e in events if by_id[e.session_id].district == d]
        counts = Counter((e.payload or {}).get("biggest_difference") for e in evs)
        cell = {"completed": len(evs), "no_big_difference": counts.get(None, 0),
                "counts": {v: counts.get(v, 0) for v in ALIGNMENT_VALUES}}
        rows.append({"district": d, **suppress(cell, len(evs))})
    return {"districts": rows, "values": ALIGNMENT_VALUES, **data_flags(db, ss)}


def evidence_gaps(db: Session, f: Filters) -> dict:
    """Ranked unanswered data requests (trade × district × concern). Groups with fewer than MIN_CELL
    distinct sessions are folded into one 'other' row so no small group is shown."""
    ss = sessions(db, f)
    ids = {s.id for s in ss}
    gaps = _by_session(db, m.EvidenceGap, ids)
    groups: dict[tuple, list[m.EvidenceGap]] = defaultdict(list)
    for g in gaps:
        # Goals with no database trade (Update 3) are grouped by the family's own words, so the radar shows which
        # trades or careers to add data for.
        trade = g.trade_slug or (f"goal: {normalise(g.query.get('aspiration_text', ''))}"
                                 if g.tool_name == "match_aspiration" and g.query.get("aspiration_text") else "unknown")
        groups[(trade, g.district or "—", g.concern_category or "other")].append(g)
    rows, other_req, other_groups = [], 0, 0
    for (trade, district, concern), items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        n_sess = len({g.session_id for g in items})
        if n_sess < min_cell():
            other_req += len(items)
            other_groups += 1
            continue
        tools = Counter(g.tool_name for g in items)
        rows.append({"trade_slug": trade, "district": district, "concern": concern, "requests": len(items),
                     "sessions": n_sess, "tools": dict(tools)})
    return {"gaps": rows, "other": {"requests": other_req, "groups": other_groups},
            "total_requests": len(gaps), **data_flags(db, ss)}


def data_quality(db: Session) -> dict:
    def by_status(model) -> dict:
        return dict(Counter(db.scalars(select(model.data_status))))
    this_year = datetime.now(timezone.utc).year
    outcomes = list(db.scalars(select(m.Outcome)))
    stale = [o for o in outcomes if o.year < this_year - 2]
    unverified_old = [o for o in outcomes if o.data_status == "verified" and o.verified_on and
                      o.verified_on < (datetime.now(timezone.utc) - timedelta(days=548)).date().isoformat()]
    trades = list(db.scalars(select(m.Trade)))
    return {
        "outcomes_by_status": by_status(m.Outcome), "providers_by_status": by_status(m.Provider),
        "costs_by_status": by_status(m.CostSupport), "outcomes_total": len(outcomes),
        "stale_outcomes": {"count": len(stale), "rule": f"year earlier than {this_year - 2}"},
        "verification_overdue": {"count": len(unverified_old), "rule": "verified more than 18 months ago"},
        "trades_missing_qualification_code": sum(1 for t in trades if not t.qualification_code),
        "trades_total": len(trades),
        "includes_demo_data": any(o.data_status == "demo" for o in outcomes),
    }


def export_csv(db: Session, f: Filters) -> str:
    """District-level aggregates only (no session-level rows), with small cells suppressed."""
    res = {r["district"]: r for r in resistance_by_district(db, f)["districts"]}
    gaps = {r["district"]: r for r in alignment_gaps(db, f)["districts"]}
    ss = sessions(db, f)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["district", "sessions", "simulated_sessions", "escalated_sessions", "parent_messages",
                "negative_parent_messages", "negative_share", "top_negative_concerns", "alignment_completed",
                "most_common_alignment_difference", "parent_mood_pre_mean", "parent_mood_post_mean", "note"])
    for d in DISTRICTS:
        ds = [s for s in ss if s.district == d]
        r, g = res[d], gaps[d]
        if len(ds) < min_cell():
            w.writerow([d, len(ds), "", "", "", "", "", "", "", "", "", "", "too few sessions"])
            continue
        pairs = [(s.mood_pre_parent, s.mood_post_parent) for s in ds if s.mood_pre_parent and s.mood_post_parent]
        top_gap = "" if g["suppressed"] else max(g["counts"], key=lambda v: g["counts"][v]) if any(g["counts"].values()) else ""
        w.writerow([d, len(ds), sum(1 for s in ds if s.simulated), sum(1 for s in ds if s.escalated),
                    r["parent_messages"], r["negative_parent_messages"], r["share"],
                    "|".join(r["top_negative_concerns"] or []), g["completed"], top_gap,
                    round(sum(p for p, _ in pairs) / len(pairs), 2) if len(pairs) >= min_cell() else "",
                    round(sum(q for _, q in pairs) / len(pairs), 2) if len(pairs) >= min_cell() else "",
                    "includes simulated sessions" if any(s.simulated for s in ds) else ""])
    return buf.getvalue()


# ---------------------------------------------------------------------------------------------- goals (Update 3)
NO_MATCH = ("degree_career", "professional_course", "unknown")


def _goal(s: m.SessionRow, who: str) -> dict | None:
    if who == "learner":
        text, slugs, cat = s.aspiration_text, s.matched_trade_slugs or [], s.aspiration_category
    else:
        text, slugs, cat = s.parent_hope_text, s.parent_hope_matched_trade_slugs or [], s.parent_hope_category
    if not text and not slugs:
        return None
    return {"text": text, "slugs": slugs, "category": cat}


def _trade_names(db: Session) -> dict[str, str]:
    return {t.slug: (t.names or {}).get("en", t.slug) for t in db.scalars(select(m.Trade))}


def top_aspirations(db: Session, f: Filters) -> dict:
    """Learners' goals by district, grouped by the matched trade, in their own words. A group needs MIN_CELL
    sessions to be shown, and an exact phrase needs MIN_CELL sessions to be quoted (free text can identify people)."""
    names = _trade_names(db)
    by_district: dict[str, dict[str, list[m.SessionRow]]] = defaultdict(lambda: defaultdict(list))
    for s in sessions(db, f):
        g = _goal(s, "learner")
        if g:
            by_district[s.district][g["slugs"][0] if g["slugs"] else "no_match"].append(s)
    out = []
    for district in [d for d in DISTRICTS if d in by_district]:
        groups, other = [], 0
        for key, ss in sorted(by_district[district].items(), key=lambda kv: -len(kv[1])):
            if len(ss) < min_cell():
                other += len(ss)
                continue
            phrases = Counter(normalise(x.aspiration_text) for x in ss if x.aspiration_text)
            words = [{"text": t, "sessions": n} for t, n in phrases.most_common() if n >= min_cell()][:5]
            groups.append({"trade_slug": None if key == "no_match" else key,
                           "trade_name": None if key == "no_match" else names.get(key, key),
                           "sessions": len(ss), "words": words,
                           "other_words_sessions": len(ss) - sum(w["sessions"] for w in words)})
        out.append({"district": district, "sessions": sum(len(v) for v in by_district[district].values()),
                    "groups": groups, "other_sessions": other})
    return {"districts": out, **data_flags(db, sessions(db, f))}


def unmatched_aspirations(db: Session, f: Filters) -> dict:
    """Goals (learner) and hopes (parent) the database has no trade for — what to add data for next."""
    rows: dict[str, dict] = {}
    for s in sessions(db, f):
        for who in ("learner", "parent"):
            g = _goal(s, who)
            if not g or g["slugs"] or not g["text"] or g["category"] not in NO_MATCH:
                continue
            key = normalise(g["text"])
            r = rows.setdefault(key, {"text": key, "category": g["category"], "session_ids": set(),
                                      "learner": 0, "parent": 0, "districts": Counter()})
            r["session_ids"].add(s.id)
            r[who] += 1
            r["districts"][s.district] += 1
    shown, other_phrases, other_ids = [], 0, set()
    for r in sorted(rows.values(), key=lambda r: -len(r["session_ids"])):
        n = len(r["session_ids"])
        if n < min_cell():
            other_phrases += 1
            other_ids |= r["session_ids"]  # distinct families, even if learner and parent both land here
            continue
        # Split counts are small cells too: anything from 1 to MIN_CELL-1 is shown as null ("fewer than 5").
        small = lambda x: x if x == 0 or x >= min_cell() else None  # noqa: E731
        shown.append({"text": r["text"], "category": r["category"], "sessions": n, "learner": small(r["learner"]),
                      "parent": small(r["parent"]), "districts": {d: small(c) for d, c in r["districts"].items()}})
    return {"goals": shown, "other": {"phrases": other_phrases, "sessions": len(other_ids)},
            **data_flags(db, sessions(db, f))}


def _differ(a: dict, b: dict) -> bool:
    if a["slugs"] and b["slugs"]:
        return set(a["slugs"]).isdisjoint(b["slugs"])
    if a["slugs"] or b["slugs"]:
        return True
    return normalise(a["text"] or "") != normalise(b["text"] or "")


def goal_vs_hope(db: Session, f: Filters) -> dict:
    """How often the learner's goal and the parent's (self-identified) hope differ, by district."""
    per: dict[str, list[bool]] = defaultdict(list)
    by_mode: dict[str, list[bool]] = defaultdict(list)
    for s in sessions(db, f):
        a, b = _goal(s, "learner"), _goal(s, "parent")
        if a and b:
            d = _differ(a, b)
            per[s.district].append(d)
            by_mode[s.participation_mode].append(d)

    def cell(xs: list[bool]) -> dict:
        return suppress({"differ": sum(xs), "differ_rate": round(100 * sum(xs) / len(xs)) if xs else None}, len(xs))
    rows = [{"district": d, **cell(per[d])} for d in DISTRICTS if d in per]
    total = [x for xs in per.values() for x in xs]
    return {"districts": rows, "overall": cell(total),
            "by_mode": {mode: cell(xs) for mode, xs in by_mode.items()}, **data_flags(db, sessions(db, f))}
