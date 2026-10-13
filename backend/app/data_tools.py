"""The ONLY place outcome figures are queried (Rule 1).

Every tool returns a dict with: found, records, geo_level_used, data_status, source, limitations.
On found=False an evidence_gaps row is written so administrators can see unanswered requests.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .config import DISTRICTS, STATE
from .i18n import norm_lang, tr

GEO_ORDER = ["district", "state", "national"]
# For the same year and place, prefer better evidence.
STATUS_PRIORITY = {"verified": 0, "historical": 1, "demo": 2, "unavailable": 3}

LIMITATION_TEXT = {
    "state_fallback": {
        "en": "District data is not available; showing the state figure.",
        "kn": "ಜಿಲ್ಲಾ ಮಟ್ಟದ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ; ರಾಜ್ಯ ಮಟ್ಟದ ಅಂಕಿಯನ್ನು ತೋರಿಸಲಾಗಿದೆ.",
    },
    "national_fallback": {
        "en": "District and state data are not available; showing the national figure.",
        "kn": "ಜಿಲ್ಲಾ ಮತ್ತು ರಾಜ್ಯ ಮಟ್ಟದ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ; ರಾಷ್ಟ್ರ ಮಟ್ಟದ ಅಂಕಿಯನ್ನು ತೋರಿಸಲಾಗಿದೆ.",
    },
    "demo": {"en": "Demo data — for testing only.", "kn": "ಡೆಮೊ ಮಾಹಿತಿ — ಪರೀಕ್ಷೆಗೆ ಮಾತ್ರ."},
    "historical": {
        "en": "This is older (historical) data.",
        "kn": "ಇದು ಹಳೆಯ ಮಾಹಿತಿ.",
    },
    "older_year": {
        "en": "The latest year is not available here; showing an earlier year.",
        "kn": "ಇತ್ತೀಚಿನ ವರ್ಷದ ಮಾಹಿತಿ ಇಲ್ಲ; ಹಿಂದಿನ ವರ್ಷದ ಅಂಕಿ ತೋರಿಸಲಾಗಿದೆ.",
    },
    "no_data": {
        "en": "No data is available for this yet.",
        "kn": "ಇದಕ್ಕೆ ಇನ್ನೂ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ.",
    },
    "income_unknown": {
        "en": "Eligibility for support depends on family income.",
        "kn": "ನೆರವಿನ ಅರ್ಹತೆ ಕುಟುಂಬದ ಆದಾಯವನ್ನು ಅವಲಂಬಿಸಿದೆ.",
    },
}

# Which learner education levels satisfy a step's minimum requirement.
SATISFIES = {
    "class_8": {"class_8", "class_10", "class_12", "iti", "diploma", "graduate"},
    "class_10": {"class_10", "class_12", "iti", "diploma", "graduate"},
    "class_12": {"class_12", "diploma", "graduate"},
    "iti": {"iti", "diploma", "graduate"},
    "diploma": {"diploma", "graduate"},
    "graduate": {"graduate"},
}

from .lang_text import LIMITATION_TEXT as _LT  # noqa: E402

for _code, _texts in _LT.items():
    LIMITATION_TEXT[_code].update(_texts)

DISTRICT_ALIASES = {
    "bengaluru": "Bengaluru Urban", "bangalore": "Bengaluru Urban", "bengaluru urban": "Bengaluru Urban",
    "ಬೆಂಗಳೂರು": "Bengaluru Urban", "ಬೆಂಗಳೂರು ನಗರ": "Bengaluru Urban",
    "mysuru": "Mysuru", "mysore": "Mysuru", "ಮೈಸೂರು": "Mysuru",
    "kalaburagi": "Kalaburagi", "gulbarga": "Kalaburagi", "ಕಲಬುರಗಿ": "Kalaburagi",
    "dharwad": "Dharwad", "hubli-dharwad": "Dharwad", "ಧಾರವಾಡ": "Dharwad",
    "बेंगलुरु": "Bengaluru Urban", "मैसूरु": "Mysuru", "मैसूर": "Mysuru", "कलबुर्गी": "Kalaburagi", "धारवाड़": "Dharwad",
    "బెంగళూరు": "Bengaluru Urban", "మైసూరు": "Mysuru", "కలబురగి": "Kalaburagi", "ధార్వాడ్": "Dharwad",
}


def normalise_district(d: str | None) -> str | None:
    if not d:
        return None
    if d in DISTRICTS:
        return d
    return DISTRICT_ALIASES.get(d.strip().lower(), d.strip())


def satisfies(learner_education: str | None, requirement: str) -> bool | None:
    if not learner_education or learner_education == "other":
        return None
    return learner_education in SATISFIES.get(requirement, set())


def limitation_texts(codes: list[str], language: str) -> list[str]:
    return [tr(LIMITATION_TEXT[c], language, f"limitation.{c}") for c in codes if c in LIMITATION_TEXT]


@dataclass
class ToolContext:
    db: Session
    session_id: str | None = None
    language: str = "en"
    concern: str | None = None
    found_false_count: int = 0
    calls: list[dict] = field(default_factory=list)


class DataTools:
    """Data tools bound to a DB session and (optionally) a chat session for gap logging."""

    def __init__(self, db: Session, session_id: str | None = None, language: str = "en",
                 concern: str | None = None):
        self.ctx = ToolContext(db=db, session_id=session_id, language=norm_lang(language), concern=concern)

    @property
    def db(self) -> Session:
        return self.ctx.db

    # ------------------------------------------------------------------ helpers
    def _name(self, t: m.Trade) -> str:
        return tr(t.names, self.ctx.language, f"trade.{t.slug}.names")

    def resolve_trade(self, trade: str | None) -> m.Trade | None:
        if not trade:
            return None
        key = trade.strip()
        slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
        row = self.db.scalar(select(m.Trade).where(m.Trade.slug == slug))
        if row:
            return row
        for t in self.db.scalars(select(m.Trade)):
            names = [n for n in (t.names or {}).values() if n]
            en = (t.names or {}).get("en", "")
            if key.lower() in [n.lower() for n in names] or slug == re.sub(r"[^a-z0-9]+", "-", en.lower()):
                return t
        return None

    def _gap(self, tool: str, trade_slug: str | None, district: str | None, query: dict) -> None:
        self.ctx.found_false_count += 1
        self.db.add(m.EvidenceGap(
            session_id=self.ctx.session_id, trade_slug=trade_slug, district=district,
            concern_category=self.ctx.concern, tool_name=tool, query=query,
        ))
        self.db.flush()

    @staticmethod
    def _source(src: m.Source | None) -> dict | None:
        if not src:
            return None
        return {"title": src.title, "url": src.url, "publisher": src.publisher,
                "reporting_period": src.reporting_period, "verified_on": src.verified_on}

    def _not_found(self, tool: str, trade_slug: str | None, district: str | None, query: dict,
                   extra: dict | None = None) -> dict:
        self._gap(tool, trade_slug, district, query)
        out = {"found": False, "records": [], "geo_level_used": None, "data_status": "unavailable",
               "source": None, "limitations": limitation_texts(["no_data"], self.ctx.language),
               "limitation_codes": ["no_data"], "query": query}
        if extra:
            out.update(extra)
        return out

    # ------------------------------------------------------------------ tools
    def list_trades(self, sector: str | None = None, language: str | None = None) -> dict:
        if language:
            self.ctx.language = norm_lang(language)
        q = select(m.Trade).order_by(m.Trade.sector, m.Trade.slug)
        if sector:
            q = q.where(m.Trade.sector.ilike(sector))
        trades = list(self.db.scalars(q))
        if not trades:
            return self._not_found("list_trades", None, None, {"sector": sector})
        records = [{
            "slug": t.slug, "name": self._name(t), "name_en": tr(t.names, "en"), "names": t.names,
            "sector": t.sector, "nsqf_level": t.nsqf_level, "duration_months": t.duration_months,
            "entry_requirement": tr(t.entry_requirement, self.ctx.language, f"trade.{t.slug}.entry_requirement"),
            "job_roles": tr(t.job_roles, self.ctx.language, f"trade.{t.slug}.job_roles"),
            "icon": t.icon,
        } for t in trades]
        return {"found": True, "records": records, "geo_level_used": None, "data_status": "demo",
                "source": None, "limitations": [], "limitation_codes": []}

    def get_trade_outcomes(self, trade_slug: str, district: str | None = None) -> dict:
        district = normalise_district(district)
        query = {"trade_slug": trade_slug, "district": district}
        trade = self.resolve_trade(trade_slug)
        if not trade:
            return self._not_found("get_trade_outcomes", trade_slug, district, query)

        for level in GEO_ORDER:
            q = select(m.Outcome).where(m.Outcome.trade_id == trade.id, m.Outcome.geo_level == level)
            if level == "district":
                if not district:
                    continue
                q = q.where(m.Outcome.district == district)
            rows = sorted(self.db.scalars(q), key=lambda r: (-r.year, STATUS_PRIORITY.get(r.data_status, 9)))
            if not rows:
                continue
            codes: list[str] = []
            if level == "state" and district:
                codes.append("state_fallback")
            if level == "national":
                codes.append("national_fallback")
            latest_year_any = self.db.scalar(
                select(m.Outcome.year).where(m.Outcome.trade_id == trade.id).order_by(m.Outcome.year.desc()).limit(1))
            if rows[0].year < (latest_year_any or rows[0].year):
                codes.append("older_year")
            statuses = {r.data_status for r in rows}
            if "demo" in statuses:
                codes.append("demo")
            if "historical" in statuses:
                codes.append("historical")
            latest = rows[0]
            return {
                "found": True,
                "trade_slug": trade.slug,
                "trade_name": self._name(trade),
                "district_requested": district,
                "geo_level_used": level,
                "data_status": latest.data_status,
                "source": self._source(latest.source),
                "limitations": limitation_texts(codes, self.ctx.language),
                "limitation_codes": codes,
                "records": [self._outcome_record(r, trade) for r in rows[:3]],
            }
        return self._not_found("get_trade_outcomes", trade.slug, district, query)

    def _outcome_record(self, r: m.Outcome, trade: m.Trade) -> dict:
        return {
            "trade_slug": trade.slug, "trade_name": self._name(trade),
            "year": r.year, "reporting_period": r.reporting_period, "geo_level": r.geo_level,
            "district": r.district if r.geo_level == "district" else None,
            "state": STATE if r.geo_level != "national" else None,
            "placement_rate": r.placement_rate, "placement_numerator": r.placement_numerator,
            "placement_denominator": r.placement_denominator,
            "earnings_min": r.earnings_min, "earnings_max": r.earnings_max,
            "earnings_median": r.earnings_median, "earnings_basis": r.earnings_basis,
            "currency": r.currency, "sample_size": r.sample_size, "data_status": r.data_status,
            "source_title": r.source.title if r.source else None,
        }

    def get_progression(self, trade_slug: str, education_level: str | None = None) -> dict:
        query = {"trade_slug": trade_slug, "education_level": education_level}
        trade = self.resolve_trade(trade_slug)
        if not trade:
            return self._not_found("get_progression", trade_slug, None, query)
        steps = list(self.db.scalars(
            select(m.ProgressionStep).where(m.ProgressionStep.trade_id == trade.id)
            .order_by(m.ProgressionStep.step_order)))
        if not steps:
            return self._not_found("get_progression", trade.slug, None, query)
        lang = self.ctx.language
        src = self.db.get(m.Source, steps[0].source_id) if steps[0].source_id else None
        records = [{
            "step_order": s.step_order, "kind": s.kind,
            "title": tr(s.titles, lang, f"step.{trade.slug}.{s.step_order}.title"),
            "nsqf_level": s.nsqf_level,
            "entry_requirement": tr(s.entry_requirement, lang, f"step.{trade.slug}.{s.step_order}.entry_requirement"),
            "duration_months": s.duration_months,
            "eligible": bool(satisfies(education_level, s.entry_min_education)),
        } for s in steps]
        return {
            "found": True, "trade_slug": trade.slug, "trade_name": self._name(trade),
            "trade_nsqf_level": trade.nsqf_level, "trade_duration_months": trade.duration_months,
            "trade_entry_requirement": tr(trade.entry_requirement, lang, f"trade.{trade.slug}.entry_requirement"),
            "can_start_training": satisfies(education_level, trade.entry_min_education),
            "education_level": education_level,
            # Ladders currently come only from the demo seed (the importer covers outcomes).
            "geo_level_used": None, "data_status": "demo",
            "source": self._source(src),
            "limitations": limitation_texts(["demo"], self.ctx.language), "limitation_codes": ["demo"],
            "records": records,
        }

    def get_providers(self, trade_slug: str, district: str) -> dict:
        district = normalise_district(district)
        query = {"trade_slug": trade_slug, "district": district}
        trade = self.resolve_trade(trade_slug)
        if not trade:
            return self._not_found("get_providers", trade_slug, district, query)
        offering = [p for p in self.db.scalars(select(m.Provider)) if trade.slug in (p.trades or [])]
        here = [p for p in offering if p.district == district]
        if not here:
            other = sorted({p.district for p in offering})
            return self._not_found("get_providers", trade.slug, district, query,
                                   {"trade_name": self._name(trade), "other_districts": other})
        statuses = {p.data_status for p in here}
        codes = ["demo"] if "demo" in statuses else []
        return {
            "found": True, "trade_slug": trade.slug, "trade_name": self._name(trade),
            "geo_level_used": "district", "data_status": "demo" if "demo" in statuses else here[0].data_status,
            "source": None, "limitations": limitation_texts(codes, self.ctx.language), "limitation_codes": codes,
            "records": [{"name": p.name, "district": p.district, "provider_type": p.provider_type,
                         "accreditation": p.accreditation, "data_status": p.data_status} for p in here],
        }

    def get_costs_and_support(self, trade_slug: str, district: str | None = None,
                              income_bracket: str | None = None) -> dict:
        district = normalise_district(district)
        query = {"trade_slug": trade_slug, "district": district, "income_bracket": income_bracket}
        trade = self.resolve_trade(trade_slug)
        if not trade:
            return self._not_found("get_costs_and_support", trade_slug, district, query)
        rows = list(self.db.scalars(select(m.CostSupport).where(m.CostSupport.trade_id == trade.id)))
        if not rows:
            return self._not_found("get_costs_and_support", trade.slug, district, query,
                                   {"trade_name": self._name(trade)})
        fee_rows = [r for r in rows if r.support_type == "none"]
        district_fee = [r for r in fee_rows if district and r.district == district]
        state_fee = [r for r in fee_rows if r.district is None]
        fee = (district_fee or state_fee or [None])[0]
        geo = "district" if district_fee else "state"
        codes: list[str] = []
        if district and not district_fee:
            codes.append("state_fallback")
        known_income = income_bracket and income_bracket != "prefer_not_to_say"
        supports = []
        for r in rows:
            if r.support_type == "none" or (r.district and r.district != district):
                continue
            targeted = bool(r.income_brackets)
            if targeted and known_income and income_bracket not in r.income_brackets:
                continue
            supports.append({
                "support_type": r.support_type,
                "description": tr(r.description, self.ctx.language, f"costs.{r.id}.description"),
                "fee_min": r.fee_min, "fee_max": r.fee_max, "data_status": r.data_status,
                "depends_on_income": targeted and not known_income,
            })
        if any(s["depends_on_income"] for s in supports):
            codes.append("income_unknown")
        codes.append("demo")
        return {
            "found": True, "trade_slug": trade.slug, "trade_name": self._name(trade),
            "geo_level_used": geo, "data_status": fee.data_status if fee else "demo",
            "source": self._source(fee.source if fee else rows[0].source),
            "limitations": limitation_texts(codes, self.ctx.language), "limitation_codes": codes,
            "records": [{
                "fee_min": fee.fee_min if fee else None, "fee_max": fee.fee_max if fee else None,
                "fee_description": tr(fee.description, self.ctx.language, f"costs.{fee.id}.description") if fee else None,
                "district": fee.district if fee else None,
                "supports": supports,
            }],
        }

    # ------------------------------------------------------------------ dispatch
    def execute(self, name: str, args: dict[str, Any]) -> dict:
        fn = {
            "list_trades": self.list_trades,
            "get_trade_outcomes": self.get_trade_outcomes,
            "get_progression": self.get_progression,
            "get_providers": self.get_providers,
            "get_costs_and_support": self.get_costs_and_support,
        }.get(name)
        if fn is None:
            return {"found": False, "error": f"unknown tool {name}"}
        try:
            result = fn(**args)
        except TypeError as exc:  # bad arguments from the model
            result = {"found": False, "error": f"invalid arguments: {exc}", "records": []}
        self.ctx.calls.append({"name": name, "input": args, "found": result.get("found", False)})
        return result


# Anthropic tool definitions (JSON Schema). The `escalate` tool is handled in chat.py.
TOOL_SCHEMAS: list[dict] = [
    {
        "name": "list_trades",
        "description": "List the vocational trades available in the pilot, optionally filtered by sector. "
                       "Use when the family asks what options exist.",
        "input_schema": {"type": "object", "properties": {
            "sector": {"type": "string", "enum": ["Electrical", "Automotive", "Healthcare", "Green Energy"]},
            "language": {"type": "string", "enum": ["en", "kn", "hi", "te"]},
        }, "additionalProperties": False},
    },
    {
        "name": "get_trade_outcomes",
        "description": "Get placement rate and earnings for a trade. Falls back district → state → national and "
                       "reports geo_level_used. Call this before mentioning ANY salary or placement figure.",
        "input_schema": {"type": "object", "properties": {
            "trade_slug": {"type": "string", "description": "e.g. electrician, solar-pv-installer"},
            "district": {"type": "string"},
        }, "required": ["trade_slug"], "additionalProperties": False},
    },
    {
        "name": "get_progression",
        "description": "Get the career ladder (NSQF level-ups, apprenticeship, diploma, degree routes) for a trade, "
                       "marking steps the learner is already eligible for.",
        "input_schema": {"type": "object", "properties": {
            "trade_slug": {"type": "string"},
            "education_level": {"type": "string",
                                "enum": ["class_8", "class_10", "class_12", "iti", "diploma", "graduate", "other"]},
        }, "required": ["trade_slug"], "additionalProperties": False},
    },
    {
        "name": "get_providers",
        "description": "List training centres for a trade in a district.",
        "input_schema": {"type": "object", "properties": {
            "trade_slug": {"type": "string"}, "district": {"type": "string"},
        }, "required": ["trade_slug", "district"], "additionalProperties": False},
    },
    {
        "name": "get_costs_and_support",
        "description": "Get course fees and financial support (schemes, stipends, scholarships) for a trade, "
                       "filtered by district and the family's income bracket.",
        "input_schema": {"type": "object", "properties": {
            "trade_slug": {"type": "string"}, "district": {"type": "string"},
            "income_bracket": {"type": "string"},
        }, "required": ["trade_slug"], "additionalProperties": False},
    },
]
