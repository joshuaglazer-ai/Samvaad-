"""SQLAlchemy models. See docs/data_dictionary.md for field meanings."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------- evidence layer
class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(String(500))
    publisher: Mapped[str | None] = mapped_column(String(200))
    reporting_period: Mapped[str | None] = mapped_column(String(50))
    verified_on: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)


class Sector(Base):
    """Training sectors (Update 3). Names are {lang: text}; the frontend gets them only through the API."""
    __tablename__ = "sectors"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    names: Mapped[dict] = mapped_column(JSON, default=dict)
    icon: Mapped[str] = mapped_column(String(40), default="tool")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    # Translatable text is stored as {"en": …, "kn": …, "hi": …, "te": …}; see app/i18n.py (English fallback).
    names: Mapped[dict] = mapped_column(JSON, default=dict)
    sector: Mapped[str] = mapped_column(String(60), index=True)  # sectors.slug
    nsqf_level: Mapped[int] = mapped_column(Integer)
    qualification_code: Mapped[str | None] = mapped_column(String(40))  # left NULL until verified on nqr.gov.in
    awarding_body: Mapped[str | None] = mapped_column(String(200))
    duration_months: Mapped[int] = mapped_column(Integer)
    entry_requirement: Mapped[dict] = mapped_column(JSON, default=dict)
    entry_min_education: Mapped[str] = mapped_column(String(20), default="class_10")
    job_roles: Mapped[dict] = mapped_column(JSON, default=dict)  # {lang: [role, …]}
    icon: Mapped[str] = mapped_column(String(40), default="tool")
    # Work styles this trade suits, for the "Not sure yet" quiz: hands | people | machines | outdoors | computers.
    traits: Mapped[list] = mapped_column(JSON, default=list)
    data_status: Mapped[str] = mapped_column(String(20), default="demo", server_default="demo")
    # The source behind the trade record; a trade can be marked verified/historical only once one is attached.
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))


class TradeSynonym(Base):
    """Everyday words people use for a trade, per language (e.g. "bijli mistri"). Needs native review."""
    __tablename__ = "trade_synonyms"
    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(5), index=True)
    term: Mapped[str] = mapped_column(String(120))
    review_status: Mapped[str] = mapped_column(String(30), default="needs_native_review")

    trade: Mapped[Trade] = relationship()


class Provider(Base):
    __tablename__ = "providers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    district: Mapped[str] = mapped_column(String(80), index=True)
    state: Mapped[str] = mapped_column(String(80))
    provider_type: Mapped[str] = mapped_column(String(60))
    accreditation: Mapped[str | None] = mapped_column(String(120))
    data_status: Mapped[str] = mapped_column(String(20), default="demo")
    trades: Mapped[list] = mapped_column(JSON, default=list)  # trade slugs offered


class Outcome(Base):
    __tablename__ = "outcomes"
    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"), index=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("providers.id"), index=True)
    geo_level: Mapped[str] = mapped_column(String(20))  # district | state | national
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    year: Mapped[int] = mapped_column(Integer)
    reporting_period: Mapped[str] = mapped_column(String(50))
    placement_numerator: Mapped[int | None] = mapped_column(Integer)
    placement_denominator: Mapped[int | None] = mapped_column(Integer)
    placement_rate: Mapped[float | None] = mapped_column(Float)  # 0..100
    earnings_min: Mapped[int | None] = mapped_column(Integer)
    earnings_max: Mapped[int | None] = mapped_column(Integer)
    earnings_median: Mapped[int | None] = mapped_column(Integer)
    earnings_basis: Mapped[str] = mapped_column(String(10), default="monthly")  # monthly | annual
    currency: Mapped[str] = mapped_column(String(5), default="INR")
    sample_size: Mapped[int | None] = mapped_column(Integer)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    data_status: Mapped[str] = mapped_column(String(20), default="demo")
    verified_on: Mapped[str | None] = mapped_column(String(20))

    trade: Mapped[Trade] = relationship()
    source: Mapped[Source] = relationship()


class ProgressionStep(Base):
    __tablename__ = "progression_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))  # job | upskill | apprenticeship | diploma | degree
    titles: Mapped[dict] = mapped_column(JSON, default=dict)
    nsqf_level: Mapped[int | None] = mapped_column(Integer)
    entry_requirement: Mapped[dict] = mapped_column(JSON, default=dict)
    entry_min_education: Mapped[str] = mapped_column(String(20), default="class_10")
    duration_months: Mapped[int | None] = mapped_column(Integer)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))


class CostSupport(Base):
    __tablename__ = "costs_support"
    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"), index=True)
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    fee_min: Mapped[int | None] = mapped_column(Integer)
    fee_max: Mapped[int | None] = mapped_column(Integer)
    support_type: Mapped[str] = mapped_column(String(20))  # scheme | stipend | scholarship | none
    description: Mapped[dict] = mapped_column(JSON, default=dict)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    data_status: Mapped[str] = mapped_column(String(20), default="demo")
    # Optional: income brackets this support targets (empty = all)
    income_brackets: Mapped[list] = mapped_column(JSON, default=list)

    source: Mapped[Source] = relationship()


# ---------------------------------------------------------------- engagement layer
class SessionRow(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    language: Mapped[str] = mapped_column(String(5), default="en")
    district: Mapped[str] = mapped_column(String(80), index=True)
    income_bracket: Mapped[str | None] = mapped_column(String(30))
    learner_education: Mapped[str] = mapped_column(String(20))
    learner_interests: Mapped[list] = mapped_column(JSON, default=list)
    top_concerns: Mapped[list] = mapped_column(JSON, default=list)
    mood_pre_learner: Mapped[int | None] = mapped_column(Integer)
    mood_pre_parent: Mapped[int | None] = mapped_column(Integer)
    mood_post_learner: Mapped[int | None] = mapped_column(Integer)
    mood_post_parent: Mapped[int | None] = mapped_column(Integer)
    helper_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    # How the family took part (Update 2): together | two_devices | learner_only. All parent data is
    # self-identified; two_devices sessions are the strongest signal that the parent really answered.
    participation_mode: Mapped[str] = mapped_column(String(20), default="together", server_default="together", index=True)
    family_code: Mapped[str | None] = mapped_column(String(4), index=True)
    family_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_language: Mapped[str | None] = mapped_column(String(5))
    # The learner's own goal, in their words (Update 3), and the parent's hope for the child. The text is saved
    # exactly as given, even when nothing in the database matches it.
    aspiration_text: Mapped[str | None] = mapped_column(Text)
    aspiration_language: Mapped[str | None] = mapped_column(String(5))
    aspiration_source: Mapped[str | None] = mapped_column(String(10))  # voice | text | browse | quiz
    matched_trade_slugs: Mapped[list] = mapped_column(JSON, default=list)
    match_confidence: Mapped[float | None] = mapped_column(Float)
    aspiration_category: Mapped[str | None] = mapped_column(String(20))  # vocational_match | degree_career | professional_course | unknown
    aspiration_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    parent_hope_text: Mapped[str | None] = mapped_column(Text)
    parent_hope_language: Mapped[str | None] = mapped_column(String(5))
    parent_hope_source: Mapped[str | None] = mapped_column(String(10))
    parent_hope_matched_trade_slugs: Mapped[list] = mapped_column(JSON, default=list)
    parent_hope_match_confidence: Mapped[float | None] = mapped_column(Float)
    parent_hope_category: Mapped[str | None] = mapped_column(String(20))
    parent_hope_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(12))  # user | assistant | counsellor
    speaker: Mapped[str] = mapped_column(String(12))  # learner | parent | helper | bot | counsellor
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(5))
    concern_category: Mapped[str | None] = mapped_column(String(30))
    sentiment: Mapped[int | None] = mapped_column(Integer)  # -2..2 (model-estimated)
    sentiment_confidence: Mapped[float | None] = mapped_column(Float)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    cards: Mapped[list] = mapped_column(JSON, default=list)
    guardrail_status: Mapped[str] = mapped_column(String(12), default="na")  # pass|regenerated|fallback|na
    # Random per-device id (no personal data) so two-device sessions can tell the phones apart.
    device_id: Mapped[str | None] = mapped_column(String(40))
    # Which LLM provider produced a bot reply (sarvam | gemini | anthropic | mock); NULL for other messages.
    llm_provider: Mapped[str | None] = mapped_column(String(20))
    # True for messages exchanged in the live counsellor room (kept out of the LLM history).
    live: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AlignmentResponse(Base):
    __tablename__ = "alignment_responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    respondent: Mapped[str] = mapped_column(String(10))  # learner | parent
    ranking: Mapped[list] = mapped_column(JSON)
    device_id: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EvidenceGap(Base):
    __tablename__ = "evidence_gaps"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    trade_slug: Mapped[str | None] = mapped_column(String(80), index=True)
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    concern_category: Mapped[str | None] = mapped_column(String(30))
    tool_name: Mapped[str] = mapped_column(String(60))
    query: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Escalation(Base):
    __tablename__ = "escalations"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    trigger: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    summary_en: Mapped[str] = mapped_column(Text)            # always English, for the counsellor
    summary_local: Mapped[str] = mapped_column(Text)         # in the session language
    summary_language: Mapped[str] = mapped_column(String(5), default="en")
    assigned_to: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CallbackRequest(Base):
    __tablename__ = "callback_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    escalation_id: Mapped[int] = mapped_column(ForeignKey("escalations.id", ondelete="CASCADE"), index=True)
    phone_encrypted: Mapped[str | None] = mapped_column(Text)
    preferred_time: Mapped[str | None] = mapped_column(String(40))
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class GuardrailLog(Base):
    """Every guardrail trigger (regenerate or fallback), for audit."""
    __tablename__ = "guardrail_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))
    reply_text: Mapped[str] = mapped_column(Text)
    unmatched: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
