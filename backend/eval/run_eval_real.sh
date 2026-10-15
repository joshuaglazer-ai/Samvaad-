#!/usr/bin/env bash
# Run the full SAMVAAD eval (40 concern questions + 12 aspiration questions) against a real LLM provider.
#
#   cd backend && bash eval/run_eval_real.sh                       # Sarvam (default)
#   cd backend && bash eval/run_eval_real.sh --provider gemini     # Google Gemini (free tier)
#   cd backend && bash eval/run_eval_real.sh --provider sarvam --pause 3
#
# Needs that provider's key in backend/.env (SARVAM_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY). The provider is
# chosen for this run only. If it errors or stays rate-limited, turns fall back to the next configured provider,
# then mock — the report shows which provider answered each turn. Results go to eval/results_real_<provider>.md,
# so the committed mock-mode eval/results.md is not overwritten. Each question uses a private in-memory database.
# This makes real API calls (about 52 turns × 2–3 calls) and uses your provider credits / free-tier quota.
set -euo pipefail
cd "$(dirname "$0")/.."
PROVIDER="sarvam"; PAUSE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --provider) PROVIDER="$2"; shift 2 ;;
    --pause) PAUSE="$2"; shift 2 ;;
    *) echo "usage: $0 [--provider sarvam|gemini|anthropic] [--pause seconds]"; exit 2 ;;
  esac
done
case "$PROVIDER" in sarvam|gemini|anthropic) ;; *) echo "provider must be sarvam, gemini or anthropic"; exit 2 ;; esac
# Free-tier friendly pauses between questions: Sarvam-105B allows 40 requests/min, Gemini Flash free tier far fewer.
if [ -z "$PAUSE" ]; then case "$PROVIDER" in gemini) PAUSE=6 ;; sarvam) PAUSE=2 ;; *) PAUSE=0 ;; esac; fi
PY=".venv/Scripts/python"; [ -x "$PY" ] || PY=".venv/bin/python"; [ -x "$PY" ] || PY="python"
export PYTHONIOENCODING=utf-8
"$PY" -m eval.run_eval --provider "$PROVIDER" --require-real --pause "$PAUSE" --out "eval/results_real_${PROVIDER}.md"
