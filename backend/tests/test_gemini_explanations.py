import asyncio
import copy
import json
from dataclasses import replace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.core.ai_config import AISettings, GeminiSettings
from app.core.errors import ApiProblem
from app.core.explanation_context import facts
from app.core.explanation_provider import (
    GenerationPermit,
    OpenAIExplanationProvider,
    context_digest,
)
from app.core.gemini_explanation_provider import GeminiExplanationProvider, gemini_request_body
from tests.evaluate_explanations import run_evaluation
from tests.explanation_fixtures import mock_output, synthetic_sources


def settings() -> GeminiSettings:
    return GeminiSettings(_env_file=None, ai_api_key=SecretStr("synthetic-test-key"))


def test_gemini_wire_contract_and_exact_preservation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
    context = facts(synthetic_sources()[:20])
    permit = GenerationPermit(uuid4(), context_digest(context), True, 0, 1)
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert (
            str(request.url)
            == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
        )
        assert request.headers["x-goog-api-key"] == "synthetic-test-key"
        body = json.loads(request.content)
        assert body == gemini_request_body(context)
        assert body["store"] is False and body["tools"] == []
        assert set(body) == {"store", "tools", "systemInstruction", "contents", "generationConfig"}
        config = body["generationConfig"]
        assert config["responseMimeType"] == "application/json"
        assert config["responseJsonSchema"]["additionalProperties"] is False
        assert config["responseJsonSchema"]["properties"]["scope"]["enum"] == ["educational"]
        assert config["maxOutputTokens"] == 4000
        assert config["thinkingConfig"] == {"thinkingLevel": "LOW", "includeThoughts": False}
        assert "synthetic-test-key" not in request.content.decode()
        return httpx.Response(200, json=envelope(mock_output(context).model_dump()))

    provider = GeminiExplanationProvider(settings(), httpx.MockTransport(respond))
    result = asyncio.run(provider.generate(context, permit))
    assert result.output == mock_output(context)
    assert result.output_tokens == 102 and result.input_tokens == 100
    assert calls == 1


def envelope(output: object) -> dict[str, Any]:
    return {
        "modelVersion": "gemini-3.8-flash",
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {"role": "model", "parts": [{"text": json.dumps(output)}]},
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 100,
            "candidatesTokenCount": 100,
            "thoughtsTokenCount": 2,
            "totalTokenCount": 202,
        },
    }


@pytest.mark.parametrize(
    "attack",
    [
        "truncated",
        "blocked",
        "tool",
        "code",
        "file",
        "thought",
        "grounding",
        "url",
        "model",
        "multiple",
        "tokens",
        "negative",
        "bool",
        "total",
        "missing_usage",
        "foreign_id",
        "decimal",
        "unit",
        "range",
        "extra",
        "diagnosis",
        "malformed",
    ],
)
def test_gemini_rejects_unsupported_output(monkeypatch: pytest.MonkeyPatch, attack: str) -> None:
    monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
    context = facts(synthetic_sources()[:1])
    output = mock_output(context).model_dump()
    raw = envelope(output)
    candidate = raw["candidates"][0]
    if attack == "truncated":
        candidate["finishReason"] = "MAX_TOKENS"
    elif attack == "blocked":
        raw["promptFeedback"] = {"blockReason": "SAFETY"}
    elif attack in {"tool", "code", "file", "thought"}:
        field = {
            "tool": "functionCall",
            "code": "executableCode",
            "file": "fileData",
            "thought": "thought",
        }[attack]
        candidate["content"]["parts"][0][field] = True
    elif attack in {"grounding", "url"}:
        candidate["groundingMetadata" if attack == "grounding" else "urlContextMetadata"] = {}
    elif attack == "model":
        raw["modelVersion"] = "unapproved-model"
    elif attack == "multiple":
        raw["candidates"].append(copy.deepcopy(candidate))
    elif attack in {"tokens", "negative", "bool", "total"}:
        field = "totalTokenCount" if attack == "total" else "thoughtsTokenCount"
        raw["usageMetadata"][field] = {"tokens": 4001, "negative": -1, "bool": True, "total": 201}[
            attack
        ]
    elif attack == "missing_usage":
        del raw["usageMetadata"]
    elif attack in {"foreign_id", "decimal", "unit", "range"}:
        field, value = {
            "foreign_id": ("evidence_id", "e99"),
            "decimal": ("value", "13.2"),
            "unit": ("unit", "mg/L"),
            "range": ("reference", "0-100"),
        }[attack]
        output["items"][0]["fact"][field] = value
        raw = envelope(output)
    elif attack == "extra":
        output["diagnosis"] = "invented"
        raw = envelope(output)
    elif attack == "diagnosis":
        output["items"][0]["explanation_code"] = "you_have_cancer"
        raw = envelope(output)
    elif attack == "malformed":
        candidate["content"]["parts"][0]["text"] = "{"
    provider = GeminiExplanationProvider(
        settings(), httpx.MockTransport(lambda r: httpx.Response(200, json=raw))
    )
    with pytest.raises(ApiProblem) as error:
        asyncio.run(
            provider.generate(
                context, GenerationPermit(uuid4(), context_digest(context), True, 0, 1)
            )
        )
    assert error.value.code == "explanation_invalid"


@pytest.mark.parametrize("status", [301, 400, 401, 403, 429, 500])
def test_gemini_errors_never_retry_or_expose_body(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
    context = facts(synthetic_sources()[:1])
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status,
            text="sensitive-provider-response",
            headers={"Location": "https://api.openai.com/"},
        )

    provider = GeminiExplanationProvider(settings(), httpx.MockTransport(respond))
    with pytest.raises(ApiProblem) as error:
        asyncio.run(
            provider.generate(
                context, GenerationPermit(uuid4(), context_digest(context), True, 0, 1)
            )
        )
    assert calls == 1
    assert "sensitive-provider-response" not in str(error.value)


def test_gemini_gates_and_openai_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    context = facts(synthetic_sources()[:1])
    permit = GenerationPermit(uuid4(), context_digest(context), True, 0, 1)
    provider = GeminiExplanationProvider(settings())
    assert not provider.available
    with pytest.raises(ApiProblem) as error:
        asyncio.run(provider.generate(context, permit))
    assert error.value.code == "explanation_disabled"
    monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
    for invalid in (
        replace(permit, synthetic_enrolled=False),
        replace(permit, evaluation_attempt=0),
        replace(permit, evaluation_attempt=21),
        replace(permit, reserved_cents=25),
        replace(permit, context_digest="wrong"),
    ):
        with pytest.raises(ApiProblem) as error:
            asyncio.run(provider.generate(context, invalid))
        assert error.value.code == "explanation_evaluation_only"
    openai = OpenAIExplanationProvider(
        AISettings(_env_file=None, ai_api_key=SecretStr("synthetic"))
    )
    with pytest.raises(ApiProblem) as error:
        asyncio.run(openai.generate(context, replace(permit, reserved_cents=25)))
    assert error.value.code == "explanation_disabled"


def test_runner_live_gates_precede_all_network(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(RuntimeError, match="stopped"):
        run_evaluation(live_ai=True)
    with pytest.raises(RuntimeError, match="RUN_AI_INTEGRATION"):
        run_evaluation(live_gemini=True)
    monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
    with pytest.raises(RuntimeError, match="Confirm Free Tier"):
        run_evaluation(live_gemini=True)
