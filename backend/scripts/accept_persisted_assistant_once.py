"""One authorized persisted Phase 9 turn through real API routes and real Supabase.

No live action without --live. Only fixed synthetic input, dedicated existing users,
the production context/validation/persistence services, and the real OpenAI adapter.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
from contextlib import ExitStack
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from app.core.ai_config import AISettings
from app.core.assistant_context import Context, ContextBuilder
from app.core.assistant_language import Language
from app.core.auth_service import AuthenticatedRequest
from app.core.config import Settings
from app.core.errors import ApiProblem
from app.core.openai_assistant_acceptance import OpenAIAssistantAcceptance
from app.factory import create_app
from tests import extraction_fixtures
from tests.integration.test_live_extraction import finish
from tests.integration.test_live_ownership import LiveContext, SignedInUser
from tests.integration.test_live_reports import metadata, put_file

ROOT = Path(__file__).resolve().parents[2]
# Fresh user authorization for Gate C; A and B remain immutable audit history.
AUDIT = ROOT / ".cache/phase13/openai-persisted-assistant-3"
QUESTION = "Explain my latest uploaded report."
MEASUREMENT_DATE = "2026-10-03"


class CheckFailed(Exception):
    def __init__(self, category: str) -> None:
        self.category = category


def require(condition: bool, category: str) -> None:
    if not condition:
        raise CheckFailed(category)


def checked(response: httpx.Response, status: int, category: str) -> Any:
    require(response.status_code == status, category + "_http_" + str(response.status_code))
    return response.json()


def verify_observation_owner(
    live: LiveContext, owner: SignedInUser, observation: dict[str, Any]
) -> None:
    # The public Observation DTO deliberately omits user_id. Verify ownership
    # through the user's RLS-scoped Data API, without changing/exposing that DTO.
    rows = checked(
        live.data(
            owner,
            "GET",
            "health_observations?id=eq." + observation["id"] + "&select=id,user_id",
        ),
        200,
        "observation_owner_read",
    )
    require(
        isinstance(rows, list)
        and len(rows) == 1
        and rows[0].get("id") == observation["id"]
        and rows[0].get("user_id") == owner.user_id,
        "observation_owner",
    )


class VerifiedContextBuilder(ContextBuilder):
    """Observe and authorize the real builder output without modifying it."""

    def __init__(
        self,
        original: ContextBuilder,
        provider: OpenAIAssistantAcceptance,
        owner: str,
        report: str,
        observation: str,
        candidate: str,
    ) -> None:
        super().__init__(original.observations)
        self.provider = provider
        self.owner, self.report, self.observation, self.candidate = (
            owner,
            report,
            observation,
            candidate,
        )
        self.verified = False
        self.safe_metadata: dict[str, object] = {}
        self.failure_category: str | None = None

    def build(
        self,
        question: str,
        history: list[str],
        current: AuthenticatedRequest,
        language: Language = "en",
    ) -> Context:
        context = super().build(question, history, current, language)
        try:
            require("RUN_AI_INTEGRATION" not in os.environ, "context_gate_must_start_unset")
            require(str(current.identity.user_id) == self.owner, "context_owner")
            require(question == QUESTION and history == [] and language == "en", "context_scope")
            require(
                context.code == "sources" and context.selection == "latest_uploaded_report",
                "context_selection",
            )
            require(
                len(context.facts) == len(context.sources) == 1 and context.calculation is None,
                "context_minimization",
            )
            fact, source = context.facts[0], context.sources[0]
            require(
                str(source.observation_id) == self.observation
                and source.revision == 1
                and str(source.report_id) == self.report
                and str(source.candidate_id) == self.candidate
                and source.review_revision == 1,
                "context_current_provenance",
            )
            require(
                fact.evidence_id == source.evidence_id == "e1"
                and fact.canonical_metric == "vitamin_d_unspecified"
                and fact.value == "18"
                and fact.unit == "ng/mL"
                and fact.reference == "30–100"
                and fact.measurement_date == MEASUREMENT_DATE
                and fact.measured_at is None
                and fact.source_type == "report"
                and fact.calculated_range_status == "unknown",
                "context_exact_facts",
            )
            serialized = context.model_input()
            for private in (
                self.owner,
                self.report,
                self.observation,
                self.candidate,
                current.access_token,
            ):
                require(private not in serialized, "context_private_identifier")
            require(len(serialized.encode()) < 4000, "context_bound")
            self.provider.expected_input_digest = hashlib.sha256(serialized.encode()).hexdigest()
            self.verified, self.safe_metadata = True, context.metadata()
            # Enable only AFTER the real context passes every authorization check.
            # The runner clears this process-local gate immediately after the API call.
            os.environ["RUN_AI_INTEGRATION"] = "1"
            return context
        except CheckFailed as error:
            self.failure_category = error.category
            raise ApiProblem(
                409, "assistant_source", "Acceptance context failed verification."
            ) from None


def offline_preflight() -> tuple[Settings, AISettings]:
    require("RUN_AI_INTEGRATION" not in os.environ, "live_flag_must_start_unset")
    require(not (AUDIT / "result.json").exists(), "acceptance_run_already_recorded")
    require(not (AUDIT / "attempt-reserved.json").exists(), "authorization_already_consumed")
    config, ai = Settings(), AISettings()
    require(config.environment == "development" and not config.secure_cookies, "development_only")
    require(config.supabase_url == "https://rbmpfgndidpzdssiicyf.supabase.co", "dedicated_project")
    require(config.report_processing_key is not None, "processing_configuration")
    require(
        ai.ai_provider == "openai" and ai.ai_model == "gpt-6.1-sol" and ai.ai_api_key is not None,
        "openai_configuration",
    )
    values = dotenv_values(ROOT / "backend/.env.integration")
    require(values.get("DISPOSABLE_TEST_ACCOUNTS_CONFIRMED") == "1", "dedicated_accounts")
    require(
        bool(values.get("TEST_USER_A_EMAIL"))
        and bool(values.get("TEST_USER_B_EMAIL"))
        and values.get("TEST_USER_A_EMAIL") != values.get("TEST_USER_B_EMAIL"),
        "distinct_accounts",
    )
    # Existing fixture generator and normal review correction preserve the requested en dash.
    require(date.fromisoformat(MEASUREMENT_DATE) <= date.today(), "fixture_date")
    return config, ai


def execute() -> dict[str, Any]:
    config, ai = offline_preflight()
    assert config.supabase_url is not None
    assert config.supabase_publishable_key is not None
    AUDIT.mkdir(parents=True, exist_ok=True)
    provider = OpenAIAssistantAcceptance(ai, AUDIT / "attempt-reserved.json")
    require(not provider.assistant_available, "live_default_disabled")
    result: dict[str, Any] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "result": "not_sent",
        "provider": "openai",
        "requested_model": "gpt-6.1-sol",
        "retries": 0,
        "fallbacks": 0,
        "conservative_cost_bound_usd": 0.06,
        "prior_openai_attempts": 1,
        "gemini_attempts": "2/20 unchanged",
        "phase8_calculation": "not_applicable_single_report",
        "correlation_id": str(uuid4()),
    }
    values = dotenv_values(ROOT / "backend/.env.integration")
    app = create_app(config, assistant_provider=provider)
    report: str | None = None
    conversation: str | None = None
    original_language: str | None = None
    users: list[SignedInUser] = []
    guarded: VerifiedContextBuilder | None = None
    stage = "login"
    with ExitStack() as stack:
        try:
            first = stack.enter_context(TestClient(app, base_url="http://127.0.0.1:8000"))
            second = TestClient(app, base_url="http://127.0.0.1:8000")
            stack.callback(second.close)
            for name, client in zip(("A", "B"), (first, second), strict=True):
                client.headers["Origin"] = config.app_origin
                require(
                    client.get("/assistant/conversations").status_code == 401, "anonymous_denial"
                )
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
                    "dedicated_login",
                )["user"]["id"]
                csrf = checked(client.get("/auth/csrf"), 200, "session_csrf")["csrf_token"]
                user = SignedInUser(
                    cast(httpx.Client, client),
                    csrf,
                    client.cookies.get("sl_access") or "",
                    identity,
                )
                users.append(user)
                stack.callback(user.close_session)
            owner, other = users
            require(owner.user_id != other.user_id, "distinct_authenticated_owners")
            database = stack.enter_context(
                httpx.Client(
                    base_url=config.supabase_url + "/rest/v1/",
                    timeout=30,
                    trust_env=False,
                    headers={"apikey": config.supabase_publishable_key.get_secret_value()},
                )
            )
            live = LiveContext((owner, other), database)
            prefs = checked(owner.client.get("/settings"), 200, "original_settings")
            original_language = prefs["assistant_language"]
            checked(
                owner.write("PATCH", "/settings", {"assistant_language": "en"}),
                200,
                "fixture_language",
            )
            stage = "synthetic_report_workflow"
            old_lines = extraction_fixtures.LINES
            try:
                extraction_fixtures.LINES = [
                    "SYNTHETIC ACCEPTANCE - NOT PATIENT DATA",
                    "Parameter | Result | Unit | Reference | Flag",
                    "Vitamin D | 18 | ng/mL | 30-100 |",
                ]
                data = extraction_fixtures.document(("native",), size=1000)
            finally:
                extraction_fixtures.LINES = old_lines
            report = checked(
                owner.write(
                    "POST",
                    "/reports",
                    metadata("synthetic-openai-assistant.pdf", "application/pdf", data),
                ),
                201,
                "reserve_report",
            )["id"]
            checked(put_file(owner, report, data, "application/pdf"), 200, "upload_report")
            route = "/reports/" + report
            checked(
                owner.write("POST", route + "/process", {"idempotency_key": str(uuid4())}),
                202,
                "process",
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
            require(len(candidates) == 1, "one_candidate")
            candidate = candidates[0]
            f = candidate["content"]["fields"]
            require(
                f["raw_value"] == "18"
                and f["original_unit"] == "ng/mL"
                and f["canonical_metric"] == "vitamin_d_unspecified",
                "parsed_exact_fact",
            )
            review = route + "/parameters/" + candidate["id"]
            checked(
                owner.write(
                    "PATCH",
                    review,
                    {
                        "action": "corrected",
                        "expected_revision": 0,
                        "idempotency_key": str(uuid4()),
                        "correction": {
                            "original_label": "Vitamin D",
                            "raw_value": "18",
                            "original_unit": "ng/mL",
                            "raw_reference": "30–100",
                        },
                    },
                ),
                200,
                "review_synthetic_reference",
            )
            observation = checked(
                owner.write(
                    "POST",
                    review + "/publish",
                    {
                        "expected_revision": 1,
                        "measurement_date": MEASUREMENT_DATE,
                    },
                ),
                200,
                "publish",
            )
            verify_observation_owner(live, owner, observation)
            require(observation["current"]["status"] == "active", "observation_active")
            require(
                other.client.get("/observations/" + observation["id"]).status_code == 404,
                "foreign_observation_denied",
            )
            stage = "conversation_preflight"
            created = checked(
                owner.write("POST", "/assistant/conversations", {"idempotency_key": str(uuid4())}),
                200,
                "create_conversation",
            )
            conversation = created["conversation"]["id"]
            require(created["messages"] == [], "new_empty_conversation")
            owner_rows = checked(
                live.data(owner, "GET", "assistant_conversations?id=eq." + conversation),
                200,
                "persisted_conversation",
            )
            require(
                len(owner_rows) == 1 and owner_rows[0]["user_id"] == owner.user_id,
                "conversation_owner",
            )
            for table in ("assistant_conversations", "assistant_messages"):
                require(
                    checked(
                        live.data(other, "GET", table + "?user_id=eq." + owner.user_id),
                        200,
                        "preflight_rls",
                    )
                    == [],
                    "preflight_rls_denial",
                )
            guarded = VerifiedContextBuilder(
                app.state.assistant_service.builder,
                provider,
                owner.user_id,
                report,
                observation["id"],
                candidate["id"],
            )
            app.state.assistant_service.builder = guarded
            result["preflight"] = "passed"
            stage = "one_live_turn"
            try:
                response = owner.write(
                    "POST",
                    f"/assistant/conversations/{conversation}/messages",
                    {"content": QUESTION, "idempotency_key": str(uuid4())},
                )
            finally:
                os.environ.pop("RUN_AI_INTEGRATION", None)
            result["application_http_status"] = response.status_code
            result["context_authorization"] = "passed" if guarded.verified else "failed"
            result["context_metadata"] = guarded.safe_metadata
            thread = checked(response, 200, "persisted_turn")
            require(
                provider.transport.calls == 1 and provider.http_status == 200, "provider_execution"
            )
            require(provider.model_confirmed, "response_model")
            require(len(thread["messages"]) == 2, "two_persisted_messages")
            sent, reply = thread["messages"]
            require(sent["role"] == "user" and sent["content"] == QUESTION, "user_message")
            require(
                reply["role"] == "assistant" and reply["status"] == "ready",
                "assistant_message_ready",
            )
            require(
                reply["provider"] == "openai"
                and reply["model"] == "gpt-6.1-sol"
                and reply["response_language"] == "en",
                "persisted_provider_language",
            )
            answer = reply["answer"]
            require(
                answer["choice"]["evidence_ids"] == ["e1"] and len(answer["facts"]) == 1,
                "persisted_evidence",
            )
            fact = answer["facts"][0]
            require(
                fact["value"] == "18"
                and fact["unit"] == "ng/mL"
                and fact["reference"] == "30–100"
                and fact["measurement_date"] == MEASUREMENT_DATE,
                "persisted_exact_facts",
            )
            require(
                answer["sources"][0]["observation_id"] == observation["id"]
                and answer["sources"][0]["report_id"] == report,
                "persisted_provenance",
            )
            stage = "readback_isolation"
            rows = checked(
                live.data(owner, "GET", "assistant_messages?conversation_id=eq." + conversation),
                200,
                "direct_persisted_messages",
            )
            require(
                len(rows) == 2 and all(r["user_id"] == owner.user_id for r in rows), "message_owner"
            )
            persisted = next(r for r in rows if r["id"] == reply["id"])
            require(
                persisted["answer"] == answer
                and persisted["response_language"] == "en"
                and persisted["provider"] == "openai"
                and persisted["model"] == "gpt-6.1-sol",
                "direct_persisted_answer",
            )
            reload = checked(
                owner.client.get(f"/assistant/conversations/{conversation}"), 200, "reload"
            )
            require(reload["messages"] == thread["messages"], "same_messages_on_reload")
            foreign_list = checked(
                other.client.get("/assistant/conversations"), 200, "foreign_conversation_list"
            )
            require(
                all(row["id"] != conversation for row in foreign_list["conversations"]),
                "foreign_conversation_list_denied",
            )
            for table, query in (
                ("assistant_conversations", "id=eq." + conversation),
                ("assistant_messages", "id=eq." + reply["id"]),
            ):
                require(
                    checked(
                        live.data(other, "GET", table + "?" + query), 200, "foreign_direct_read"
                    )
                    == [],
                    "foreign_message_evidence_denied",
                )
            require(
                other.client.get(f"/assistant/conversations/{conversation}").status_code == 404,
                "foreign_conversation_read_denied",
            )
            require(
                other.write(
                    "POST",
                    f"/assistant/conversations/{conversation}/messages",
                    {"content": QUESTION, "idempotency_key": str(uuid4())},
                ).status_code
                == 404,
                "foreign_send_denied",
            )
            require(provider.transport.calls == 1, "no_reload_or_foreign_provider_call")
            result.update(
                result="passed",
                schema_validation="passed",
                evidence_validation="passed",
                exact_facts_and_date="passed",
                safety="passed",
                evidence_minimization="passed",
                user_message_persistence="passed",
                assistant_message_persistence="passed",
                evidence_association_persistence="passed",
                provider_model_language_persistence="passed",
                reload_readback="passed",
                reload_additional_calls=0,
                two_user_isolation="passed",
            )
        except CheckFailed as error:
            result.update(
                result="failed",
                failure_stage=stage,
                failure_category=error.category,
                exception_type="CheckFailed",
            )
        except Exception as error:
            result.update(
                result="failed",
                failure_stage=stage,
                failure_category="local_or_provider_failure",
                # Class names only, never messages, args, tracebacks or request/response bodies.
                exception_type=type(error).__name__
                if type(error).__name__
                in {
                    "KeyError",
                    "ValueError",
                    "TypeError",
                    "AssertionError",
                    "ApiProblem",
                    "ReadTimeout",
                    "ConnectTimeout",
                    "ConnectError",
                    "RuntimeError",
                }
                else "OtherException",
            )
        finally:
            os.environ.pop("RUN_AI_INTEGRATION", None)
            if guarded is not None:
                result["context_authorization"] = "passed" if guarded.verified else "failed"
                result["context_metadata"] = guarded.safe_metadata
                result["context_failure_category"] = guarded.failure_category
            cleanup = True
            if users:
                for route in (
                    [f"/assistant/conversations/{conversation}"] if conversation else []
                ) + ([f"/reports/{report}"] if report else []):
                    try:
                        cleanup = users[0].write("DELETE", route, {}).status_code == 200 and cleanup
                    except Exception:
                        cleanup = False
                if original_language is not None:
                    try:
                        cleanup = (
                            users[0]
                            .write("PATCH", "/settings", {"assistant_language": original_language})
                            .status_code
                            == 200
                            and cleanup
                        )
                    except Exception:
                        cleanup = False
            result["synthetic_cleanup_and_preferences"] = "passed" if cleanup else "failed"
    asyncio.run(provider.transport.aclose())
    result.update(
        provider_http_status=provider.http_status,
        confirmed_model=provider.model if provider.model_confirmed else None,
        provider_error_code=provider.error_code,
        usage=provider.usage,
        new_openai_attempts=provider.transport.calls,
        provider_invocation_started=provider.transport.calls > 0,
        total_openai_attempts=1 + provider.transport.calls,
        live_integration_final="unset",
    )
    if "total_tokens" in provider.usage:
        result["estimated_cost_usd"] = round(
            (provider.usage["input_tokens"] * 2 + provider.usage["output_tokens"] * 10) / 1000000, 6
        )
    serialized = json.dumps(result, ensure_ascii=True, indent=2)
    for secret in (ai.ai_api_key, config.report_processing_key, config.csrf_signing_key):
        if secret:
            require(secret.get_secret_value() not in serialized, "artifact_secret_check")
    for user in users:
        require(user.access not in serialized, "artifact_session_check")
    with (AUDIT / "result.json").open("x", encoding="utf-8") as output:
        output.write(serialized + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        if args.live:
            result = execute()
        else:
            offline_preflight()
            result = {
                "offline_preflight": "passed",
                "provider": "openai",
                "model": "gpt-6.1-sol",
                "network_requests": 0,
                "live_integration": "unset",
            }
    except Exception:
        os.environ.pop("RUN_AI_INTEGRATION", None)
        print('{"result":"stopped","category":"local_preflight_or_audit_failure"}')
        raise SystemExit(1) from None
    print(json.dumps(result, indent=2))
    if result.get("result") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
