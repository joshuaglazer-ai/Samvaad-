"""One interface over the real Anthropic client and the deterministic mock.

`respond(system, context_text, messages, tools, ctx)` returns an LLMResponse whose `content` can be appended
back into `messages` unchanged (SDK blocks for the real client, dicts for the mock). Both make real
data-tool calls through chat.py.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .config import Settings, get_settings
from . import mock_counsellor

log = logging.getLogger(__name__)


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    stop_reason: str
    content: list[Any]                 # appended back as the assistant turn
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class BaseLLM:
    is_mock = True

    def respond(self, system: str, context_text: str, messages: list[dict], tools: list[dict],
                ctx: dict) -> LLMResponse:
        raise NotImplementedError

    def quick_json(self, system: str, text: str) -> str:
        raise NotImplementedError


class MockLLM(BaseLLM):
    """Deterministic stand-in: plans real tool calls, then narrates only from their results."""

    is_mock = True

    def respond(self, system, context_text, messages, tools, ctx) -> LLMResponse:
        last = messages[-1]
        content = last["content"]
        tool_results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"] \
            if isinstance(content, list) else []
        user_text = ctx.get("user_text", "")

        if tool_results:
            # Pair each result with the tool name from the preceding assistant turn.
            prev = messages[-2]["content"]
            names = {b["id"]: b["name"] for b in prev if isinstance(b, dict) and b.get("type") == "tool_use"}
            results = [(names.get(r["tool_use_id"], "?"), json.loads(r["content"])) for r in tool_results]
            text = mock_counsellor.compose(user_text, ctx, results)
            return LLMResponse("end_turn", [{"type": "text", "text": text}], text=text)

        if isinstance(content, str) and content.startswith("[Guardrail correction]"):
            # The mock never invents numbers, but if asked to correct, answer without figures.
            text = mock_counsellor.T["kn" if ctx.get("language") == "kn" else "en"]["nodata"]
            return LLMResponse("end_turn", [{"type": "text", "text": text}], text=text)

        calls = [ToolCall(id=f"mock_{i}", name=n, input=a) for i, (n, a) in enumerate(mock_counsellor.plan(user_text, ctx))]
        blocks = [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls]
        return LLMResponse("tool_use", blocks, tool_calls=calls)

    def quick_json(self, system, text) -> str:  # not used: mock tagging is keyword based
        return "{}"


class AnthropicLLM(BaseLLM):
    is_mock = False

    def __init__(self, settings: Settings):
        import anthropic

        self.settings = settings
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=60, max_retries=2)

    def _extra(self) -> dict:
        if not self.settings.anthropic_fallbacks:
            return {}
        # Server-side refusal fallback: if a turn is declined, the API re-runs it on a fallback model.
        return {"extra_headers": {"anthropic-beta": "server-side-fallback-2026-07-01"},
                "extra_body": {"fallbacks": self.settings.anthropic_fallbacks}}

    def respond(self, system, context_text, messages, tools, ctx) -> LLMResponse:
        resp = self.client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=8000,
            # Static prompt is cached; the per-session context block follows it.
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": context_text}],
            tools=tools,
            messages=messages,
            output_config={"effort": "low"},  # short counselling turns; thinking stays adaptive
            **self._extra(),
        )
        if resp.stop_reason == "refusal":
            log.warning("model refused a turn: %s", getattr(resp, "stop_details", None))
            return LLMResponse("refusal", [], text="")
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        calls = [ToolCall(id=b.id, name=b.name, input=dict(b.input)) for b in resp.content if b.type == "tool_use"]
        return LLMResponse(resp.stop_reason or "end_turn", list(resp.content), text=text, tool_calls=calls)

    def quick_json(self, system, text) -> str:
        resp = self.client.messages.create(
            model=self.settings.anthropic_fast_model, max_tokens=200, system=system,
            messages=[{"role": "user", "content": text}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")


_client: BaseLLM | None = None


def get_llm() -> BaseLLM:
    global _client
    if _client is None:
        s = get_settings()
        _client = MockLLM() if s.use_mock_llm else AnthropicLLM(s)
    return _client


def set_llm(client: BaseLLM | None) -> None:
    """Testing hook."""
    global _client
    _client = client
