"""Deterministic data fetching (Update 5): the backend decides which data a question needs — from the concern tagged
for the message and the trade (named in the message, the last trade discussed, or the learner's confirmed goal) —
and fetches it BEFORE any model is called. The model narrates from these results; it may call tools for extra details,
but a correct answer never depends on it choosing the right tool. Cards are built from these results. Mock mode uses
the same plan, so mock and real providers start from the same data.

    concern               data fetched
    income, job_security  outcomes
    cost                  costs and support
    degree_first          progression + outcomes   (both paths explained from the ladder)
    social_status         outcomes + progression
    distance_migration    training centres for that trade
    safety                progression (+ the escalation check for sensitive safety worries)
    other                 outcomes
    "what other options"  list of trades
"""
from __future__ import annotations

from .sentiment import is_sensitive, wants_counsellor

CONCERN_TOOLS: dict[str, list[str]] = {
    "income": ["outcomes"], "job_security": ["outcomes"], "other": ["outcomes"],
    "cost": ["costs"], "degree_first": ["progression", "outcomes"], "social_status": ["outcomes", "progression"],
    "distance_migration": ["providers"], "safety": ["progression"],
}


def _call(kind: str, trade: str, ctx: dict) -> tuple[str, dict]:
    district = ctx.get("district")
    if kind == "outcomes":
        return "get_trade_outcomes", {"trade_slug": trade, "district": district}
    if kind == "costs":
        args = {"trade_slug": trade, "district": district}
        if ctx.get("income_bracket"):
            args["income_bracket"] = ctx["income_bracket"]
        return "get_costs_and_support", args
    if kind == "progression":
        return "get_progression", {"trade_slug": trade, "education_level": ctx.get("learner_education")}
    return "get_providers", {"trade_slug": trade, "district": district}


def plan(text: str, ctx: dict) -> list[tuple[str, dict]]:
    """The tools the backend runs before the model answers. Returns [(tool name, input), ...]."""
    from .mock_counsellor import detect_intent, detect_trade

    if is_sensitive(text):
        return [("escalate", {"reason": "Sensitive topic raised by the family", "trigger": "sensitive_topic"})]
    if wants_counsellor(text):
        return [("escalate", {"reason": "Family asked to talk to a counsellor", "trigger": "user_request"})]
    if detect_intent(text) == "options":
        return [("list_trades", {"language": ctx.get("language", "en")})]
    trade = ctx.get("named_trade") or detect_trade(text) or ctx.get("last_trade") or ctx.get("suggested_trade")
    if not trade:
        goal = ctx.get("goal") or {}
        if goal.get("text") and not goal.get("trades"):
            # The learner's own goal has no database trade: the backend answers kindly from the match (no figures).
            return [("match_aspiration", {"text": goal["text"], "language": ctx.get("language", "en")})]
        return [("list_trades", {"language": ctx.get("language", "en")})]
    concern = ctx.get("concern")
    if concern in (None, "other"):
        # Untagged or "other": the words of the question still say what is needed ("next steps", "fees", "near us").
        from .sentiment import keyword_concern

        concern = keyword_concern(text) or {"progression": "degree_first", "costs": "cost",
                                            "providers": "distance_migration"}.get(detect_intent(text), "other")
    kinds = CONCERN_TOOLS.get(concern, CONCERN_TOOLS["other"])
    return [_call(k, trade, ctx) for k in kinds]
