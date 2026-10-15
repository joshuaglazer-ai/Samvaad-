import pytest
from sqlalchemy import func, select

from app import models as m
from app.chat import handle_turn
from app.guardrail import check
from app.llm import BaseLLM, LLMResponse, MockLLM, ToolCall


def new_session(client, **over):
    body = {"language": "en", "district": "Mysuru", "learner_education": "class_10",
            "learner_interests": ["electricity"], "top_concerns": ["income"], "income_bracket": "<1.5L",
            "helper_mode": False, "consent_given": True}
    body.update(over)
    r = client.post("/api/session", json=body)
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def say(client, sid, text, speaker="parent", language="en"):
    r = client.post("/api/chat", json={"session_id": sid, "speaker": speaker, "text": text, "language": language})
    assert r.status_code == 200, r.text
    return r.json()


def test_consent_required(client):
    r = client.post("/api/session", json={"district": "Mysuru", "learner_education": "class_10", "consent_given": False})
    assert r.status_code == 400


def test_income_question_returns_outcome_card_with_evidence(client):
    sid = new_session(client)
    out = say(client, sid, "How much can an electrician earn?")
    assert out["guardrail_status"] == "pass"
    card = out["cards"][0]
    assert card["type"] == "outcome"
    ev = card["evidence"]
    assert ev["data_status"] == "demo" and ev["source"] == "SAMVAAD simulated demo dataset"
    assert ev["reporting_period"] and ev["sample_size"] and ev["geo_level"] == "district"
    assert "It's natural to think about earnings first." in out["reply_text"]  # reassure first
    assert "about ₹" in out["reply_text"] and "demo data" in out["reply_text"].lower()
    assert len(out["reply_text"].split()) <= 50  # short answers (Update 2)
    assert out["quick_replies"]
    # every number in the reply is backed by the card data
    assert check(out["reply_text"], [card["data"], card["evidence"]]).passed


def test_kannada_reply_and_state_fallback(client):
    sid = new_session(client, language="kn", district="Kalaburagi", learner_interests=["vehicles"])
    out = say(client, sid, "EV ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞರಿಗೆ ಸಂಬಳ ಎಷ್ಟು?", language="kn")
    card = out["cards"][0]
    assert card["evidence"]["geo_level"] == "state"
    assert "ರಾಜ್ಯ ಮಟ್ಟದ ಅಂಕಿ" in out["reply_text"]  # honest state-level fallback, said briefly
    assert out["guardrail_status"] == "pass"


def test_ladder_card_marks_eligibility(client):
    sid = new_session(client)
    out = say(client, sid, "What are the next steps after electrician training?")
    card = out["cards"][0]
    assert card["type"] == "ladder"
    assert card["data"]["steps"][0]["eligible"] is True
    assert "growth path" in out["reply_text"] and "Your child can start now." in out["reply_text"]


def test_follow_up_uses_last_trade(client):
    sid = new_session(client, learner_interests=[])
    say(client, sid, "Tell me about solar panel jobs and salary")
    out = say(client, sid, "How much does training cost?")
    assert out["cards"][0]["type"] == "costs"
    assert out["cards"][0]["data"]["trade_slug"] == "solar-pv-installer"


def test_unknown_trade_is_honest_and_logs_gap(client, SessionMaker):
    sid = new_session(client)
    out = say(client, sid, "How much does a plumber earn?")
    assert "I don't have reliable data on this yet. A counsellor can help — would you like that?" in out["reply_text"]
    assert out["cards"][0]["evidence"]["data_status"] == "unavailable"
    with SessionMaker() as db:
        gaps = db.scalars(select(m.EvidenceGap).where(m.EvidenceGap.session_id == sid)).all()
        assert len(gaps) == 1 and gaps[0].trade_slug == "plumber"


def test_two_gaps_escalate_with_no_data(client, SessionMaker):
    sid = new_session(client)
    say(client, sid, "What does a tailor earn?")
    out = say(client, sid, "And a welder?")
    assert out["escalation"] and out["escalation"]["trigger"] == "no_data"
    assert "counsellor" in out["reply_text"].lower()


def test_sensitive_topic_escalates(client, SessionMaker):
    sid = new_session(client)
    out = say(client, sid, "Is it safe for my daughter to work night shifts?")
    assert out["escalation"]["trigger"] == "sensitive_topic"
    with SessionMaker() as db:
        case = db.scalar(select(m.Escalation).where(m.Escalation.session_id == sid))
        assert case.summary_en.count("\n") == 2 and "Mysuru" in case.summary_en
        # English session: the local summary is the English one (always English + session language)
        assert case.summary_language == "en" and case.summary_local == case.summary_en
        assert db.get(m.SessionRow, sid).escalated is True


def test_counsellor_request_and_no_duplicate_case(client, SessionMaker):
    sid = new_session(client)
    a = say(client, sid, "I want to talk to a counsellor")
    b = say(client, sid, "Please, a counsellor")
    assert a["escalation"]["trigger"] == "user_request"
    assert b["escalation"]["id"] == a["escalation"]["id"]
    with SessionMaker() as db:
        assert db.scalar(select(func.count()).select_from(m.Escalation).where(m.Escalation.session_id == sid)) == 1


def test_negative_parent_sentiment_escalates(client):
    sid = new_session(client)
    say(client, sid, "I am very worried, this is a waste of time")
    say(client, sid, "I am scared, it is risky and not good")
    out = say(client, sid, "I don't want this, I am worried about the electrician pay")
    assert out["escalation"] and out["escalation"]["trigger"] == "negative_sentiment"


def test_alignment_feeds_context(client):
    sid = new_session(client)
    values = ["earning_soon", "near_home", "respect", "study_further", "safety"]
    client.post(f"/api/session/{sid}/alignment", json={"respondent": "learner", "ranking": values})
    r = client.post(f"/api/session/{sid}/alignment",
                    json={"respondent": "parent", "ranking": ["study_further", "safety", "respect", "near_home", "earning_soon"]})
    res = r.json()
    assert res["complete"] and res["biggest_difference"] == "earning_soon"
    out = say(client, sid, "How much can an electrician earn?")
    assert out["reply_text"].startswith("You both want what is best.")


def test_summary_built_from_shown_cards(client):
    sid = new_session(client)
    say(client, sid, "How much can an electrician earn?")
    say(client, sid, "What are the next steps after training?")
    s = client.get(f"/api/session/{sid}/summary").json()
    assert s["has_demo_data"] is True
    assert s["trades_discussed"][0]["slug"] == "electrician"
    assert s["figures"][0]["type"] == "outcome" and s["ladder"]["type"] == "ladder"


# ---------------------------------------------------------------- guardrail regeneration path
class LyingLLM(BaseLLM):
    """Calls the outcomes tool, then invents a salary; on correction it either fixes it or lies again."""
    is_mock = True

    def __init__(self, fix_on_retry: bool):
        self.fix = fix_on_retry
        self.calls = 0

    def respond(self, system, context_text, messages, tools, ctx):
        self.calls += 1
        last = messages[-1]["content"]
        if isinstance(last, str) and last.startswith("[Guardrail correction]"):
            text = "That is an important question. Please see the card below." if self.fix else "It pays ₹99,999."
            return LLMResponse("end_turn", [{"type": "text", "text": text}], text=text)
        if isinstance(last, list):
            text = "Electricians earn ₹99,999 a month."
            return LLMResponse("end_turn", [{"type": "text", "text": text}], text=text)
        call = ToolCall("t1", "get_trade_outcomes", {"trade_slug": "electrician", "district": "Mysuru"})
        return LLMResponse("tool_use", [{"type": "tool_use", "id": "t1", "name": call.name, "input": call.input}],
                           tool_calls=[call])


@pytest.mark.parametrize("fix,expected", [(True, "regenerated"), (False, "fallback")])
def test_guardrail_regenerates_then_falls_back(db, fix, expected):
    s = m.SessionRow(language="en", district="Mysuru", learner_education="class_10", consent_given=True)
    db.add(s)
    db.commit()
    out = handle_turn(db, s.id, "parent", "How much does an electrician earn?", "en", llm=LyingLLM(fix))
    assert out["guardrail_status"] == expected
    assert "99,999" not in out["reply_text"]
    assert out["cards"][0]["type"] == "outcome"  # cards come from tools, so they survive
    logs = db.scalars(select(m.GuardrailLog).where(m.GuardrailLog.session_id == s.id)).all()
    assert logs[0].outcome == "regenerated" and "₹99,999" in logs[0].unmatched[0]
    if expected == "fallback":
        assert logs[-1].outcome == "fallback"
        assert "counsellor" in out["reply_text"].lower()


def test_two_guardrail_fallbacks_escalate(db):
    s = m.SessionRow(language="en", district="Mysuru", learner_education="class_10", consent_given=True)
    db.add(s)
    db.commit()
    handle_turn(db, s.id, "learner", "How much?", "en", llm=LyingLLM(False))
    out = handle_turn(db, s.id, "learner", "How much again?", "en", llm=LyingLLM(False))
    assert out["escalation"]["trigger"] == "repeated_failure"


def test_mock_is_default_without_key():
    from app.llm import get_llm, set_llm
    set_llm(None)
    assert isinstance(get_llm(), MockLLM)


def test_kannada_inflected_cost_word_routes_to_costs(client):
    # "ಖರ್ಚಾಗುತ್ತದೆ" (inflected) must match the cost keyword stem — regression from the eval run.
    sid = new_session(client, language="kn")
    out = say(client, sid, "ಕಾರು ಮೆಕ್ಯಾನಿಕ್ ತರಬೇತಿಗೆ ಎಷ್ಟು ಖರ್ಚಾಗುತ್ತದೆ?", language="kn")
    assert out["cards"][0]["type"] == "costs"


def test_job_after_training_question_shows_outcomes(client):
    sid = new_session(client)
    out = say(client, sid, "Will a hospital assistant get a steady job after training?")
    assert out["cards"][0]["type"] == "outcome"
