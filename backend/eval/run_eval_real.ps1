# Run the full SAMVAAD eval (40 concern questions + 12 aspiration questions) against the real Claude API.
#
#   cd backend; powershell -ExecutionPolicy Bypass -File eval\run_eval_real.ps1
#
# Needs ANTHROPIC_API_KEY in backend\.env (or set in the environment). LLM_MODE is forced to "anthropic" for this
# run only; the models come from ANTHROPIC_MODEL / ANTHROPIC_FAST_MODEL as usual. Results go to eval\results_real.md,
# so the committed mock-mode eval\results.md is not overwritten. Each question uses a private in-memory database.
# This makes real API calls (roughly 52 chat turns plus tagging and goal matching) and is billed to your account.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$env:LLM_MODE = "anthropic"
$env:PYTHONIOENCODING = "utf-8"
try {
    & $py -m eval.run_eval --require-real --out eval\results_real.md
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Remove-Item Env:LLM_MODE -ErrorAction SilentlyContinue
}
