"""Update 3 · Step 2: match_aspiration — the learner's own words → database trades only, never forced."""
import json

import pytest
from sqlalchemy import select

from app import aspiration, models as m
from app.data_tools import TOOL_SCHEMAS, DataTools


def match(db, text, lang="en", **kw):
    return DataTools(db, language=lang).match_aspiration(text, lang, **kw)


@pytest.mark.parametrize("lang,text,slug", [
    ("en", "I want to become an electrician", "electrician"),
    ("en", "house wiring", "wireman"),
    ("en", "hospital assistant", "general-duty-assistant"),
    ("kn", "ನಾನು ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಆಗಬೇಕು", "electrician"),
    ("kn", "ಸೋಲಾರ್ ಪ್ಯಾನೆಲ್ ಕೆಲಸ", "solar-pv-installer"),
    ("hi", "मुझे बिजली मिस्त्री बनना है", "electrician"),
    ("hi", "बुज़ुर्गों की देखभाल", "home-health-aide"),
    ("te", "బైక్ మెకానిక్ అవ్వాలి", "two-wheeler-service-technician"),
    ("te", "గ్యారేజ్ పని", "automotive-service-technician"),
])
def test_synonyms_match_in_all_four_languages(db, lang, text, slug):
    r = match(db, text, lang)
    assert r["matched"] and r["category"] == "vocational_match"
    assert r["candidates"][0]["slug"] == slug
    assert r["candidates"][0]["reason"] and r["confidence"] >= aspiration.MATCH_THRESHOLD


@pytest.mark.parametrize("text,slug", [
    ("bijli mistri", "electrician"), ("bijlee mistry", "electrician"),   # romanised Hindi, spelling variants
    ("current kelasa", "electrician"),                                     # romanised Kannada
    ("garage pani", "automotive-service-technician"),                      # romanised Telugu
    ("electrision", "electrician"),                                        # typo
])
def test_transliterated_and_misspelt_input(db, text, slug):
    r = match(db, text, "en")
    assert r["matched"] and r["candidates"][0]["slug"] == slug


def test_more_specific_match_ranks_first_and_at_most_three(db):
    r = match(db, "bike mechanic")
    assert [c["slug"] for c in r["candidates"]][:2] == ["two-wheeler-service-technician", "automotive-service-technician"]
    assert len(r["candidates"]) <= 3
    assert r["candidates"][0]["score"] > r["candidates"][1]["score"]


@pytest.mark.parametrize("text", ["drone pilot", "makeup artist", "plumber", "something with computers", "car"])
def test_low_confidence_is_not_matched_and_never_forced(db, text):
    r = match(db, text)
    assert r["matched"] is False and r["category"] == "unknown" and r["candidates"] == []
    assert r["text"] == text  # kept exactly as said


@pytest.mark.parametrize("lang,text,career", [
    ("en", "doctor", "doctor"), ("en", "software engineer", "engineer"), ("en", "Police officer", "police"),
    ("en", "teacher", "teacher"), ("hi", "डॉक्टर बनना है", "doctor"), ("kn", "ನಾನು ಇಂಜಿನಿಯರ್ ಆಗಬೇಕು", "engineer"),
    ("te", "నేను నర్సు అవ్వాలి", "nurse"), ("hi", "vakil", "lawyer"),
])
def test_degree_careers(db, lang, text, career):
    r = match(db, text, lang)
    assert r["matched"] is False and r["category"] == "degree_career" and r["degree_career"] == career
    assert r["candidates"] == []


def test_degree_career_offers_related_options_only_from_the_database(db):
    r = match(db, "doctor")
    assert r["related_sector"] == "healthcare"
    assert {c["slug"] for c in r["related"]} == {"general-duty-assistant", "home-health-aide"}
    assert match(db, "engineer")["related"] == []


def test_unmatched_goals_create_evidence_gaps(db):
    DataTools(db).match_aspiration("drone pilot", "en", district="Mysuru")
    DataTools(db).match_aspiration("doctor", "en", district="Kalaburagi")
    DataTools(db).match_aspiration("electrician", "en", district="Mysuru")
    gaps = list(db.scalars(select(m.EvidenceGap).where(m.EvidenceGap.tool_name == "match_aspiration")))
    assert [(g.query["aspiration_text"], g.district, g.query["category"]) for g in gaps] == [
        ("drone pilot", "Mysuru", "unknown"), ("doctor", "Kalaburagi", "degree_career")]
    assert all(g.query["language"] == "en" and g.trade_slug is None for g in gaps)


def test_gap_uses_the_session_district(db):
    s = m.SessionRow(district="Dharwad", learner_education="class_10", language="te")
    db.add(s)
    db.commit()
    DataTools(db, session_id=s.id, language="te").match_aspiration("makeup artist")
    gap = db.scalar(select(m.EvidenceGap).where(m.EvidenceGap.session_id == s.id))
    assert gap.district == "Dharwad" and gap.query["language"] == "te"


def test_tool_is_offered_to_the_model_and_runs_through_execute(db):
    assert any(t["name"] == "match_aspiration" for t in TOOL_SCHEMAS)
    r = DataTools(db).execute("match_aspiration", {"text": "wiring", "language": "en"})
    assert r["found"] and r["candidates"][0]["slug"] == "wireman"


# ---------------------------------------------------------------- real mode (fast model, candidate list only)
class FakeLLM:
    is_mock = False

    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def structured_json(self, system, text, schema):
        self.calls.append(schema)
        if isinstance(self.reply, Exception):
            raise self.reply
        return json.dumps(self.reply)


def test_real_mode_schema_restricts_slugs_to_the_candidate_list(db):
    llm = FakeLLM({"category": "vocational_match", "matches": [{"slug": "electrician", "score": 0.95}]})
    r = match(db, "bijli ka kaam", "hi", llm=llm)
    assert r["matched"] and r["mode"] == "model" and r["candidates"][0]["slug"] == "electrician"
    enum = llm.calls[0]["properties"]["matches"]["items"]["properties"]["slug"]["enum"]
    assert set(enum) == {t.slug for t in db.scalars(select(m.Trade))}


def test_real_mode_cannot_return_a_trade_outside_the_candidate_list(db):
    llm = FakeLLM({"category": "vocational_match", "matches": [
        {"slug": "drone-pilot", "score": 0.99}, {"slug": "plumber", "score": 0.9}]})
    r = match(db, "drone pilot", llm=llm)
    assert r["matched"] is False and r["candidates"] == []
    assert r["rejected_slugs"] == ["drone-pilot", "plumber"]
    assert db.scalar(select(m.EvidenceGap).where(m.EvidenceGap.tool_name == "match_aspiration")) is not None


def test_real_mode_low_scores_are_not_forced(db):
    llm = FakeLLM({"category": "vocational_match", "matches": [{"slug": "wireman", "score": 0.4}]})
    assert match(db, "something electrical maybe", llm=llm)["matched"] is False


def test_real_mode_degree_career(db):
    llm = FakeLLM({"category": "degree_career", "matches": []})
    r = match(db, "doctor", llm=llm)
    assert r["category"] == "degree_career" and r["related_sector"] == "healthcare" and not r["candidates"]


def test_real_mode_failure_falls_back_to_fuzzy(db):
    r = match(db, "bijli mistri", "hi", llm=FakeLLM(RuntimeError("timeout")))
    assert r["matched"] and r["mode"] == "fuzzy" and r["candidates"][0]["slug"] == "electrician"


def test_empty_text(db):
    r = match(db, "   ")
    assert r["matched"] is False and r["error"] == "empty text"


def test_multi_word_terms_need_every_word_close(db):
    """"bike mechanic" must not pull in "ev mechanic" just because most letters overlap."""
    assert "ev-service-technician" not in [c["slug"] for c in match(db, "bike mechanic")["candidates"]]
