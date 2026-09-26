"""Real RLS + application context with explicit test-only AI injection. Synthetic data only."""

import json
import os
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.factory import create_app
from tests import extraction_fixtures
from tests.assistant_fixtures import MockAssistantProvider
from tests.integration.test_live_extraction import finish
from tests.integration.test_live_ownership import LiveContext, SignedInUser, expect_status
from tests.integration.test_live_ownership import live as live
from tests.integration.test_live_reports import metadata, put_file
from tests.parameter_fixtures import NATIVE_LINES

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real Supabase opt-in"
)


def test_live_assistant_two_users_grounding_correction_deletion_and_revocation(
    live: LiveContext,
) -> None:
    provider = MockAssistantProvider()
    config = Settings()
    app = create_app(config, assistant_provider=provider)
    created: list[tuple[SignedInUser, str]] = []
    manuals: list[tuple[SignedInUser, str]] = []
    old_settings: list[tuple[SignedInUser, str]] = []
    with ExitStack() as stack:
        first = stack.enter_context(TestClient(app, base_url="http://127.0.0.1:8000"))
        second = TestClient(app, base_url="http://127.0.0.1:8000")
        stack.callback(second.close)
        users = []
        for existing, client in zip(live.users, (first, second), strict=True):
            client.cookies.update(existing.client.cookies)
            client.headers["Origin"] = config.app_origin
            users.append(
                SignedInUser(
                    cast(httpx.Client, client), existing.csrf, existing.access, existing.user_id
                )
            )
        try:
            for index, user in enumerate(users):
                old_settings.append((user, user.client.get("/settings").json()["timezone"]))
                expect_status(
                    user.write("PATCH", "/settings", {"timezone": "UTC"}), 200, "Synthetic timezone"
                )
                for day in range(14 if index == 0 else 1):
                    when = (
                        datetime.now(UTC) - timedelta(days=14 - day if index == 0 else 1)
                    ).replace(hour=0, minute=0, second=0, microsecond=0)
                    response = user.write(
                        "POST",
                        "/observations/manual",
                        {
                            "metric": "weight",
                            "unit": "kg",
                            "raw_value": ("70.250" if day < 8 else "72.750")
                            if index == 0
                            else "90.125",
                            "measured_at": when.isoformat(),
                            "idempotency_key": str(uuid4()),
                        },
                    )
                    expect_status(response, 200, "Synthetic manual observation")
                    manuals.append((user, response.json()["id"]))
                key = str(uuid4())
                response = user.write("POST", "/assistant/conversations", {"idempotency_key": key})
                expect_status(response, 200, "Create owned conversation")
                identifier = response.json()["conversation"]["id"]
                created.append((user, identifier))
                again = user.write("POST", "/assistant/conversations", {"idempotency_key": key})
                assert again.json()["conversation"]["id"] == identifier
                question = (
                    "Has my weight been increasing?" if index == 0 else "What was my latest weight?"
                )
                key = str(uuid4())
                body: dict[str, object] = {"content": question, "idempotency_key": key}
                response = user.write(
                    "POST", f"/assistant/conversations/{identifier}/messages", body
                )
                expect_status(response, 200, "Grounded mock answer")
                answer = response.json()["messages"][-1]
                assert answer["status"] == "ready" and answer["provider"] == "mock-test"
                if index == 0:
                    assert answer["answer"]["calculation"]["status"] == "increasing"
                    assert answer["answer"]["calculation"]["change"]["absolute"] == "2.500"
                else:
                    assert answer["answer"]["facts"][0]["value"] == "90.125"
                before = provider.calls
                replay = user.write("POST", f"/assistant/conversations/{identifier}/messages", body)
                assert len(replay.json()["messages"]) == 2 and provider.calls == before
                assert (
                    user.client.get(f"/assistant/conversations/{identifier}").headers[
                        "cache-control"
                    ]
                    == "no-store"
                )
                assert (
                    user.client.post(
                        f"/assistant/conversations/{identifier}/messages", json=body
                    ).status_code
                    == 403
                )
                assert (
                    user.write(
                        "POST",
                        f"/assistant/conversations/{identifier}/messages",
                        body | {"user_id": users[1 - index].user_id},
                    ).status_code
                    == 422
                )
                assert (
                    user.write(
                        "POST",
                        f"/assistant/conversations/{identifier}/messages",
                        body | {"evidence_ids": ["e1"]},
                    ).status_code
                    == 422
                )

            for index, (user, identifier) in enumerate(created):
                other_id = created[1 - index][1]
                listed = user.client.get("/assistant/conversations").json()["conversations"]
                assert identifier in [c["id"] for c in listed] and other_id not in [
                    c["id"] for c in listed
                ]
                for method, suffix, foreign_body in [
                    ("GET", "", None),
                    ("DELETE", "", {}),
                    ("POST", "/messages", {"content": "foreign", "idempotency_key": str(uuid4())}),
                ]:
                    response = (
                        user.client.get(f"/assistant/conversations/{other_id}")
                        if method == "GET"
                        else user.write(
                            method,
                            f"/assistant/conversations/{other_id}{suffix}",
                            dict(foreign_body or {}),
                        )
                    )
                    expect_status(response, 404, "Cross-owner conversation denial")
                for table in ("assistant_conversations", "assistant_messages"):
                    response = live.data(
                        user, "GET", f"{table}?user_id=eq.{users[1 - index].user_id}"
                    )
                    expect_status(response, 200, "Direct RLS read")
                    assert response.json() == []
                    denied = live.data(user, "POST", table, {"user_id": user.user_id})
                    assert denied.status_code in (401, 403)

            a, conversation = created[0]
            manual = manuals[13][1]
            old = a.client.get("/observations/" + manual).json()
            expect_status(
                a.write(
                    "PATCH",
                    "/observations/" + manual,
                    {
                        "metric": "weight",
                        "unit": "kg",
                        "raw_value": "73.125",
                        "measured_at": old["current"]["measured_at"],
                        "expected_revision": 1,
                        "idempotency_key": str(uuid4()),
                    },
                ),
                200,
                "Source correction",
            )
            stale = a.client.get(f"/assistant/conversations/{conversation}").json()["messages"][-1]
            assert stale["status"] == "stale" and stale["answer"] is None
            response = a.write(
                "POST",
                f"/assistant/conversations/{conversation}/messages",
                {"content": "latest weight", "idempotency_key": str(uuid4())},
            )
            expect_status(response, 200, "Fresh corrected context")
            answer = response.json()["messages"][-1]["answer"]
            assert answer["facts"][0]["value"] == "73.125" and answer["sources"][0]["revision"] == 2
            expect_status(
                a.write("DELETE", "/observations/" + manual, {"expected_revision": 2}),
                200,
                "Source deletion",
            )
            assert (
                a.client.get(f"/assistant/conversations/{conversation}").json()["messages"][-1][
                    "answer"
                ]
                is None
            )
            response = a.write(
                "POST",
                f"/assistant/conversations/{conversation}/messages",
                {"content": "latest weight", "idempotency_key": str(uuid4())},
            )
            assert all(
                s["observation_id"] != manual
                for s in response.json()["messages"][-1]["answer"]["sources"]
            )
            # Another conversation supplies no dialogue to a new thread.
            assert json.loads(provider.requests[-1].input_json)[
                "dialogue_untrusted_not_evidence"
            ] == [
                "Has my weight been increasing?",
                "latest weight",
            ]
            b, b_conversation = created[1]
            provider.output_override = {"answer": "diagnosis", "evidence_ids": [manual]}
            response = b.write(
                "POST",
                f"/assistant/conversations/{b_conversation}/messages",
                {"content": "latest weight", "idempotency_key": str(uuid4())},
            )
            assert response.json()["messages"][-1]["status"] == "failed"
            assert response.json()["messages"][-1]["error_category"] == "invalid_output"
            provider.output_override = None
            provider.error = TimeoutError()
            response = b.write(
                "POST",
                f"/assistant/conversations/{b_conversation}/messages",
                {"content": "latest weight", "idempotency_key": str(uuid4())},
            )
            assert response.json()["messages"][-1]["error_category"] == "timeout"
            provider.error = None
            provider.assistant_available = False
            response = b.write(
                "POST",
                f"/assistant/conversations/{b_conversation}/messages",
                {"content": "latest weight", "idempotency_key": str(uuid4())},
            )
            assert response.json()["messages"][-1]["error_category"] == "unavailable"
            # Clear own data before revoking the session; both directions were verified above.
            for user, identifier in created:
                expect_status(
                    user.write("DELETE", f"/assistant/conversations/{identifier}", {}),
                    200,
                    "Owned conversation deletion",
                )
                assert (
                    live.data(
                        user, "GET", f"assistant_messages?conversation_id=eq.{identifier}"
                    ).json()
                    == []
                )
            created.clear()
            for user, identifier in manuals:
                r = user.client.get("/observations/" + identifier)
                if r.status_code == 200:
                    expect_status(
                        user.write(
                            "DELETE",
                            "/observations/" + identifier,
                            {"expected_revision": r.json()["current"]["revision"]},
                        ),
                        200,
                        "Remove synthetic observation",
                    )
            manuals.clear()
            for user, zone in old_settings:
                expect_status(
                    user.write("PATCH", "/settings", {"timezone": zone}), 200, "Restore timezone"
                )
            old_settings.clear()
            access = a.access
            a.close_session()
            a.client.cookies.set("sl_access", access)
            expect_status(a.client.get("/assistant/conversations"), 401, "Revoked assistant API")
            assert live.data(a, "GET", "assistant_messages").json() == []
        finally:
            for user, identifier in created:
                user.write("DELETE", f"/assistant/conversations/{identifier}", {})
            for user, identifier in manuals:
                r = user.client.get("/observations/" + identifier)
                if r.status_code == 200:
                    user.write(
                        "DELETE",
                        "/observations/" + identifier,
                        {"expected_revision": r.json()["current"]["revision"]},
                    )
            for user, zone in old_settings:
                user.write("PATCH", "/settings", {"timezone": zone})


def test_live_assistant_report_publication_correction_and_deletion(
    live: LiveContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = MockAssistantProvider()
    config = Settings()
    existing = live.users[0]
    monkeypatch.setattr(extraction_fixtures, "LINES", NATIVE_LINES)
    data = extraction_fixtures.document(("native",))
    response = existing.write(
        "POST", "/reports", metadata("synthetic-assistant.pdf", "application/pdf", data)
    )
    expect_status(response, 201, "Reserve synthetic assistant report")
    report = response.json()["id"]
    conversation = None
    with TestClient(
        create_app(config, assistant_provider=provider), base_url="http://127.0.0.1:8000"
    ) as client:
        client.cookies.update(existing.client.cookies)
        client.headers["Origin"] = config.app_origin
        user = SignedInUser(
            cast(httpx.Client, client), existing.csrf, existing.access, existing.user_id
        )
        try:
            expect_status(
                put_file(existing, report, data, "application/pdf"),
                200,
                "Upload synthetic assistant report",
            )
            route = "/reports/" + report
            expect_status(
                existing.write("POST", route + "/process", {"idempotency_key": str(uuid4())}),
                202,
                "Extract synthetic report",
            )
            source = finish(existing, report)
            expect_status(
                existing.write(
                    "POST",
                    route + "/extract-parameters",
                    {"source_run_id": source["id"], "idempotency_key": str(uuid4())},
                ),
                200,
                "Parse synthetic report",
            )
            candidates = existing.client.get(route + "/parameters").json()["candidates"]
            conversation = user.write(
                "POST", "/assistant/conversations", {"idempotency_key": str(uuid4())}
            ).json()["conversation"]["id"]

            def ask(question: str) -> dict[str, object]:
                response = user.write(
                    "POST",
                    f"/assistant/conversations/{conversation}/messages",
                    {"content": question, "idempotency_key": str(uuid4())},
                )
                expect_status(response, 200, "Synthetic report question")
                message = response.json()["messages"][-1]
                assert message["status"] == "ready"
                return cast(dict[str, object], message["answer"])

            assert ask("Explain my latest report")["choice"]["explanation_code"] == "no_data"  # type: ignore[index]
            for c in candidates:
                review = route + "/parameters/" + c["id"]
                expect_status(
                    existing.write(
                        "PATCH",
                        review,
                        {
                            "action": "confirmed",
                            "expected_revision": 0,
                            "idempotency_key": str(uuid4()),
                        },
                    ),
                    200,
                    "Review synthetic candidate",
                )
            assert ask("Explain my latest report")["choice"]["explanation_code"] == "no_data"  # type: ignore[index]
            for c in candidates:
                expect_status(
                    existing.write(
                        "POST",
                        route + "/parameters/" + c["id"] + "/publish",
                        {
                            "expected_revision": 1,
                            "measurement_date": None
                            if c["content"]["fields"]["canonical_metric"] == "tsh"
                            else (datetime.now(UTC) - timedelta(days=1)).date().isoformat(),
                        },
                    ),
                    200,
                    "Explicit publication",
                )
            answer = ask("Explain my latest report")
            facts = cast(list[dict[str, object]], answer["facts"])
            assert {f["value"] for f in facts} == {"13.20", "18", "2.4", "<70", ">10"}
            assert (
                next(f for f in facts if f["canonical_metric"] == "tsh")["measurement_date"] is None
            )
            assert {s["report_id"] for s in cast(list[dict[str, object]], answer["sources"])} == {
                report
            }
            assert provider.calls == 1
            assert (
                cast(
                    dict[str, object], ask("How has my Vitamin D changed over 30 days?")["choice"]
                )["explanation_code"]
                == "insufficient_data"
            )
            tsh = next(c for c in candidates if c["content"]["fields"]["canonical_metric"] == "tsh")
            review = route + "/parameters/" + tsh["id"]
            expect_status(
                existing.write(
                    "PATCH",
                    review,
                    {
                        "action": "corrected",
                        "expected_revision": 1,
                        "idempotency_key": str(uuid4()),
                        "correction": {
                            "original_label": "TSH",
                            "raw_value": "2.5",
                            "original_unit": "mIU/L",
                            "raw_reference": "0.4-4.0",
                        },
                    },
                ),
                200,
                "Correct report source",
            )
            assert all(
                m["answer"] is None
                for m in user.client.get(f"/assistant/conversations/{conversation}").json()[
                    "messages"
                ]
            )
            expect_status(
                existing.write(
                    "POST", review + "/publish", {"expected_revision": 2, "measurement_date": None}
                ),
                200,
                "Republish current revision",
            )
            assert ask("latest TSH")["facts"][0]["value"] == "2.5"  # type: ignore[index]
            expect_status(existing.write("DELETE", route, {}), 200, "Delete synthetic source")
            assert all(
                m["answer"] is None
                for m in user.client.get(f"/assistant/conversations/{conversation}").json()[
                    "messages"
                ]
            )
            remaining = ask("latest TSH")
            # A dedicated development account can retain other owned reports.
            # Deleting this fixture must remove its evidence, not unrelated history.
            assert all(
                s["report_id"] != report
                for s in cast(list[dict[str, object]], remaining["sources"])
            )
            if not remaining["facts"]:
                assert remaining["choice"]["explanation_code"] == "no_data"  # type: ignore[index]
            else:
                assert remaining["choice"]["explanation_code"] == "sources"  # type: ignore[index]
        finally:
            if conversation:
                user.write("DELETE", f"/assistant/conversations/{conversation}", {})
            existing.write("DELETE", "/reports/" + report, {})
