"""Update 3 · Step 5: Admin → Trades (no code changes), catalogue CSV import, and the goal dashboard panels."""
import csv
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select

from app import analytics as a
from app import models as m
from seed.import_catalogue import import_catalogue
from seed.simulate_sessions import simulate

H = {"X-Role-Pin": "admin-test"}
SEED = Path(__file__).resolve().parent.parent / "seed"
NEW_TRADE = {"slug": "plumber", "sector": "construction", "names": {"en": "Plumber", "hi": "प्लंबर"},
             "nsqf_level": 3, "duration_months": 6, "entry_min_education": "class_8", "traits": ["hands"],
             "icon": "gear"}


def rows(name: str) -> list[dict]:
    with (SEED / "examples" / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


MAPPING = yaml.safe_load((SEED / "mapping.catalogue.example.yaml").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- admin API
def test_catalogue_admin_requires_the_admin_pin(client):
    assert client.get("/api/admin/catalogue").status_code == 401
    assert client.get("/api/admin/catalogue", headers={"X-Role-Pin": "counsellor-test"}).status_code == 401
    assert client.post("/api/admin/trades", json=NEW_TRADE).status_code == 401


def test_catalogue_lists_everything_with_status(client):
    c = client.get("/api/admin/catalogue", headers=H).json()
    assert len(c["sectors"]) == 4 and len(c["trades"]) == 8 and c["sources"]
    elec = next(t for t in c["trades"] if t["slug"] == "electrician")
    assert elec["data_status"] == "demo" and elec["source_id"] and elec["synonyms"] and elec["steps"]
    assert elec["outcomes_by_status"]["demo"] > 0 and elec["missing_languages"] == []


def test_add_a_trade_without_code_changes_and_it_works_everywhere(client):
    assert client.post("/api/admin/trades", headers=H, json=NEW_TRADE).status_code == 422  # sector first
    r = client.post("/api/admin/sectors", headers=H, json={"slug": "construction", "names": {"en": "Construction",
                                                                                            "kn": "ನಿರ್ಮಾಣ ಕೆಲಸ"},
                                                             "icon": "building", "sort_order": 5})
    assert r.status_code == 201
    t = client.post("/api/admin/trades", headers=H, json=NEW_TRADE).json()
    assert t["data_status"] == "unavailable" and t["missing_languages"] == ["kn", "te"]  # default until a source
    syn = client.post("/api/admin/trades/plumber/synonyms", headers=H, json={"language": "hi", "term": "nal ka kaam"})
    assert syn.status_code == 201
    assert client.post("/api/admin/trades/plumber/synonyms", headers=H,
                       json={"language": "hi", "term": "nal  ka kaam"}).status_code == 409
    steps = [{"kind": "job", "titles": {"en": "Assistant Plumber"}, "nsqf_level": 3},
             {"kind": "upskill", "titles": {"en": "Senior Plumber"}, "nsqf_level": 4, "entry_min_education": "class_10"}]
    assert [s["titles"]["en"] for s in client.put("/api/admin/trades/plumber/steps", headers=H, json=steps)
            .json()["steps"]] == ["Assistant Plumber", "Senior Plumber"]
    # Families now see it: sector list, browse, and their own words match it.
    assert any(s["slug"] == "construction" for s in client.get("/api/sectors").json())
    assert [x["slug"] for x in client.get("/api/trades", params={"sector": "construction"}).json()] == ["plumber"]
    m_ = client.post("/api/aspiration/match", json={"text": "nal ka kaam", "language": "hi"}).json()
    assert m_["matched"] and m_["candidates"][0]["slug"] == "plumber"
    # Its data status is shown honestly: no outcome data yet → the tools say so.
    s = client.post("/api/session", json={"language": "en", "district": "Mysuru", "learner_education": "class_10",
                                          "consent_given": True}).json()["session_id"]
    r = client.post("/api/chat", json={"session_id": s, "speaker": "learner", "text": "How much does a plumber earn?",
                                       "language": "en"}).json()
    assert "I don't have reliable data" in r["reply_text"]


def test_verified_needs_a_source_and_slugs_are_fixed(client):
    c = client.get("/api/admin/catalogue", headers=H).json()
    wire = next(t for t in c["trades"] if t["slug"] == "wireman")
    body = {k: wire[k] for k in ("slug", "sector", "names", "nsqf_level", "duration_months", "entry_min_education",
                                 "entry_requirement", "job_roles", "icon", "traits")}
    assert client.put("/api/admin/trades/wireman", headers=H,
                      json=body | {"data_status": "verified", "source_id": None}).status_code == 422
    ok = client.put("/api/admin/trades/wireman", headers=H,
                    json=body | {"data_status": "verified", "source_id": c["sources"][0]["id"],
                                 "names": {**body["names"], "en": "Wireman (house wiring)"}}).json()
    assert ok["data_status"] == "verified" and ok["names"]["en"] == "Wireman (house wiring)"
    assert client.put("/api/admin/trades/wireman", headers=H, json=body | {"slug": "wire-man"}).status_code == 422
    assert client.post("/api/admin/trades", headers=H, json=body | {"names": {"kn": "x"}}).status_code == 422  # en needed


def test_synonym_review_and_delete(client, db):
    syn = db.scalar(select(m.TradeSynonym))
    r = client.put(f"/api/admin/synonyms/{syn.id}", headers=H,
                   json={"language": syn.language, "term": syn.term, "review_status": "reviewed"}).json()
    assert r["review_status"] == "reviewed"
    assert client.delete(f"/api/admin/synonyms/{syn.id}", headers=H).json() == {"ok": True}
    assert client.delete(f"/api/admin/synonyms/{syn.id}", headers=H).status_code == 404


# ---------------------------------------------------------------- CSV import
def test_catalogue_csv_import_from_the_examples(db):
    assert import_catalogue(db, "sectors", rows("sectors.example.csv"), MAPPING).created == 1
    rep = import_catalogue(db, "trades", rows("trades.example.csv"), MAPPING)
    assert rep.created == 1 and rep.rejected == 0
    t = db.scalar(select(m.Trade).where(m.Trade.slug == "plumber"))
    assert t.data_status == "unavailable" and t.traits == ["hands", "outdoors"] and t.names["te"] == "ప్లంబర్"
    assert import_catalogue(db, "synonyms", rows("synonyms.example.csv"), MAPPING).created == 4
    again = import_catalogue(db, "synonyms", rows("synonyms.example.csv"), MAPPING)
    assert again.created == 0 and again.updated == 4  # re-import is safe


def test_catalogue_import_rejects_bad_rows_with_reasons(db):
    bad = [{"Trade ID": "Bad Slug", "Sector ID": "electrical", "Trade (English)": "X", "NSQF level": "4", "Months": "6"},
           {"Trade ID": "x-ray-tech", "Sector ID": "space", "Trade (English)": "X", "NSQF level": "4", "Months": "6"},
           {"Trade ID": "x-ray-tech", "Sector ID": "healthcare", "Trade (English)": "", "NSQF level": "4", "Months": "6"},
           {"Trade ID": "x-ray-tech", "Sector ID": "healthcare", "Trade (English)": "X-ray Technician",
            "NSQF level": "4", "Months": "6", "Data status": "verified"}]
    rep = import_catalogue(db, "trades", bad, MAPPING)
    assert rep.rejected == 4 and rep.created == 0
    reasons = " | ".join(e["reason"] for e in rep.errors)
    assert "lowercase" in reasons and "unknown sector" in reasons and "name_en" in reasons and "source" in reasons
    with_source = MAPPING | {"source": {"title": "Test register extract"}}
    assert import_catalogue(db, "trades", bad[3:], with_source).created == 1
    assert db.scalar(select(m.Trade).where(m.Trade.slug == "x-ray-tech")).source_id is not None


def test_catalogue_import_cli_dry_run(tmp_path, monkeypatch, capsys):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app import config, db as app_db
    from seed import import_csv

    url = f"sqlite:///{(tmp_path / 'cli.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(app_db, "SessionLocal", sessionmaker(bind=create_engine(url)))
    config.get_settings.cache_clear()
    try:
        monkeypatch.setattr("sys.argv", ["import_csv", "--kind", "sectors", "--file",
                                         str(SEED / "examples" / "sectors.example.csv"),
                                         "--mapping", str(SEED / "mapping.catalogue.example.yaml"), "--dry-run",
                                         "--errors", str(tmp_path / "e.csv")])
        import_csv.main()
    finally:
        config.get_settings.cache_clear()
    out = capsys.readouterr().out
    assert "sectors: rows read 1 | created 1" in out and "DRY RUN" in out
    with sessionmaker(bind=create_engine(url))() as check:
        assert check.scalar(select(m.Sector).where(m.Sector.slug == "construction")) is None  # nothing saved


# ---------------------------------------------------------------- dashboard panels
@pytest.fixture()
def simulated(db):
    simulate(db, n=120, seed=5, days=60)
    return db


def test_top_aspirations_group_by_trade_with_small_cell_suppression(client, simulated):
    r = client.get("/api/admin/top-aspirations", headers=H).json()
    assert r["districts"] and r["min_cell_size"] == 5
    for d in r["districts"]:
        for g in d["groups"]:
            assert g["sessions"] >= 5
            assert all(w["sessions"] >= 5 for w in g["words"])  # exact words only when 5+ families used them
    names = {g["trade_name"] for d in r["districts"] for g in d["groups"]}
    assert "Electrician" in names


def test_unmatched_aspirations_feed_the_gap_radar(client, simulated):
    r = client.get("/api/admin/unmatched-aspirations", headers=H).json()
    assert r["goals"] and all(g["sessions"] >= 5 for g in r["goals"])
    for g in r["goals"]:  # split counts below 5 are suppressed too
        for n in [g["learner"], g["parent"], *g["districts"].values()]:
            assert n is None or n == 0 or n >= 5
    cats = {g["category"] for g in r["goals"]}
    assert cats <= {"degree_career", "professional_course", "unknown"}
    assert any(g["text"] in ("engineer", "government job") for g in r["goals"])
    radar = client.get("/api/admin/evidence-gaps", headers=H).json()
    assert any(row["trade_slug"].startswith("goal: ") for row in radar["gaps"])


def test_goal_vs_hope_by_district(client, simulated):
    r = client.get("/api/admin/goal-vs-hope", headers=H).json()
    assert r["parent_data_note"] == "Self-identified parent responses"
    shown = [d for d in r["districts"] if not d["suppressed"]]
    assert shown and all(0 <= d["differ_rate"] <= 100 and d["differ"] <= d["sessions"] for d in shown)
    assert r["overall"]["sessions"] == sum(d["sessions"] for d in r["districts"])
    assert set(r["by_mode"]) <= {"together", "two_devices"}  # learner-only sessions have no parent hope


def test_goal_panels_suppress_small_groups(db):
    for _ in range(3):
        s = m.SessionRow(language="en", district="Dharwad", learner_education="class_10", consent_given=True,
                         aspiration_text="astronaut", aspiration_category="unknown", parent_hope_text="doctor",
                         parent_hope_category="degree_career")
        db.add(s)
    db.commit()
    assert a.unmatched_aspirations(db, a.Filters())["goals"] == []
    assert a.unmatched_aspirations(db, a.Filters())["other"] == {"phrases": 2, "sessions": 3}
    d = a.goal_vs_hope(db, a.Filters())["districts"][0]
    assert d["suppressed"] and d["differ_rate"] is None
    top = a.top_aspirations(db, a.Filters())["districts"][0]
    assert top["groups"] == [] and top["other_sessions"] == 3
