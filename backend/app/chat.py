"""Chat turn: history → tool-use loop → numeric guardrail → escalation checks → structured response.

Cards are built by the backend directly from tool results, never from model text.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from .alignment import session_alignment
from .data_tools import TOOL_SCHEMAS, DataTools
from .escalation import case_info, check_triggers, create_case
from . import lang_text as _lt
from .guardrail import FALLBACK_TEXT, check, claim_check, correction_note
from .i18n import detect_script, norm_lang
from .llm import BaseLLM, LLMResponse, get_llm
from .goals import compare_goals
from .prompts import SYSTEM_PROMPT, context_block
from .sentiment import is_sensitive, tag_message, wants_counsellor

log = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 4
HISTORY_MESSAGES = 12

ESCALATE_TOOL = {
    "name": "escalate",
    "description": "Hand the conversation to a human counsellor. Use for sensitive topics (safety worries about a "
                   "daughter or son, family conflict, debt, distress, harassment), when the family asks for a person, "
                   "or when you cannot help with verified data.",
    "input_schema": {"type": "object", "properties": {
        "reason": {"type": "string"},
        "trigger": {"type": "string", "enum": ["user_request", "no_data", "sensitive_topic", "negative_sentiment",
                                               "repeated_failure"]},
    }, "required": ["reason", "trigger"], "additionalProperties": False},
}
TOOLS = TOOL_SCHEMAS + [ESCALATE_TOOL]

ESCALATION_LINE = {
    "en": "A counsellor will join shortly. You can wait here or ask for a call back.",
    "kn": "ಸಲಹೆಗಾರರು ಸ್ವಲ್ಪ ಸಮಯದಲ್ಲಿ ಸೇರುತ್ತಾರೆ. ಇಲ್ಲೇ ಕಾಯಬಹುದು ಅಥವಾ ಮರಳಿ ಕರೆ ಕೇಳಬಹುದು.",
}
QUICK = {
    "en": {"outcome": "How much can I earn?", "ladder": "What are the next steps after training?",
           "costs": "How much does training cost?", "providers": "Training centres near us",
           "options": "Show other options", "counsellor": "Talk to a counsellor"},
    "kn": {"outcome": "ಎಷ್ಟು ಸಂಪಾದಿಸಬಹುದು?", "ladder": "ತರಬೇತಿಯ ನಂತರ ಮುಂದಿನ ಹಂತಗಳೇನು?",
           "costs": "ತರಬೇತಿಗೆ ಎಷ್ಟು ಖರ್ಚಾಗುತ್ತದೆ?", "providers": "ಹತ್ತಿರದ ತರಬೇತಿ ಕೇಂದ್ರಗಳು",
           "options": "ಬೇರೆ ಆಯ್ಕೆಗಳನ್ನು ತೋರಿಸಿ", "counsellor": "ಸಲಹೆಗಾರರೊಂದಿಗೆ ಮಾತನಾಡಿ"},
}
TOOL_TO_CARD = {"get_trade_outcomes": "outcome", "get_progression": "ladder", "get_providers": "providers",
                "get_costs_and_support": "costs"}


# ------------------------------------------------------------------------------------------------ context
def build_history(db: Session, session_id: str, exclude_id: int | None) -> list[dict]:
    rows = list(db.scalars(select(m.Message).where(
        m.Message.session_id == session_id, m.Message.role.in_(("user", "assistant")), m.Message.live.is_(False))
        .order_by(m.Message.id.desc()).limit(HISTORY_MESSAGES + 1)))
    rows = [r for r in reversed(rows) if r.id != exclude_id][-HISTORY_MESSAGES:]
    msgs: list[dict] = []
    for r in rows:
        role = r.role
        text = r.text if role == "assistant" else f"[{r.speaker}] {r.text}"
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"] += "\n" + text
        else:
            msgs.append({"role": role, "content": text})
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


def trades_discussed(db: Session, session_id: str) -> list[str]:
    slugs: list[str] = []
    for msg in db.scalars(select(m.Message).where(m.Message.session_id == session_id, m.Message.role == "assistant")
                          .order_by(m.Message.id)):
        for c in msg.cards or []:
            slug = c.get("data", {}).get("trade_slug")
            if slug and not c.get("data", {}).get("unavailable"):
                if slug in slugs:
                    slugs.remove(slug)
                slugs.append(slug)
    return slugs


def build_context(db: Session, s: m.SessionRow, speaker: str, language: str, user_text: str) -> dict:
    discussed = trades_discussed(db, s.id)
    # The learner's own goal comes first (Update 3): its matched trade, or — when nothing matched — the words as said.
    goals = compare_goals(db, s, language)
    suggested = next(iter(s.matched_trade_slugs or []), None)
    return {
        "language": language, "speaker": speaker, "district": s.district,
        "learner_education": s.learner_education,
        "income_bracket": s.income_bracket if s.income_bracket != "prefer_not_to_say" else None,
        "helper_mode": s.helper_mode, "learner_interests": s.learner_interests or [],
        "top_concerns": s.top_concerns or [], "alignment": session_alignment(db, s.id),
        "trades_discussed": discussed, "last_trade": discussed[-1] if discussed else None,
        "suggested_trade": suggested, "user_text": user_text,
        "goal": goals["learner"], "parent_hope": goals["parent"], "goals_differ": goals["differ"],
        "turn": db.scalar(select(func.count()).select_from(m.Message).where(
            m.Message.session_id == s.id, m.Message.role == "assistant")) or 0,
    }


# ------------------------------------------------------------------------------------------------ cards
def build_card(tool: str, out: dict, language: str) -> dict | None:
    ctype = TOOL_TO_CARD.get(tool)
    if not ctype:
        return None
    base_evidence = {"source": (out.get("source") or {}).get("title"), "source_url": (out.get("source") or {}).get("url"),
                     "reporting_period": None, "sample_size": None, "geo_level": out.get("geo_level_used"),
                     "data_status": out.get("data_status", "unavailable"), "limitations": out.get("limitations", [])}
    if not out.get("found"):
        q = out.get("query", {})
        return {"type": ctype, "data": {"unavailable": True, "trade_slug": q.get("trade_slug"),
                                        "trade_name": out.get("trade_name") or q.get("trade_slug"),
                                        "district": q.get("district"), "other_districts": out.get("other_districts", [])},
                "evidence": {**base_evidence, "data_status": "unavailable"}}
    if ctype == "outcome":
        rec = out["records"][0]
        return {"type": "outcome",
                "data": {**rec, "trade_slug": out["trade_slug"], "trade_name": out["trade_name"],
                         "district_requested": out.get("district_requested"),
                         "fallback_note": next((t for c, t in zip(out.get("limitation_codes", []), out.get("limitations", []))
                                                if c in ("state_fallback", "national_fallback")), None),
                         "history": [{"year": r["year"], "reporting_period": r["reporting_period"],
                                      "placement_rate": r["placement_rate"], "earnings_median": r["earnings_median"]}
                                     for r in out["records"]]},
                "evidence": {**base_evidence, "reporting_period": rec["reporting_period"],
                             "sample_size": rec.get("sample_size"), "geo_level": rec["geo_level"],
                             "data_status": rec["data_status"]}}
    if ctype == "ladder":
        return {"type": "ladder",
                "data": {"trade_slug": out["trade_slug"], "trade_name": out["trade_name"], "steps": out["records"],
                         "trade_nsqf_level": out.get("trade_nsqf_level"),
                         "trade_duration_months": out.get("trade_duration_months"),
                         "can_start_training": out.get("can_start_training"),
                         "trade_entry_requirement": out.get("trade_entry_requirement")},
                "evidence": base_evidence}
    if ctype == "providers":
        return {"type": "providers",
                "data": {"trade_slug": out["trade_slug"], "trade_name": out["trade_name"],
                         "district": out["records"][0]["district"], "providers": out["records"]},
                "evidence": {**base_evidence, "source": base_evidence["source"] or "SAMVAAD demo provider list"}}
    rec = out["records"][0]
    return {"type": "costs",
            "data": {"trade_slug": out["trade_slug"], "trade_name": out["trade_name"], **rec},
            "evidence": {**base_evidence, "geo_level": out.get("geo_level_used")}}


def quick_replies(cards: list[dict], language: str, escalated: bool, goal_unmatched: bool = False) -> list[str]:
    q = QUICK.get(language, QUICK["en"])
    if goal_unmatched:  # no data for their goal: offer related options and a person, not more figures
        return [q["options"]] + ([] if escalated else [q["counsellor"]])
    shown = {c["type"] for c in cards if not c["data"].get("unavailable")}
    order = ["outcome", "ladder", "costs", "providers"]
    picks = [q[k] for k in order if k not in shown][:2] if shown else [q["outcome"], q["ladder"]]
    picks.append(q["options"])
    if not escalated:
        picks.append(q["counsellor"])
    return picks


# ------------------------------------------------------------------------------------------------ loop
def run_tool_loop(llm: BaseLLM, messages: list[dict], ctx: dict, context_text: str, tools: DataTools,
                  outputs: list[tuple[str, dict, dict]], on_escalate) -> LLMResponse:
    resp = llm.respond(SYSTEM_PROMPT, context_text, messages, TOOLS, ctx)
    for _ in range(MAX_TOOL_ITERATIONS):
        if resp.stop_reason != "tool_use" or not resp.tool_calls:
            break
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for call in resp.tool_calls:
            if call.name == "escalate":
                out = on_escalate(call.input.get("trigger", "sensitive_topic"))
            else:
                out = tools.execute(call.name, call.input)
            outputs.append((call.name, out, call.input))
            results.append({"type": "tool_result", "tool_use_id": call.id,
                            "content": json.dumps(out, ensure_ascii=False, default=str)})
        messages.append({"role": "user", "content": results})
        resp = llm.respond(SYSTEM_PROMPT, context_text, messages, TOOLS, ctx)
    return resp


def handle_turn(db: Session, session_id: str, speaker: str, text: str, language: str,
                llm: BaseLLM | None = None, device_id: str | None = None) -> dict[str, Any]:
    llm = llm or get_llm()
    s = db.get(m.SessionRow, session_id)
    if s is None:
        raise LookupError("session not found")
    language = norm_lang(language)
    # If someone writes in a different supported script than the session language, answer in the language they
    # used and offer to switch (Latin text is ambiguous — English or transliteration — so it never switches).
    written_in = detect_script(text)
    suggest_language = written_in if written_in and written_in != language else None
    if suggest_language:
        language = suggest_language

    tag = tag_message(text, llm)
    user_msg = m.Message(session_id=s.id, role="user", speaker=speaker, text=text, language=language,
                         concern_category=tag.concern_category, sentiment=tag.sentiment,
                         sentiment_confidence=tag.confidence, tool_calls=[], cards=[], guardrail_status="na",
                         device_id=device_id)
    db.add(user_msg)
    db.flush()

    ctx = build_context(db, s, speaker, language, text)
    # The concern is tagged BEFORE the reply is written, so the reassurance and the answer address what was asked.
    ctx["concern"] = tag.concern_category
    context_text = context_block(ctx)
    messages = build_history(db, s.id, exclude_id=user_msg.id)
    messages.append({"role": "user", "content": f"[{speaker}] {text}"})
    if messages[0]["role"] != "user":
        messages = messages[-1:]

    tools = DataTools(db, session_id=s.id, language=language, concern=tag.concern_category)
    outputs: list[tuple[str, dict, dict]] = []  # (tool name, result, input)
    escalation: dict | None = None

    def on_escalate(trigger: str) -> dict:
        nonlocal escalation
        case, _ = create_case(db, s, trigger)
        escalation = case_info(db, case)
        return {"escalated": True, "case_id": case.id, "trigger": case.trigger}

    resp = run_tool_loop(llm, messages, ctx, context_text, tools, outputs, on_escalate)
    reply = resp.text
    status = "pass"

    if not reply:
        reply, status = FALLBACK_TEXT[language], "fallback"
        db.add(m.GuardrailLog(session_id=s.id, attempt=1, outcome="fallback", reply_text="(empty or refused)",
                              unmatched=[]))
    else:
        # Numbers must come from this turn's tools, and so must claims such as "government", "free", "guaranteed",
        # "certified" or "accredited". Either failure: regenerate once with a correction note, then fall back.
        result = check(reply, [o for _, o, _ in outputs])
        claims = claim_check(reply, [o for _, o, _ in outputs])
        if not result.passed or claims:
            db.add(m.GuardrailLog(session_id=s.id, attempt=1, outcome="regenerated", reply_text=reply,
                                  unmatched=result.unmatched + [f"claim:{c}" for c in claims]))
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": correction_note(result.unmatched, language, claims)})
            resp = run_tool_loop(llm, messages, ctx, context_text, tools, outputs, on_escalate)
            retry = resp.text
            second = check(retry, [o for _, o, _ in outputs]) if retry else None
            claims2 = claim_check(retry, [o for _, o, _ in outputs]) if retry else []
            if second and second.passed and not claims2:
                reply, status = retry, "regenerated"
            else:
                db.add(m.GuardrailLog(session_id=s.id, attempt=2, outcome="fallback", reply_text=retry or "",
                                      unmatched=(second.unmatched if second else []) + [f"claim:{c}" for c in claims2]))
                reply, status = FALLBACK_TEXT[language], "fallback"
            log.info("guardrail triggered for session %s: %s", s.id, status)

    # Explicit requests and sensitive topics always reach a person, even if the model did not call escalate.
    flagged = "sensitive_topic" if is_sensitive(text) else ("user_request" if wants_counsellor(text) else None)
    if flagged and escalation is None:
        on_escalate(flagged)

    if suggest_language:
        reply = f"{reply} {_lt.SWITCH_OFFER[suggest_language]}"

    provider = resp.provider
    log.info("turn in session %s answered by %s%s%s", s.id, provider,
             " (backend called the data tools)" if ctx.get("backend_planned_tools") else "",
             f" after failures: {ctx['provider_failures']}" if ctx.get("provider_failures") else "")

    cards: list[dict] = []
    for name, out, _ in outputs:
        card = build_card(name, out, language)
        if card:
            cards = [c for c in cards if not (c["type"] == card["type"])] + [card]

    assistant = m.Message(session_id=s.id, role="assistant", speaker="bot", text=reply, language=language,
                          tool_calls=[{"name": n, "input": i, "found": o.get("found", o.get("escalated", False))}
                                      for n, o, i in outputs],
                          cards=cards, guardrail_status=status, device_id=device_id, llm_provider=provider)
    db.add(assistant)
    db.flush()

    if escalation is None:
        trigger = check_triggers(db, s)
        if trigger:
            on_escalate(trigger)
    if escalation and not any(w in reply.lower() for w in ("counsel", "ಸಲಹೆಗಾರ", "काउंसलर", "కౌన్సిలర్")):
        reply = f"{reply} {ESCALATION_LINE[language]}"
        assistant.text = reply

    for c in cards:
        if c["data"].get("unavailable"):
            continue
        etype = {"outcome": "outcome_viewed", "ladder": "ladder_viewed", "providers": "providers_viewed",
                 "costs": "costs_viewed"}[c["type"]]
        db.add(m.Event(session_id=s.id, event_type=etype, payload={"trade_slug": c["data"].get("trade_slug")}))

    db.commit()
    return {
        "message_id": assistant.id,
        "reply_text": reply,
        "cards": cards,
        "quick_replies": quick_replies(cards, language, escalated=escalation is not None,
                                       goal_unmatched=any(n == "match_aspiration" and not o.get("matched")
                                                          for n, o, _ in outputs)),
        "guardrail_status": status,
        "escalation": escalation,
        "reply_language": language,
        "llm_provider": provider,
        "suggest_language": suggest_language,
    }


QUICK.update(_lt.QUICK)
ESCALATION_LINE.update(_lt.ESCALATION_LINE)
