from sqlalchemy import select

from app import models as m

C = {"X-Role-Pin": "counsellor-test"}
A = {"X-Role-Pin": "admin-test"}


def session(client):
    r = client.post("/api/session", json={"language": "kn", "district": "Dharwad", "learner_education": "class_12",
                                          "top_concerns": ["safety"], "consent_given": True})
    return r.json()["session_id"]


def escalate(client, sid):
    r = client.post("/api/escalate", json={"session_id": sid, "trigger": "user_request"})
    assert r.status_code == 200
    return r.json()


def test_escalate_creates_case_with_bilingual_summary(client):
    sid = session(client)
    client.post("/api/chat", json={"session_id": sid, "speaker": "parent", "text": "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಸಂಬಳ ಎಷ್ಟು?", "language": "kn"})
    info = escalate(client, sid)
    assert info["status"] == "pending" and info["counsellor_online"] is False
    q = client.get("/api/counsellor/queue", headers=C).json()
    case = next(c for c in q if c["id"] == info["id"])
    assert case["district"] == "Dharwad" and case["language"] == "kn"
    assert "Dharwad" in case["summary_en"] and "ಧಾರವಾಡ" in case["summary_kn"]
    assert "earnings & placement – Electrician" in case["summary_en"]
    assert len(case["summary_en"].splitlines()) == 3


def test_counsellor_endpoints_require_pin(client):
    assert client.get("/api/counsellor/queue").status_code == 401
    assert client.get("/api/counsellor/queue", headers={"X-Role-Pin": "wrong"}).status_code == 401
    assert client.get("/api/counsellor/queue", headers=A).status_code == 200  # admins may open the console


def test_case_detail_has_full_transcript(client):
    sid = session(client)
    client.post("/api/chat", json={"session_id": sid, "speaker": "parent", "text": "Is it safe for my daughter?", "language": "en"})
    case_id = client.get("/api/counsellor/queue", headers=C).json()[-1]["id"]
    d = client.get(f"/api/counsellor/cases/{case_id}", headers=C).json()
    assert d["trigger"] == "sensitive_topic"
    assert [t["role"] for t in d["transcript"]][:2] == ["user", "assistant"]
    assert d["transcript"][0]["concern_category"] is not None  # internal tags visible to counsellors


def test_status_flow_and_reply_polling(client):
    sid = session(client)
    case_id = escalate(client, sid)["id"]
    r = client.patch(f"/api/counsellor/cases/{case_id}", headers=C, json={"assigned_to": "Counsellor A"})
    assert r.json()["status"] == "assigned"
    client.post(f"/api/counsellor/cases/{case_id}/reply", headers=C, json={"text": "Namaskara, I am here to help."})
    assert client.get(f"/api/escalations/{case_id}").json()["status"] == "in_progress"
    msgs = client.get(f"/api/escalations/{case_id}/messages").json()
    assert msgs[-1]["role"] == "counsellor"
    family = client.post(f"/api/escalations/{case_id}/messages?speaker=parent", json={"text": "Thank you"}).json()
    after = client.get(f"/api/escalations/{case_id}/messages?after={msgs[-1]['id']}").json()
    assert [x["id"] for x in after] == [family["id"]]
    r = client.patch(f"/api/counsellor/cases/{case_id}", headers=C, json={"status": "resolved"})
    assert r.json()["status"] == "resolved"
    assert all(c["id"] != case_id for c in client.get("/api/counsellor/queue", headers=C).json())


def test_live_messages_stay_out_of_llm_history(client, SessionMaker):
    from app.chat import build_history
    sid = session(client)
    case_id = escalate(client, sid)["id"]
    client.post(f"/api/escalations/{case_id}/messages", json={"text": "private note to counsellor"})
    with SessionMaker() as db:
        assert all("private note" not in h["content"] for h in build_history(db, sid, None))


def test_callback_requires_consent_and_encrypts_phone(client, SessionMaker):
    sid = session(client)
    case_id = escalate(client, sid)["id"]
    bad = client.post(f"/api/escalate/{case_id}/callback", json={"phone": "9876543210", "preferred_time": "evening", "consent": False})
    assert bad.status_code == 400
    ok = client.post(f"/api/escalate/{case_id}/callback", json={"phone": "+91 98765 43210", "preferred_time": "evening", "consent": True})
    assert ok.status_code == 200
    with SessionMaker() as db:
        row = db.scalar(select(m.CallbackRequest).where(m.CallbackRequest.escalation_id == case_id))
        assert "9876543210" not in row.phone_encrypted  # stored encrypted, separate from the session
    cbs = client.get("/api/counsellor/callbacks", headers=C).json()
    cb = next(c for c in cbs if c["escalation_id"] == case_id)
    assert cb["phone"] == "+919876543210"
    assert client.delete(f"/api/counsellor/callbacks/{cb['id']}", headers=C).json()["ok"]
    with SessionMaker() as db:
        row = db.get(m.CallbackRequest, cb["id"])
        assert row.phone_encrypted is None and row.deleted_at is not None
    assert all(c["id"] != cb["id"] for c in client.get("/api/counsellor/callbacks", headers=C).json())


def test_websocket_live_chat_between_family_and_counsellor(client):
    sid = session(client)
    case_id = escalate(client, sid)["id"]
    with client.websocket_connect("/ws/counsellor?pin=counsellor-test"):
        assert client.get(f"/api/escalations/{case_id}").json()["counsellor_online"] is True
        with client.websocket_connect(f"/ws/escalation/{case_id}?role=family") as fam, \
             client.websocket_connect(f"/ws/escalation/{case_id}?role=counsellor&pin=counsellor-test") as cou:
            fam.send_json({"type": "message", "text": "Hello, we are waiting", "speaker": "parent"})
            got = cou.receive_json()
            assert got["type"] == "message" and got["message"]["text"] == "Hello, we are waiting"
            assert fam.receive_json()["message"]["speaker"] == "parent"  # echo to sender
            cou.send_json({"type": "message", "text": "I am here."})
            assert fam.receive_json()["message"]["role"] == "counsellor"
    assert client.get(f"/api/escalations/{case_id}").json()["status"] == "in_progress"


def test_websocket_counsellor_needs_pin(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    sid = session(client)
    case_id = escalate(client, sid)["id"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/escalation/{case_id}?role=counsellor&pin=nope") as ws:
            ws.receive_json()
