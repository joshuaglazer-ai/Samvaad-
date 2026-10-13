"""Import sectors, trades and trade synonyms from CSV (Update 3) — used by `import_csv.py --kind ...`.

    python -m seed.import_csv --kind sectors  --file sectors.csv  --mapping seed/mapping.catalogue.example.yaml
    python -m seed.import_csv --kind trades   --file trades.csv   --mapping ... --status unavailable|demo|verified|historical
    python -m seed.import_csv --kind synonyms --file synonyms.csv --mapping ...

Rows are upserted by slug (sectors, trades) or by (trade, language, term) (synonyms). Translations are columns such
as name_en / name_kn / name_hi / name_te; English is required, other languages may be blank (they fall back to
English in the app, logged). A trade can only be verified/historical when the mapping names a source. Rejected rows
go to the errors file with reasons; nothing is guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.config import EDUCATION_LEVELS
from app.i18n import LANGS

KINDS = ("sectors", "trades", "synonyms")
TRADE_STATUSES = ("unavailable", "demo", "verified", "historical")
TRAITS = ("hands", "people", "machines", "outdoors", "computers")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class CatalogueReport:
    created: int = 0
    updated: int = 0
    rejected: int = 0
    errors: list[dict] = field(default_factory=list)

    @property
    def accepted(self) -> int:
        return self.created + self.updated


def _get(row: dict, cols: dict, key: str) -> str:
    col = cols.get(key)
    return (row.get(col) or "").strip() if col else ""


def _langs(row: dict, cols: dict, prefix: str) -> dict[str, str]:
    return {lang: v for lang in LANGS if (v := _get(row, cols, f"{prefix}_{lang}"))}


def _int(raw: str, lo: int, hi: int, name: str) -> int:
    try:
        v = int(float(raw))
    except ValueError as exc:
        raise ValueError(f"{name} is not a number: {raw!r}") from exc
    if not lo <= v <= hi:
        raise ValueError(f"{name} must be {lo}–{hi}")
    return v


def _source(db: Session, mapping: dict) -> m.Source | None:
    spec = mapping.get("source") or {}
    if not spec.get("title"):
        return None
    src = db.scalar(select(m.Source).where(m.Source.title == spec["title"]))
    if not src:
        src = m.Source(title=spec["title"], publisher=spec.get("publisher"), url=spec.get("url"),
                       reporting_period=spec.get("reporting_period"), verified_on=spec.get("verified_on"))
        db.add(src)
        db.flush()
    return src


def _sector(db: Session, row: dict, cols: dict) -> bool:
    slug = _get(row, cols, "slug")
    if not SLUG.match(slug):
        raise ValueError(f"slug must be lowercase words joined by hyphens: {slug!r}")
    names = _langs(row, cols, "name")
    if not names.get("en"):
        raise ValueError("name_en is required")
    icon = _get(row, cols, "icon") or "tool"
    order = _int(_get(row, cols, "sort_order") or "0", 0, 999, "sort_order")
    s = db.scalar(select(m.Sector).where(m.Sector.slug == slug))
    if s:
        s.names, s.icon, s.sort_order = {**(s.names or {}), **names}, icon, order
        return False
    db.add(m.Sector(slug=slug, names=names, icon=icon, sort_order=order))
    return True


def _trade(db: Session, row: dict, cols: dict, status: str, src: m.Source | None) -> bool:
    slug = _get(row, cols, "slug")
    if not SLUG.match(slug):
        raise ValueError(f"slug must be lowercase words joined by hyphens: {slug!r}")
    sector = _get(row, cols, "sector")
    if not db.scalar(select(m.Sector).where(m.Sector.slug == sector)):
        raise ValueError(f"unknown sector {sector!r} (import sectors first)")
    names = _langs(row, cols, "name")
    if not names.get("en"):
        raise ValueError("name_en is required")
    edu = _get(row, cols, "entry_min_education") or "class_10"
    if edu not in EDUCATION_LEVELS:
        raise ValueError(f"entry_min_education must be one of {EDUCATION_LEVELS}")
    traits = [t.strip() for t in re.split(r"[;,|]", _get(row, cols, "traits")) if t.strip()]
    if bad := [t for t in traits if t not in TRAITS]:
        raise ValueError(f"unknown traits {bad}; use {list(TRAITS)}")
    row_status = _get(row, cols, "data_status") or status
    if row_status not in TRADE_STATUSES:
        raise ValueError(f"data_status must be one of {list(TRADE_STATUSES)}")
    if row_status in ("verified", "historical") and not src:
        raise ValueError("a verified/historical trade needs a source in the mapping")
    fields: dict[str, Any] = dict(
        sector=sector, nsqf_level=_int(_get(row, cols, "nsqf_level"), 1, 10, "nsqf_level"),
        duration_months=_int(_get(row, cols, "duration_months"), 1, 60, "duration_months"),
        entry_min_education=edu, entry_requirement=_langs(row, cols, "entry_requirement"),
        icon=_get(row, cols, "icon") or "tool", traits=traits, data_status=row_status,
        source_id=src.id if src else None,
    )
    t = db.scalar(select(m.Trade).where(m.Trade.slug == slug))
    if t:
        t.names = {**(t.names or {}), **names}
        for k, v in fields.items():
            setattr(t, k, v)
        return False
    db.add(m.Trade(slug=slug, names=names, job_roles={}, **fields))
    return True


def _synonym(db: Session, row: dict, cols: dict) -> bool:
    from .import_csv import resolve_trade

    trade = resolve_trade(db, _get(row, cols, "trade"), {})
    if not trade:
        raise ValueError(f"unknown trade {_get(row, cols, 'trade')!r}")
    lang = _get(row, cols, "language")
    if lang not in LANGS:
        raise ValueError(f"language must be one of {list(LANGS)}")
    term = " ".join(_get(row, cols, "term").split())
    if not term or len(term) > 120:
        raise ValueError("term is required (at most 120 characters)")
    review = _get(row, cols, "review_status") or "needs_native_review"
    if review not in ("needs_native_review", "reviewed"):
        raise ValueError("review_status must be needs_native_review or reviewed")
    s = db.scalar(select(m.TradeSynonym).where(m.TradeSynonym.trade_id == trade.id, m.TradeSynonym.language == lang,
                                               m.TradeSynonym.term == term))
    if s:
        s.review_status = review
        return False
    db.add(m.TradeSynonym(trade_id=trade.id, language=lang, term=term, review_status=review))
    return True


def import_catalogue(db: Session, kind: str, rows: list[dict], mapping: dict,
                     status: str = "unavailable") -> CatalogueReport:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    cols = (mapping.get(kind) or {}).get("columns") or {}
    required = {"sectors": ["slug", "name_en"], "trades": ["slug", "sector", "name_en", "nsqf_level",
                                                          "duration_months"],
                "synonyms": ["trade", "language", "term"]}[kind]
    if missing := [k for k in required if not cols.get(k)]:
        raise SystemExit(f"mapping.{kind}.columns needs {missing}")
    src = _source(db, mapping) if kind == "trades" else None
    report = CatalogueReport()
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            # Each handler validates the whole row before adding anything, so a rejected row writes nothing.
            # (No SAVEPOINT: on SQLite, releasing one would commit, which broke --dry-run.)
            created = {"sectors": lambda: _sector(db, row, cols),
                       "trades": lambda: _trade(db, row, cols, status, src),
                       "synonyms": lambda: _synonym(db, row, cols)}[kind]()
            db.flush()
            report.created += created
            report.updated += not created
        except ValueError as exc:
            report.rejected += 1
            report.errors.append({"row": i, "reason": str(exc), **row})
    return report
