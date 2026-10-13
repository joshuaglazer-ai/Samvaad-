"""Update 3 · Step 1: sectors, trade synonyms and the catalogue API the frontend reads instead of hard-coded lists."""
import pytest
from sqlalchemy import select

from app import models as m
from app.data_tools import DataTools
from app.i18n import LANGS


def test_sectors_endpoint_is_ordered_and_translated(client):
    rows = client.get("/api/sectors", params={"language": "te"}).json()
    assert [r["slug"] for r in rows] == ["electrical", "automotive", "healthcare", "green-energy"]
    assert all(r["name"] == r["names"]["te"] and r["icon"] for r in rows)
    assert sum(r["trade_count"] for r in rows) == 8


@pytest.mark.parametrize("sector", ["healthcare", "Healthcare", "ಆರೋಗ್ಯ ಸೇವೆ", "स्वास्थ्य सेवा"])
def test_trades_filter_by_sector_slug_or_name_in_any_language(client, sector):
    rows = client.get("/api/trades", params={"sector": sector, "language": "hi"}).json()
    assert {r["slug"] for r in rows} == {"general-duty-assistant", "home-health-aide"}
    assert all(r["sector"] == "healthcare" and r["sector_name"] == "स्वास्थ्य सेवा" for r in rows)


def test_unknown_sector_is_404_and_not_an_evidence_gap(client, db):
    assert client.get("/api/trades", params={"sector": "aviation"}).status_code == 404
    assert db.scalar(select(m.EvidenceGap).where(m.EvidenceGap.tool_name == "list_trades")) is None


def test_every_trade_has_synonyms_in_all_four_languages(db):
    for trade in db.scalars(select(m.Trade)):
        langs = {s.language for s in db.scalars(select(m.TradeSynonym).where(m.TradeSynonym.trade_id == trade.id))}
        assert langs == set(LANGS), trade.slug
    assert all(s.review_status == "needs_native_review" for s in db.scalars(select(m.TradeSynonym)))


def test_trades_carry_synonyms_traits_and_data_status(db):
    recs = DataTools(db).list_trades()["records"]
    elec = next(r for r in recs if r["slug"] == "electrician")
    assert "bijli mistri" in elec["synonyms"]["hi"]
    assert elec["traits"] and elec["data_status"] == "demo"
    assert all(r["traits"] for r in recs)


def test_session_stores_aspiration_fields(db):
    s = m.SessionRow(district="Mysuru", learner_education="class_10", aspiration_text="drone pilot",
                     aspiration_language="en", aspiration_source="text", matched_trade_slugs=[],
                     aspiration_category="unknown", parent_hope_text="engineer", parent_hope_category="degree_career")
    db.add(s)
    db.commit()
    got = db.get(m.SessionRow, s.id)
    assert got.aspiration_text == "drone pilot" and got.aspiration_confirmed is False
    assert got.parent_hope_text == "engineer" and got.parent_hope_matched_trade_slugs == []


def test_alembic_migrations_reach_head_on_sqlite(tmp_path, monkeypatch):
    """The new migration runs on a fresh SQLite file and produces the Update 3 tables and columns."""
    from sqlalchemy import create_engine, inspect

    from app import config, schema_setup

    url = f"sqlite:///{(tmp_path / 'mig.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    config.get_settings.cache_clear()
    try:
        schema_setup.upgrade_to_head()
    finally:
        monkeypatch.undo()
        config.get_settings.cache_clear()
    insp = inspect(create_engine(url))
    assert {"sectors", "trade_synonyms"} <= set(insp.get_table_names())
    cols = {c["name"] for c in insp.get_columns("sessions")}
    assert {"aspiration_text", "matched_trade_slugs", "aspiration_confirmed", "parent_hope_text",
            "parent_hope_confirmed"} <= cols
