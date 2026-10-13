from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models as m
from ..config import CONCERN_CATEGORIES, DISTRICT_COORDS, DISTRICTS, EDUCATION_LEVELS, get_settings
from ..data_tools import DataTools
from ..db import get_db
from ..goals import suggest_trades
from ..schemas import EventIn, MatchIn, SuggestIn

router = APIRouter(prefix="/api", tags=["data"])

ALLOWED_EVENTS = {"session_started", "outcome_viewed", "ladder_viewed", "alignment_completed", "summary_shared",
                  "summary_downloaded", "mood_recorded", "voice_used", "read_aloud_used", "lite_mode",
                  "language_switched", "quick_reply_used", "counsellor_button", "goal_option_chosen",
                  "goal_changed"}


@router.get("/config")
def config() -> dict:
    return {"income_brackets": get_settings().income_bracket_list, "districts": DISTRICTS,
            "concerns": CONCERN_CATEGORIES, "education_levels": EDUCATION_LEVELS}


@router.get("/districts")
def districts() -> list[dict]:
    return [{"name": d, "lat": DISTRICT_COORDS[d][0], "lng": DISTRICT_COORDS[d][1]} for d in DISTRICTS]


@router.get("/sectors")
def sectors(language: str = "en", db: Session = Depends(get_db)) -> list[dict]:
    r = DataTools(db, language=language).list_sectors()
    db.rollback()
    return r["records"]


@router.get("/trades")
def trades(language: str = "en", sector: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    r = DataTools(db, language=language).list_trades(sector=sector)
    db.rollback()  # browsing the catalogue is not an evidence gap
    if sector and not r["found"]:
        raise HTTPException(404, "sector not found")
    return r["records"]


@router.post("/aspiration/match")
def match_aspiration(body: MatchIn, db: Session = Depends(get_db)) -> dict:
    """Preview what the app understood, before the session exists. Nothing is stored (the gap is logged on save)."""
    r = DataTools(db, language=body.language).match_aspiration(body.text, body.language)
    db.rollback()
    return r


@router.post("/aspiration/suggest")
def suggest(body: SuggestIn, db: Session = Depends(get_db)) -> dict:
    district = body.district if body.district in DISTRICTS else None
    return {"suggestions": suggest_trades(db, body.likes, body.near_home, district, body.language)}


@router.get("/trades/{slug}/progression")
def progression(slug: str, education_level: str | None = None, language: str = "en",
                db: Session = Depends(get_db)) -> dict:
    r = DataTools(db, language=language).get_progression(slug, education_level)
    db.rollback()
    if not r["found"]:
        raise HTTPException(404, "trade not found")
    return r


@router.post("/events")
def event(body: EventIn, db: Session = Depends(get_db)) -> dict:
    if body.event_type not in ALLOWED_EVENTS:
        raise HTTPException(422, f"event_type must be one of {sorted(ALLOWED_EVENTS)}")
    if body.session_id and not db.get(m.SessionRow, body.session_id):
        raise HTTPException(404, "session not found")
    db.add(m.Event(session_id=body.session_id, event_type=body.event_type, payload=body.payload))
    db.commit()
    return {"ok": True}
