# Decision log

Each entry: what was ambiguous, what we chose, and why (tied to the problem statement SIH26241).

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-10-12 | The repo root is this folder (`Samvaad/`), not a nested `samvaad/` subfolder. | The GitHub repo was created empty for this purpose; one less level of nesting. |
| D2 | 2026-10-12 | Python 3.13 locally (spec: 3.11+). | That is what is installed; code avoids 3.12+-only syntax where practical. |
| D3 | 2026-10-12 | `ANTHROPIC_FAST_MODEL` defaults to `claude-haiku-4-5`, not `claude-haiku-5-5`. | `claude-haiku-5-5` is not a published model ID; Haiku 4.5 is the current fast model. Main model stays `claude-sonnet-5-5` as specified. |
| D4 | 2026-10-12 | Real-LLM calls use `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) on the Claude API, configurable via `ANTHROPIC_FALLBACKS` (empty disables). | If a safety classifier declines a turn, the API re-runs it on a fallback model instead of returning nothing to a family mid-conversation. |
| D5 | 2026-10-12 | Sonnet 5.5 rejects forced `tool_choice` (`any`/`tool`); we use `auto` and steer via the system prompt. Mock mode calls tools deterministically. | API constraint. The numeric guardrail still enforces "numbers only from tools". |
| D6 | 2026-10-12 | Income bracket slugs use ASCII hyphens: `<1.5L`, `1.5-3L`, `3-6L`, `>6L`, `prefer_not_to_say`; configurable via `INCOME_BRACKETS`. | Avoid en-dash mismatches in URLs/CSV; organiser data may define other bands. |
| D7 | 2026-10-12 | Extra columns beyond the spec schema: `providers.trades` (JSON slugs offered), `messages.cards` (JSON, cards shown with that reply), `sessions.simulated` (bool), `costs_support.income_brackets` (JSON targeting), and a `guardrail_logs` table. | Needed to (a) filter providers by trade, (b) rebuild the Family Summary from what was actually shown, (c) label simulated sessions in the dashboard, (d) tailor support by income bracket, (e) "log every guardrail trigger" (Rule 2). |
| D8 | 2026-10-12 | Frontend pinned to React 18 with `@react-three/fiber@8`, `drei@9`, `react-leaflet@4`. | Spec requires React 18; the newer majors of these libraries require React 19. |
| D9 | 2026-10-12 | Tailwind CSS v4 (`@tailwindcss/vite`); design tokens are declared with `@theme` in `src/styles/index.css`, which exposes them as both Tailwind classes and CSS variables. | Current Tailwind; satisfies "Tailwind theme tokens and CSS variables" in one place. |
| D10 | 2026-10-12 | Root font size 18px; chat bubbles 20px+. | Low-literacy baseline from Section 10.3. |
