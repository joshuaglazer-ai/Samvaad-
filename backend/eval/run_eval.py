"""Run the 40 concern questions and 12 aspiration questions; write eval/results.md (generated — do not hand-edit).

    python -m eval.run_eval                                  # uses LLM_PROVIDER from .env (mock by default)
    python -m eval.run_eval --provider sarvam --require-real   # real run (see run_eval_real.ps1 / .sh)

Each question runs in a fresh session on a private in-memory database seeded with the demo data, so the
eval never touches the real database. Recorded per question: detected concern, tools called, guardrail
status, whether a source was shown, whether escalation happened, and expected vs actual.
"""
from __future__ import annotations

import argparse
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models as m
from app import lang_text as _lt
from app.aspiration import match_fuzzy
from app.chat import handle_turn
from app.data_tools import DataTools
from app.goals import save_goal
from app.config import get_settings
from app.db import Base
from app.guardrail import check
from app.llm import get_llm
from app.prompts import PROMISE_WORDS

# Word limits per language. Kannada and Telugu are agglutinative: one written word often carries what English
# says in two or three (e.g. "ಸಂಪಾದಿಸುತ್ತಾರೆ" = "they earn"), and scripts split differently, so the same short
# answer counts as fewer — but longer — words. 80 keeps the same spoken length budget (decision D26).
WORD_LIMIT = {"en": 60, "hi": 60, "kn": 80, "te": 80}
COUNSELLOR_WORDS = ("counsel", "ಸಲಹೆಗಾರ", "काउंसलर", "కౌన్సిలర్")
from seed.seed import seed

HERE = Path(__file__).resolve().parent


def fresh_db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    db = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)()
    seed(db)
    return db


def run_one(db, q: dict, llm) -> dict:
    s = m.SessionRow(language=q["lang"], district=q["district"], learner_education=q.get("education", "class_10"),
                     learner_interests=[], top_concerns=[], consent_given=True)
    db.add(s)
    db.commit()
    out = handle_turn(db, s.id, q.get("speaker", "parent"), q["text"], q["lang"], llm=llm)
    user = db.scalar(select(m.Message).where(m.Message.session_id == s.id, m.Message.role == "user"))
    bot = db.get(m.Message, out["message_id"])
    tools = [c["name"] for c in bot.tool_calls if c.get("name") != "escalate"]
    found = [c.get("found") for c in bot.tool_calls if c.get("name") != "escalate"]
    gaps = len(list(db.scalars(select(m.EvidenceGap).where(m.EvidenceGap.session_id == s.id))))
    cards_ok = [c for c in out["cards"] if not c["data"].get("unavailable")]
    source_shown = bool(cards_ok) and all(c["evidence"].get("source") and c["evidence"].get("data_status") for c in cards_ok)
    reply_cites = ("Source" in out["reply_text"] or "ಮೂಲ" in out["reply_text"])
    # Independent re-check: every number in the final reply appears in the cards/tool data shown
    numbers_ok = check(out["reply_text"], [c["data"] for c in out["cards"]] + [c["evidence"] for c in out["cards"]] +
                       [bot.tool_calls]).passed
    exp = q["expect"]
    actual = {
        "concern": user.concern_category, "tools": tools, "guardrail": out["guardrail_status"],
        "data_found": (any(found) if found else None), "escalated": out["escalation"] is not None,
        "source_shown": source_shown, "reply_cites_source": reply_cites, "gap_logged": gaps > 0,
        "numbers_backed": numbers_ok,
        "geo_level": next((c["evidence"]["geo_level"] for c in cards_ok if c["type"] == "outcome"), None),
        "reply": out["reply_text"],
        "words": len(out["reply_text"].split()),
        "provider": out.get("llm_provider") or "mock",
    }
    checks = {
        "concern": actual["concern"] == exp["concern"],
        "tools": (not exp["tools"] and not tools) or any(t in tools for t in exp["tools"]),
        "data": exp["data_found"] is None or actual["data_found"] == exp["data_found"],
        "escalation": actual["escalated"] == exp["escalate"],
        # Missing data → an evidence gap is logged AND a counsellor is offered (in any of the four languages).
        "honest_fallback": exp["data_found"] is not False or (
            actual["gap_logged"] and any(w in out["reply_text"].lower() for w in COUNSELLOR_WORDS)),
        # Figures must carry evidence; a plain list of options has no figures and no card.
        "evidence": exp["data_found"] is not True or source_shown or tools == ["list_trades"],
        "guardrail": actual["guardrail"] in ("pass", "regenerated") and numbers_ok,
        "length": actual["words"] <= WORD_LIMIT.get(q["lang"], 60),
        "no_promises": not any(w.lower() in out["reply_text"].lower() for w in PROMISE_WORDS),
    }
    return {"q": q, "actual": actual, "checks": checks, "pass": all(checks.values())}


NUMBER_CHARS = "0123456789०१२३४५६७८९౦౧౨౩౪౫౬౭౮౯೦೧೨೩೪೫೬೭೮೯₹"
NO_MATCH_KEY = {"degree_career": "degree", "professional_course": "professional", "unknown": "unknown"}


def run_aspiration(db, q: dict, llm) -> dict:
    """The learner says a goal in their own words; the app confirms the closest database trade (if any), as the
    onboarding screen does; then the family asks a question in chat."""
    s = m.SessionRow(language=q["lang"], district=q["district"], learner_education=q.get("education", "class_10"),
                     learner_interests=[], top_concerns=[], consent_given=True)
    db.add(s)
    db.commit()
    if llm.is_mock:
        r = match_fuzzy(q["goal"], q["lang"], DataTools(db).trade_terms())
    else:  # real mode: the fast model picks from the candidate list (preview only; nothing stored)
        r = DataTools(db, language=q["lang"]).match_aspiration(q["goal"], q["lang"], llm=llm)
        db.rollback()
    save_goal(db, s, "learner", q["goal"], q["lang"], "text", [r["candidates"][0]["slug"]] if r["matched"] else [], True)
    db.commit()
    out = handle_turn(db, s.id, "learner", q["text"], q["lang"], llm=llm)
    bot = db.get(m.Message, out["message_id"])
    exp = q["expect"]
    trade = (s.matched_trade_slugs or [None])[0]
    card_trades = [c["data"].get("trade_slug") for c in out["cards"] if not c["data"].get("unavailable")]
    reply = out["reply_text"]
    gaps = list(db.scalars(select(m.EvidenceGap).where(m.EvidenceGap.session_id == s.id,
                                                       m.EvidenceGap.tool_name == "match_aspiration")))
    no_trade = exp["trade"] is None
    actual = {"provider": out.get("llm_provider") or "mock",
              "category": s.aspiration_category, "trade": trade, "card_trades": card_trades, "gaps": len(gaps),
              "tools": [c["name"] for c in bot.tool_calls], "guardrail": out["guardrail_status"], "reply": reply,
              "words": len(reply.split())}
    nomatch_line = _lt.GOAL_NOMATCH[q["lang"]][NO_MATCH_KEY[exp["category"]]] if no_trade else ""
    checks = {
        "category": actual["category"] == exp["category"],
        "trade": trade == exp["trade"],  # database trades only; never forced when nothing fits
        # A matched goal is what the chat answers about; an unmatched goal gets no figures and no card.
        "answers_goal": (card_trades[:1] == [exp["trade"]]) if not no_trade
        else (not card_trades and not any(ch in reply for ch in NUMBER_CHARS)),
        "kind_no_match": not no_trade or reply.startswith(nomatch_line),
        "gap_logged": (len(gaps) == 1) if no_trade else (len(gaps) == 0),
        "counsellor_offered": not no_trade or any(w in reply.lower() for w in COUNSELLOR_WORDS),
        "guardrail": actual["guardrail"] in ("pass", "regenerated", "na"),
        "length": actual["words"] <= WORD_LIMIT.get(q["lang"], 60),
        "no_promises": not any(w.lower() in reply.lower() for w in PROMISE_WORDS),
    }
    return {"q": q, "actual": actual, "checks": checks, "pass": all(checks.values())}


def md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def aspiration_section(results: list[dict]) -> list[str]:
    n = len(results)
    agg = {k: sum(r["checks"][k] for r in results) for k in results[0]["checks"]}
    lines = [
        "", "## Aspiration questions (Update 3)", "",
        f"All checks passed: **{sum(r['pass'] for r in results)}/{n}** (3 per language; 2 degree careers, 2 unknown goals, "
        "1 professional course).", "",
        "| Check | Passed |", "|---|---|", *[f"| {k} | {v}/{n} |" for k, v in agg.items()], "",
        "Checks: **category** goal sorted as expected · **trade** matched to the expected database trade, or to none "
        "(never forced) · **answers_goal** a matched goal is what the chat answers about; an unmatched goal gets no "
        "figures and no card · **kind_no_match** the agreed kind line for degree careers, professional courses and "
        "unknown goals · **gap_logged** one evidence gap for an unmatched goal, none for a matched one · "
        "**counsellor_offered** for unmatched goals · **guardrail**, **length**, **no_promises** as above.", "",
        "| ID | Lang | Goal (their words) | Category (exp → act) | Trade (exp → act) | Card | Words | Result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        q, a, e = r["q"], r["actual"], r["q"]["expect"]
        result = "PASS" if r["pass"] else "FAIL: " + ", ".join(k for k, v in r["checks"].items() if not v)
        cards = ", ".join(x or "?" for x in a["card_trades"]) or "—"
        lines.append(f"| {q['id']} | {q['lang']} | {md_escape(q['goal'])} | {e['category']} → {a['category']} | "
                     f"{e['trade'] or '—'} → {a['trade'] or '—'} | {cards} | {a['words']} | {result} |")
    lines += ["", "### Aspiration replies", ""]
    for r in results:
        lines.append(f"**{r['q']['id']}** — goal “{md_escape(r['q']['goal'])}”, then: {md_escape(r['q']['text'])}  ")
        lines.append(f"> {md_escape(r['actual']['reply'])}")
        lines.append("")
    return lines


def write_report(results: list[dict], mode: str, path: Path, aspirations: list[dict] | None = None) -> None:
    n = len(results)
    passed = sum(r["pass"] for r in results)
    agg = {k: sum(r["checks"][k] for r in results) for k in results[0]["checks"]}
    lines = [
        "# SAMVAAD evaluation results",
        "",
        f"_Generated by `python -m eval.run_eval` on {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} — do not hand-edit._",
        "",
        f"- LLM mode: **{mode}**",
        "- Answered by: " + ", ".join(f"**{p}** {n}" for p, n in Counter(
            r["actual"]["provider"] for r in results + (aspirations or [])).most_common()) +
        " (turns that fell back to another provider are counted under the provider that answered)",
        f"- Questions: **{n}** (" + ", ".join(f"{sum(r['q']['lang'] == code for r in results)} {name}" for code, name in
                                         (("en", "English"), ("kn", "Kannada"), ("hi", "Hindi"), ("te", "Telugu"))) + ")",
        f"- All checks passed: **{passed}/{n}**",
        "",
        "| Check | Passed |",
        "|---|---|",
        *[f"| {k} | {v}/{n} |" for k, v in agg.items()],
        "",
        "Checks: **concern** detected category = expected · **tools** expected data tool called · **data** found / not found as expected · "
        "**escalation** case created iff expected · **honest_fallback** missing data → gap logged + counsellor offered · "
        "**evidence** every shown card carries source + status · **guardrail** reply passed the numeric guardrail and every number "
        "re-checks against the shown data (spoken rounding allowed only after \"about\") · **length** ≤ 60 words "
        "(≤ 80 for Kannada/Telugu, see D26) · **no_promises** no \"guaranteed / surely / 100%\"-style words.",
        "",
        "| ID | Lang | Question | Concern (exp → act) | Tools called | Data found (exp → act) | Geo level | Guardrail | Source shown | Escalated (exp → act) | Words | Result |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        q, a, e = r["q"], r["actual"], r["q"]["expect"]
        lines.append(
            f"| {q['id']} | {q['lang']} | {md_escape(q['text'])} | {e['concern']} → {a['concern']} | {', '.join(a['tools']) or '—'} | "
            f"{e['data_found']} → {a['data_found']} | {a['geo_level'] or '—'} | {a['guardrail']} | {'yes' if a['source_shown'] else 'no'} | "
            f"{e['escalate']} → {a['escalated']} | {a['words']} | {'PASS' if r['pass'] else 'FAIL: ' + ', '.join(k for k, v in r['checks'].items() if not v)} |")
    lines += ["", "## Replies", ""]
    for r in results:
        lines.append(f"**{r['q']['id']}** — {md_escape(r['q']['text'])}  ")
        lines.append(f"> {md_escape(r['actual']['reply'])}")
        lines.append("")
    if aspirations:
        lines += aspiration_section(aspirations)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "results.md"))
    ap.add_argument("--provider", choices=["mock", "sarvam", "gemini", "anthropic"],
                    help="override LLM_PROVIDER for this run")
    ap.add_argument("--require-real", action="store_true",
                    help="stop instead of falling back to mock mode when the provider has no API key")
    ap.add_argument("--pause", type=float, default=0.0, help="seconds to wait between questions (rate limits)")
    args = ap.parse_args()
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
        get_settings.cache_clear()
    settings = get_settings()
    if args.require_real and (settings.use_mock_llm or (args.provider and settings.provider_chain[0] != args.provider)):
        want = args.provider or settings.chosen_provider
        raise SystemExit(f"Real-API eval needs an API key for '{want}' in backend/.env "
                         f"({want.upper()}_API_KEY). Nothing was run.")
    spec = yaml.safe_load((HERE / "questions.yaml").read_text(encoding="utf-8"))
    questions, aspirations = spec["questions"], spec.get("aspirations", [])
    llm = get_llm()
    chain = settings.provider_chain
    model = {"sarvam": settings.sarvam_model, "gemini": settings.gemini_model,
             "anthropic": settings.anthropic_model}.get(chain[0], "")
    mode = "mock" if chain == ["mock"] else f"{chain[0]} ({model}); fallback: {' → '.join(chain[1:])}"
    results = []
    for i, q in enumerate(questions):
        if i and args.pause:
            time.sleep(args.pause)
        db = fresh_db()
        try:
            results.append(run_one(db, q, llm))
        finally:
            db.close()
    asp_results = []
    for q in aspirations:
        if args.pause:
            time.sleep(args.pause)
        db = fresh_db()
        try:
            asp_results.append(run_aspiration(db, q, llm))
        finally:
            db.close()
    write_report(results, mode, Path(args.out), asp_results)
    passed = sum(r["pass"] for r in results)
    print(f"LLM: {mode}")
    print(f"{passed}/{len(results)} questions passed all checks → {args.out}")
    print(f"{sum(r['pass'] for r in asp_results)}/{len(asp_results)} aspiration questions passed all checks")
    for r in asp_results:
        if not r["pass"]:
            failed = [k for k, v in r["checks"].items() if not v]
            print(f"  FAIL {r['q']['id']}: {failed} actual={ {k: r['actual'][k] for k in ('category', 'trade', 'card_trades', 'gaps')} }")
    for r in results:
        if not r["pass"]:
            print(f"  FAIL {r['q']['id']}: {[k for k, v in r['checks'].items() if not v]} actual={ {k: r['actual'][k] for k in ('concern', 'tools', 'data_found', 'escalated')} }")


if __name__ == "__main__":
    main()
