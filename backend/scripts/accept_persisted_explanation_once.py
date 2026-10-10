"""Exactly one authorized persisted Phase 7 OpenAI request; explicit --live only.

Derived from the passed Gate H application workflow. No mock generation, retry,
fallback or second fixture. A durable run marker also fences pre-dispatch stops.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from app.core.ai_config import AISettings
from app.core.config import Settings
from app.core.errors import ApiProblem
from app.core.explanation_context import (
    CATALOG_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    facts,
    model_input,
)
from app.core.explanation_provider import (
    GenerationPermit,
    GenerationResult,
    OpenAIExplanationProvider,
    context_digest,
    request_body,
)
from app.core.openai_acceptance import OneShotOpenAITransport, create_acceptance_provider
from app.factory import create_app
from app.schemas.explanations import ModelFact, SourceEvidence
from scripts.accept_persisted_assistant_once import (
    CheckFailed,
    checked,
    require,
    verify_observation_owner,
)
from tests import extraction_fixtures
from tests.integration.test_live_extraction import finish
from tests.integration.test_live_ownership import LiveContext, SignedInUser
from tests.integration.test_live_reports import metadata, put_file

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / ".cache/phase13/openai-persisted-explanation-9"


def verify_deleted_facts(
    live: LiveContext, user: SignedInUser, report: str, observation: str
) -> None:
    """Assert denial and independently inspect owner-scoped fact/revision rows."""
    require(
        user.client.get("/observations?report_id=" + report).status_code == 404,
        "deleted_observations_inaccessible",
    )
    require(
        user.client.get("/observations/" + observation).status_code == 404,
        "deleted_observation_id_inaccessible",
    )
    for query in (
        "health_observations?report_id=eq." + report,
        "health_observations?id=eq." + observation,
        "health_observation_revisions?observation_id=eq." + observation,
    ):
        require(
            checked(live.data(user, "GET", query), 200, "deleted_fact_rows") == [],
            "deleted_facts_and_revisions_absent",
        )


class VerifiedLiveProvider:
    """Verify the actual application context/reservation before enabling one dispatch."""

    name = "openai"
    model = "gpt-6.1-sol"

    def __init__(self, real: OpenAIExplanationProvider) -> None:
        require(type(real) is OpenAIExplanationProvider, "real_provider_required")
        require(type(real._transport) is OneShotOpenAITransport, "one_shot_transport_required")
        require(real.name == "openai" and real.model == self.model, "exact_real_provider")
        self.real = real
        self.preflight_passed = False
        self.failure_category: str | None = None
        self.usage: dict[str, object] = {}
        self.calls = 0
        self.sources: list[SourceEvidence] = []
        self.private: list[str] = []
        self.verify_reservation: Any = None
        self.boundaries: list[dict[str, object]] = []

    @property
    def available(self) -> bool:
        return "RUN_AI_INTEGRATION" not in os.environ

    async def generate(
        self, context: list[ModelFact], permit: GenerationPermit
    ) -> GenerationResult:
        require(self.available and self.calls == 0, "single_live_boundary")
        require(context == facts(self.sources) and len(context) == 1, "exact_current_context")
        require(permit.synthetic_enrolled and permit.reserved_cents == 25, "real_reservation")
        require(permit.context_digest == context_digest(context), "reservation_context_digest")
        self.verify_reservation(permit)
        serialized = model_input(context)
        for secret in self.private:
            require(bool(secret) and secret not in serialized, "context_private_data")
        f = context[0]
        require(
            f.evidence_id == "e1"
            and f.value == "18"
            and f.unit == "ng/mL"
            and f.reference == "30–100",
            "exact_synthetic_fact",
        )
        body = request_body(context, model=self.model, max_output_tokens=1536)
        require(len(json.dumps(body, ensure_ascii=False).encode()) <= 10000, "bounded_request")
        require(
            body["tools"] == [] and body["tool_choice"] == "none" and body["store"] is False,
            "no_tools_or_storage",
        )
        self.boundaries.append(
            {
                "evidence_count": 1,
                "opaque_ids": True,
                "reservation_model": self.model,
                "context_bytes": len(serialized.encode()),
            }
        )
        require(not self.real.available, "live_gate_locked_before_preflight")
        require(type(self.real._transport) is OneShotOpenAITransport, "no_mock_transport")
        assert isinstance(self.real._transport, OneShotOpenAITransport)
        require(self.real._transport.calls == 0, "authorization_not_consumed")
        self.preflight_passed = True
        self.calls += 1
        # This is the only live enablement. All real owner/context/reservation checks ran above.
        os.environ["RUN_AI_INTEGRATION"] = "1"
        try:
            generated = await self.real.generate(context, permit)
            self.usage = {
                "input_tokens": generated.input_tokens,
                "output_tokens": generated.output_tokens,
                "total_tokens": generated.input_tokens + generated.output_tokens,
                "estimated_cost_usd": round(
                    (generated.input_tokens * 2 + generated.output_tokens * 10) / 1000000, 6
                ),
            }
            return generated
        except ApiProblem as error:
            self.failure_category = error.code
            raise
        finally:
            os.environ.pop("RUN_AI_INTEGRATION", None)


def run(*, live_authorized: bool = False) -> dict[str, Any]:
    require(live_authorized, "explicit_live_authorization_required")
    require("RUN_AI_INTEGRATION" not in os.environ, "live_gate_must_be_unset")
    require(not (AUDIT / "result.json").exists(), "preparation_already_recorded")
    require(not (AUDIT / "run-started.json").exists(), "acceptance_already_started")
    require(not (AUDIT / "attempt-reserved.json").exists(), "authorization_already_consumed")
    config, ai = Settings(), AISettings()
    require(config.environment == "development" and not config.secure_cookies, "development_only")
    require(config.supabase_url == "https://rbmpfgndidpzdssiicyf.supabase.co", "dedicated_project")
    require(
        ai.ai_provider == "openai" and ai.ai_model == "gpt-6.1-sol" and ai.ai_api_key is not None,
        "selected_provider_configuration",
    )
    values = dotenv_values(ROOT / "backend/.env.integration")
    require(values.get("DISPOSABLE_TEST_ACCOUNTS_CONFIRMED") == "1", "dedicated_accounts")
    assert config.report_processing_key is not None
    assert config.supabase_url is not None
    assert config.supabase_publishable_key is not None
    assert ai.ai_api_key is not None
    worker = config.report_processing_key.get_secret_value()
    AUDIT.mkdir(parents=True, exist_ok=True)
    with (AUDIT / "run-started.json").open("x", encoding="utf-8") as started:
        started.write('{"authorized_max_requests":1,"prior_openai_requests":2}\n')
    live_candidate = create_acceptance_provider(ai, AUDIT / "attempt-reserved.json")
    provider = VerifiedLiveProvider(live_candidate)
    require(
        not live_candidate.available and type(live_candidate._transport) is OneShotOpenAITransport,
        "real_live_adapter_stays_locked",
    )
    original_send = httpx.HTTPTransport.handle_request

    def supabase_only(transport: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        require(
            request.url.host == "rbmpfgndidpzdssiicyf.supabase.co", "external_network_forbidden"
        )
        return original_send(transport, request)

    original_async = httpx.AsyncHTTPTransport.handle_async_request

    async def one_openai_only(
        transport: httpx.AsyncHTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        require(
            isinstance(live_candidate._transport, OneShotOpenAITransport)
            and transport is live_candidate._transport
            and request.method == "POST"
            and str(request.url) == "https://api.openai.com/v1/responses"
            and provider.preflight_passed
            and provider.calls == 1
            and live_candidate._transport.calls == 1
            and os.environ.get("RUN_AI_INTEGRATION") == "1",
            "unauthorized_async_network",
        )
        return await original_async(transport, request)

    result: dict[str, Any] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "correlation_id": str(uuid4()),
        "mode": "single_live_real_application",
        "requested_model": "gpt-6.1-sol",
        "conservative_cost_bound_usd": 0.06,
        "result": "not_started",
        "new_ai_requests": 0,
        "total_openai_live_requests": 2,
        "gemini_attempts": "2/20 unchanged",
        "retries": 0,
        "fallbacks": 0,
    }
    reports: list[tuple[SignedInUser, str]] = []
    manuals: list[tuple[SignedInUser, str]] = []
    stage = "login"
    with ExitStack() as stack:
        stack.enter_context(patch.object(httpx.HTTPTransport, "handle_request", supabase_only))
        stack.enter_context(
            patch.object(httpx.AsyncHTTPTransport, "handle_async_request", one_openai_only)
        )
        app = create_app(config, explanation_provider=provider)
        first = stack.enter_context(TestClient(app, base_url="http://127.0.0.1:8000"))
        second = TestClient(app, base_url="http://127.0.0.1:8000")
        stack.callback(second.close)
        users = []
        try:
            for name, client in zip(("A", "B"), (first, second), strict=True):
                client.headers["Origin"] = config.app_origin
                csrf = checked(client.get("/auth/csrf"), 200, "csrf")["csrf_token"]
                identity = checked(
                    client.post(
                        "/auth/login",
                        json={
                            "email": values.get(f"TEST_USER_{name}_EMAIL"),
                            "password": values.get(f"TEST_USER_{name}_PASSWORD"),
                        },
                        headers={"X-CSRF-Token": csrf},
                    ),
                    200,
                    "login",
                )["user"]["id"]
                user = SignedInUser(
                    cast(httpx.Client, client),
                    checked(client.get("/auth/csrf"), 200, "session_csrf")["csrf_token"],
                    client.cookies.get("sl_access") or "",
                    identity,
                )
                users.append(user)
                stack.callback(user.close_session)
            require(users[0].user_id != users[1].user_id, "distinct_owners")
            database = stack.enter_context(
                httpx.Client(
                    base_url=config.supabase_url + "/rest/v1/",
                    timeout=30,
                    trust_env=False,
                    headers={"apikey": config.supabase_publishable_key.get_secret_value()},
                )
            )
            live = LiveContext((users[0], users[1]), database)

            def rpc(
                user: SignedInUser,
                operation: str,
                report: str,
                payload: dict[str, Any] | None = None,
            ) -> httpx.Response:
                return live.data(
                    user,
                    "POST",
                    "rpc/explanation_call",
                    {
                        "p_operation": operation,
                        "p_payload": {"report_id": report, **(payload or {})},
                        "p_worker_secret": worker,
                    },
                )

            completed = []
            for index, owner in enumerate(users[:1]):
                other = users[1 - index]
                stage = "synthetic_report_workflow"
                old_lines = extraction_fixtures.LINES
                try:
                    extraction_fixtures.LINES = [
                        "SYNTHETIC ONLY - NOT PATIENT DATA",
                        "Parameter | Result | Unit | Reference | Flag",
                        "Vitamin D | 18 | ng/mL | 30-100 |",
                        "Synthetic rejected | 9 | | |",
                        "Synthetic unreviewed | 7 | | |",
                    ]
                    data = extraction_fixtures.document(("native",), size=1000)
                finally:
                    extraction_fixtures.LINES = old_lines
                report = checked(
                    owner.write(
                        "POST",
                        "/reports",
                        metadata("synthetic-phase7-live-acceptance.pdf", "application/pdf", data),
                    ),
                    201,
                    "reserve_report",
                )["id"]
                reports.append((owner, report))
                checked(put_file(owner, report, data, "application/pdf"), 200, "upload")
                route = f"/reports/{report}"
                path = route + "/explanations"
                checked(
                    owner.write("POST", route + "/process", {"idempotency_key": str(uuid4())}),
                    202,
                    "extract",
                )
                source = finish(owner, report)
                require(source["status"] == "completed", "extraction_completed")
                checked(
                    owner.write(
                        "POST",
                        route + "/extract-parameters",
                        {"source_run_id": source["id"], "idempotency_key": str(uuid4())},
                    ),
                    200,
                    "parse",
                )
                candidates = checked(owner.client.get(route + "/parameters"), 200, "candidates")[
                    "candidates"
                ]
                require(len(candidates) == 3, "three_synthetic_candidates")
                candidate = next(
                    c for c in candidates if c["content"]["fields"]["original_label"] == "Vitamin D"
                )
                rejected = next(
                    c
                    for c in candidates
                    if c["content"]["fields"]["original_label"] == "Synthetic rejected"
                )
                require(
                    checked(owner.client.get(path), 200, "unreviewed_state")["eligible_count"] == 0,
                    "unreviewed_excluded",
                )
                checked(
                    owner.write(
                        "PATCH",
                        route + "/parameters/" + rejected["id"],
                        {
                            "idempotency_key": str(uuid4()),
                            "expected_revision": 0,
                            "action": "rejected",
                        },
                    ),
                    200,
                    "reject",
                )
                review = route + "/parameters/" + candidate["id"]
                correction = {
                    "original_label": "Vitamin D",
                    "raw_value": "18",
                    "original_unit": "ng/mL",
                    "raw_reference": "30–100",
                }
                checked(
                    owner.write(
                        "PATCH",
                        review,
                        {
                            "idempotency_key": str(uuid4()),
                            "expected_revision": 0,
                            "action": "corrected",
                            "correction": correction,
                        },
                    ),
                    200,
                    "review",
                )
                require(
                    checked(owner.client.get(path), 200, "unpublished_state")["eligible_count"]
                    == 0,
                    "unpublished_excluded",
                )
                observation = checked(
                    owner.write(
                        "POST",
                        review + "/publish",
                        {"expected_revision": 1, "measurement_date": None},
                    ),
                    200,
                    "publish",
                )
                verify_observation_owner(live, owner, observation)
                c = candidate["content"]
                expected: list[dict[str, Any]] = [
                    {
                        "observation_id": observation["id"],
                        "revision": 1,
                        "candidate_id": candidate["id"],
                        "review_revision": 1,
                        "source_run_id": source["id"],
                        "parameter_run_id": candidate["run_id"],
                        "page_number": c["page_number"],
                        "source_start": c["source_start"],
                        "source_end": c["source_end"],
                        "fields": observation["current"]["fields"],
                    }
                ]
                state = checked(rpc(owner, "state", report), 200, "trusted_state")
                require(state["evidence"] == expected, "current_owned_evidence_only")
                checked(
                    rpc(
                        owner,
                        "enroll_synthetic",
                        report,
                        {
                            "fixture_sha256": hashlib.sha256(data).hexdigest(),
                            "expected_evidence": expected,
                        },
                    ),
                    200,
                    "exact_synthetic_enrollment",
                )
                provider.sources = [SourceEvidence.model_validate(e) for e in expected]
                assert isinstance(source["id"], str)
                provider.private = [
                    owner.access,
                    worker,
                    ai.ai_api_key.get_secret_value(),
                    owner.user_id,
                    report,
                    observation["id"],
                    candidate["id"],
                    source["id"],
                    candidate["run_id"],
                ]

                def verify_reserved(
                    permit: GenerationPermit,
                    owner: SignedInUser = owner,
                    report: str = report,
                    expected: list[dict[str, Any]] = expected,
                    other: SignedInUser = other,
                ) -> None:
                    rows = checked(
                        live.data(
                            owner, "GET", "report_explanations?id=eq." + str(permit.generation_id)
                        ),
                        200,
                        "persisted_reservation",
                    )
                    require(len(rows) == 1, "one_reservation")
                    row = rows[0]
                    require(
                        row["user_id"] == owner.user_id
                        and row["report_id"] == report
                        and row["provider"] == "openai"
                        and row["model"] == "gpt-6.1-sol"
                        and row["status"] == "generating"
                        and row["evidence"] == expected,
                        "selected_model_owner_reservation",
                    )
                    require(
                        row["prompt_version"] == PROMPT_VERSION
                        and row["schema_version"] == SCHEMA_VERSION
                        and row["catalog_version"] == CATALOG_VERSION,
                        "reservation_versions",
                    )
                    require(
                        checked(
                            live.data(other, "GET", "report_explanations?id=eq." + row["id"]),
                            200,
                            "foreign_reservation",
                        )
                        == [],
                        "foreign_reservation_hidden",
                    )
                    for method in ("PATCH", "DELETE"):
                        require(
                            live.data(
                                other,
                                method,
                                "report_explanations?id=eq." + row["id"],
                                {"status": "failed"} if method == "PATCH" else None,
                            ).status_code
                            == 403,
                            "foreign_reservation_mutation_denied",
                        )

                provider.verify_reservation = verify_reserved
                stage = "live_generation_and_persistence"
                body = {"idempotency_key": str(uuid4()), "consent": True}
                calls_before = provider.calls
                for response in (
                    other.client.get(route),
                    other.client.get(path),
                    other.write("POST", path, body),
                    other.write("DELETE", route, {}),
                ):
                    require(response.status_code == 404, "foreign_report_mutation_read_denied")
                result_view = checked(owner.write("POST", path, body), 200, "live_generation")
                require("RUN_AI_INTEGRATION" not in os.environ, "gate_cleared_after_generation")
                record = result_view["record"]
                if record is None or record["status"] != "ready":
                    raise CheckFailed(provider.failure_category or "generation_not_ready")
                require(
                    record["status"] == "ready"
                    and record["model"] == "gpt-6.1-sol"
                    and record["provider"] == "openai"
                    and len(record["items"]) == 1,
                    "persisted_ready_model",
                )
                require(record["items"][0]["source"] == expected[0], "persisted_exact_evidence")
                require(
                    checked(owner.client.get(path), 200, "reload")["record"] == record,
                    "same_record_on_reload",
                )
                persisted = checked(
                    live.data(owner, "GET", "report_explanations?id=eq." + record["id"]),
                    200,
                    "persisted_ready_row",
                )
                require(
                    len(persisted) == 1
                    and persisted[0]["user_id"] == owner.user_id
                    and persisted[0]["report_id"] == report
                    and persisted[0]["evidence"] == expected
                    and persisted[0]["provider"] == "openai"
                    and persisted[0]["model"] == "gpt-6.1-sol"
                    and persisted[0]["prompt_version"] == PROMPT_VERSION
                    and persisted[0]["schema_version"] == SCHEMA_VERSION
                    and persisted[0]["catalog_version"] == CATALOG_VERSION == "education-en-v1"
                    and persisted[0]["input_tokens"] == provider.usage["input_tokens"]
                    and persisted[0]["output_tokens"] == provider.usage["output_tokens"],
                    "persisted_owner_evidence_versions_usage",
                )
                result.update(
                    persistence="passed",
                    evidence_associations="passed",
                    reload="passed",
                    structured_validation="passed",
                    evidence_validation="passed",
                    response_language="fixed English catalog education-en-v1",
                    fixture_date="not_supplied_no_fabrication",
                    reload_additional_calls=0,
                )
                require(provider.calls == calls_before + 1, "reload_replay_zero_calls")
                require(
                    other.client.get(path + "/" + record["id"]).status_code == 404,
                    "foreign_explanation_hidden",
                )
                require(
                    checked(
                        live.data(other, "GET", "report_explanations?id=eq." + record["id"]),
                        200,
                        "foreign_answer_evidence",
                    )
                    == [],
                    "foreign_answer_hidden",
                )
                require(
                    live.data(
                        other, "DELETE", "report_explanations?id=eq." + record["id"]
                    ).status_code
                    == 403,
                    "foreign_direct_mutation_denied",
                )
                stage = "correction_stale_superseded"
                checked(
                    owner.write(
                        "PATCH",
                        review,
                        {
                            "idempotency_key": str(uuid4()),
                            "expected_revision": 1,
                            "action": "corrected",
                            "correction": {**correction, "raw_value": "19"},
                        },
                    ),
                    200,
                    "correct_source",
                )
                stale = checked(owner.client.get(path), 200, "stale_state")
                require(
                    stale["record"]["status"] == "stale"
                    and stale["record"]["items"] == []
                    and stale["eligible_count"] == 0,
                    "stale_erased_and_unpublished",
                )
                old = checked(
                    owner.client.get("/observations/" + observation["id"]), 200, "superseded_source"
                )
                require(old["current"]["status"] == "superseded", "prior_revision_superseded")
                require(
                    checked(rpc(owner, "state", report), 200, "superseded_context")["evidence"]
                    == [],
                    "superseded_evidence_excluded",
                )
                revised = checked(
                    owner.write(
                        "POST",
                        review + "/publish",
                        {"expected_revision": 2, "measurement_date": None},
                    ),
                    200,
                    "republish_corrected_source",
                )
                current = checked(rpc(owner, "state", report), 200, "corrected_context")
                require(
                    len(current["evidence"]) == 1
                    and current["evidence"][0]["revision"] == 2
                    and current["evidence"][0]["fields"]["raw_value"] == "19"
                    and current["record"]["status"] == "stale",
                    "only_corrected_revision_current",
                )
                require(revised["current"]["revision"] == 2, "published_revision_two")
                result.update(correction_stale="passed", superseded_exclusion="passed")
                stage = "deletion_and_manual_preservation"
                manual = checked(
                    owner.write(
                        "POST",
                        "/observations/manual",
                        {
                            "idempotency_key": str(uuid4()),
                            "metric": "weight",
                            "unit": "kg",
                            "raw_value": "70",
                            "measured_at": "2020-01-02T12:00:00Z",
                        },
                    ),
                    200,
                    "unrelated_synthetic_manual",
                )
                manuals.append((owner, manual["id"]))
                before_manual = checked(
                    owner.client.get("/observations/" + manual["id"]), 200, "manual_before"
                )
                checked(owner.write("DELETE", route, {}), 200, "owner_report_delete")
                reports.remove((owner, report))
                for user in (owner, other):
                    require(
                        user.client.get(route).status_code == 404
                        and user.client.get(route + "/file").status_code == 404,
                        "deleted_report_and_object_inaccessible",
                    )
                    require(
                        user.client.get(path).status_code == 404
                        and user.client.get(path + "/" + record["id"]).status_code == 404,
                        "deleted_explanation_inaccessible",
                    )
                    deleted_context = rpc(user, "state", report)
                    require(
                        deleted_context.status_code == 400
                        and deleted_context.json().get("message") == "explanation_not_found",
                        "deleted_context_unavailable",
                    )
                    require(
                        checked(
                            live.data(user, "GET", "report_explanations?report_id=eq." + report),
                            200,
                            "deleted_explanation_rows",
                        )
                        == [],
                        "deleted_evidence_scrubbed",
                    )
                    verify_deleted_facts(live, user, report, observation["id"])
                    require(
                        user.write("POST", path, body).status_code == 404,
                        "deleted_evidence_cannot_regenerate",
                    )
                    require(
                        user.write(
                            "POST",
                            review + "/publish",
                            {"expected_revision": 2, "measurement_date": None},
                        ).status_code
                        == 404,
                        "deleted_source_cannot_republish",
                    )
                require(
                    checked(owner.client.get("/observations/" + manual["id"]), 200, "manual_after")
                    == before_manual,
                    "manual_unchanged_by_report_deletion",
                )
                require(provider.calls == calls_before + 1, "no_correction_or_delete_generation")
                completed.append(
                    {
                        "owner_case": index + 1,
                        "lifecycle": "passed",
                        "isolation": "passed",
                        "deleted_fact_rows": "absent",
                        "manual_preservation": "passed",
                    }
                )
            result.update(
                result="passed",
                cases=completed,
                provider_boundaries=provider.boundaries,
                provider_generations=provider.calls,
                reload_additional_calls=0,
                correction_stale="passed",
                deletion="passed",
                manual_preservation="passed",
                two_user_isolation="passed",
                final_provider_boundary="passed",
                internal_reservation_increment_cents=provider.calls * 25,
                reservation_refund="none_by_design",
            )
        except Exception as error:
            result.update(
                result="failed",
                failure_stage=stage,
                failure_category=error.category
                if isinstance(error, CheckFailed)
                else "local_or_api_failure",
                exception_type=type(error).__name__
                if type(error).__name__
                in {"KeyError", "ValueError", "TypeError", "AssertionError", "CheckFailed"}
                else "OtherException",
            )
        finally:
            os.environ.pop("RUN_AI_INTEGRATION", None)
            cleanup = True
            for user, report in reports:
                try:
                    cleanup = (
                        user.write("DELETE", "/reports/" + report, {}).status_code == 200
                        and cleanup
                    )
                except Exception:
                    cleanup = False
            for user, identifier in manuals:
                try:
                    cleanup = (
                        user.write(
                            "DELETE", "/observations/" + identifier, {"expected_revision": 1}
                        ).status_code
                        == 200
                        and cleanup
                    )
                except Exception:
                    cleanup = False
            result["cleanup"] = "passed" if cleanup else "failed"
    assert isinstance(live_candidate._transport, OneShotOpenAITransport)
    require(live_candidate._transport.calls <= 1, "single_dispatch_limit")
    result.update(
        new_ai_requests=live_candidate._transport.calls,
        total_openai_live_requests=2 + live_candidate._transport.calls,
        provider_invocation_occurred=live_candidate._transport.calls == 1,
        preflight="passed" if provider.preflight_passed else "failed_or_not_reached",
        http_status=live_candidate.http_status,
        provider="openai",
        provider_reported_model="gpt-6.1-sol" if live_candidate.model_confirmed else None,
        provider_error_code=live_candidate.error_code,
        usage=provider.usage,
    )
    if (
        not provider.preflight_passed
        and result["result"] == "failed"
        and stage == "live_generation_and_persistence"
    ):
        result["failure_stage"] = "final_provider_preflight"
    if result["result"] == "passed":
        require(
            live_candidate._transport.calls == 1 and live_candidate.model_confirmed,
            "one_confirmed_response",
        )
    asyncio.run(live_candidate._transport.aclose())
    require("RUN_AI_INTEGRATION" not in os.environ, "live_gate_final_unset")
    result["live_gate"] = "unset"
    AUDIT.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result, indent=2)
    for secret in (worker, ai.ai_api_key.get_secret_value(), *(u.access for u in users)):
        require(secret not in serialized, "artifact_secret_check")
    with (AUDIT / "result.json").open("x", encoding="utf-8") as output:
        output.write(serialized + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        outcome = run(live_authorized=args.live)
    except Exception:
        os.environ.pop("RUN_AI_INTEGRATION", None)
        consumed = int((AUDIT / "attempt-reserved.json").exists())
        print(
            json.dumps(
                {
                    "result": "stopped",
                    "failure_category": "local_preflight_or_audit_failure",
                    "new_ai_requests": consumed,
                    "total_openai_live_requests": 2 + consumed,
                    "live_gate": "unset",
                }
            )
        )
        raise SystemExit(1) from None
    print(json.dumps(outcome, indent=2))
    raise SystemExit(0 if outcome["result"] == "passed" and outcome["cleanup"] == "passed" else 1)
