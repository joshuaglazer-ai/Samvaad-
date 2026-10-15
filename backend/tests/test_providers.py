"""Free providers (Sarvam, Gemini) behind the LLM interface — tested with a fake HTTP transport, no network."""
import json

import httpx
import pytest
from sqlalchemy import select

from app import models as m
from app.chat import TOOLS, handle_turn
from app.config import Settings
from app.llm import MockLLM, build_llm
from app.providers import FallbackLLM, OpenAICompatLLM, ProviderError, to_openai_messages, to_openai_tools
from app.sentiment import tag_message


def reply(content=None, tool_calls=None, finish="stop"):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = [{"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
                             for i, (n, a) in enumerate(tool_calls)]
        finish = "tool_calls"
    return httpx.Response(200, json={"choices": [{"index": 0, "message": msg, "finish_reason": finish}]})


class Script:
    """Fake provider: returns queued responses in order and records every request body."""

    def __init__(self, *responses, auto_tag=True):
        self.queue, self.requests, self.tag_requests, self.auto_tag = list(responses), [], [], auto_tag

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["model"].endswith("-small") and "tools" not in body and self.auto_tag:  # per-message tagging call
            self.tag_requests.append(body)
            return reply('{"concern_category": "income", "sentiment": 0, "confidence": 0.7}')
        self.requests.append(body)
        r = self.queue.pop(0)
        return r(request) if callable(r) else r


def provider(name, script, **kw):
    sleeps = []
    llm = OpenAICompatLLM(name, f"https://{name}.test/v1", {"api-subscription-key": "x"}, f"{name}-big", f"{name}-small",
                          transport=httpx.MockTransport(script), sleep=sleeps.append, **kw)
    return llm, sleeps


def session(db, lang="en", district="Mysuru"):
    s = m.SessionRow(language=lang, district=district, learner_education="class_10", consent_given=True)
    db.add(s)
    db.commit()
    return s


# ---------------------------------------------------------------- translation
def test_messages_and_tools_translate_to_openai_format():
    msgs = [{"role": "user", "content": "[parent] How much?"},
            {"role": "assistant", "content": [{"type": "text", "text": "Let me check."},
                                              {"type": "tool_use", "id": "t1", "name": "get_trade_outcomes",
                                               "input": {"trade_slug": "electrician"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{\"found\": true}"}]}]
    out = to_openai_messages("SYS", "CTX", msgs)
    assert out[0] == {"role": "system", "content": "SYS\n\nCTX"}
    assert out[2]["tool_calls"][0]["function"] == {"name": "get_trade_outcomes", "arguments": '{"trade_slug": "electrician"}'}
    assert out[3] == {"role": "tool", "tool_call_id": "t1", "name": "get_trade_outcomes", "content": '{"found": true}'}
    strict = to_openai_tools(TOOLS, strict_schema=True)
    loose = to_openai_tools(TOOLS, strict_schema=False)
    assert {t["function"]["name"] for t in strict} == {t["name"] for t in TOOLS}
    assert "additionalProperties" in json.dumps(strict) and "additionalProperties" not in json.dumps(loose)


# ---------------------------------------------------------------- chat turns
def test_native_tool_calling_round_trip_and_provider_is_logged(db):
    script = Script(reply(tool_calls=[("get_trade_outcomes", {"trade_slug": "electrician", "district": "Mysuru"})]),
                    reply("It's natural to think about earnings. The card shows the figures. Shall I show the growth path?"))
    llm, _ = provider("sarvam", script)
    s = session(db)
    out = handle_turn(db, s.id, "parent", "How much does an electrician earn?", "en", llm=llm)
    assert out["cards"][0]["data"]["trade_slug"] == "electrician" and out["guardrail_status"] == "pass"
    assert out["llm_provider"] == "sarvam"
    assert db.get(m.Message, out["message_id"]).llm_provider == "sarvam"
    second = script.requests[1]["messages"]
    assert second[-1]["role"] == "tool" and '"found": true' in second[-1]["content"]
    assert script.requests[0]["model"] == "sarvam-big" and script.requests[0]["tool_choice"] == "auto"


def test_figures_without_tools_make_the_backend_call_the_data_tools(db):
    """A model that skips tool calling and states a number never gets that number through."""
    script = Script(reply("Electricians earn ₹99,999 a month."),  # invented figure, no tool call
                    reply("Earnings matter to every family. The card shows what this data says. Shall I show more?"))
    llm, _ = provider("gemini", script)
    s = session(db)
    out = handle_turn(db, s.id, "parent", "How much does an electrician earn?", "en", llm=llm)
    assert "99,999" not in out["reply_text"]
    assert out["cards"] and out["cards"][0]["type"] == "outcome"  # the backend fetched the data itself
    assert script.requests[1]["messages"][-1]["role"] == "tool"


def test_backend_tool_mode_calls_tools_before_the_model(db):
    script = Script(reply("Many families have this question. The card shows the cost. Shall I show centres near you?"))
    llm, _ = provider("sarvam", script, tool_mode="backend")
    s = session(db)
    out = handle_turn(db, s.id, "parent", "How much does solar training cost?", "en", llm=llm)
    assert len(script.requests) == 1 and script.requests[0]["messages"][-1]["role"] == "tool"
    assert out["cards"][0]["type"] == "costs"


def test_guardrail_still_rejects_unsupported_numbers_from_a_provider(db):
    script = Script(reply(tool_calls=[("get_trade_outcomes", {"trade_slug": "electrician", "district": "Mysuru"})]),
                    reply("They earn about ₹77,000 a month."), reply("They earn about ₹77,000 a month."))
    llm, _ = provider("sarvam", script)
    out = handle_turn(db, session(db).id, "parent", "How much does an electrician earn?", "en", llm=llm)
    assert out["guardrail_status"] == "fallback" and "77,000" not in out["reply_text"]


# ---------------------------------------------------------------- rate limits and fallback
def test_429_is_retried_with_backoff_at_most_twice(db):
    script = Script(httpx.Response(429, headers={"retry-after": "3"}), httpx.Response(429),
                    reply("Thank you for asking. Would you like to see the options?"))
    llm, sleeps = provider("sarvam", script)
    out = llm.respond("S", "C", [{"role": "user", "content": "hello"}], TOOLS, {"user_text": "hello"})
    assert out.text.startswith("Thank you") and sleeps == [3.0, 3.0]  # Retry-After honoured, then 1.5 × 2


def test_still_rate_limited_falls_back_to_the_next_provider_then_mock(db):
    sarvam, s_sleeps = provider("sarvam", Script(*[httpx.Response(429)] * 3))
    gemini, _ = provider("gemini", Script(httpx.Response(500, text="boom")))
    chain = FallbackLLM([sarvam, gemini, MockLLM()])
    out = handle_turn(db, session(db).id, "parent", "How much does an electrician earn?", "en", llm=chain)
    assert len(s_sleeps) == 2  # two retries, then give up on sarvam
    assert out["llm_provider"] == "mock" and out["cards"][0]["data"]["trade_slug"] == "electrician"
    assert db.get(m.Message, out["message_id"]).llm_provider == "mock"


def test_fallback_uses_the_next_provider_and_keeps_it_for_the_turn(db):
    sarvam, _ = provider("sarvam", Script(httpx.Response(401, text="bad key")))
    gemini_script = Script(reply(tool_calls=[("list_trades", {"language": "en"})]),
                           reply("Thank you for asking. Some options are on the list. Which one interests you?"))
    gemini, _ = provider("gemini", gemini_script)
    out = handle_turn(db, session(db).id, "parent", "What options are there?", "en",
                      llm=FallbackLLM([sarvam, gemini, MockLLM()]))
    assert out["llm_provider"] == "gemini" and len(gemini_script.requests) == 2


def test_refusal_gives_the_safe_fallback(db):
    llm, _ = provider("gemini", Script(reply("", finish="content_filter")))
    out = handle_turn(db, session(db).id, "parent", "Tell me about jobs", "en", llm=llm)
    assert out["guardrail_status"] == "fallback"


# ---------------------------------------------------------------- small JSON tasks
def test_tagging_uses_the_fast_model_and_falls_back_to_keywords():
    script = Script(reply('{"concern_category": "safety", "sentiment": -1, "confidence": 0.8}'), auto_tag=False)
    llm, _ = provider("sarvam", script)
    tag = tag_message("Is it safe at night?", llm)
    assert tag.concern_category == "safety" and script.requests[0]["model"] == "sarvam-small"
    assert script.requests[0]["response_format"] == {"type": "json_object"}
    broken, _ = provider("sarvam", Script(httpx.Response(500), auto_tag=False))
    assert tag_message("How much salary?", broken).concern_category == "income"  # keyword tagger


def test_structured_json_retries_without_response_format_on_400():
    script = Script(httpx.Response(400, text="response_format not supported"),
                    reply('Here: {"category": "unknown", "matches": []}'), auto_tag=False)
    llm, _ = provider("sarvam", script)
    out = json.loads(llm.structured_json("S", "drone pilot", {"type": "object"}))
    assert out == {"category": "unknown", "matches": []} and "response_format" not in script.requests[1]


def test_aspiration_matching_with_a_provider_and_with_a_failing_chain(db):
    from app.data_tools import DataTools

    script = Script(reply('{"category": "vocational_match", "matches": [{"slug": "electrician", "score": 0.93}]}'),
                    auto_tag=False)
    llm, _ = provider("gemini", script, strict_schema=False)
    r = DataTools(db).match_aspiration("bijli ka kaam", "hi", llm=llm)
    assert r["matched"] and r["mode"] == "model"
    assert "additionalProperties" not in json.dumps(script.requests[0]["response_format"])
    dead = FallbackLLM([provider("sarvam", Script(httpx.Response(500), auto_tag=False))[0], MockLLM()])
    assert DataTools(db).match_aspiration("bijli mistri", "hi", llm=dead)["mode"] == "fuzzy"


# ---------------------------------------------------------------- configuration
@pytest.mark.parametrize("env,chain", [
    ({"llm_provider": "mock", "sarvam_api_key": "k", "gemini_api_key": "k"}, ["mock"]),
    ({"llm_provider": "sarvam", "sarvam_api_key": "k", "gemini_api_key": "k"}, ["sarvam", "gemini", "mock"]),
    ({"llm_provider": "gemini", "sarvam_api_key": "k", "gemini_api_key": "k"}, ["gemini", "sarvam", "mock"]),
    ({"llm_provider": "sarvam", "sarvam_api_key": "", "gemini_api_key": "k"}, ["gemini", "mock"]),
    ({"llm_provider": "sarvam"}, ["mock"]),
    ({"llm_provider": "", "llm_mode": "anthropic", "anthropic_api_key": "k"}, ["anthropic", "mock"]),  # old setting
])
def test_provider_chain(env, chain):
    base = {"sarvam_api_key": "", "gemini_api_key": "", "anthropic_api_key": "", "llm_mode": "mock"}
    s = Settings(_env_file=None, **(base | env))
    assert s.provider_chain == chain and s.use_mock_llm == (chain[0] == "mock")


def test_build_llm_wires_the_chain():
    s = Settings(_env_file=None, llm_provider="sarvam", sarvam_api_key="k", gemini_api_key="g", anthropic_api_key="")
    llm = build_llm(s)
    assert isinstance(llm, FallbackLLM) and [x.name for x in llm.chain] == ["sarvam", "gemini", "mock"]
    sarvam = llm.chain[0]
    assert sarvam.url == "https://api.sarvam.ai/v1/chat/completions" and sarvam.headers == {"api-subscription-key": "k"}
    assert sarvam.model == "sarvam-105b" and llm.chain[1].headers == {"Authorization": "Bearer g"}
    assert isinstance(build_llm(Settings(_env_file=None, llm_provider="mock")), MockLLM)


def test_provider_error_carries_status():
    llm, _ = provider("sarvam", Script(httpx.Response(404, text="unknown model"), auto_tag=False))
    with pytest.raises(ProviderError) as e:
        llm.quick_json("S", "x")
    assert e.value.status == 404


def test_turn_records_provider_for_mock(client, db):
    sid = client.post("/api/session", json={"language": "en", "district": "Mysuru", "learner_education": "class_10",
                                            "consent_given": True}).json()["session_id"]
    r = client.post("/api/chat", json={"session_id": sid, "speaker": "parent", "text": "How much can I earn?",
                                       "language": "en"}).json()
    assert r["llm_provider"] == "mock"
    assert db.scalar(select(m.Message.llm_provider).where(m.Message.role == "assistant")) == "mock"


def test_reasoning_that_eats_the_budget_is_retried_without_thinking(db):
    script = Script(httpx.Response(200, json={"choices": [{"index": 0, "message": {"role": "assistant", "content": ""},
                                                           "finish_reason": "length"}]}),
                    reply("Thank you for asking. Would you like to see the options?"))
    llm, _ = provider("sarvam", script, chat_extra={"reasoning_effort": "low"})
    out = llm.respond("S", "C", [{"role": "user", "content": "hello"}], TOOLS, {"user_text": "hello"})
    assert out.text.startswith("Thank you") and script.requests[1]["reasoning_effort"] is None


def test_sarvam_fast_tasks_run_without_thinking():
    s = Settings(_env_file=None, llm_provider="sarvam", sarvam_api_key="k", gemini_api_key="")
    sarvam = build_llm(s).chain[0]
    assert sarvam.fast_extra == {"reasoning_effort": None} and sarvam.chat_extra == {"reasoning_effort": "low"}
