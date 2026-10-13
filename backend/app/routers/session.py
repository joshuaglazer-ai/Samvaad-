import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..alignment import compare, latest_rankings, session_alignment, validate_ranking
from ..db import get_db
from ..schemas import AlignmentIn, JoinIn, MoodIn, SessionCreate, SessionUpdate

router = APIRouter(prefix="/api/session", tags=["session"])
join_router = APIRouter(prefix="/api", tags=["session"])

FAMILY_CODE_TTL = timedelta(hours=2)
JOIN_LIMIT = 10              # failed attempts ...
JOIN_WINDOW_SECONDS = 600    # ... per client per 10 minutes (4-digit codes are short; this blunts guessing)
_failed_joins: dict[str, deque] = defaultdict(deque)


def _new_family_code(db: Session) -> str:
    """4-digit code, unique among codes that have not expired."""
    now = m.utcnow()
    for _ in range(50):
        code = f"{secrets.randbelow(10000):04d}"
        clash = db.scalar(select(m.SessionRow.id).where(m.SessionRow.family_code == code,
                                                        m.SessionRow.family_code_expires_at > now))
        if not clash:
            return code
    raise HTTPException(503, "could not allocate a family code, please try again")


def _aware(dt):
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=m.utcnow().tzinfo)


def get_session_or_404(db: Session, session_id: str) -> m.SessionRow:
    s = db.get(m.SessionRow, session_id)
    if not s:
        raise HTTPException(404, "session not found")
    return s


@router.post("")
def create_session(body: SessionCreate, db: Session = Depends(get_db)) -> dict:
    if not body.consent_given:
        raise HTTPException(400, "consent is required to start a session")
    s = m.SessionRow(**body.model_dump(exclude={"device_id"}))
    if s.participation_mode == "two_devices":
        s.family_code = _new_family_code(db)
        s.family_code_expires_at = m.utcnow() + FAMILY_CODE_TTL
    db.add(s)
    db.flush()
    db.add(m.Event(session_id=s.id, event_type="session_started",
                   payload={"language": s.language, "district": s.district, "helper_mode": s.helper_mode,
                            "participation_mode": s.participation_mode}))
    db.commit()
    return {"session_id": s.id, "family_code": s.family_code,
            "family_code_expires_at": s.family_code_expires_at.isoformat() if s.family_code_expires_at else None}


@router.post("/{session_id}/family-code")
def refresh_family_code(session_id: str, db: Session = Depends(get_db)) -> dict:
    """(Re)issue the 4-digit code the parent uses to join on their own phone. Switches the session to two_devices."""
    s = get_session_or_404(db, session_id)
    s.participation_mode = "two_devices"
    s.family_code = _new_family_code(db)
    s.family_code_expires_at = m.utcnow() + FAMILY_CODE_TTL
    db.commit()
    return {"family_code": s.family_code, "family_code_expires_at": s.family_code_expires_at.isoformat()}


@router.get("/{session_id}/status")
def session_status(session_id: str, db: Session = Depends(get_db)) -> dict:
    """Polled by both phones in a family session to see who has done what."""
    s = get_session_or_404(db, session_id)
    rankings = latest_rankings(db, s.id)
    return {
        "participation_mode": s.participation_mode,
        "parent_joined": s.parent_joined_at is not None,
        "parent_language": s.parent_language,
        "learner_language": s.language,
        "alignment": {"learner_done": "learner" in rankings, "parent_done": "parent" in rankings},
        "mood_pre": {"learner": s.mood_pre_learner is not None, "parent": s.mood_pre_parent is not None},
        "family_code": s.family_code if s.participation_mode == "two_devices" else None,
    }


@join_router.post("/join")
def join_family(body: JoinIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """A parent joins the learner's session from their own phone with the 4-digit family code."""
    client = request.client.host if request.client else "unknown"
    window = _failed_joins[client]
    now_ts = time.monotonic()
    while window and now_ts - window[0] > JOIN_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= JOIN_LIMIT:
        raise HTTPException(429, "too many attempts, please wait a few minutes")
    s = db.scalar(select(m.SessionRow).where(m.SessionRow.family_code == body.code))
    if not s or not s.family_code_expires_at or _aware(s.family_code_expires_at) < m.utcnow():
        window.append(now_ts)
        raise HTTPException(404, "code not found or expired")
    s.parent_joined_at = s.parent_joined_at or m.utcnow()
    s.parent_language = body.language
    db.add(m.Event(session_id=s.id, event_type="parent_joined",
                   payload={"language": body.language, "device": bool(body.device_id)}))
    db.commit()
    return {"session_id": s.id, "district": s.district, "learner_language": s.language,
            "learner_education": s.learner_education}


@router.patch("/{session_id}")
def update_session(session_id: str, body: SessionUpdate, db: Session = Depends(get_db)) -> dict:
    s = get_session_or_404(db, session_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/end")
def end_session(session_id: str, db: Session = Depends(get_db)) -> dict:
    s = get_session_or_404(db, session_id)
    s.ended_at = m.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/mood")
def record_mood(session_id: str, body: MoodIn, db: Session = Depends(get_db)) -> dict:
    s = get_session_or_404(db, session_id)
    setattr(s, f"mood_{body.phase}_{body.respondent}", body.value)
    db.add(m.Event(session_id=s.id, event_type="mood_recorded", payload=body.model_dump(exclude={"device_id"})))
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/alignment")
def save_alignment(session_id: str, body: AlignmentIn, db: Session = Depends(get_db)) -> dict:
    s = get_session_or_404(db, session_id)
    try:
        validate_ranking(body.ranking)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.add(m.AlignmentResponse(session_id=s.id, respondent=body.respondent, ranking=body.ranking,
                               device_id=body.device_id))
    db.flush()
    rankings = latest_rankings(db, s.id)
    result = compare(rankings.get("learner"), rankings.get("parent"))
    if result["complete"]:
        db.add(m.Event(session_id=s.id, event_type="alignment_completed",
                       payload={"shared_top": result["shared_top"], "biggest_difference": result["biggest_difference"]}))
    db.commit()
    return result


@router.get("/{session_id}/alignment")
def get_alignment(session_id: str, db: Session = Depends(get_db)) -> dict:
    get_session_or_404(db, session_id)
    return session_alignment(db, session_id)


@router.get("/{session_id}/messages")
def transcript(session_id: str, db: Session = Depends(get_db)) -> list[dict]:
    get_session_or_404(db, session_id)
    rows = db.scalars(select(m.Message).where(m.Message.session_id == session_id).order_by(m.Message.id))
    return [message_out(r) for r in rows]


def message_out(r: m.Message, internal: bool = False) -> dict:
    out = {"id": r.id, "role": r.role, "speaker": r.speaker, "text": r.text, "language": r.language,
           "cards": r.cards or [], "created_at": r.created_at.isoformat() if r.created_at else None,
           "device_id": r.device_id}
    if internal:
        out.update(concern_category=r.concern_category, sentiment=r.sentiment,
                   guardrail_status=r.guardrail_status, tool_calls=r.tool_calls)
    return out


@router.get("/{session_id}/summary")
def summary(session_id: str, db: Session = Depends(get_db)) -> dict:
    """Family Summary Card data. Built only from cards that were actually shown (tool results)."""
    s = get_session_or_404(db, session_id)
    msgs = list(db.scalars(select(m.Message).where(m.Message.session_id == s.id, m.Message.role == "assistant")
                           .order_by(m.Message.id)))
    figures: dict[tuple, dict] = {}
    ladder = None
    trades: dict[str, str] = {}
    for msg in msgs:
        for c in msg.cards or []:
            d = c.get("data", {})
            if d.get("unavailable"):
                continue
            if d.get("trade_slug"):
                trades[d["trade_slug"]] = d.get("trade_name", d["trade_slug"])
            if c["type"] in ("outcome", "costs"):
                figures[(c["type"], d.get("trade_slug"))] = c
            elif c["type"] == "ladder":
                ladder = c
    concerns = list(dict.fromkeys([*(s.top_concerns or []), *[
        r for r in db.scalars(select(m.Message.concern_category).where(
            m.Message.session_id == s.id, m.Message.role == "user", m.Message.concern_category.is_not(None)))
        if r != "other"]]))
    all_cards = list(figures.values()) + ([ladder] if ladder else [])
    db.add(m.Event(session_id=s.id, event_type="summary_viewed", payload={}))
    db.commit()
    return {
        "session_id": s.id, "language": s.language, "district": s.district,
        "trades_discussed": [{"slug": k, "name": v} for k, v in trades.items()],
        "figures": list(figures.values()), "ladder": ladder,
        "alignment": session_alignment(db, s.id), "concerns": concerns,
        "has_demo_data": any(c["evidence"].get("data_status") == "demo" for c in all_cards),
    }
