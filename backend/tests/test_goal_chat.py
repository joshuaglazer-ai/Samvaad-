"""Update 3 · Step 4: the chat works from the learner's own goal; unmatched goals get a kind, number-free reply."""
import re

import pytest
from sqlalchemy import select

from app import lang_text as lt
from app.chat import QUICK
from app import models as m
from app.prompts import context_block

BASE = {"language": "en", "district": "Mysuru", "learner_education": "class_10", "consent_given": True}


def start(client, **goal):
    return client.post("/api/session", json=BASE | goal).json()["session_id"]


def ask(client, sid, text, lang="en", speaker="learner"):
    return client.post("/api/chat", json={"session_id": sid, "speaker": speaker, "text": text, "language": lang}).json()


def test_chat_answers_about_the_confirmed_goal_first(client, db):
    sid = start(client, aspiration={"text": "bike mechanic", "source": "text",
                                    "selected_slugs": ["two-wheeler-service-technician"]})
    r = ask(client, sid, "How much can I earn?")
    assert r["cards"] and r["cards"][0]["data"]["trade_slug"] == "two-wheeler-service-technician"
    assert "₹" in r["reply_text"]


@pytest.mark.parametrize("lang,text,key", [
    ("en", "doctor", "degree"), ("hi", "डॉक्टर", "degree"), ("en", "drone pilot", "unknown"), ("te", "మేకప్ ఆర్టిస్ట్", "unknown"),
])
def test_unmatched_goal_gets_a_kind_reply_without_numbers(client, db, lang, text, key):
    sid = client.post("/api/session", json=BASE | {"language": lang,
                                                   "aspiration": {"text": text, "language": lang, "source": "text"}}).json()["session_id"]
    r = ask(client, sid, QUICK[lang]["outcome"], lang)
    assert r["reply_text"].startswith(lt.GOAL_NOMATCH[lang][key])
    assert not re.search(r"[0-9०-९౦-౯₹]", r["reply_text"])
    assert r["cards"] == []
    assert QUICK[lang]["counsellor"] in r["quick_replies"] and QUICK[lang]["outcome"] not in r["quick_replies"]
    gaps = list(db.scalars(select(m.EvidenceGap).where(m.EvidenceGap.session_id == sid,
                                                       m.EvidenceGap.tool_name == "match_aspiration")))
    assert len(gaps) == 1 and gaps[0].query["aspiration_text"] == text  # saved once, not again per chat turn


def test_degree_goal_mentions_related_sector_from_the_database(client):
    sid = start(client, aspiration={"text": "doctor", "source": "text"})
    r = ask(client, sid, "What can I do?")
    assert "Healthcare" in r["reply_text"]
    sid = start(client, aspiration={"text": "engineer", "source": "text"})
    assert ask(client, sid, "What can I do?")["reply_text"] == lt.GOAL_NOMATCH["en"]["degree"]


@pytest.mark.parametrize("lang,text", [("en", "nurse"), ("hi", "नर्स")])
def test_nursing_goal_reply_is_not_called_a_degree_and_keeps_related_offer(client, lang, text):
    sid = client.post("/api/session", json=BASE | {"language": lang,
                                                   "aspiration": {"text": text, "language": lang, "source": "text"}}).json()["session_id"]
    r = ask(client, sid, QUICK[lang]["outcome"], lang)
    assert r["reply_text"].startswith(lt.GOAL_NOMATCH[lang]["professional"])
    assert lt.GOAL_NOMATCH[lang]["related"].split("{sector}")[0].strip() in r["reply_text"]
    assert "degree" not in r["reply_text"].lower() and not re.search(r"[0-9०-९₹]", r["reply_text"])


def test_family_can_still_ask_for_other_options(client):
    sid = start(client, aspiration={"text": "drone pilot", "source": "text"})
    r = ask(client, sid, "Show other options")
    assert "Electrician" in r["reply_text"]


def test_naming_a_trade_in_chat_still_works_with_an_unmatched_goal(client):
    sid = start(client, aspiration={"text": "drone pilot", "source": "text"})
    r = ask(client, sid, "How much does an electrician earn?")
    assert r["cards"][0]["data"]["trade_slug"] == "electrician"


def test_change_goal_is_used_by_the_next_turn(client):
    sid = start(client, aspiration={"text": "drone pilot", "source": "text"})
    client.put(f"/api/session/{sid}/aspiration", json={"who": "learner", "source": "browse",
                                                        "selected_slugs": ["solar-pv-installer"]})
    r = ask(client, sid, "How much can I earn?")
    assert r["cards"][0]["data"]["trade_slug"] == "solar-pv-installer"


def test_context_block_carries_goal_and_parent_hope(client, db):
    from app.chat import build_context

    sid = start(client, aspiration={"text": "bijli mistri", "language": "hi", "source": "text",
                                    "selected_slugs": ["electrician"]},
                parent_hope={"text": "doctor", "source": "voice"})
    block = context_block(build_context(db, db.get(m.SessionRow, sid), "learner", "en", "hi"))
    assert '- learner_goal: "bijli mistri" → electrician' in block
    assert '- parent_hope: "doctor" → no database match (degree_career)' in block
    assert "differ" in block and "suggested" not in block
    assert "trade for the learner's goal (if they have not named another): electrician" in block
