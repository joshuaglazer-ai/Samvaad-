"""Update 3 · Step 3: saving the learner's goal and the parent's hope, the quiz, and comparing the two."""
from sqlalchemy import select

from app import models as m

BASE = {"language": "en", "district": "Mysuru", "learner_education": "class_10", "consent_given": True}


def gaps(db, sid=None):
    q = select(m.EvidenceGap).where(m.EvidenceGap.tool_name == "match_aspiration")
    if sid:
        q = q.where(m.EvidenceGap.session_id == sid)
    return list(db.scalars(q))


def test_match_preview_stores_nothing(client, db):
    r = client.post("/api/aspiration/match", json={"text": "drone pilot", "language": "en"}).json()
    assert r["matched"] is False and r["category"] == "unknown"
    assert gaps(db) == []
    r = client.post("/api/aspiration/match", json={"text": "बिजली मिस्त्री", "language": "hi"}).json()
    assert r["candidates"][0]["slug"] == "electrician" and r["candidates"][0]["name"] == "इलेक्ट्रीशियन"


def test_create_session_with_typed_goal_and_parent_hope(client, db):
    body = BASE | {"aspiration": {"text": "bijli mistri", "language": "hi", "source": "text",
                                  "selected_slugs": ["electrician"]},
                   "parent_hope": {"text": "engineer", "language": "en", "source": "voice"}}
    sid = client.post("/api/session", json=body).json()["session_id"]
    s = db.get(m.SessionRow, sid)
    db.refresh(s)
    assert s.aspiration_text == "bijli mistri" and s.aspiration_source == "text" and s.aspiration_confirmed
    assert s.matched_trade_slugs == ["electrician"] and s.aspiration_category == "vocational_match"
    assert s.match_confidence == 1.0
    assert s.parent_hope_text == "engineer" and s.parent_hope_category == "degree_career"
    assert s.parent_hope_matched_trade_slugs == []
    g = gaps(db, sid)
    assert len(g) == 1 and g[0].query["aspiration_text"] == "engineer" and g[0].district == "Mysuru"


def test_goals_compare_side_by_side(client):
    body = BASE | {"aspiration": {"text": "electrician", "source": "text", "selected_slugs": ["electrician"]},
                   "parent_hope": {"text": "Degree in engineering", "source": "text"}}
    sid = client.post("/api/session", json=body).json()["session_id"]
    r = client.get(f"/api/session/{sid}/aspirations", params={"language": "kn"}).json()
    assert r["differ"] is True
    assert r["learner"]["label"] == "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್" and r["parent"]["label"] == "Degree in engineering"
    assert client.get(f"/api/session/{sid}/status").json()["goals"] == {"learner_done": True, "parent_done": True}


def test_same_goal_does_not_differ(client):
    sid = client.post("/api/session", json=BASE | {
        "aspiration": {"source": "browse", "selected_slugs": ["wireman"], "text": "Wireman"},
        "parent_hope": {"source": "text", "text": "wiring work", "selected_slugs": ["wireman"]}}).json()["session_id"]
    assert client.get(f"/api/session/{sid}/aspirations").json()["differ"] is False


def test_parent_hope_from_own_phone_and_change_goal(client, db):
    sid = client.post("/api/session", json=BASE | {"participation_mode": "two_devices"}).json()["session_id"]
    assert client.get(f"/api/session/{sid}/status").json()["goals"]["parent_done"] is False
    r = client.put(f"/api/session/{sid}/aspiration", json={
        "who": "parent", "text": "నర్సు", "language": "te", "source": "voice", "device_id": "phone-b"}).json()
    assert r["parent"]["category"] == "degree_career" and r["learner"] is None and r["differ"] is False
    r = client.put(f"/api/session/{sid}/aspiration", json={
        "who": "learner", "source": "browse", "selected_slugs": ["home-health-aide"], "language": "te"}).json()
    assert r["learner"]["trades"][0]["slug"] == "home-health-aide" and r["differ"] is True
    events = [e.payload for e in db.scalars(select(m.Event).where(m.Event.event_type == "aspiration_saved"))]
    assert {"who": "parent", "source": "voice", "category": "degree_career", "matched": 0} in events


def test_none_of_these_is_respected_and_logged(client, db):
    sid = client.post("/api/session", json=BASE).json()["session_id"]
    r = client.put(f"/api/session/{sid}/aspiration", json={
        "who": "learner", "text": "bike mechanic", "source": "text", "selected_slugs": []}).json()
    assert r["learner"]["category"] == "unknown" and r["learner"]["trades"] == []
    assert r["learner"]["label"] == "bike mechanic"
    assert gaps(db, sid)[0].query["category"] == "rejected_matches"


def test_saving_the_same_unmatched_goal_twice_logs_one_gap(client, db):
    sid = client.post("/api/session", json=BASE).json()["session_id"]
    for _ in range(2):
        client.put(f"/api/session/{sid}/aspiration", json={"who": "learner", "text": "makeup artist", "source": "text"})
    assert len(gaps(db, sid)) == 1


def test_unknown_trade_slug_is_rejected(client):
    r = client.post("/api/session", json=BASE | {"aspiration": {"source": "browse", "selected_slugs": ["astronaut"]}})
    assert r.status_code == 422
    sid = client.post("/api/session", json=BASE).json()["session_id"]
    r = client.put(f"/api/session/{sid}/aspiration", json={"who": "learner", "source": "browse", "selected_slugs": ["x"]})
    assert r.status_code == 422


def test_learner_only_has_no_parent_hope(client):
    sid = client.post("/api/session", json=BASE | {"participation_mode": "learner_only",
                                                   "parent_hope": {"source": "text", "text": "doctor"}}).json()["session_id"]
    assert client.get(f"/api/session/{sid}/aspirations").json()["parent"] is None
    assert client.put(f"/api/session/{sid}/aspiration",
                      json={"who": "parent", "source": "text", "text": "doctor"}).status_code == 409


def test_not_sure_quiz_suggests_database_trades_with_reasons(client):
    r = client.post("/api/aspiration/suggest", json={"likes": ["people"], "language": "hi"}).json()["suggestions"]
    assert {x["slug"] for x in r} == {"general-duty-assistant", "home-health-aide"}
    assert all(x["reason"] == "अगर लोगों की मदद करना पसंद है तो अच्छा" for x in r)
    r = client.post("/api/aspiration/suggest", json={"likes": ["hands", "machines", "outdoors"]}).json()["suggestions"]
    assert len(r) == 3 and all(x["reason"] for x in r)
    assert client.post("/api/aspiration/suggest", json={"likes": []}).json()["suggestions"] == []


def test_quiz_near_home_prefers_trades_taught_in_the_district(client):
    # Demo gap: no EV training centre in Kalaburagi.
    near = client.post("/api/aspiration/suggest", json={"likes": ["computers"], "near_home": True,
                                                        "district": "Kalaburagi"}).json()["suggestions"]
    anywhere = client.post("/api/aspiration/suggest", json={"likes": ["computers"], "near_home": False,
                                                            "district": "Kalaburagi"}).json()["suggestions"]
    assert [x["slug"] for x in anywhere] == ["ev-service-technician"]
    assert near == anywhere  # nothing local fits, so the family still gets the suggestion rather than nothing
