"""Update 5: deterministic data fetching, centre relevance, degree-first answers, language purity, same-record numbers."""
import httpx
import pytest
from sqlalchemy import select

from app import models as m
from app.chat import QUICK, TOOLS, handle_turn, shown_cards
from app.data_tools import DataTools
from app.guardrail import centre_check, latin_check
from app.prefetch import plan
from tests.test_providers import Script, provider, reply


def session(db, lang="en", district="Mysuru", **kw):
    s = m.SessionRow(language=lang, district=district, learner_education="class_10", consent_given=True, **kw)
    db.add(s)
    db.commit()
    return s


# ---------------------------------------------------------------- the concern → tool map
@pytest.mark.parametrize("concern,tools", [
    ("income", ["get_trade_outcomes"]), ("job_security", ["get_trade_outcomes"]), ("other", ["get_trade_outcomes"]),
    ("cost", ["get_costs_and_support"]), ("degree_first", ["get_progression", "get_trade_outcomes"]),
    ("social_status", ["get_trade_outcomes", "get_progression"]), ("distance_migration", ["get_providers"]),
    ("safety", ["get_progression"]),
])
def test_concern_decides_the_data(concern, tools):
    ctx = {"concern": concern, "named_trade": "electrician", "district": "Mysuru", "learner_education": "class_10"}
    calls = plan("tell me about it", ctx)
    assert [n for n, _ in calls] == tools and all(a["trade_slug"] == "electrician" for _, a in calls)


def test_plan_uses_the_confirmed_goal_and_handles_special_cases():
    assert plan("How much can I earn?", {"concern": "income", "suggested_trade": "wireman"})[0][1]["trade_slug"] == "wireman"
    assert plan("What other options are there?", {"concern": "other"}) == [("list_trades", {"language": "en"})]
    assert plan("How much?", {"concern": "income"}) == [("list_trades", {"language": "en"})]
    assert plan("How much?", {"concern": "income", "goal": {"text": "drone pilot", "trades": []}})[0][0] == "match_aspiration"
    assert plan("Is it safe for my daughter to travel alone at night?", {"concern": "safety"})[0][0] == "escalate"


def test_the_answer_never_depends_on_the_model_choosing_a_tool(db):
    """The model calls no tool at all; the data and the card are there anyway, and the reply is checked against them."""
    script = Script(reply("It's natural to think about earnings first. The card shows what this data says."))
    llm, _ = provider("sarvam", script)
    out = handle_turn(db, session(db).id, "parent", "How much does a wireman earn?", "en", llm=llm)
    assert out["cards"][0]["type"] == "outcome" and out["cards"][0]["data"]["trade_slug"] == "wireman"
    assert db.scalar(select(m.Message).where(m.Message.role == "assistant")).tool_calls[0]["name"] == "get_trade_outcomes"


def test_the_chat_model_is_never_offered_goal_matching():
    assert "match_aspiration" not in {t["name"] for t in TOOLS}


def test_unmatched_goal_is_answered_by_the_template_without_a_model_call(db):
    script = Script()
    llm, _ = provider("sarvam", script)
    s = session(db, aspiration_text="drone pilot", aspiration_category="unknown")
    out = handle_turn(db, s.id, "learner", "How much can I earn?", "en", llm=llm)
    assert out["llm_provider"] == "template" and script.requests == []
    assert out["reply_text"].startswith("Thank you for sharing.")


# ---------------------------------------------------------------- unknown trade IDs → synonym matching
@pytest.mark.parametrize("given,slug", [("ev-technician", "ev-service-technician"), ("bike-mechanic", "two-wheeler-service-technician"),
                                        ("electrician", "electrician"), ("Wireman", "wireman")])
def test_close_trade_ids_are_resolved(db, given, slug):
    assert DataTools(db).resolve_trade(given).slug == slug


@pytest.mark.parametrize("given", ["plumber", "technician", "drone-pilot"])
def test_unclear_trade_ids_stay_unknown(db, given):
    assert DataTools(db).resolve_trade(given) is None


def test_synonyms_in_the_question_name_the_trade(db):
    out = handle_turn(db, session(db, "hi").id, "parent", "बिजली मिस्त्री कितना कमाता है?", "hi")
    assert out["cards"][0]["data"]["trade_slug"] == "electrician"


# ---------------------------------------------------------------- centres must teach the trade (te09)
def test_no_centre_for_this_trade_says_so_and_offers_the_nearest(db):
    out = handle_turn(db, session(db, "en", "Kalaburagi").id, "parent",
                      "Is there an EV technician training centre near us?", "en")
    assert "No training centre for this trade was found nearby in our data" in out["reply_text"]
    assert "Dharwad" in out["reply_text"] or "Mysuru" in out["reply_text"] or "Bengaluru" in out["reply_text"]
    assert "counsellor" in out["reply_text"].lower() and "ITI" not in out["reply_text"]
    r = DataTools(db).get_providers("ev-service-technician", "Kalaburagi")
    assert r["found"] is False and r["nearest_district"] in r["other_districts"]


@pytest.mark.parametrize("lang,text", [
    ("en", "Is there an EV training centre near us?"), ("kn", "ಹತ್ತಿರದಲ್ಲಿ ಇವಿ ತರಬೇತಿ ಕೇಂದ್ರ ಇದೆಯೇ?"),
    ("hi", "पास में ईवी ट्रेनिंग केंद्र है क्या?"), ("te", "దగ్గరలో ఈవీ శిక్షణ కేంద్రం ఉందా?"),
])
def test_a_reply_naming_another_trades_centre_is_regenerated(db, lang, text):
    wrong = {"en": "Yes, there is a Demo Government ITI nearby.", "kn": "ಹತ್ತಿರದಲ್ಲೇ ಡೆಮೊ ಸರ್ಕಾರಿ ಐಟಿಐ ಇದೆ.",
             "hi": "पास में डेमो सरकारी आईटीआई है।", "te": "దగ్గరలోనే డెమో ప్రభుత్వ ఐటీఐ ఉంది."}[lang]
    fixed = {"en": "Staying close to family matters. No training centre for this trade was found nearby in our data.",
             "kn": "ಕುಟುಂಬದ ಹತ್ತಿರ ಇರುವುದು ಮುಖ್ಯ. ನಮ್ಮ ಮಾಹಿತಿಯಲ್ಲಿ ಈ ತರಬೇತಿಯ ಕೇಂದ್ರ ಹತ್ತಿರದಲ್ಲಿ ಸಿಗಲಿಲ್ಲ.",
             "hi": "परिवार के पास रहना ज़रूरी है। हमारी जानकारी में इस ट्रेड का कोई ट्रेनिंग केंद्र पास में नहीं मिला।",
             "te": "కుటుంబానికి దగ్గరగా ఉండటం ముఖ్యం. మా సమాచారంలో ఈ ట్రేడ్‌కు దగ్గరలో శిక్షణ కేంద్రం దొరకలేదు."}[lang]
    script = Script(reply(wrong), reply(fixed))
    llm, _ = provider("sarvam", script)
    out = handle_turn(db, session(db, lang, "Kalaburagi").id, "parent", text, lang, llm=llm)
    assert out["reply_text"].startswith(fixed) and out["guardrail_status"] == "regenerated"
    assert "centre:government_iti" in db.scalar(select(m.GuardrailLog)).unmatched


def test_centre_check_accepts_only_the_discussed_trades_centres():
    ev_none = [{"found": False, "trade_slug": "ev-service-technician", "records": []}]
    elec = [{"found": True, "trade_slug": "electrician", "records": [{"name": "Demo Government ITI, Kalaburagi",
                                                                      "provider_type": "government_iti"}]}]
    assert centre_check("There is a Demo Government ITI nearby.", ev_none, "ev-service-technician") == ["government_iti"]
    assert centre_check("There is a Demo Government ITI nearby.", ev_none + elec, "ev-service-technician") == ["government_iti"]
    assert centre_check("You can visit Demo Government ITI, Kalaburagi.", elec, "electrician") == []
    assert centre_check("After ITI or Class 12 you can join.", [{"found": True, "entry": "After ITI or Class 12"}], "x") == []


# ---------------------------------------------------------------- degree first (kn07, te07)
@pytest.mark.parametrize("lang,text", [
    ("en", "Should we choose a degree first instead of hospital assistant training?"),
    ("kn", "ಆಸ್ಪತ್ರೆ ಸಹಾಯಕ ಬದಲು ಮೊದಲು ಪದವಿ ಮಾಡಿಸಬೇಕೇ?"),
    ("te", "ఆసుపత్రి సహాయకుడి బదులు ముందు డిగ్రీ చేయాలా?"),
])
def test_degree_first_explains_both_paths_from_the_ladder(db, lang, text):
    out = handle_turn(db, session(db, lang).id, "parent", text, lang)
    types = [c["type"] for c in out["cards"]]
    assert types[0] == "ladder" and "outcome" in types  # progression + outcomes were fetched
    ladder = out["cards"][0]["data"]["steps"]
    assert ladder[-1]["title"] in out["reply_text"]  # the later study step in the data is named
    honest = {"en": "a degree is also a good path", "kn": "ಪದವಿಯೂ ಒಳ್ಳೆಯ ದಾರಿ", "te": "డిగ్రీ"}[lang]
    assert honest in out["reply_text"]


def test_the_degree_first_context_asks_for_both_paths(db):
    script = Script(reply('{"concern_category": "degree_first", "sentiment": 0, "confidence": 0.9}'),
                    reply("Many families think about a degree first. The ladder shows both paths. Shall I show it?"),
                    auto_tag=False)
    llm, _ = provider("sarvam", script)
    handle_turn(db, session(db).id, "parent", "Should we do a degree first instead of electrician training?", "en", llm=llm)
    system = script.requests[1]["messages"][0]["content"]
    assert "Explain both paths from the ladder" in system and "Data already fetched" in system


# ---------------------------------------------------------------- language purity (asp-hi2)
@pytest.mark.parametrize("lang,mixed,clean", [
    ("hi", "कमाई के बारे में सोचना सही है। average about ₹15,000 महीने।",
     "कमाई के बारे में सोचना सही है। कार्ड में आँकड़े देखिए।"),
    ("kn", "ಸಂಪಾದನೆ ಮುಖ್ಯ. salary ಬಗ್ಗೆ ಕಾರ್ಡ್ ನೋಡಿ.", "ಸಂಪಾದನೆ ಮುಖ್ಯ. ಕಾರ್ಡ್ ನೋಡಿ."),
    ("te", "సంపాదన ముఖ్యం. monthly income కార్డులో ఉంది.", "సంపాదన ముఖ్యం. కార్డు చూడండి."),
])
def test_english_words_in_an_indian_language_reply_are_regenerated(db, lang, mixed, clean):
    script = Script(reply(mixed), reply(clean))
    llm, _ = provider("sarvam", script)
    out = handle_turn(db, session(db, lang).id, "parent", QUICK[lang]["outcome"], lang, llm=llm)
    assert out["reply_text"] == clean and out["guardrail_status"] == "regenerated"
    assert any(u.startswith("latin:") for u in db.scalar(select(m.GuardrailLog)).unmatched)
    correction = script.requests[1]["messages"][-1]["content"]
    assert "only ₹, %, ITI and NSQF" in correction


def test_a_stray_english_word_after_one_retry_does_not_throw_away_a_correct_answer(db):
    script = Script(reply("कमाई ज़रूरी है। salary कार्ड में है।"), reply("कमाई ज़रूरी है। card देखिए।"))
    llm, _ = provider("sarvam", script)
    out = handle_turn(db, session(db, "hi").id, "parent", QUICK["hi"]["outcome"], "hi", llm=llm)
    assert out["guardrail_status"] == "regenerated" and out["reply_text"] == "कमाई ज़रूरी है। card देखिए।"


def test_latin_check_allows_symbols_iti_nsqf_and_words_from_the_data():
    data = [{"reporting_period": "FY 2025-26", "trade_name": "ವಿದ್ಯುತ್ ವಾಹನ (EV) ಸರ್ವಿಸ್ ತಂತ್ರಜ್ಞ"}]
    assert latin_check("ಸುಮಾರು ₹15,000 (FY 2025-26). ITI ನಂತರ NSQF ಮಟ್ಟ. EV ಸರ್ವಿಸ್ 70%", data, "kn") == []
    assert latin_check("सुमारु average", data, "hi") == ["average"]
    assert latin_check("Any English at all", [], "en") == []


def test_names_are_passed_in_the_session_language(db):
    script = Script(reply("ಸಂಪಾದನೆ ಮುಖ್ಯ. ಕಾರ್ಡ್ ನೋಡಿ."))
    llm, _ = provider("sarvam", script)
    handle_turn(db, session(db, "kn").id, "parent", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಎಷ್ಟು ಸಂಪಾದಿಸುತ್ತಾರೆ?", "kn", llm=llm)
    system = script.requests[0]["messages"][0]["content"]
    assert "district = ಮೈಸೂರು" in system and "electrician = ಎಲೆಕ್ಟ್ರಿಷಿಯನ್" in system


# ---------------------------------------------------------------- same record for reply and card (kn02)
def test_each_trade_and_district_keeps_its_own_card():
    def outcome(slug, district, median):
        return ("get_trade_outcomes", {"found": True, "trade_slug": slug, "trade_name": slug,
                                       "records": [{"earnings_median": median, "district": district, "reporting_period": "FY",
                                                    "geo_level": "district", "data_status": "demo", "year": 2025,
                                                    "placement_rate": 70, "sample_size": 100}]}, {})
    cards = shown_cards([outcome("electrician", "Mysuru", 15000), outcome("wireman", "Mysuru", 12000),
                         outcome("electrician", "Mysuru", 15500)], "en")
    assert [(c["data"]["trade_slug"], c["data"]["earnings_median"]) for c in cards] == [("wireman", 12000), ("electrician", 15500)]


def test_a_number_from_a_record_that_is_not_on_a_card_is_rejected(db):
    """Reply numbers are checked against what the family can see (the cards), not every result fetched."""
    script = Script(reply(tool_calls=[("get_trade_outcomes", {"trade_slug": "electrician", "district": "Mysuru"})]),
                    reply("It's natural to think about earnings first. About 1% of learners found work."),
                    reply("It's natural to think about earnings first. The card shows the figures."))
    llm, _ = provider("sarvam", script)
    out = handle_turn(db, session(db).id, "parent", "How much does an electrician earn?", "en", llm=llm)
    assert out["guardrail_status"] == "regenerated" and "1%" not in out["reply_text"]
