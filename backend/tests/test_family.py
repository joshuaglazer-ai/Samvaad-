from datetime import timedelta

from sqlalchemy import select

from app import models as m
from app import analytics as a


def create(client, mode="two_devices", **over):
    body = {"language": "kn", "district": "Mysuru", "learner_education": "class_10", "consent_given": True,
            "participation_mode": mode, "device_id": "learner-phone-1"}
    body.update(over)
    r = client.post("/api/session", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_two_device_session_gets_a_family_code(client):
    out = create(client)
    assert len(out["family_code"]) == 4 and out["family_code"].isdigit()
    assert create(client, mode="together")["family_code"] is None


def test_parent_joins_with_code_in_own_language(client):
    out = create(client)
    r = client.post("/api/join", json={"code": out["family_code"], "language": "en", "device_id": "parent-phone-1"})
    assert r.status_code == 200
    assert r.json()["session_id"] == out["session_id"] and r.json()["learner_language"] == "kn"
    st = client.get(f"/api/session/{out['session_id']}/status").json()
    assert st["parent_joined"] and st["parent_language"] == "en" and st["participation_mode"] == "two_devices"


def test_messages_and_alignment_are_tagged_by_device(client, SessionMaker):
    out = create(client)
    sid = out["session_id"]
    client.post("/api/join", json={"code": out["family_code"], "language": "en", "device_id": "parent-phone-1"})
    client.post("/api/chat", json={"session_id": sid, "speaker": "parent", "text": "How much can an electrician earn?",
                                   "language": "en", "device_id": "parent-phone-1"})
    client.post("/api/chat", json={"session_id": sid, "speaker": "learner", "text": "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಸಂಬಳ ಎಷ್ಟು?",
                                   "language": "kn", "device_id": "learner-phone-1"})
    vals = ["earning_soon", "near_home", "respect", "study_further", "safety"]
    client.post(f"/api/session/{sid}/alignment", json={"respondent": "parent", "ranking": vals, "device_id": "parent-phone-1"})
    with SessionMaker() as db:
        msgs = db.scalars(select(m.Message).where(m.Message.session_id == sid).order_by(m.Message.id)).all()
        assert [x.device_id for x in msgs] == ["parent-phone-1"] * 2 + ["learner-phone-1"] * 2
        assert [x.language for x in msgs] == ["en", "en", "kn", "kn"]  # each phone is answered in its own language
        al = db.scalar(select(m.AlignmentResponse).where(m.AlignmentResponse.session_id == sid))
        assert al.device_id == "parent-phone-1"
    st = client.get(f"/api/session/{sid}/status").json()
    assert st["alignment"] == {"learner_done": False, "parent_done": True}


def test_wrong_code_and_expired_code_are_rejected(client, SessionMaker):
    out = create(client)
    bad = "0000" if out["family_code"] != "0000" else "1111"
    assert client.post("/api/join", json={"code": bad}).status_code == 404
    with SessionMaker() as db:
        s = db.get(m.SessionRow, out["session_id"])
        s.family_code_expires_at = m.utcnow() - timedelta(minutes=1)
        db.commit()
    assert client.post("/api/join", json={"code": out["family_code"]}).status_code == 404


def test_join_attempts_are_rate_limited(client):
    from app.routers import session as sess
    sess._failed_joins.clear()
    codes = [f"{i:04d}" for i in range(9990, 10000)]
    for c in codes:
        client.post("/api/join", json={"code": c})
    assert client.post("/api/join", json={"code": "9989"}).status_code == 429
    sess._failed_joins.clear()


def test_code_must_be_four_digits(client):
    assert client.post("/api/join", json={"code": "12a4"}).status_code == 422


def test_refresh_code_switches_to_two_devices(client):
    out = create(client, mode="together")
    r = client.post(f"/api/session/{out['session_id']}/family-code").json()
    assert len(r["family_code"]) == 4
    assert client.get(f"/api/session/{out['session_id']}/status").json()["participation_mode"] == "two_devices"


def test_dashboard_filters_by_participation_mode(db):
    for mode in ["together"] * 6 + ["two_devices"] * 5 + ["learner_only"] * 5:
        db.add(m.SessionRow(language="en", district="Mysuru", learner_education="class_10", consent_given=True,
                            participation_mode=mode))
    db.commit()
    o = a.overview(db, a.Filters())
    assert o["participation_modes"] == {"together": 6, "two_devices": 5, "learner_only": 5}
    assert o["parent_data_note"] == "Self-identified parent responses"
    assert a.overview(db, a.Filters(participation_mode="two_devices"))["sessions"] == 5


def test_admin_rejects_unknown_mode(client):
    r = client.get("/api/admin/overview?participation_mode=phone", headers={"X-Role-Pin": "admin-test"})
    assert r.status_code == 422
