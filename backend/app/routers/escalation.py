"""Escalation endpoints: family side (escalate, callback, live chat, polling) and counsellor console."""
from __future__ import annotations

import json
import logging

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..auth import require_counsellor
from ..config import get_settings
from ..db import get_db, get_session_factory
from ..escalation import case_info, create_case, now, rooms
from ..schemas import CallbackIn, CaseUpdate, CounsellorReply, EscalateIn
from .session import message_out

log = logging.getLogger(__name__)
router = APIRouter(tags=["escalation"])


# ------------------------------------------------------------------------------------------------ crypto
def _fernet() -> Fernet:
    key = get_settings().phone_encryption_key
    if not key:
        # Demo fallback: derive a per-process key so phones are never stored in plain text.
        # Documented: set PHONE_ENCRYPTION_KEY in production or numbers become unreadable after restart.
        global _EPHEMERAL_KEY
        if _EPHEMERAL_KEY is None:
            _EPHEMERAL_KEY = Fernet.generate_key()
            log.warning("PHONE_ENCRYPTION_KEY not set; using an ephemeral key for this process")
        key = _EPHEMERAL_KEY.decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


_EPHEMERAL_KEY: bytes | None = None


def encrypt_phone(phone: str) -> str:
    return _fernet().encrypt(phone.encode()).decode()


def decrypt_phone(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


# ------------------------------------------------------------------------------------------------ family side
def _case_or_404(db: Session, case_id: int) -> m.Escalation:
    case = db.get(m.Escalation, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    return case


@router.post("/api/escalate")
def escalate(body: EscalateIn, db: Session = Depends(get_db)) -> dict:
    s = db.get(m.SessionRow, body.session_id)
    if not s:
        raise HTTPException(404, "session not found")
    case, _ = create_case(db, s, body.trigger)
    db.commit()
    return case_info(db, case)


@router.get("/api/escalations/{case_id}")
def escalation_status(case_id: int, db: Session = Depends(get_db)) -> dict:
    return case_info(db, _case_or_404(db, case_id))


@router.post("/api/escalate/{case_id}/callback")
def request_callback(case_id: int, body: CallbackIn, db: Session = Depends(get_db)) -> dict:
    case = _case_or_404(db, case_id)
    if not body.consent:
        raise HTTPException(400, "explicit consent is required to store a phone number")
    db.add(m.CallbackRequest(escalation_id=case.id, phone_encrypted=encrypt_phone(body.phone),
                             preferred_time=body.preferred_time, consent=True))
    db.add(m.Event(session_id=case.session_id, event_type="callback_requested", payload={"time": body.preferred_time}))
    db.commit()
    rooms.notify_counsellors_sync({"type": "callback", "case_id": case.id})
    return {"ok": True}


def _live_messages(db: Session, case: m.Escalation, after: int = 0) -> list[m.Message]:
    """Messages exchanged after escalation (counsellor replies and family messages in the live room)."""
    return list(db.scalars(select(m.Message).where(
        m.Message.session_id == case.session_id, m.Message.id > after,
        m.Message.live.is_(True))
        .order_by(m.Message.id)))


def _add_live_message(db: Session, case: m.Escalation, role: str, speaker: str, text: str) -> m.Message:
    s = db.get(m.SessionRow, case.session_id)
    msg = m.Message(session_id=case.session_id, role=role, speaker=speaker, text=text[:2000],
                    language=s.language if s else "en", tool_calls=[], cards=[], guardrail_status="na", live=True)
    db.add(msg)
    db.commit()
    return msg


@router.get("/api/escalations/{case_id}/messages")
def poll_messages(case_id: int, after: int = 0, db: Session = Depends(get_db)) -> list[dict]:
    """Polling fallback for the live chat (every 3 s)."""
    case = _case_or_404(db, case_id)
    return [message_out(r) for r in _live_messages(db, case, after)]


@router.post("/api/escalations/{case_id}/messages")
def family_message(case_id: int, body: CounsellorReply, speaker: str = "parent", db: Session = Depends(get_db)) -> dict:
    case = _case_or_404(db, case_id)
    msg = _add_live_message(db, case, "user", speaker if speaker in ("learner", "parent", "helper") else "parent", body.text)
    out = message_out(msg)
    rooms.broadcast_case_sync(case.id, {"type": "message", "message": out})
    return out


@router.websocket("/ws/escalation/{case_id}")
async def live_chat(ws: WebSocket, case_id: int, role: str = Query("family"), pin: str | None = Query(None),
                    SessionLocal=Depends(get_session_factory)):
    """Family ↔ counsellor live chat. Counsellors must pass ?pin=; family connects with the case id."""
    if role == "counsellor":
        try:
            require_counsellor(pin)
        except HTTPException:
            await ws.close(code=4401)
            return
    with SessionLocal() as db:
        if not db.get(m.Escalation, case_id):
            await ws.close(code=4404)
            return
    await ws.accept()
    await rooms.join_case(case_id, ws)
    try:
        while True:
            data = json.loads(await ws.receive_text())
            if data.get("type") != "message" or not str(data.get("text", "")).strip():
                continue
            with SessionLocal() as db:
                case = db.get(m.Escalation, case_id)
                if role == "counsellor":
                    msg = _add_live_message(db, case, "counsellor", "counsellor", data["text"])
                    if case.status in ("pending", "assigned"):
                        case.status = "in_progress"
                        db.commit()
                else:
                    sp = data.get("speaker") if data.get("speaker") in ("learner", "parent", "helper") else "parent"
                    msg = _add_live_message(db, case, "user", sp, data["text"])
                out = message_out(msg)
            await rooms.broadcast_case(case_id, {"type": "message", "message": out})
    except WebSocketDisconnect:
        pass
    finally:
        rooms.leave_case(case_id, ws)


@router.websocket("/ws/counsellor")
async def counsellor_lobby(ws: WebSocket, pin: str | None = Query(None)):
    """Counsellors stay connected here while the console is open; this is how 'online' is known."""
    try:
        require_counsellor(pin)
    except HTTPException:
        await ws.close(code=4401)
        return
    await ws.accept()
    await rooms.join_lobby(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive pings
    except WebSocketDisconnect:
        pass
    finally:
        rooms.leave_lobby(ws)


# ------------------------------------------------------------------------------------------------ counsellor
def case_out(db: Session, c: m.Escalation) -> dict:
    s = db.get(m.SessionRow, c.session_id)
    has_cb = db.scalar(select(m.CallbackRequest.id).where(m.CallbackRequest.escalation_id == c.id,
                                                          m.CallbackRequest.deleted_at.is_(None)).limit(1)) is not None
    created = c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=now().tzinfo)
    return {"id": c.id, "session_id": c.session_id, "trigger": c.trigger, "status": c.status,
            "summary_en": c.summary_en, "summary_local": c.summary_local, "summary_language": c.summary_language,
            "assigned_to": c.assigned_to,
            "created_at": created.isoformat(), "waiting_minutes": int((now() - created).total_seconds() // 60),
            "district": s.district if s else "", "language": s.language if s else "en", "has_callback": has_cb}


@router.get("/api/counsellor/queue")
def queue(include_resolved: bool = False, db: Session = Depends(get_db), _: str = Depends(require_counsellor)) -> list[dict]:
    q = select(m.Escalation).order_by(m.Escalation.created_at)
    if not include_resolved:
        q = q.where(m.Escalation.status != "resolved")
    return [case_out(db, c) for c in db.scalars(q)]


@router.get("/api/counsellor/cases/{case_id}")
def case_detail(case_id: int, db: Session = Depends(get_db), _: str = Depends(require_counsellor)) -> dict:
    c = _case_or_404(db, case_id)
    s = db.get(m.SessionRow, c.session_id)
    transcript = db.scalars(select(m.Message).where(m.Message.session_id == c.session_id).order_by(m.Message.id))
    return {**case_out(db, c), "top_concerns": s.top_concerns if s else [],
            "transcript": [message_out(r, internal=True) for r in transcript]}


@router.patch("/api/counsellor/cases/{case_id}")
def update_case(case_id: int, body: CaseUpdate, db: Session = Depends(get_db), _: str = Depends(require_counsellor)) -> dict:
    c = _case_or_404(db, case_id)
    if body.assigned_to is not None:
        c.assigned_to = body.assigned_to
        c.assigned_at = c.assigned_at or now()
        if c.status == "pending":
            c.status = "assigned"
    if body.status:
        c.status = body.status
        if body.status in ("assigned", "in_progress") and not c.assigned_at:
            c.assigned_at = now()
        if body.status == "resolved":
            c.resolved_at = now()
    db.commit()
    rooms.broadcast_case_sync(c.id, {"type": "status", "status": c.status})
    return case_out(db, c)


@router.post("/api/counsellor/cases/{case_id}/reply")
def counsellor_reply(case_id: int, body: CounsellorReply, db: Session = Depends(get_db),
                     _: str = Depends(require_counsellor)) -> dict:
    """HTTP alternative to the WebSocket (used by the console's polling fallback)."""
    c = _case_or_404(db, case_id)
    msg = _add_live_message(db, c, "counsellor", "counsellor", body.text)
    if c.status in ("pending", "assigned"):
        c.status = "in_progress"
        c.assigned_at = c.assigned_at or now()
        db.commit()
    out = message_out(msg)
    rooms.broadcast_case_sync(c.id, {"type": "message", "message": out})
    rooms.broadcast_case_sync(c.id, {"type": "status", "status": c.status})
    return out


@router.get("/api/counsellor/callbacks")
def callbacks(db: Session = Depends(get_db), _: str = Depends(require_counsellor)) -> list[dict]:
    rows = db.scalars(select(m.CallbackRequest).where(m.CallbackRequest.deleted_at.is_(None))
                      .order_by(m.CallbackRequest.created_at))
    out = []
    for cb in rows:
        case = db.get(m.Escalation, cb.escalation_id)
        s = db.get(m.SessionRow, case.session_id) if case else None
        out.append({"id": cb.id, "escalation_id": cb.escalation_id, "phone": decrypt_phone(cb.phone_encrypted),
                    "preferred_time": cb.preferred_time, "created_at": cb.created_at.isoformat(),
                    "district": s.district if s else ""})
    return out


@router.delete("/api/counsellor/callbacks/{cb_id}")
def delete_callback(cb_id: int, db: Session = Depends(get_db), _: str = Depends(require_counsellor)) -> dict:
    """Delete a phone number (privacy: numbers are deletable on request). The row is kept without the number."""
    cb = db.get(m.CallbackRequest, cb_id)
    if not cb:
        raise HTTPException(404, "callback not found")
    cb.phone_encrypted = None
    cb.deleted_at = now()
    db.commit()
    return {"ok": True}
