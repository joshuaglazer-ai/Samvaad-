"""The real-API eval must never fall back to mock mode silently (backend/eval/run_eval_real.*)."""
import pytest


def test_require_real_stops_without_a_key(monkeypatch, tmp_path):
    from app import config
    from eval import run_eval

    out = tmp_path / "results_real.md"
    monkeypatch.setenv("LLM_MODE", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setattr("sys.argv", ["run_eval", "--require-real", "--out", str(out)])
    config.get_settings.cache_clear()
    try:
        with pytest.raises(SystemExit, match="Nothing was run"):
            run_eval.main()
    finally:
        config.get_settings.cache_clear()
    assert not out.exists()
