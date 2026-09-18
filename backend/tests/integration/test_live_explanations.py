"""Real Supabase two-user lifecycle; the provider remains deterministic and offline."""

import os

import pytest

from tests.evaluate_explanations import run_evaluation


@pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real Supabase opt-in"
)
def test_live_explanations_with_mock_provider() -> None:
    result = run_evaluation(live_ai=False)
    assert result["critical_grounding_errors"] == 0
    assert result["security_checks"] == 18
