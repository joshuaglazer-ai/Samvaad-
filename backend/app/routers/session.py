from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..alignment import compare, latest_rankings, session_alignment, validate_ranking
from ..db import get_db
from ..schemas import AlignmentIn, MoodIn, SessionCreate, SessionUpdate

router = APIRouter(prefix="/api/session", tags=["session"])


def get_session_or_404(db: Session, session_id: str) -> m.SessionRow:
    s = db.get(m.SessionRow, session_id)
    if not s:
        raise HTTPException(404, "session not found")
    return s


@router.post("")
def create_session(body: SessionCreate, db: Session = Depends(get_db)) -> dict:
    if not body.consent_given:
        raise HTTPException(400, "consent is required to start a session")
    s = m.SessionRow(**body.model_dump())
    db.add(s)
    db.flush()
    db.add(m.Event(session_id=s.id, event_type="session_started",
                   payload={"language": s.language, "district": s.district, "helper_mode": s.helper_mode}))
    db.commit()
    return {"session_id": s.id}


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
    db.add(m.Event(session_id=s.id, event_type="mood_recorded", payload=body.model_dump()))
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/alignment")
def save_alignment(session_id: str, body: AlignmentIn, db: Session = Depends(get_db)) -> dict:
    s = get_session_or_404(db, session_id)
    try:
        validate_ranking(body.ranking)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.add(m.AlignmentResponse(session_id=s.id, respondent=body.respondent, ranking=body.ranking))
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
           "cards": r.cards or [], "created_at": r.created_at.isoformat() if r.created_at else None}
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
