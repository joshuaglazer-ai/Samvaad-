"""The reply addresses the concern tagged before it was written, and states no unsupported facts (Update 4)."""
import httpx
import pytest
from sqlalchemy import select

from app import lang_text as lt
from app import models as m
from app.chat import QUICK, handle_turn
from app.guardrail import claim_check, correction_note
from app.mock_counsellor import REASSURE
from tests.test_providers import Script, provider, reply


def session(db, lang="en", district="Mysuru"):
    s = m.SessionRow(language=lang, district=district, learner_education="class_10", consent_given=True)
    db.add(s)
    db.commit()
    return s


# ---------------------------------------------------------------- concern first
@pytest.mark.parametrize("lang,text", [
    ("en", "How much does electrician training cost?"),
    ("kn", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ತರಬೇತಿಗೆ ಎಷ್ಟು ಖರ್ಚಾಗುತ್ತದೆ?"),   # the reply that was about income in the live test
    ("hi", "इलेक्ट्रीशियन ट्रेनिंग की फ़ीस कितनी है?"),
    ("te", "ఎలక్ట్రీషియన్ శిక్షణకు ఎంత ఖర్చు అవుతుంది?"),
])
def test_mock_reply_addresses_the_tagged_cost_concern(db, lang, text):
    out = handle_turn(db, session(db, lang).id, "parent", text, lang)
    user = db.scalar(select(m.Message).where(m.Message.role == "user"))
    assert user.concern_category == "cost"
    assert any(out["reply_text"].startswith(r) for r in REASSURE[lang]["cost"])  # reassurance about cost, not income
    assert out["cards"][0]["type"] == "costs" and lt.addresses_concern(out["reply_text"], "cost")


def test_the_tagged_concern_reaches_the_model_before_it_answers(db):
    script = Script(reply('{"concern_category": "cost", "sentiment": 0, "confidence": 0.9}'),   # tagging, first
                    reply("Cost is an important part of this decision. The card shows the fees. Shall I show centres?"),
                    auto_tag=False)
    llm, _ = provider("sarvam", script)
    handle_turn(db, session(db).id, "parent", "How much does solar training cost?", "en", llm=llm)
    assert script.requests[0]["model"] == "sarvam-small"  # the concern was tagged before the reply was written
    system = script.requests[1]["messages"][0]["content"]
    assert "The family is asking about: cost" in system and "must both address this" in system


@pytest.mark.parametrize("reply_text,concern,ok", [
    ("Cost is an important part of this decision. Fees are on the card.", "cost", True),
    ("It's natural to think about earnings first. Electricians earn well.", "cost", False),
    ("ನಿಮ್ಮ ಮಗುವಿನ ಸುರಕ್ಷತೆ ಎಲ್ಲಕ್ಕಿಂತ ಮುಖ್ಯ.", "safety", True),
    ("कमाई के बारे में सोचना स्वाभाविक है।", "income", True),
    ("మీ పిల్లల భద్రత చాలా ముఖ్యం.", "cost", False),
    ("Thank you for asking.", "other", True),
])
def test_addresses_concern_check(reply_text, concern, ok):
    assert lt.addresses_concern(reply_text, concern) is ok


# ---------------------------------------------------------------- claim check, four languages
NO_SUPPORT = [{"found": True, "records": [{"earnings_median": 15000, "placement_rate": 70.0}],
               "source": {"title": "SAMVAAD simulated demo dataset"}}]


@pytest.mark.parametrize("text,claims", [
    ("These courses are free at government centres.", ["government", "free"]),
    ("A job is guaranteed after this certified, accredited course.", ["guaranteed", "certified", "accredited"]),
    ("ಸರ್ಕಾರಿ ಕೇಂದ್ರಗಳಲ್ಲಿ ಉಚಿತ ತರಬೇತಿ ಇದೆ.", ["government", "free"]),
    ("ಕೆಲಸ ಗ್ಯಾರಂಟಿ, ಪ್ರಮಾಣೀಕೃತ ಕೋರ್ಸ್.", ["guaranteed", "certified"]),
    ("सरकारी केंद्र में मुफ़्त ट्रेनिंग है।", ["government", "free"]),
    ("नौकरी की गारंटी है, कोर्स मान्यता प्राप्त है।", ["guaranteed", "accredited"]),
    ("ప్రభుత్వ కేంద్రాల్లో ఉచిత శిక్షణ ఉంది.", ["government", "free"]),
    ("ఉద్యోగం గ్యారంటీ, సర్టిఫైడ్ కోర్సు.", ["guaranteed", "certified"]),
    ("sarkari ITI mein muft training hai.", ["government", "free"]),
])
def test_unsupported_claims_are_flagged_in_every_language(text, claims):
    assert claim_check(text, NO_SUPPORT) == claims


@pytest.mark.parametrize("text,support", [
    ("Some courses are free.", [{"records": [{"fee_min": 0, "fee_max": 12000}]}]),           # fee 0 → free
    ("ಕೆಲವು ಕೋರ್ಸ್‌ಗಳು ಉಚಿತ.", [{"records": [{"fee_min": 0}]}]),
    ("You can visit the government ITI.", [{"records": [{"provider_type": "government_iti", "name": "Demo ITI"}]}]),
    ("यह केंद्र मान्यता प्राप्त है।", [{"records": [{"accreditation": "NCVET"}]}]),
    ("ప్రభుత్వ కోర్సులు చాలాసార్లు ఉచితం.", [{"supports": [{"description": "ప్రభుత్వ కోర్సులు చాలాసార్లు ఉచితం."}]}]),
    ("Feel free to ask more.", NO_SUPPORT),                                                  # not a claim
])
def test_claims_supported_by_the_tool_results_pass(text, support):
    assert claim_check(text, support) == []


def test_correction_note_names_the_claims_and_the_language():
    note = correction_note([], "te", ["government", "free"])
    assert "government" in note and "free / no fee" in note and note.endswith("Reply in Telugu.")
    assert "Reply in Hindi." in correction_note(["₹99"], "hi")


@pytest.mark.parametrize("lang,bad,good", [
    ("en", "Training is free at government centres.", "Earnings matter to every family. The card shows the figures."),
    ("kn", "ಸರ್ಕಾರಿ ಕೇಂದ್ರಗಳಲ್ಲಿ ಉಚಿತ ತರಬೇತಿ ಇದೆ.", "ಸಂಪಾದನೆ ಪ್ರತಿಯೊಂದು ಕುಟುಂಬಕ್ಕೂ ಮುಖ್ಯ. ಕಾರ್ಡ್ ನೋಡಿ."),
    ("hi", "सरकारी केंद्र में नौकरी की गारंटी है।", "कमाई हर परिवार के लिए ज़रूरी है। कार्ड देखिए।"),
    ("te", "ప్రభుత్వ కేంద్రాల్లో ఉద్యోగం గ్యారంటీ.", "సంపాదన ప్రతి కుటుంబానికీ ముఖ్యం. కార్డు చూడండి."),
])
def test_an_unsupported_claim_is_regenerated_once(db, lang, bad, good):
    script = Script(reply(tool_calls=[("get_trade_outcomes", {"trade_slug": "electrician", "district": "Mysuru"})]),
                    reply(bad), reply(good))
    llm, _ = provider("sarvam", script)
    out = handle_turn(db, session(db, lang).id, "parent", QUICK[lang]["outcome"], lang, llm=llm)
    assert out["guardrail_status"] == "regenerated" and out["reply_text"] == good
    log = db.scalar(select(m.GuardrailLog))
    assert log.outcome == "regenerated" and any(u.startswith("claim:") for u in log.unmatched)
    assert "[Guardrail correction]" in script.requests[2]["messages"][-1]["content"]


@pytest.mark.parametrize("lang", ["en", "kn", "hi", "te"])
def test_a_repeated_unsupported_claim_falls_back_to_the_safe_message(db, lang):
    bad = {"en": "A job is guaranteed.", "kn": "ಕೆಲಸ ಗ್ಯಾರಂಟಿ.", "hi": "नौकरी की गारंटी है।", "te": "ఉద్యోగం గ్యారంటీ."}[lang]
    script = Script(reply(tool_calls=[("get_trade_outcomes", {"trade_slug": "electrician", "district": "Mysuru"})]),
                    reply(bad), reply(bad))
    llm, _ = provider("gemini", script)
    out = handle_turn(db, session(db, lang).id, "parent", QUICK[lang]["outcome"], lang, llm=llm)
    assert out["guardrail_status"] == "fallback" and bad not in out["reply_text"]
    logs = list(db.scalars(select(m.GuardrailLog).order_by(m.GuardrailLog.attempt)))
    assert [g.outcome for g in logs] == ["regenerated", "fallback"] and "claim:guaranteed" in logs[1].unmatched


def test_hedged_text_from_the_data_is_allowed(db):
    """The costs data itself says government courses are often free — repeating that is supported."""
    script = Script(reply(tool_calls=[("get_costs_and_support", {"trade_slug": "electrician", "district": "Mysuru"})]),
                    reply("Cost is an important part of this decision. Government-run courses are often free. "
                          "Shall I show centres near you?"))
    llm, _ = provider("sarvam", script)
    out = handle_turn(db, session(db).id, "parent", "How much does electrician training cost?", "en", llm=llm)
    assert out["guardrail_status"] == "pass"


def test_the_prompt_states_the_facts_rule():
    from app.prompts import SYSTEM_PROMPT

    assert "Only state facts that appear in the tool results" in SYSTEM_PROMPT
    assert "who runs a centre, government status" in SYSTEM_PROMPT and "eligibility unless the tool result says so" in SYSTEM_PROMPT
