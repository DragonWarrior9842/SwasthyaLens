"""Offline tests of the live runner fence; synthetic HTTP responses only."""

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest

from app.core.errors import ApiProblem
from app.core.explanation_context import facts
from app.core.explanation_provider import (
    GenerationPermit,
    OpenAIExplanationProvider,
    context_digest,
)
from app.core.openai_acceptance import OneShotOpenAITransport, create_acceptance_provider
from scripts.accept_openai_once import synthetic_source
from scripts.accept_persisted_assistant_once import CheckFailed
from scripts.accept_persisted_explanation_once import VerifiedLiveProvider, run
from tests.test_explanations import envelope
from tests.test_openai_acceptance import settings


@pytest.mark.parametrize(
    "variant", ["valid", "bad_fact", "bad_reservation", "provider_503", "invalid_output"]
)
def test_one_request_after_verified_context_only(
    variant: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "consumed.json"
    real = create_acceptance_provider(settings(), marker)
    assert isinstance(real._transport, OneShotOpenAITransport)
    provider = VerifiedLiveProvider(real)
    provider.sources = [synthetic_source()]
    provider.private = ["synthetic-private-test-key"]
    provider.verify_reservation = Mock()
    if variant == "bad_reservation":
        provider.verify_reservation.side_effect = CheckFailed("wrong_reservation")
    context = facts(provider.sources)
    if variant == "bad_fact":
        context[0].value = "180"
    permit = GenerationPermit(uuid4(), context_digest(context), True, 25)
    dispatches = 0

    async def send(self: httpx.AsyncHTTPTransport, request: httpx.Request) -> httpx.Response:
        nonlocal dispatches
        dispatches += 1
        assert provider.preflight_passed
        assert os.environ.get("RUN_AI_INTEGRATION") == "1"
        assert marker.exists()
        body = json.loads(request.content)
        assert body["model"] == "gpt-6.1-sol" and body["max_output_tokens"] == 1536
        assert body["tools"] == [] and body["store"] is False
        if variant == "provider_503":
            return httpx.Response(503, json={"error": {"code": "unavailable"}})
        data = envelope(context)
        data["model"] = "gpt-6.1-sol"
        if variant == "invalid_output":
            data["output"] = []
        return httpx.Response(200, json=data)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", send)
    try:
        if variant == "valid":
            generated = asyncio.run(provider.generate(context, permit))
            assert generated.output.items[0].fact == context[0]
            assert (
                provider.usage["total_tokens"] == generated.input_tokens + generated.output_tokens
            )
        else:
            with pytest.raises((CheckFailed, ApiProblem)):
                asyncio.run(provider.generate(context, permit))
        expected = 0 if variant in {"bad_fact", "bad_reservation"} else 1
        assert dispatches == real._transport.calls == expected
        assert marker.exists() == bool(expected)
        assert "RUN_AI_INTEGRATION" not in os.environ
        if expected:
            with pytest.raises(CheckFailed):
                asyncio.run(provider.generate(context, permit))
            assert dispatches == 1
    finally:
        asyncio.run(real._transport.aclose())


def test_live_runner_requires_explicit_opt_in() -> None:
    with pytest.raises(CheckFailed, match="explicit_live_authorization_required"):
        run()


def test_mock_transport_cannot_enter_live_runner() -> None:
    real = OpenAIExplanationProvider(settings(), httpx.MockTransport(lambda _: httpx.Response(200)))
    with pytest.raises(CheckFailed, match="one_shot_transport_required"):
        VerifiedLiveProvider(real)
