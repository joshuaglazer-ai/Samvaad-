from sqlalchemy import func, select

from app import models as m
from app.data_tools import DataTools


def gap_count(db):
    return db.scalar(select(func.count()).select_from(m.EvidenceGap))


def test_all_seed_outcomes_are_demo(db):
    statuses = set(db.scalars(select(m.Outcome.data_status)))
    assert statuses == {"demo"}
    titles = set(db.scalars(select(m.Source.title)))
    assert "SAMVAAD simulated demo dataset" in titles


def test_seed_leaves_official_codes_null(db):
    assert all(t.qualification_code is None and t.awarding_body is None for t in db.scalars(select(m.Trade)))


def test_district_level_outcome(db):
    r = DataTools(db).get_trade_outcomes("electrician", "Mysuru")
    assert r["found"] is True
    assert r["geo_level_used"] == "district"
    rec = r["records"][0]
    assert rec["district"] == "Mysuru" and rec["year"] == 2025
    assert rec["earnings_min"] <= rec["earnings_median"] <= rec["earnings_max"]
    assert r["source"]["title"] == "SAMVAAD simulated demo dataset"
    assert "demo" in r["limitation_codes"]


def test_state_fallback_is_reported(db):
    r = DataTools(db).get_trade_outcomes("ev-service-technician", "Kalaburagi")
    assert r["found"] and r["geo_level_used"] == "state"
    assert "state_fallback" in r["limitation_codes"]
    assert any("District data is not available" in x for x in r["limitations"])


def test_national_fallback(db):
    r = DataTools(db).get_trade_outcomes("home-health-aide", "Dharwad")
    assert r["found"] and r["geo_level_used"] == "national"
    assert "national_fallback" in r["limitation_codes"]


def test_older_year_flagged(db):
    r = DataTools(db).get_trade_outcomes("solar-pv-installer", "Dharwad")
    assert r["geo_level_used"] == "district"
    assert r["records"][0]["year"] == 2024
    assert "older_year" in r["limitation_codes"]


def test_unknown_trade_logs_gap(db):
    before = gap_count(db)
    tools = DataTools(db, session_id=None, concern="income")
    r = tools.get_trade_outcomes("plumber", "Mysuru")
    assert r["found"] is False and r["data_status"] == "unavailable"
    assert gap_count(db) == before + 1
    gap = db.scalars(select(m.EvidenceGap).order_by(m.EvidenceGap.id.desc())).first()
    assert gap.trade_slug == "plumber" and gap.district == "Mysuru" and gap.concern_category == "income"
    assert tools.ctx.found_false_count == 1


def test_provider_gap(db):
    r = DataTools(db).get_providers("ev-service-technician", "Kalaburagi")
    assert r["found"] is False
    assert "Mysuru" in r["other_districts"]
    ok = DataTools(db).get_providers("ev-service-technician", "Mysuru")
    assert ok["found"] and ok["records"][0]["name"].startswith("Demo ")


def test_costs_gap_for_wireman(db):
    assert DataTools(db).get_costs_and_support("wireman", "Mysuru")["found"] is False


def test_costs_filtered_by_income(db):
    low = DataTools(db).get_costs_and_support("electrician", "Mysuru", "<1.5L")
    high = DataTools(db).get_costs_and_support("electrician", "Mysuru", ">6L")
    unknown = DataTools(db).get_costs_and_support("electrician", "Mysuru", None)
    kinds = lambda r: {s["support_type"] for s in r["records"][0]["supports"]}  # noqa: E731
    assert "scheme" in kinds(low)
    assert "scheme" not in kinds(high)
    assert "scheme" in kinds(unknown) and "income_unknown" in unknown["limitation_codes"]


def test_costs_district_specific_fee(db):
    blr = DataTools(db).get_costs_and_support("electrician", "Bengaluru Urban")
    assert blr["geo_level_used"] == "district"
    assert blr["records"][0]["fee_max"] > DataTools(db).get_costs_and_support("electrician", "Mysuru")["records"][0]["fee_max"]


def test_progression_marks_eligibility(db):
    r = DataTools(db).get_progression("electrician", "class_10")
    by_kind = {s["kind"]: s["eligible"] for s in r["records"]}
    assert by_kind["job"] is True
    assert by_kind["apprenticeship"] is False  # needs ITI
    assert r["can_start_training"] is True
    iti = DataTools(db).get_progression("electrician", "iti")
    assert {s["kind"]: s["eligible"] for s in iti["records"]}["diploma"] is True


def test_progression_kannada(db):
    r = DataTools(db, language="kn").get_progression("general-duty-assistant", None)
    assert any("ನರ್ಸಿಂಗ್" in s["title"] for s in r["records"])


def test_trade_resolution_by_name_and_alias_district(db):
    r = DataTools(db).get_trade_outcomes("Electrician", "Mysore")
    assert r["found"] and r["geo_level_used"] == "district"


def test_list_trades(db):
    r = DataTools(db, language="kn").list_trades(sector="Healthcare")
    assert r["found"] and len(r["records"]) == 2
    assert all(rec["name"] == rec["name_kn"] for rec in r["records"])


def test_execute_handles_bad_args(db):
    t = DataTools(db)
    r = t.execute("get_trade_outcomes", {"wrong": 1})
    assert r["found"] is False and "invalid arguments" in r["error"]
    assert t.ctx.calls[-1]["name"] == "get_trade_outcomes"
