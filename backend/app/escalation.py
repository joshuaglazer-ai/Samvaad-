"""Human escalation: triggers, cases with bilingual summaries, and live-chat rooms."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import WebSocket
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m

log = logging.getLogger(__name__)

OPEN_STATUSES = ("pending", "assigned", "in_progress")
TRIGGERS = ("user_request", "no_data", "negative_sentiment", "sensitive_topic", "repeated_failure")

TRIGGER_TEXT = {
    "user_request": ("The family asked to talk to a counsellor.", "ಕುಟುಂಬವು ಸಲಹೆಗಾರರೊಂದಿಗೆ ಮಾತನಾಡಲು ಕೇಳಿದೆ."),
    "no_data": ("Data was not available for their questions twice.", "ಅವರ ಪ್ರಶ್ನೆಗಳಿಗೆ ಎರಡು ಬಾರಿ ಮಾಹಿತಿ ಲಭ್ಯವಿರಲಿಲ್ಲ."),
    "negative_sentiment": ("The parent sounded worried in 3 messages in a row.", "ಪೋಷಕರು ಸತತ 3 ಸಂದೇಶಗಳಲ್ಲಿ ಚಿಂತಿತರಾಗಿದ್ದರು."),
    "sensitive_topic": ("A sensitive topic came up (safety, family, debt or distress).", "ಸೂಕ್ಷ್ಮ ವಿಷಯ ಬಂದಿದೆ (ಸುರಕ್ಷತೆ, ಕುಟುಂಬ, ಸಾಲ ಅಥವಾ ಒತ್ತಡ)."),
    "repeated_failure": ("The assistant could not give a checked answer twice.", "ಸಹಾಯಕವು ಎರಡು ಬಾರಿ ಪರಿಶೀಲಿತ ಉತ್ತರ ನೀಡಲಾಗಲಿಲ್ಲ."),
}
CONCERN_KN = {"income": "ಆದಾಯ", "job_security": "ಉದ್ಯೋಗ ಭದ್ರತೆ", "social_status": "ಸಮಾಜದಲ್ಲಿ ಗೌರವ", "safety": "ಸುರಕ್ಷತೆ",
              "cost": "ತರಬೇತಿಯ ಖರ್ಚು", "distance_migration": "ಮನೆಯಿಂದ ದೂರ ಕೆಲಸ", "degree_first": "ಮೊದಲು ಪದವಿಯೇ?",
              "other": "ಇತರೆ"}
DISTRICT_KN = {"Bengaluru Urban": "ಬೆಂಗಳೂರು ನಗರ", "Mysuru": "ಮೈಸೂರು", "Kalaburagi": "ಕಲಬುರಗಿ", "Dharwad": "ಧಾರವಾಡ"}
CARD_EN = {"outcome": "earnings & placement", "ladder": "career ladder", "providers": "training centres", "costs": "fees & support"}
CARD_KN = {"outcome": "ಸಂಪಾದನೆ ಮತ್ತು ಉದ್ಯೋಗ", "ladder": "ವೃತ್ತಿ ಏಣಿ", "providers": "ತರಬೇತಿ ಕೇಂದ್ರಗಳು", "costs": "ಶುಲ್ಕ ಮತ್ತು ನೆರವು"}


def open_case(db: Session, session_id: str) -> m.Escalation | None:
    return db.scalar(select(m.Escalation).where(m.Escalation.session_id == session_id,
                                                m.Escalation.status.in_(OPEN_STATUSES))
                     .order_by(m.Escalation.id.desc()))


def main_concern(db: Session, s: m.SessionRow) -> str:
    rows = db.execute(select(m.Message.concern_category, func.count()).where(
        m.Message.session_id == s.id, m.Message.role == "user", m.Message.concern_category.is_not(None),
        m.Message.concern_category != "other").group_by(m.Message.concern_category)
        .order_by(func.count().desc())).all()
    if rows:
        return rows[0][0]
    return (s.top_concerns or ["other"])[0]


def build_summary(db: Session, s: m.SessionRow, trigger: str) -> tuple[str, str]:
    """Three plain lines in English and Kannada: who/where/concern, what was answered, why escalated."""
    concern = main_concern(db, s)
    shown: list[tuple[str, str]] = []
    for msg in db.scalars(select(m.Message).where(m.Message.session_id == s.id, m.Message.role == "assistant")):
        for c in msg.cards or []:
            key = (c.get("type"), c.get("data", {}).get("trade_name", ""))
            if key not in shown:
                shown.append(key)
    lang_en = "Kannada" if s.language == "kn" else "English"
    lang_kn = "ಕನ್ನಡ" if s.language == "kn" else "ಇಂಗ್ಲಿಷ್"
    answered_en = "; ".join(f"{CARD_EN.get(t, t)} – {n}" for t, n in shown[:4]) or "nothing yet"
    answered_kn = "; ".join(f"{CARD_KN.get(t, t)} – {n}" for t, n in shown[:4]) or "ಇನ್ನೂ ಏನೂ ಇಲ್ಲ"
    why_en, why_kn = TRIGGER_TEXT.get(trigger, (trigger, trigger))
    en = (f"Language: {lang_en} · District: {s.district} · Main concern: {concern.replace('_', ' ')}\n"
          f"Answered so far: {answered_en}\n"
          f"Escalated because: {why_en}")
    kn = (f"ಭಾಷೆ: {lang_kn} · ಜಿಲ್ಲೆ: {DISTRICT_KN.get(s.district, s.district)} · ಮುಖ್ಯ ಚಿಂತೆ: {CONCERN_KN.get(concern, concern)}\n"
          f"ಇಲ್ಲಿಯವರೆಗೆ ಉತ್ತರಿಸಿದ್ದು: {answered_kn}\n"
          f"ಸಲಹೆಗಾರರಿಗೆ ಕಳುಹಿಸಿದ ಕಾರಣ: {why_kn}")
    return en, kn


def create_case(db: Session, s: m.SessionRow, trigger: str) -> tuple[m.Escalation, bool]:
    """Return (case, created). An open case for the session is reused, never duplicated."""
    if trigger not in TRIGGERS:
        trigger = "user_request"
    existing = open_case(db, s.id)
    if existing:
        return existing, False
    en, kn = build_summary(db, s, trigger)
    case = m.Escalation(session_id=s.id, trigger=trigger, status="pending", summary_en=en, summary_kn=kn)
    s.escalated = True
    db.add(case)
    db.add(m.Event(session_id=s.id, event_type="escalated", payload={"trigger": trigger}))
    db.flush()
    rooms.notify_counsellors_sync({"type": "new_case", "case_id": case.id})
    return case, True


def check_triggers(db: Session, s: m.SessionRow) -> str | None:
    """Automatic triggers evaluated after each turn (user requests and sensitive topics are handled in chat)."""
    gaps = db.scalar(select(func.count()).select_from(m.EvidenceGap).where(m.EvidenceGap.session_id == s.id)) or 0
    if gaps >= 2:
        return "no_data"
    parent = list(db.scalars(select(m.Message.sentiment).where(
        m.Message.session_id == s.id, m.Message.role == "user", m.Message.speaker == "parent")
        .order_by(m.Message.id.desc()).limit(3)))
    if len(parent) == 3 and all(x is not None and x <= -1 for x in parent):
        return "negative_sentiment"
    fallbacks = db.scalar(select(func.count()).select_from(m.Message).where(
        m.Message.session_id == s.id, m.Message.guardrail_status == "fallback")) or 0
    if fallbacks >= 2:
        return "repeated_failure"
    return None


def case_info(db: Session, case: m.Escalation) -> dict:
    return {"id": case.id, "trigger": case.trigger, "status": case.status,
            "counsellor_online": rooms.counsellor_online()}


# ---------------------------------------------------------------------------------------------- live rooms
class Rooms:
    """In-process WebSocket rooms. Family and counsellor share a room per escalation id; counsellors also
    join a lobby so we know whether anyone is online. Polling (GET /api/escalations/{id}/messages) is the
    fallback when WebSockets are unavailable."""

    def __init__(self) -> None:
        self.cases: dict[int, set[WebSocket]] = defaultdict(set)
        self.lobby: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def counsellor_online(self) -> bool:
        return len(self.lobby) > 0

    async def join_case(self, case_id: int, ws: WebSocket) -> None:
        self.loop = asyncio.get_running_loop()
        self.cases[case_id].add(ws)

    def leave_case(self, case_id: int, ws: WebSocket) -> None:
        self.cases[case_id].discard(ws)

    async def join_lobby(self, ws: WebSocket) -> None:
        self.loop = asyncio.get_running_loop()
        self.lobby.add(ws)

    def leave_lobby(self, ws: WebSocket) -> None:
        self.lobby.discard(ws)

    async def _send_all(self, targets: set[WebSocket], payload: dict) -> None:
        data = json.dumps(payload, default=str, ensure_ascii=False)
        for ws in list(targets):
            try:
                await ws.send_text(data)
            except Exception:  # client went away
                targets.discard(ws)

    async def broadcast_case(self, case_id: int, payload: dict) -> None:
        await self._send_all(self.cases.get(case_id, set()), payload)

    async def notify_counsellors(self, payload: dict) -> None:
        await self._send_all(self.lobby, payload)

    def _schedule(self, coro) -> None:
        loop = self.loop
        if loop is None or loop.is_closed():
            coro.close()
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            loop.create_task(coro)
        else:
            asyncio.run_coroutine_threadsafe(coro, loop)

    def broadcast_case_sync(self, case_id: int, payload: dict) -> None:
        """Called from sync request handlers (thread pool)."""
        self._schedule(self.broadcast_case(case_id, payload))

    def notify_counsellors_sync(self, payload: dict) -> None:
        self._schedule(self.notify_counsellors(payload))


rooms = Rooms()


def now() -> datetime:
    return datetime.now(timezone.utc)
