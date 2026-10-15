"""Free LLM providers behind the same interface as the Claude client: Sarvam AI and Google Gemini.

Both speak the OpenAI-style chat-completions API with function calling (Sarvam: api.sarvam.ai/v1, header
`api-subscription-key`; Gemini: its OpenAI-compatible endpoint, `Authorization: Bearer`). chat.py keeps its own
message format (assistant `tool_use` blocks, user `tool_result` blocks); this module translates both ways, so the tool
loop, the numeric guardrail and the data tools are unchanged.

Rules kept here:
- Numbers only from data tools: if a model answers a family's question with figures but called no tool, the backend
  plans and runs the data tools itself (the same planner the mock uses) and asks the model to answer from the results.
  `*_TOOL_MODE=backend` does this for every turn, for providers whose tool calling is unreliable.
- Rate limits: 429 (and 503 "overloaded") are retried with backoff, at most `LLM_MAX_RETRIES` (2) times, honouring
  Retry-After. After that — or on any other error — FallbackLLM moves to the next configured provider, then to mock.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable

import httpx

from . import mock_counsellor
from .config import Settings
from .llm import BaseLLM, LLMResponse, ToolCall

log = logging.getLogger("samvaad.llm")

RETRY_STATUS = {429, 503}
MAX_BACKOFF_SECONDS = 10.0
NUMBER = re.compile(r"[0-9०-९೦-೯౦-౯₹%]")
THINK = re.compile(r"<think>.*?</think>", re.S)


class ProviderError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _get(block: Any, key: str) -> Any:
    """Read a content block that may be a dict (mock / these providers) or an SDK object (Claude)."""
    return block.get(key) if isinstance(block, dict) else getattr(block, key, None)


def _strip_unsupported(schema: Any) -> Any:
    """Gemini's OpenAI-compatible endpoint rejects `additionalProperties`; drop it (the backend validates inputs)."""
    if isinstance(schema, dict):
        return {k: _strip_unsupported(v) for k, v in schema.items() if k != "additionalProperties"}
    if isinstance(schema, list):
        return [_strip_unsupported(v) for v in schema]
    return schema


def to_openai_tools(tools: list[dict], strict_schema: bool) -> list[dict]:
    out = []
    for t in tools:
        params = t.get("input_schema", {"type": "object", "properties": {}})
        out.append({"type": "function", "function": {
            "name": t["name"], "description": t.get("description", ""),
            "parameters": params if strict_schema else _strip_unsupported(params)}})
    return out


def to_openai_messages(system: str, context_text: str, messages: list[dict]) -> list[dict]:
    out: list[dict] = [{"role": "system", "content": f"{system}\n\n{context_text}".strip()}]
    names: dict[str, str] = {}
    for msg in messages:
        role, content = msg["role"], msg["content"]
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        if role == "assistant":
            text = "".join(_get(b, "text") or "" for b in content if _get(b, "type") == "text")
            calls = []
            for b in content:
                if _get(b, "type") == "tool_use":
                    names[_get(b, "id")] = _get(b, "name")
                    calls.append({"id": _get(b, "id"), "type": "function", "function": {
                        "name": _get(b, "name"), "arguments": json.dumps(_get(b, "input") or {}, ensure_ascii=False)}})
            m: dict[str, Any] = {"role": "assistant", "content": text}
            if calls:
                m["tool_calls"] = calls
            out.append(m)
            continue
        for b in content:  # user turn: tool results and/or text
            kind = _get(b, "type")
            if kind == "tool_result":
                body = _get(b, "content")
                out.append({"role": "tool", "tool_call_id": _get(b, "tool_use_id"),
                            "name": names.get(_get(b, "tool_use_id"), ""),
                            "content": body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)})
            elif kind == "text":
                out.append({"role": "user", "content": _get(b, "text")})
    return out


def _is_first_call(messages: list[dict]) -> bool:
    """True before any tool result has come back in this turn (earlier turns are kept as plain text, so any
    tool_result block belongs to this turn — including during a guardrail regeneration)."""
    return not any(isinstance(msg["content"], list) and any(_get(b, "type") == "tool_result" for b in msg["content"])
                   for msg in messages)


def _clean(text: str | None) -> str:
    return THINK.sub("", text or "").strip()


def _json_object(text: str) -> str:
    """The first {...} in a reply (models sometimes wrap JSON in prose or code fences)."""
    text = _clean(text)
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start >= 0 and end > start else text


class OpenAICompatLLM(BaseLLM):
    is_mock = False

    def __init__(self, name: str, base_url: str, headers: dict[str, str], model: str, fast_model: str,
                 tool_mode: str = "native", max_retries: int = 2, chat_extra: dict | None = None,
                 fast_extra: dict | None = None, strict_schema: bool = True,
                 transport: httpx.BaseTransport | None = None, sleep: Callable[[float], None] = time.sleep):
        self.name = name
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.headers = headers
        self.model, self.fast_model = model, fast_model
        self.tool_mode = tool_mode
        self.max_retries = max_retries
        self.chat_extra, self.fast_extra = chat_extra or {}, fast_extra or {}
        self.strict_schema = strict_schema
        self.sleep = sleep
        self.http = httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0), transport=transport)

    @classmethod
    def for_provider(cls, name: str, s: Settings) -> "OpenAICompatLLM":
        if name == "sarvam":
            return cls("sarvam", s.sarvam_base_url, {"api-subscription-key": s.sarvam_api_key}, s.sarvam_model,
                       s.sarvam_fast_model, s.sarvam_tool_mode, s.llm_max_retries,
                       chat_extra={"reasoning_effort": "low"}, fast_extra={"reasoning_effort": "low"})
        if name == "gemini":
            return cls("gemini", s.gemini_base_url, {"Authorization": f"Bearer {s.gemini_api_key}"}, s.gemini_model,
                       s.gemini_fast_model, s.gemini_tool_mode, s.llm_max_retries,
                       chat_extra={"reasoning_effort": "low"}, fast_extra={"reasoning_effort": "low"},
                       strict_schema=False)
        raise ValueError(f"unknown provider {name}")

    # ---------------------------------------------------------------- HTTP with backoff
    def _post(self, payload: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            try:
                r = self.http.post(self.url, json=payload, headers=self.headers)
            except httpx.HTTPError as exc:
                raise ProviderError(f"{self.name}: {type(exc).__name__}: {exc}") from exc
            if r.status_code in RETRY_STATUS and attempt < self.max_retries:
                try:
                    delay = float(r.headers.get("retry-after", ""))
                except ValueError:
                    delay = 1.5 * 2 ** attempt
                delay = min(max(delay, 0.0), MAX_BACKOFF_SECONDS)
                log.warning("%s returned %s; retry %d/%d in %.1fs", self.name, r.status_code, attempt + 1,
                            self.max_retries, delay)
                self.sleep(delay)
                continue
            if r.status_code >= 400:
                raise ProviderError(f"{self.name} HTTP {r.status_code}: {r.text[:300]}", r.status_code)
            try:
                return r.json()
            except ValueError as exc:
                raise ProviderError(f"{self.name}: response was not JSON") from exc
        raise ProviderError(f"{self.name}: still rate-limited after {self.max_retries} retries", 429)

    # ---------------------------------------------------------------- chat with tools
    def _planned(self, ctx: dict) -> LLMResponse | None:
        """The backend chooses and calls the data tools (same planner as mock mode); the model then narrates."""
        plan = mock_counsellor.plan(ctx.get("user_text", ""), ctx)
        if not plan:
            return None
        calls = [ToolCall(id=f"plan_{i}", name=n, input=a) for i, (n, a) in enumerate(plan)]
        blocks = [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls]
        ctx["backend_planned_tools"] = True
        return LLMResponse("tool_use", blocks, tool_calls=calls, provider=self.name)

    def respond(self, system, context_text, messages, tools, ctx) -> LLMResponse:
        first = _is_first_call(messages)
        if first and self.tool_mode == "backend":
            planned = self._planned(ctx)
            if planned:
                return planned
        data = self._post({
            "model": self.model, "messages": to_openai_messages(system, context_text, messages),
            "tools": to_openai_tools(tools, self.strict_schema), "tool_choice": "auto",
            "max_tokens": 1500, "temperature": 0.3, **self.chat_extra,
        })
        try:
            choice = data["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.name}: unexpected response shape") from exc
        if choice.get("finish_reason") == "content_filter" or msg.get("refusal"):
            return LLMResponse("refusal", [], text="", provider=self.name)
        text = _clean(msg.get("content"))
        raw_calls = msg.get("tool_calls") or []
        if raw_calls:
            calls = []
            for i, c in enumerate(raw_calls):
                fn = c.get("function") or {}
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except ValueError:
                    args = {}
                calls.append(ToolCall(id=c.get("id") or f"call_{i}", name=fn.get("name", ""),
                                      input=args if isinstance(args, dict) else {}))
            blocks: list[dict] = [{"type": "text", "text": text}] if text else []
            blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls]
            return LLMResponse("tool_use", blocks, text=text, tool_calls=calls, provider=self.name)
        # The model answered without calling a tool. If it gave figures (or nothing), it skipped the data tools:
        # the backend fetches the data itself and the model answers again from the results.
        if first and (not text or NUMBER.search(text)):
            planned = self._planned(ctx)
            if planned:
                log.info("%s answered without tools; backend called the data tools itself", self.name)
                return planned
        return LLMResponse("end_turn", [{"type": "text", "text": text}], text=text, provider=self.name)

    # ---------------------------------------------------------------- small JSON tasks (tagging, matching)
    def _fast(self, system: str, text: str, response_format: dict | None) -> str:
        payload: dict[str, Any] = {"model": self.fast_model, "max_tokens": 600, "temperature": 0,
                                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
                                   **self.fast_extra}
        if response_format:
            payload["response_format"] = response_format
        data = self._post(payload)
        return _json_object(data["choices"][0]["message"].get("content") or "")

    def quick_json(self, system, text) -> str:
        try:
            return self._fast(system, text, {"type": "json_object"})
        except ProviderError as exc:
            if exc.status != 400:
                raise
            return self._fast(system + "\nReply with one JSON object only.", text, None)

    def structured_json(self, system, text, schema) -> str:
        fmt = {"type": "json_schema", "json_schema": {
            "name": "result", "strict": True, "schema": schema if self.strict_schema else _strip_unsupported(schema)}}
        try:
            return self._fast(system, text, fmt)
        except ProviderError as exc:
            if exc.status != 400:
                raise
            return self._fast(f"{system}\nReply with one JSON object only, matching this JSON schema:\n"
                              f"{json.dumps(schema)}", text, None)


class FallbackLLM(BaseLLM):
    """Try providers in order; on an error (after retries) use the next one, ending with mock.
    Within one chat turn the provider that answered keeps the rest of the turn (ctx["_provider_index"])."""

    is_mock = False

    def __init__(self, chain: list[BaseLLM]):
        self.chain = chain
        self.name = chain[0].name

    def respond(self, system, context_text, messages, tools, ctx) -> LLMResponse:
        start = ctx.get("_provider_index", 0)
        for i in range(start, len(self.chain)):
            llm = self.chain[i]
            try:
                resp = llm.respond(system, context_text, messages, tools, ctx)
            except Exception as exc:  # any provider failure → next provider; mock never fails
                nxt = self.chain[i + 1].name if i + 1 < len(self.chain) else "none"
                log.warning("provider %s failed (%s); falling back to %s", llm.name, exc, nxt)
                ctx.setdefault("provider_failures", []).append({"provider": llm.name, "error": str(exc)[:200]})
                continue
            ctx["_provider_index"] = i
            return resp
        raise RuntimeError("no LLM provider could answer")

    def _first_working(self, method: str, *args) -> str:
        errors = []
        for llm in self.chain:
            if llm.is_mock:
                break
            try:
                return getattr(llm, method)(*args)
            except Exception as exc:
                errors.append(f"{llm.name}: {exc}")
                log.warning("provider %s failed on %s (%s)", llm.name, method, exc)
        raise RuntimeError("; ".join(errors) or "no provider")  # callers fall back (keywords / fuzzy matching)

    def quick_json(self, system, text) -> str:
        return self._first_working("quick_json", system, text)

    def structured_json(self, system, text, schema) -> str:
        return self._first_working("structured_json", system, text, schema)
