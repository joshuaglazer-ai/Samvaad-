import pytest

from app import analytics as a
from app import models as m
from seed.simulate_sessions import clear_simulated, simulate

H = {"X-Role-Pin": "admin-test"}


@pytest.fixture()
def simulated(db):
    simulate(db, n=40, seed=3, days=60)
    return db


def test_admin_requires_pin(client):
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers={"X-Role-Pin": "counsellor-test"}).status_code == 401


def test_overview_counts_and_flags(client, simulated):
    o = client.get("/api/admin/overview", headers=H).json()
    assert o["sessions"] == 40 and o["simulated_sessions"] == 40
    assert o["includes_demo_data"] and o["includes_simulated_sessions"]
    cov = o["evidence_coverage"]
    assert 0 < cov["numerator"] <= cov["denominator"]


def test_small_cells_suppressed(db):
    # 3 sessions in one district → below the 5-session threshold
    for _ in range(3):
        s = m.SessionRow(language="en", district="Mysuru", learner_education="class_10", consent_given=True)
        db.add(s)
        db.flush()
        db.add(m.Message(session_id=s.id, role="user", speaker="parent", text="x", language="en",
                         concern_category="income", sentiment=-2))
    db.commit()
    res = {r["district"]: r for r in a.resistance_by_district(db, a.Filters())["districts"]}
    assert res["Mysuru"]["suppressed"] is True and res["Mysuru"]["share"] is None and res["Mysuru"]["sessions"] == 3
    c = a.concerns(db, a.Filters())
    assert all(g["suppressed"] for g in c["by_district"])
    o = a.overview(db, a.Filters())
    assert o["mood_shift_parent"]["mean"] is None


def test_every_cell_has_counts_and_denominators(simulated):
    r = a.resistance_by_district(simulated, a.Filters())
    for d in r["districts"]:
        if not d["suppressed"]:
            assert d["parent_messages"] >= d["negative_parent_messages"]
            assert d["share"] == round(d["negative_parent_messages"] / d["parent_messages"], 3)
    f = a.funnel(simulated, a.Filters())
    assert f["steps"][0]["sessions"] == f["steps"][0]["denominator"] == 40
    assert all(s["sessions"] <= s["denominator"] for s in f["steps"])


def test_sentiment_and_mood_reported_separately(simulated):
    s = a.sentiment_shift(simulated, a.Filters())
    assert "model_sentiment_by_parent_turn" in s and "self_reported_mood" in s
    assert all(-2 <= t["mean_sentiment"] <= 2 for t in s["model_sentiment_by_parent_turn"] if not t["suppressed"])
    mood = s["self_reported_mood"]["parent"]
    assert mood["suppressed"] or 1 <= mood["pre_mean"] <= 5


def test_evidence_gaps_fold_small_groups(simulated):
    g = a.evidence_gaps(simulated, a.Filters())
    assert all(row["sessions"] >= 5 for row in g["gaps"])
    assert sum(r["requests"] for r in g["gaps"]) + g["other"]["requests"] == g["total_requests"]


def test_filters_apply(simulated):
    all_ = a.overview(simulated, a.Filters())["sessions"]
    k = a.overview(simulated, a.Filters(district="Kalaburagi"))["sessions"]
    assert 0 < k < all_
    assert a.overview(simulated, a.Filters(include_simulated=False))["sessions"] == 0


def test_export_csv_is_aggregate_only(client, simulated):
    assert client.get("/api/admin/export.csv").status_code == 401
    r = client.get("/api/admin/export.csv?pin=admin-test")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("district,sessions") and len(lines) == 5  # header + 4 districts, no session rows
    assert "includes simulated sessions" in r.text


def test_data_quality(client):
    q = client.get("/api/admin/data-quality", headers=H).json()
    assert q["outcomes_by_status"] == {"demo": q["outcomes_total"]}
    assert q["trades_missing_qualification_code"] == q["trades_total"]


def test_clear_simulated(simulated):
    assert clear_simulated(simulated) == 40
    assert a.overview(simulated, a.Filters())["sessions"] == 0
