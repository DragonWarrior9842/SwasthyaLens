"""Preparation harness guards only; no remote API or provider call."""

import asyncio
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest

from app.core.explanation_context import facts
from app.core.explanation_provider import GenerationPermit, context_digest
from scripts.accept_openai_once import synthetic_source
from scripts.accept_persisted_assistant_once import CheckFailed
from scripts.rehearse_phase7_lifecycle import PreparationProvider, verify_deleted_facts


@pytest.mark.parametrize("variant", ["matching", "wrong_fact", "unreserved", "wrong_digest"])
def test_preparation_preserves_real_context_and_reservation_contract(variant: str) -> None:
    provider = PreparationProvider()
    provider.sources = [synthetic_source()]
    provider.private = ["synthetic-private-secret"]
    provider.verify_reservation = Mock()
    context = facts(provider.sources)
    permit = GenerationPermit(
        uuid4(),
        "wrong" if variant == "wrong_digest" else context_digest(context),
        True,
        0 if variant == "unreserved" else 25,
    )
    if variant == "wrong_fact":
        context[0].value = "80"
    if variant == "matching":
        result = asyncio.run(provider.generate(context, permit))
        assert result.output.items[0].fact == context[0]
        assert provider.calls == 1
        assert provider.boundaries[0]["reservation_model"] == "gpt-6.1-sol"
    else:
        with pytest.raises(CheckFailed):
            asyncio.run(provider.generate(context, permit))
        assert provider.calls == 0


def test_preparation_cannot_activate_when_live_gate_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = PreparationProvider()
    provider.sources = [synthetic_source()]
    provider.verify_reservation = Mock()
    context = facts(provider.sources)
    monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
    assert not provider.available
    with pytest.raises(CheckFailed):
        asyncio.run(
            provider.generate(context, GenerationPermit(uuid4(), context_digest(context), True, 25))
        )
    assert provider.calls == 0
    provider.verify_reservation.assert_not_called()


@pytest.mark.parametrize("retained", [None, 0, 1, 2])
def test_deleted_report_denial_does_not_substitute_for_fact_verification(
    retained: int | None,
) -> None:
    user, live = Mock(), Mock()
    user.client.get.return_value = httpx.Response(404)
    live.data.side_effect = [
        httpx.Response(200, json=[{"id": "synthetic"}] if retained == index else [])
        for index in range(3)
    ]
    if retained is None:
        verify_deleted_facts(live, user, "report", "observation")
        assert live.data.call_count == 3
    else:
        with pytest.raises(CheckFailed, match="deleted_facts_and_revisions_absent"):
            verify_deleted_facts(live, user, "report", "observation")


def test_deleted_report_requires_404() -> None:
    user, live = Mock(), Mock()
    user.client.get.return_value = httpx.Response(200, json={"items": []})
    with pytest.raises(CheckFailed, match="deleted_observations_inaccessible"):
        verify_deleted_facts(live, user, "report", "observation")
    live.data.assert_not_called()
