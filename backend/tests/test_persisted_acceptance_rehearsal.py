"""Offline rehearsal of the actual acceptance orchestrator up to provider dispatch.

HTTP application/storage/database boundaries are mocked; PDF extraction, parsing,
review field parsing, owner validation and the production context builder are real.
No private settings, credentials, remote services or AI network are accessed.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.core.assistant_context import ContextBuilder
from app.core.auth_service import AuthenticatedRequest
from app.core.extraction import extract
from app.core.identity import VerifiedIdentity
from app.core.observations import ObservationService
from app.core.parameter_parser import fields, parse
from app.schemas.parameters import RawFields
from scripts import accept_persisted_assistant_once as runner
from tests.auth_support import auth_settings
from tests.test_openai_acceptance import settings


@pytest.mark.parametrize("foreign_owner", [False, True])
def test_whole_runner_reaches_guarded_provider_boundary_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_owner: bool
) -> None:
    config = auth_settings(report_processing_key=SecretStr("synthetic-worker-only"))
    owner, other, report, candidate, obs, conv, run = [str(uuid4()) for _ in range(7)]
    token = "synthetic-owner-session"
    current = AuthenticatedRequest(
        VerifiedIdentity(UUID(owner), uuid4(), "a@test.invalid", 1), token, 1
    )
    state: dict = {}
    steps: list[str] = []
    database = Mock()

    def gateway(method, route, **kwargs):
        assert kwargs["access_token"] == token
        if route == "/rest/v1/reports":
            assert kwargs["params"]["user_id"] == "eq." + owner
            return [{"id": report, "user_id": owner}]
        assert route == "/rest/v1/rpc/observation_call"
        operation = kwargs["payload"]["p_operation"]
        if operation == "list":
            assert kwargs["payload"]["p_payload"]["report_id"] == report
            return {"items": [state["row"]], "offset": 0}
        assert operation == "get"
        assert kwargs["payload"]["p_payload"]["id"] == obs
        return state["row"]

    database.request.side_effect = gateway
    observations = ObservationService(
        SimpleNamespace(
            extraction=SimpleNamespace(settings=config, reports=SimpleNamespace(gateway=database))
        )
    )
    app = SimpleNamespace(
        state=SimpleNamespace(
            assistant_service=SimpleNamespace(builder=ContextBuilder(observations))
        )
    )

    def handle(request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        is_other = "sl_access=synthetic-other-session" in request.headers.get("cookie", "")
        signed_in = "sl_access=" in request.headers.get("cookie", "")
        body = json.loads(request.content) if request.content and method != "PUT" else {}
        status, output = 200, {}
        # Every preparation request must run while the live gate is absent.
        assert "RUN_AI_INTEGRATION" not in os.environ
        if path == "/auth/csrf":
            output = {"csrf_token": "synthetic-csrf"}
        elif path == "/auth/login":
            second = body["email"] == "b@test.invalid"
            return httpx.Response(
                200,
                json={"user": {"id": other if second else owner}},
                headers={
                    "Set-Cookie": "sl_access="
                    + ("synthetic-other-session" if second else token)
                    + "; Path=/"
                },
            )
        elif path == "/auth/logout":
            pass
        elif path == "/settings":
            output = {"assistant_language": "en"}
        elif path == "/assistant/conversations" and method == "GET":
            status, output = (200, {"conversations": []}) if signed_in else (401, {})
        elif path == "/reports" and method == "POST":
            steps.append("reserve")
            output, status = {"id": report}, 201
        elif path == f"/reports/{report}/file":
            assert steps[-1] == "reserve"
            steps.append("upload")
            state["pdf"] = request.content
        elif path == f"/reports/{report}/process":
            assert steps[-1] == "upload"
            state["extracted"] = extract(state["pdf"], "application/pdf", config)
            steps.append("extract")
            status = 202
        elif path == f"/reports/{report}/processing":
            output = {"runs": [{"id": run, "status": "completed"}]}
        elif path == f"/reports/{report}/extract-parameters":
            assert body["source_run_id"] == run
            parsed, _ = parse(state["extracted"].pages)
            assert len(parsed) == 1
            state["content"] = parsed[0].model_dump(mode="json")
            steps.append("parse")
        elif path == f"/reports/{report}/parameters":
            output = {"candidates": [{"id": candidate, "content": state["content"]}]}
        elif path == f"/reports/{report}/parameters/{candidate}":
            assert body["action"] == "corrected" and body["expected_revision"] == 0
            state["reviewed"] = fields(RawFields.model_validate(body["correction"])).model_dump(
                mode="json"
            )
            steps.append("review")
        elif path == f"/reports/{report}/parameters/{candidate}/publish":
            assert steps[-1] == "review" and body["expected_revision"] == 1
            now = "2026-10-03T12:00:00Z"
            revision = dict(
                revision=1,
                status="active",
                fields=state["reviewed"],
                catalog_version="observations-v1",
                measurement_date=body["measurement_date"],
                measured_at=None,
                candidate_id=candidate,
                review_revision=1,
                created_at=now,
                status_changed_at=now,
            )
            state["row"] = dict(
                id=obs,
                user_id=owner,
                source_type="report",
                report_id=report,
                candidate_id=candidate,
                created_at=now,
                current=revision,
                revisions=[revision],
                evidence=dict(
                    report_name="synthetic.pdf",
                    report_created_at=now,
                    source_run_id=run,
                    parameter_run_id=str(uuid4()),
                    content=state["content"],
                ),
            )
            # Real DTO intentionally omits user_id, exactly as in the failed Gate B.
            output = ObservationService.row(state["row"], current).model_dump(mode="json")
            assert "user_id" not in output
            steps.append("publish")
        elif path == f"/observations/{obs}" and is_other:
            status = 404
        elif path == "/assistant/conversations" and method == "POST":
            assert steps[-1] == "owner_verified"
            output = {"conversation": {"id": conv}, "messages": []}
            steps.append("conversation")
        elif path == f"/assistant/conversations/{conv}/messages":
            guarded = app.state.assistant_service.builder
            context = guarded.build(body["content"], [], current, "en")
            assert guarded.verified and os.environ["RUN_AI_INTEGRATION"] == "1"
            assert guarded.provider.expected_input_digest is not None
            assert context.expected().evidence_ids == ["e1"]
            steps.append("provider_boundary")
            # Deliberate stop before dispatch; no provider monkeypatch or live bypass.
            raise runner.CheckFailed("offline_provider_boundary_reached")
        elif method == "DELETE":
            steps.append("cleanup")
        else:
            raise AssertionError((method, path))
        return httpx.Response(status, json=output)

    def data(live, user, method, route, body=None):
        assert "RUN_AI_INTEGRATION" not in os.environ
        if route.startswith("health_observations?"):
            assert user.user_id == owner and user.access == token
            assert route == f"health_observations?id=eq.{obs}&select=id,user_id"
            steps.append("owner_verified")
            rows = [{"id": obs, "user_id": other if foreign_owner else owner}]
        elif route == "assistant_conversations?id=eq." + conv:
            rows = [{"id": conv, "user_id": owner}]
        else:
            assert user.user_id == other
            rows = []
        return httpx.Response(200, json=rows)

    # Any accidental non-mock I/O fails before connecting, including Supabase.
    def forbid_network(*args, **kwargs):
        raise AssertionError("Unexpected external I/O in offline rehearsal")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbid_network)
    monkeypatch.setattr(runner, "AUDIT", tmp_path)
    monkeypatch.setattr(runner, "offline_preflight", lambda: (config, settings()))
    monkeypatch.setattr(
        runner,
        "dotenv_values",
        lambda _: {"TEST_USER_A_EMAIL": "a@test.invalid", "TEST_USER_B_EMAIL": "b@test.invalid"},
    )
    monkeypatch.setattr(runner, "create_app", lambda *args, **kwargs: app)
    monkeypatch.setattr(
        runner,
        "TestClient",
        lambda app, base_url: httpx.Client(
            base_url=base_url, transport=httpx.MockTransport(handle)
        ),
    )
    monkeypatch.setattr(runner.LiveContext, "data", data)
    result = runner.execute()
    assert result["new_openai_attempts"] == 0
    assert result["provider_invocation_started"] is False
    assert result["synthetic_cleanup_and_preferences"] == "passed"
    assert "RUN_AI_INTEGRATION" not in os.environ
    assert not (tmp_path / "attempt-reserved.json").exists()
    assert steps[:7] == [
        "reserve",
        "upload",
        "extract",
        "parse",
        "review",
        "publish",
        "owner_verified",
    ]
    if foreign_owner:
        assert result["failure_category"] == "observation_owner"
        assert "provider_boundary" not in steps
    else:
        assert "provider_boundary" in steps
        assert result["failure_category"] == "offline_provider_boundary_reached"
        assert result["context_authorization"] == "passed"
        assert result["context_metadata"]["evidence_count"] == 1
