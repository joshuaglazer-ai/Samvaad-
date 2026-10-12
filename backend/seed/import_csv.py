"""Import organiser placement/earnings data into the outcomes table.

    python -m seed.import_csv --file data.csv --mapping mapping.yaml --status demo|verified|historical [--dry-run]

Every row is validated. Rejected rows go to import_errors.csv with reasons. Missing values are left
empty — the importer never guesses.
"""
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.config import DISTRICTS
from app.data_tools import normalise_district

STATUSES = {"demo", "verified", "historical"}
EARNING_UNITS = {
    # unit → (multiplier to rupees, basis)
    "monthly": (1, "monthly"),
    "annual": (1, "annual"),
    "monthly_thousand": (1000, "monthly"),
    "annual_lakh": (100000, "annual"),
}


@dataclass
class ImportReport:
    accepted: int = 0
    rejected: int = 0
    errors: list[dict] = field(default_factory=list)
    providers_created: int = 0


def _num(raw: Any) -> float | None:
    """Parse a number like '12,000', '₹ 12000', '12k', '1.2 lakh'. Empty → None. Invalid → ValueError."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() in {"na", "n/a", "-", "null", "none"}:
        return None
    s = s.replace("₹", "").replace(",", "").replace("Rs.", "").replace("Rs", "").replace("%", "").strip()
    mult = 1.0
    low = s.lower()
    if low.endswith("lakh") or low.endswith("lac"):
        mult, s = 100000, re.sub(r"(lakh|lac)$", "", low).strip()
    elif low.endswith("k"):
        mult, s = 1000, low[:-1].strip()
    return float(s) * mult


def _year(raw: Any) -> int:
    s = str(raw or "").strip()
    mt = re.search(r"(19|20)\d{2}", s)
    if not mt:
        raise ValueError(f"year '{s}' is not a year")
    return int(mt.group(0))


def convert_earnings(value: float | None, unit: str, output_basis: str) -> int | None:
    if value is None:
        return None
    mult, basis = EARNING_UNITS[unit]
    rupees = value * mult
    if basis == "annual" and output_basis == "monthly":
        rupees /= 12
    elif basis == "monthly" and output_basis == "annual":
        rupees *= 12
    return int(round(rupees))


def resolve_trade(db: Session, name: str, aliases: dict[str, str]) -> m.Trade | None:
    key = (name or "").strip()
    if not key:
        return None
    slug = aliases.get(key) or re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
    row = db.scalar(select(m.Trade).where(m.Trade.slug == slug))
    if row:
        return row
    return db.scalar(select(m.Trade).where(m.Trade.name_en.ilike(key)))


def validate_mapping(mapping: dict) -> None:
    cols = mapping.get("columns") or {}
    for req in ("trade", "year"):
        if not cols.get(req):
            raise SystemExit(f"mapping.columns.{req} is required")
    units = mapping.get("units") or {}
    if units.get("earnings", "monthly") not in EARNING_UNITS:
        raise SystemExit(f"units.earnings must be one of {sorted(EARNING_UNITS)}")
    if units.get("output_basis", "monthly") not in {"monthly", "annual"}:
        raise SystemExit("units.output_basis must be monthly or annual")
    if units.get("placement_rate", "percent") not in {"percent", "fraction"}:
        raise SystemExit("units.placement_rate must be percent or fraction")


def import_rows(db: Session, rows: list[dict], mapping: dict, status: str,
                source_label: str = "import") -> ImportReport:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")
    validate_mapping(mapping)
    cols = mapping["columns"]
    units = mapping.get("units") or {}
    e_unit = units.get("earnings", "monthly")
    out_basis = units.get("output_basis", "monthly")
    rate_unit = units.get("placement_rate", "percent")
    trade_aliases = mapping.get("trade_aliases") or {}
    district_aliases = mapping.get("district_aliases") or {}
    src_cfg = mapping.get("source") or {}
    state = (mapping.get("defaults") or {}).get("state", "Karnataka")

    source = m.Source(
        title=src_cfg.get("title") or f"Imported dataset ({source_label})",
        url=src_cfg.get("url"), publisher=src_cfg.get("publisher"),
        reporting_period=src_cfg.get("reporting_period"),
        verified_on=date.today().isoformat() if status == "verified" else None,
        notes=f"Imported by seed/import_csv.py from {source_label} with status={status}",
    )
    db.add(source)
    db.flush()

    report = ImportReport()

    def get(row: dict, key: str) -> Any:
        col = cols.get(key)
        return row.get(col) if col else None

    for i, row in enumerate(rows, start=2):  # header is line 1
        reasons: list[str] = []
        trade = resolve_trade(db, get(row, "trade"), trade_aliases)
        if not trade:
            reasons.append(f"unknown trade '{get(row, 'trade')}'")

        raw_d = (get(row, "district") or "").strip()
        district = normalise_district(district_aliases.get(raw_d, raw_d)) if raw_d else None
        if district and district not in DISTRICTS:
            reasons.append(f"district '{raw_d}' is outside the pilot districts")
        geo = (get(row, "geo_level") or "").strip().lower() or ("district" if district else "state")
        if geo not in {"district", "state", "national"}:
            reasons.append(f"geo_level '{geo}' invalid")
        if geo == "district" and not district:
            reasons.append("geo_level is district but district is empty")

        year = None
        try:
            year = _year(get(row, "year"))
        except ValueError as exc:
            reasons.append(str(exc))

        def parse(key: str) -> float | None:
            try:
                v = _num(get(row, key))
            except ValueError:
                reasons.append(f"{key} '{get(row, key)}' is not a number")
                return None
            if v is not None and v < 0:
                reasons.append(f"{key} is negative")
            return v

        placed, trained = parse("placed"), parse("trained")
        rate_raw = parse("placement_rate")
        e_min, e_max, e_med = parse("earnings_min"), parse("earnings_max"), parse("earnings_median")
        sample = parse("sample_size")

        rate = None
        if placed is not None and trained is not None:
            if trained == 0:
                reasons.append("trained (denominator) is zero")
            elif placed > trained:
                reasons.append("placed is greater than trained")
            else:
                rate = round(100 * placed / trained, 1)
        elif rate_raw is not None:
            rate = rate_raw * 100 if rate_unit == "fraction" else rate_raw
            if not 0 <= rate <= 100:
                reasons.append(f"placement rate {rate_raw} out of range")
        e_min_c = convert_earnings(e_min, e_unit, out_basis)
        e_max_c = convert_earnings(e_max, e_unit, out_basis)
        e_med_c = convert_earnings(e_med, e_unit, out_basis)
        if e_min_c is not None and e_max_c is not None and e_min_c > e_max_c:
            reasons.append("earnings_min is greater than earnings_max")
        if e_med_c is not None and ((e_min_c is not None and e_med_c < e_min_c) or
                                    (e_max_c is not None and e_med_c > e_max_c)):
            reasons.append("earnings_median is outside min-max")
        if rate is None and e_min_c is None and e_max_c is None and e_med_c is None:
            reasons.append("row has no placement or earnings figure")

        if reasons:
            report.rejected += 1
            report.errors.append({"line": i, "reasons": "; ".join(reasons), **row})
            continue

        provider_id = None
        pname = (get(row, "provider") or "").strip()
        if pname:
            prov = db.scalar(select(m.Provider).where(m.Provider.name == pname, m.Provider.district == district))
            if not prov:
                prov = m.Provider(name=pname, district=district or "", state=state, provider_type="imported",
                                  accreditation=None, data_status=status, trades=[])
                db.add(prov)
                db.flush()
                report.providers_created += 1
            if trade.slug not in (prov.trades or []):
                prov.trades = [*(prov.trades or []), trade.slug]
            provider_id = prov.id

        period = (get(row, "reporting_period") or "").strip() or src_cfg.get("reporting_period") or str(year)
        db.add(m.Outcome(
            trade_id=trade.id, provider_id=provider_id, geo_level=geo,
            district=district if geo == "district" else None, year=year, reporting_period=period,
            placement_numerator=int(placed) if placed is not None else None,
            placement_denominator=int(trained) if trained is not None else None,
            placement_rate=rate, earnings_min=e_min_c, earnings_max=e_max_c, earnings_median=e_med_c,
            earnings_basis=out_basis, currency="INR",
            sample_size=int(sample) if sample is not None else (int(trained) if trained is not None else None),
            source_id=source.id, data_status=status,
            verified_on=source.verified_on,
        ))
        report.accepted += 1
    return report


def write_errors(errors: list[dict], path: Path) -> None:
    if not errors:
        return
    keys: list[str] = []
    for e in errors:
        keys.extend(k for k in e if k not in keys)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(errors)


def main() -> None:
    from app.db import SessionLocal
    from app.schema_setup import upgrade_to_head

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True)
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--status", required=True, choices=sorted(STATUSES))
    ap.add_argument("--errors", default="import_errors.csv")
    ap.add_argument("--dry-run", action="store_true", help="validate only; do not write to the database")
    args = ap.parse_args()

    mapping = yaml.safe_load(Path(args.mapping).read_text(encoding="utf-8"))
    with Path(args.file).open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    upgrade_to_head()
    with SessionLocal() as db:
        report = import_rows(db, rows, mapping, args.status, source_label=Path(args.file).name)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    write_errors(report.errors, Path(args.errors))
    print(f"Rows read: {len(rows)} | accepted: {report.accepted} | rejected: {report.rejected} | "
          f"providers created: {report.providers_created} | status: {args.status}"
          f"{' | DRY RUN — nothing saved' if args.dry_run else ''}")
    if report.errors:
        print(f"Rejected rows with reasons written to {args.errors}")


if __name__ == "__main__":
    main()
