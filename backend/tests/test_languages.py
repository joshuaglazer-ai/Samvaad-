"""Hindi and Telugu support (Update 2, Section 1)."""
import re
from pathlib import Path

import pytest

from app import i18n
from app.guardrail import check
from app.i18n import detect_script, tr
from app.mock_counsellor import detect_trade, plan
from app.sentiment import is_sensitive, keyword_tag, wants_counsellor

TOOLS = [{"earnings_median": 14250, "earnings_min": 12000, "placement_rate": 73.6, "fee_max": 118000,
          "reporting_period": "FY 2025-26"}]


# ---------------------------------------------------------------- guardrail: digits and number words
@pytest.mark.parametrize("text", [
    "आमतौर पर लगभग ₹१४,००० महीना।",          # Devanagari digits + लगभग
    "₹१२,००० से शुरू।",
    "लगभग ७४% को काम मिला।",
    "लगभग 74 प्रतिशत को काम मिला।",
    "फ़ीस 1.18 लाख तक।",
    "12 हज़ार रुपये से शुरू।",
    "నెలకు సుమారు ₹౧౪,౦౦౦.",                  # Telugu digits + సుమారు
    "సుమారు 74 శాతం మందికి పని దొరికింది.",
    "ఫీజు 1.18 లక్ష వరకు.",
    "12 వేలు నుండి మొదలు.",
    "12 హజార్ నుండి మొదలు.",
])
def test_indic_numbers_are_checked_and_pass(text):
    assert check(text, TOOLS).passed, text


@pytest.mark.parametrize("text", ["लगभग ₹२५,००० महीना।", "90 प्रतिशत को काम।", "నెలకు ₹౨౫,౦౦౦.", "90 శాతం మందికి.",
                                  "2 लाख तक।", "5 లక్ష వరకు."])
def test_unsupported_indic_numbers_fail(text):
    assert not check(text, TOOLS).passed, text


def test_school_classes_in_hindi_and_telugu_are_exempt():
    assert check("12वीं के बाद डिप्लोमा।", []).passed
    assert check("कक्षा 12 के बाद।", []).passed
    assert check("12వ తరగతి తర్వాత.", []).passed


# ---------------------------------------------------------------- tagging, sensitivity, routing
@pytest.mark.parametrize("text,concern", [
    ("इलेक्ट्रीशियन कितना कमा सकता है?", "income"),
    ("क्या स्थिर नौकरी मिलेगी?", "job_security"),
    ("क्या समाज में इज़्ज़त मिलेगी?", "social_status"),
    ("क्या यह काम सुरक्षित है?", "safety"),
    ("ट्रेनिंग की फ़ीस कितनी है?", "cost"),
    ("ఎలక్ట్రీషియన్ ఎంత సంపాదిస్తారు?", "income"),
    ("ఈ పనిలో ప్రమాదం ఉందా?", "safety"),
    ("శిక్షణకు ఎంత ఖర్చవుతుంది?", "cost"),
    ("ముందు డిగ్రీ చదవాలా?", "degree_first"),
])
def test_concern_tagging(text, concern):
    assert keyword_tag(text).concern_category == concern


def test_sensitive_and_counsellor_requests():
    assert is_sensitive("क्या मेरी बेटी का रात में अकेले काम पर जाना सुरक्षित है?")
    assert is_sensitive("हम पर कर्ज़ का बोझ है।")
    assert is_sensitive("మా అమ్మాయి రాత్రి ఒంటరిగా పనికి వెళ్లడం సురక్షితమేనా?")
    assert is_sensitive("మాకు అప్పుల భారం ఉంది.")
    assert not is_sensitive("क्या यह काम सुरक्षित है?")
    assert wants_counsellor("मुझे काउंसलर से बात करनी है")
    assert wants_counsellor("కౌన్సిలర్‌తో మాట్లాడాలి")


def test_trade_and_intent_detection():
    assert detect_trade("सोलर पैनल का काम") == "solar-pv-installer"
    assert detect_trade("ఈవీ టెక్నీషియన్") == "ev-service-technician"
    assert detect_trade("प्लंबर कितना कमाता है?") == "plumber"
    assert plan("ट्रेनिंग के बाद अगले कदम क्या हैं?", {"last_trade": "electrician"})[0][0] == "get_progression"
    assert plan("శిక్షణకు ఎంత ఖర్చవుతుంది?", {"last_trade": "electrician"})[0][0] == "get_costs_and_support"


# ---------------------------------------------------------------- chat end to end in hi / te
def _session(client, lang):
    r = client.post("/api/session", json={"language": lang, "district": "Mysuru", "learner_education": "class_10",
                                          "consent_given": True})
    return r.json()["session_id"]


@pytest.mark.parametrize("lang,question,marker", [
    ("hi", "इलेक्ट्रीशियन कितना कमा सकता है?", "लगभग ₹"),
    ("te", "ఎలక్ట్రీషియన్ ఎంత సంపాదిస్తారు?", "సుమారు ₹"),
])
def test_hindi_and_telugu_answers(client, lang, question, marker):
    sid = _session(client, lang)
    out = client.post("/api/chat", json={"session_id": sid, "speaker": "parent", "text": question, "language": lang}).json()
    assert out["guardrail_status"] == "pass"
    assert marker in out["reply_text"]
    assert out["cards"][0]["type"] == "outcome"
    assert detect_script(out["reply_text"]) == lang


def test_reply_in_the_language_the_family_used_and_offer_to_switch(client):
    sid = _session(client, "en")
    out = client.post("/api/chat", json={"session_id": sid, "speaker": "parent", "text": "इलेक्ट्रीशियन कितना कमा सकता है?",
                                         "language": "en"}).json()
    assert out["reply_language"] == "hi" and out["suggest_language"] == "hi"
    assert detect_script(out["reply_text"]) == "hi"
    assert "भाषा हिंदी" in out["reply_text"]
    # Latin text never switches (it could be English or transliteration)
    out2 = client.post("/api/chat", json={"session_id": sid, "speaker": "parent", "text": "kitna kamata hai electrician",
                                          "language": "en"}).json()
    assert out2["suggest_language"] is None


def test_escalation_summary_english_plus_telugu(client, SessionMaker):
    from sqlalchemy import select

    from app import models as m
    sid = _session(client, "te")
    client.post("/api/chat", json={"session_id": sid, "speaker": "parent",
                                   "text": "మా అమ్మాయి రాత్రి ఒంటరిగా పనికి వెళ్లడం సురక్షితమేనా?", "language": "te"})
    with SessionMaker() as db:
        case = db.scalar(select(m.Escalation).where(m.Escalation.session_id == sid))
        assert case.summary_language == "te"
        assert "Telugu" in case.summary_en and "Mysuru" in case.summary_en
        assert "మైసూరు" in case.summary_local and detect_script(case.summary_local) == "te"


# ---------------------------------------------------------------- data + translation fallback
def test_data_tools_return_hindi_and_telugu_names(db):
    from app.data_tools import DataTools
    assert DataTools(db, language="hi").get_trade_outcomes("electrician", "Mysuru")["trade_name"] == "इलेक्ट्रीशियन"
    lad = DataTools(db, language="te").get_progression("general-duty-assistant", None)
    assert any("నర్సింగ్" in s["title"] for s in lad["records"])
    st = DataTools(db, language="hi").get_trade_outcomes("ev-service-technician", "Kalaburagi")
    assert "राज्य" in st["limitations"][0]


def test_missing_translation_falls_back_to_english_and_is_logged(caplog):
    with caplog.at_level("WARNING", logger="samvaad.i18n"):
        assert tr({"en": "Electrician", "kn": "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್"}, "te", "test.field") == "Electrician"
    assert any("missing te translation for test.field" in r.message for r in caplog.records)
    assert i18n.missing_counter.get("te", 0) >= 1


def test_no_mixed_script_typos_in_translated_text():
    root = Path(__file__).resolve().parent.parent
    ranges = {"deva": (0x900, 0x97F), "kn": (0xC80, 0xCFF), "te": (0xC00, 0xC7F)}
    for path in [root / "seed" / "reference_data.py", root / "app" / "lang_text.py", root / "app" / "mock_counsellor.py"]:
        for lit in re.findall(r'"([^"]+)"', path.read_text(encoding="utf-8")):
            scripts = {n for n, (a, b) in ranges.items() if any(a <= ord(c) <= b for c in lit)}
            assert len(scripts) <= 1, f"{path.name}: mixed scripts in {lit!r}"
