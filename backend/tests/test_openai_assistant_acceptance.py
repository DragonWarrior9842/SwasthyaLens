"""Offline single-use Phase 9 provider, schema and evidence checks."""

import asyncio
import hashlib
import json
from pathlib import Path

import httpx
import pytest

from app.core.assistant_context import Context, validate_answer
from app.core.errors import ApiProblem
from app.core.explanation_context import facts
from app.core.explanation_provider import assistant_request
from app.core.openai_assistant_acceptance import OpenAIAssistantAcceptance
from app.schemas.assistant import AssistantFact
from scripts.accept_openai_once import synthetic_source
from tests.test_openai_acceptance import settings


@pytest.mark.parametrize("variant", ["owned", "empty", "foreign", "wrong_id"])
def test_public_observation_owner_check_uses_rls(variant: str) -> None:
    from scripts.accept_persisted_assistant_once import CheckFailed, verify_observation_owner
    from tests.integration.test_live_ownership import LiveContext, SignedInUser

    observation = {"id": "synthetic-observation"}  # Public DTO has no user_id.

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/health_observations"
        assert request.url.params["select"] == "id,user_id"
        assert request.headers["Authorization"] == "Bearer synthetic-user-token"
        rows = (
            []
            if variant == "empty"
            else [
                {
                    "id": "wrong" if variant == "wrong_id" else observation["id"],
                    "user_id": "other" if variant == "foreign" else "owner",
                }
            ]
        )
        return httpx.Response(200, json=rows)

    with httpx.Client(
        base_url="https://synthetic.invalid/rest/v1/", transport=httpx.MockTransport(handle)
    ) as database:
        owner = SignedInUser(database, "synthetic-csrf", "synthetic-user-token", "owner")
        live = LiveContext((owner, owner), database)
        if variant == "owned":
            verify_observation_owner(live, owner, observation)
        else:
            with pytest.raises(CheckFailed) as error:
                verify_observation_owner(live, owner, observation)
            assert error.value.category == "observation_owner"


def test_recorded_failed_run_cannot_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import accept_persisted_assistant_once as acceptance

    monkeypatch.setattr(acceptance, "AUDIT", tmp_path)
    (tmp_path / "result.json").write_text('{"new_openai_attempts":0}', encoding="utf-8")
    with pytest.raises(acceptance.CheckFailed) as error:
        acceptance.offline_preflight()
    assert error.value.category == "acceptance_run_already_recorded"


def context() -> Context:
    f = facts([synthetic_source()])[0].model_dump()
    f.update(measurement_date="2026-10-03", measured_at=None, source_type="report")
    return Context(
        "Explain my latest uploaded report.",
        [],
        "sources",
        "latest_uploaded_report",
        [AssistantFact.model_validate(f)],
    )


@pytest.mark.parametrize(
    "variant", ["valid", "401", "403", "404", "429", "503", "evidence", "model", "tool"]
)
def test_assistant_response_and_no_retry(
    variant: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = OpenAIAssistantAcceptance(settings(), tmp_path / "attempt")
    ctx = context()
    request = assistant_request(ctx)
    provider.expected_input_digest = hashlib.sha256(request.input_json.encode()).hexdigest()
    monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
    calls = 0

    async def send(self: httpx.AsyncHTTPTransport, outgoing: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        body = json.loads(outgoing.content)
        assert body["input"][0]["content"][0]["text"] == request.input_json
        assert body["model"] == "gpt-6.1-sol" and body["max_output_tokens"] == 1536
        assert body["text"]["format"]["schema"] == request.output_schema
        if variant.isdigit():
            return httpx.Response(
                int(variant),
                json={
                    "error": {
                        "code": "model_not_found",
                        "message": "synthetic-private-test-key must stay private",
                    }
                },
            )
        answer = ctx.expected().model_dump()
        if variant == "evidence":
            answer["evidence_ids"] = ["foreign"]
        message = {
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": json.dumps(answer)}],
        }
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "store": False,
                "model": "other-model" if variant == "model" else "gpt-6.1-sol",
                "output": [
                    {"type": "function_call" if variant == "tool" else "reasoning"},
                    message,
                ],
                "usage": {"input_tokens": 900, "output_tokens": 100, "total_tokens": 1000},
            },
        )

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", send)
    if variant == "valid":
        output = asyncio.run(provider.generate_assistant(request))
        assert validate_answer(output, ctx) == ctx.expected()
        assert provider.usage["total_tokens"] == 1000
    else:
        with pytest.raises(ApiProblem) as error:
            output = asyncio.run(provider.generate_assistant(request))
            validate_answer(output, ctx)
        assert "synthetic-private-test-key" not in str(error.value)
    with pytest.raises(ApiProblem):
        asyncio.run(provider.generate_assistant(request))
    assert calls == provider.transport.calls == 1
    assert not provider.assistant_available


def test_live_flag_and_verified_context_both_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = OpenAIAssistantAcceptance(settings(), tmp_path / "attempt")
    request = assistant_request(context())
    for flag in (False, True):
        if flag:
            monkeypatch.setenv("RUN_AI_INTEGRATION", "1")
        with pytest.raises(ApiProblem):
            asyncio.run(provider.generate_assistant(request))
    assert provider.transport.calls == 0
    assert not (tmp_path / "attempt").exists()
