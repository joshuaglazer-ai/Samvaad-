"""Admin → Trades: manage sectors, trades, synonyms and progression steps without code changes (Update 3, Step 5).

PIN-protected (admin). Every trade carries a data status; new trades start as `unavailable` (or `demo`), and a trade
can be marked `verified` or `historical` only when a source is attached. Text is {lang: text}; English is required,
other languages fall back to English (logged) until filled in.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models as m
from ..auth import require_admin
from ..config import EDUCATION_LEVELS
from ..db import get_db
from ..i18n import LANGS

router = APIRouter(prefix="/api/admin", tags=["admin-catalogue"], dependencies=[Depends(require_admin)])

SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
Status = Literal["demo", "unavailable", "verified", "historical"]
Trait = Literal["hands", "people", "machines", "outdoors", "computers"]
StepKind = Literal["job", "upskill", "apprenticeship", "diploma", "degree"]


def _lang_text(v: dict, field: str, required: bool = True) -> dict:
    bad = [k for k in v if k not in LANGS]
    if bad:
        raise ValueError(f"{field}: unknown languages {bad}")
    clean = {k: x.strip() if isinstance(x, str) else x for k, x in v.items() if x not in (None, "", [])}
    if required and not clean.get("en"):
        raise ValueError(f"{field}: English text is required")
    return clean


class SectorIn(BaseModel):
    slug: str = Field(pattern=SLUG, max_length=60)
    names: dict[str, str]
    icon: str = Field(default="tool", max_length=40)
    sort_order: int = Field(default=0, ge=0, le=999)

    @field_validator("names")
    @classmethod
    def _names(cls, v):
        return _lang_text(v, "names")


class TradeIn(BaseModel):
    slug: str = Field(pattern=SLUG, max_length=80)
    sector: str
    names: dict[str, str]
    nsqf_level: int = Field(ge=1, le=10)
    duration_months: int = Field(ge=1, le=60)
    entry_min_education: str = "class_10"
    entry_requirement: dict[str, str] = {}
    job_roles: dict[str, list[str]] = {}
    icon: str = Field(default="tool", max_length=40)
    traits: list[Trait] = []
    data_status: Status = "unavailable"
    source_id: int | None = None

    @field_validator("names")
    @classmethod
    def _names(cls, v):
        return _lang_text(v, "names")

    @field_validator("entry_requirement")
    @classmethod
    def _req(cls, v):
        return _lang_text(v, "entry_requirement", required=False)

    @field_validator("job_roles")
    @classmethod
    def _roles(cls, v):
        return _lang_text({k: [r.strip() for r in x if r.strip()] for k, x in v.items()}, "job_roles", required=False)

    @field_validator("entry_min_education")
    @classmethod
    def _edu(cls, v):
        if v not in EDUCATION_LEVELS:
            raise ValueError(f"entry_min_education must be one of {EDUCATION_LEVELS}")
        return v


class SynonymIn(BaseModel):
    language: Literal["en", "kn", "hi", "te"]
    term: str = Field(min_length=1, max_length=120)
    review_status: Literal["needs_native_review", "reviewed"] = "needs_native_review"


class StepIn(BaseModel):
    kind: StepKind
    titles: dict[str, str]
    nsqf_level: int | None = Field(default=None, ge=1, le=10)
    entry_min_education: str = "class_10"
    entry_requirement: dict[str, str] = {}
    duration_months: int | None = Field(default=None, ge=0, le=120)

    @field_validator("titles")
    @classmethod
    def _titles(cls, v):
        return _lang_text(v, "titles")

    @field_validator("entry_requirement")
    @classmethod
    def _req(cls, v):
        return _lang_text(v, "entry_requirement", required=False)


# ---------------------------------------------------------------- views
def _synonym_out(s: m.TradeSynonym) -> dict:
    return {"id": s.id, "language": s.language, "term": s.term, "review_status": s.review_status}


def _trade_out(db: Session, t: m.Trade) -> dict:
    steps = db.scalars(select(m.ProgressionStep).where(m.ProgressionStep.trade_id == t.id)
                       .order_by(m.ProgressionStep.step_order))
    syns = db.scalars(select(m.TradeSynonym).where(m.TradeSynonym.trade_id == t.id)
                      .order_by(m.TradeSynonym.language, m.TradeSynonym.term))
    outcomes = db.scalars(select(m.Outcome.data_status).where(m.Outcome.trade_id == t.id))
    by_status: dict[str, int] = {}
    for st in outcomes:
        by_status[st] = by_status.get(st, 0) + 1
    return {
        "slug": t.slug, "sector": t.sector, "names": t.names, "nsqf_level": t.nsqf_level,
        "duration_months": t.duration_months, "entry_min_education": t.entry_min_education,
        "entry_requirement": t.entry_requirement, "job_roles": t.job_roles, "icon": t.icon, "traits": t.traits or [],
        "data_status": t.data_status, "source_id": t.source_id,
        "missing_languages": [lang for lang in LANGS if not (t.names or {}).get(lang)],
        "outcomes_by_status": by_status,
        "synonyms": [_synonym_out(s) for s in syns],
        "steps": [{"kind": s.kind, "titles": s.titles, "nsqf_level": s.nsqf_level,
                   "entry_min_education": s.entry_min_education, "entry_requirement": s.entry_requirement,
                   "duration_months": s.duration_months} for s in steps],
    }


def _trade_or_404(db: Session, slug: str) -> m.Trade:
    t = db.scalar(select(m.Trade).where(m.Trade.slug == slug))
    if not t:
        raise HTTPException(404, "trade not found")
    return t


def _check_trade(db: Session, body: TradeIn) -> None:
    if not db.scalar(select(m.Sector).where(m.Sector.slug == body.sector)):
        raise HTTPException(422, f"unknown sector {body.sector}")
    if body.source_id is not None and not db.get(m.Source, body.source_id):
        raise HTTPException(422, "unknown source")
    if body.data_status in ("verified", "historical") and body.source_id is None:
        raise HTTPException(422, "attach a source before marking a trade verified or historical")


@router.get("/catalogue")
def catalogue(db: Session = Depends(get_db)) -> dict:
    return {
        "sectors": [{"slug": s.slug, "names": s.names, "icon": s.icon, "sort_order": s.sort_order}
                    for s in db.scalars(select(m.Sector).order_by(m.Sector.sort_order, m.Sector.slug))],
        "trades": [_trade_out(db, t) for t in db.scalars(select(m.Trade).order_by(m.Trade.sector, m.Trade.slug))],
        "sources": [{"id": s.id, "title": s.title, "reporting_period": s.reporting_period, "verified_on": s.verified_on}
                    for s in db.scalars(select(m.Source).order_by(m.Source.id))],
        "languages": list(LANGS), "education_levels": EDUCATION_LEVELS,
    }


@router.post("/sectors", status_code=201)
def add_sector(body: SectorIn, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(m.Sector).where(m.Sector.slug == body.slug)):
        raise HTTPException(409, "a sector with this slug exists")
    db.add(m.Sector(**body.model_dump()))
    db.commit()
    return {"ok": True, "slug": body.slug}


@router.put("/sectors/{slug}")
def edit_sector(slug: str, body: SectorIn, db: Session = Depends(get_db)) -> dict:
    s = db.scalar(select(m.Sector).where(m.Sector.slug == slug))
    if not s:
        raise HTTPException(404, "sector not found")
    if body.slug != slug:
        raise HTTPException(422, "the slug cannot be changed (trades point to it)")
    s.names, s.icon, s.sort_order = body.names, body.icon, body.sort_order
    db.commit()
    return {"ok": True}


@router.post("/trades", status_code=201)
def add_trade(body: TradeIn, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(m.Trade).where(m.Trade.slug == body.slug)):
        raise HTTPException(409, "a trade with this slug exists")
    _check_trade(db, body)
    t = m.Trade(**body.model_dump())
    db.add(t)
    db.add(m.Event(event_type="trade_added", payload={"slug": body.slug, "data_status": body.data_status}))
    db.commit()
    return _trade_out(db, t)


@router.put("/trades/{slug}")
def edit_trade(slug: str, body: TradeIn, db: Session = Depends(get_db)) -> dict:
    t = _trade_or_404(db, slug)
    if body.slug != slug:
        raise HTTPException(422, "the slug cannot be changed (outcomes and sessions point to it)")
    _check_trade(db, body)
    for k, v in body.model_dump(exclude={"slug"}).items():
        setattr(t, k, v)
    db.commit()
    return _trade_out(db, t)


@router.post("/trades/{slug}/synonyms", status_code=201)
def add_synonym(slug: str, body: SynonymIn, db: Session = Depends(get_db)) -> dict:
    t = _trade_or_404(db, slug)
    term = " ".join(body.term.split())
    dup = db.scalar(select(m.TradeSynonym).where(m.TradeSynonym.trade_id == t.id,
                                                 m.TradeSynonym.language == body.language,
                                                 m.TradeSynonym.term == term))
    if dup:
        raise HTTPException(409, "this word is already listed")
    s = m.TradeSynonym(trade_id=t.id, language=body.language, term=term, review_status=body.review_status)
    db.add(s)
    db.commit()
    return _synonym_out(s)


@router.put("/synonyms/{synonym_id}")
def edit_synonym(synonym_id: int, body: SynonymIn, db: Session = Depends(get_db)) -> dict:
    s = db.get(m.TradeSynonym, synonym_id)
    if not s:
        raise HTTPException(404, "synonym not found")
    s.language, s.term, s.review_status = body.language, " ".join(body.term.split()), body.review_status
    db.commit()
    return _synonym_out(s)


@router.delete("/synonyms/{synonym_id}")
def remove_synonym(synonym_id: int, db: Session = Depends(get_db)) -> dict:
    s = db.get(m.TradeSynonym, synonym_id)
    if not s:
        raise HTTPException(404, "synonym not found")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.put("/trades/{slug}/steps")
def replace_steps(slug: str, body: list[StepIn], db: Session = Depends(get_db)) -> dict:
    """Replace the whole career ladder of a trade (order = list order)."""
    t = _trade_or_404(db, slug)
    if len(body) > 12:
        raise HTTPException(422, "at most 12 steps")
    db.execute(delete(m.ProgressionStep).where(m.ProgressionStep.trade_id == t.id))
    for i, step in enumerate(body, start=1):
        db.add(m.ProgressionStep(trade_id=t.id, step_order=i, source_id=t.source_id, **step.model_dump()))
    db.commit()
    return _trade_out(db, t)
