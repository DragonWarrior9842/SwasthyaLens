"""Offline coverage for the explicit one-use live acceptance path."""

import asyncio
import json
import os
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.ai_config import AISettings
from app.core.errors import ApiProblem
from app.core.explanation_context import facts
from app.core.explanation_provider import (
    GenerationPermit,
    OpenAIExplanationProvider,
    context_digest,
)
from app.core.openai_acceptance import create_acceptance_provider
from scripts import accept_openai_once as acceptance
from tests.test_explanations import envelope


def settings() -> AISettings:
    return AISettings(
        _env_file=None,
        ai_provider="openai",
        ai_model="gpt-6.1-sol",
        ai_api_key=SecretStr("synthetic-private-test-key"),
    )


@pytest.mark.parametrize(
    "variant", ["valid", "401", "403", "404", "429", "503", "evidence", "tool"]
)
def test_single_attempt_sanitized_and_no_retry(
    variant: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(acceptance, "AUDIT", tmp_path / "acceptance")
    calls = 0

    async def send(self: httpx.AsyncHTTPTransport, request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert str(request.url) == "https://api.openai.com/v1/responses"
        body = json.loads(request.content)
        assert body["model"] == "gpt-6.1-sol"
        assert body["reasoning"] == {"effort": "low"}
        assert body["max_output_tokens"] == 1536
        assert body["text"]["format"]["strict"] is True
        assert body["tools"] == [] and body["store"] is False
        assert "synthetic-private-test-key" not in request.content.decode()
        if variant.isdigit():
            return httpx.Response(
                int(variant),
                json={
                    "error": {
                        "code": "model_not_found" if variant == "404" else "unrecognized",
                        "message": "synthetic-private-test-key Authorization Bearer private",
                    }
                },
            )
        context = facts([acceptance.synthetic_source()])
        data = envelope(context)
        data["model"] = "gpt-6.1-sol"
        data["output"].insert(0, {"type": "reasoning", "summary": []})
        if variant == "evidence":
            text = json.loads(data["output"][1]["content"][0]["text"])
            text["items"][0]["fact"]["value"] = "180"
            data["output"][1]["content"][0]["text"] = json.dumps(text)
        if variant == "tool":
            data["output"][0] = {"type": "function_call"}
        return httpx.Response(200, json=data)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", send)
    result = asyncio.run(acceptance.attempt(settings()))
    assert result["result"] == ("passed" if variant == "valid" else "failed")
    assert result["outbound_provider_dispatches"] == calls == 1
    assert result["retries"] == 0
    assert "RUN_AI_INTEGRATION" not in os.environ
    assert result["database_storage_access"] is False
    saved = (acceptance.AUDIT / "result.json").read_text()
    assert "synthetic-private-test-key" not in saved and "Bearer" not in saved
    assert result["provider_error_code"] == ("model_not_found" if variant == "404" else None)
    # A second process/run cannot reuse the already consumed authorization.
    with pytest.raises(ValueError, match="already consumed"):
        asyncio.run(acceptance.attempt(settings()))
    assert calls == 1


def test_default_provider_remains_locked_even_with_live_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
    source = acceptance.synthetic_source()
    context = facts([source])
    provider = OpenAIExplanationProvider(settings())
    with pytest.raises(ApiProblem) as error:
        asyncio.run(
            provider.generate(
                context, GenerationPermit(source.observation_id, context_digest(context), True, 25)
            )
        )
    assert error.value.code == "explanation_disabled"
    assert not provider.assistant_available


def test_wrong_provider_model_and_missing_key_fail_before_transport(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        AISettings(_env_file=None, ai_provider="gemini")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="selected"):
        create_acceptance_provider(AISettings(_env_file=None), tmp_path / "marker")
    with pytest.raises(ValueError, match="credential"):
        create_acceptance_provider(
            AISettings(_env_file=None, ai_model="gpt-6.1-sol"), tmp_path / "marker"
        )
    assert not (tmp_path / "marker").exists()
