#!/usr/bin/env bash
# Run the full SAMVAAD eval (40 concern questions + 12 aspiration questions) against the real Claude API.
#
#   cd backend && bash eval/run_eval_real.sh
#
# Needs ANTHROPIC_API_KEY in backend/.env (or exported). LLM_MODE is forced to "anthropic" for this run only; the
# models come from ANTHROPIC_MODEL / ANTHROPIC_FAST_MODEL as usual. Results go to eval/results_real.md, so the
# committed mock-mode eval/results.md is not overwritten. Each question uses a private in-memory database.
# This makes real API calls (roughly 52 chat turns plus tagging and goal matching) and is billed to your account.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/Scripts/python"; [ -x "$PY" ] || PY=".venv/bin/python"; [ -x "$PY" ] || PY="python"
export LLM_MODE=anthropic PYTHONIOENCODING=utf-8
"$PY" -m eval.run_eval --require-real --out eval/results_real.md
