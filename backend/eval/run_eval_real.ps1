# Run the full SAMVAAD eval (40 concern questions + 12 aspiration questions) against a real LLM provider.
#
#   cd backend; powershell -ExecutionPolicy Bypass -File eval\run_eval_real.ps1                     # Sarvam (default)
#   cd backend; powershell -ExecutionPolicy Bypass -File eval\run_eval_real.ps1 -Provider gemini    # Google Gemini
#   cd backend; powershell -ExecutionPolicy Bypass -File eval\run_eval_real.ps1 -Provider sarvam -Pause 3
#
# Needs that provider's key in backend\.env (SARVAM_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY). The provider is
# chosen for this run only. If it errors or stays rate-limited, turns fall back to the next configured provider,
# then mock - the report shows which provider answered each turn. Results go to eval\results_real_<provider>.md,
# so the committed mock-mode eval\results.md is not overwritten. Each question uses a private in-memory database.
# This makes real API calls (about 52 turns x 2-3 calls) and uses your provider credits / free-tier quota.
param(
    [ValidateSet("sarvam", "gemini", "anthropic")] [string] $Provider = "sarvam",
    [double] $Pause = -1
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
# Free-tier friendly pauses between questions: Sarvam-105B allows 40 requests/min, Gemini Flash free tier far fewer.
if ($Pause -lt 0) { $Pause = @{ "gemini" = 6; "sarvam" = 2; "anthropic" = 0 }[$Provider] }
$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$env:PYTHONIOENCODING = "utf-8"
& $py -m eval.run_eval --provider $Provider --require-real --pause $Pause --out "eval\results_real_$Provider.md"
exit $LASTEXITCODE
