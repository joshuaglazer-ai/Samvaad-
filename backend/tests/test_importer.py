import csv
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select

from app import models as m
from app.data_tools import DataTools
from seed.import_csv import _num, convert_earnings, import_rows, write_errors

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def load_sample():
    mapping = yaml.safe_load((SEED_DIR / "mapping.example.yaml").read_text(encoding="utf-8"))
    with (SEED_DIR / "sample_organiser_data.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return mapping, rows


def test_number_parsing():
    assert _num("12,000") == 12000
    assert _num("₹ 15000") == 15000
    assert _num("12k") == 12000
    assert _num("1.2 lakh") == 120000
    assert _num("") is None and _num("NA") is None
    with pytest.raises(ValueError):
        _num("abc")


def test_unit_conversions():
    assert convert_earnings(180000, "annual", "monthly") == 15000
    assert convert_earnings(1.8, "annual_lakh", "monthly") == 15000
    assert convert_earnings(15, "monthly_thousand", "monthly") == 15000
    assert convert_earnings(15000, "monthly", "annual") == 180000


def test_sample_import_accepts_and_rejects(db, tmp_path):
    mapping, rows = load_sample()
    report = import_rows(db, rows, mapping, "verified", source_label="sample.csv")
    db.commit()
    assert report.accepted == 3
    assert report.rejected == 5
    reasons = " | ".join(e["reasons"] for e in report.errors)
    assert "unknown trade 'Plumber'" in reasons
    assert "outside the pilot districts" in reasons
    assert "placed is greater than trained" in reasons
    assert "no placement or earnings figure" in reasons
    assert "earnings_min is greater than earnings_max" in reasons

    out = tmp_path / "errs.csv"
    write_errors(report.errors, out)
    assert out.read_text(encoding="utf-8").count("\n") == 6  # header + 5 rows


def test_imported_rows_are_verified_and_never_guessed(db):
    mapping, rows = load_sample()
    import_rows(db, rows, mapping, "verified")
    db.commit()
    imported = list(db.scalars(select(m.Outcome).where(m.Outcome.data_status == "verified")))
    gda = next(o for o in imported if o.trade.slug == "general-duty-assistant")
    assert gda.district == "Kalaburagi" and gda.year == 2023
    assert gda.placement_rate == pytest.approx(66.7)
    solar = next(o for o in imported if o.trade.slug == "solar-pv-installer")
    assert solar.placement_numerator is None and solar.placement_rate == 71  # rate used only as given
    assert solar.sample_size == 95
    # Imported provider is linked and inherits the status
    prov = db.scalar(select(m.Provider).where(m.Provider.name == "Sample Organiser ITI Mysuru"))
    assert prov.data_status == "verified" and "electrician" in prov.trades


def test_mapping_requires_trade_column(db):
    with pytest.raises(SystemExit):
        import_rows(db, [], {"columns": {"year": "Y"}}, "demo")


def test_bad_status_rejected(db):
    mapping, rows = load_sample()
    with pytest.raises(ValueError):
        import_rows(db, rows, mapping, "real")


def test_imported_data_visible_through_tools(db):
    mapping, rows = load_sample()
    import_rows(db, rows, mapping, "verified")
    db.commit()
    r = DataTools(db).get_trade_outcomes("general-duty-assistant", "Kalaburagi")
    assert r["records"][0]["year"] == 2025  # newer years still win on recency
    fy23 = [rec for rec in r["records"] if rec["year"] == 2023]
    assert fy23 and fy23[0]["data_status"] == "verified"  # same year: verified beats demo
