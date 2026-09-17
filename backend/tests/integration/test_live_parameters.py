"""Real upload -> Phase 4 -> Phase 5; only disposable synthetic documents."""

import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from dotenv import dotenv_values

from tests import extraction_fixtures
from tests.integration.test_live_extraction import finish
from tests.integration.test_live_ownership import (
    LiveContext,
    SignedInUser,
    expect_empty,
    expect_status,
    object_body,
)
from tests.integration.test_live_ownership import live as live
from tests.integration.test_live_reports import metadata, put_file
from tests.parameter_fixtures import NATIVE_LINES

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real provider opt-in required"
)


def test_live_parameter_ownership_review_retry_and_delete(
    live: LiveContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extraction_fixtures, "LINES", NATIVE_LINES)
    data = extraction_fixtures.document(("native", "native"))
    created: list[tuple[SignedInUser, str]] = []
    completed: list[tuple[str, str, str, str]] = []
    try:
        for index, user in enumerate(live.users):
            other = live.users[1 - index]
            response = user.write(
                "POST", "/reports", metadata("synthetic-parameters.pdf", "application/pdf", data)
            )
            expect_status(response, 201, "Reserve synthetic report")
            report = str(object_body(response)["id"])
            created.append((user, report))
            expect_status(
                put_file(user, report, data, "application/pdf"), 200, "Upload synthetic report"
            )
            route = f"/reports/{report}"
            body: dict[str, object] = {
                "source_run_id": str(uuid4()),
                "idempotency_key": str(uuid4()),
            }
            expect_status(
                user.write("POST", route + "/extract-parameters", body), 404, "No completed source"
            )
            expect_status(
                user.write("POST", route + "/process", {"idempotency_key": str(uuid4())}),
                202,
                "Start Phase 4",
            )
            source = finish(user, report)
            assert source["status"] == "completed"
            source_id = str(source["id"])
            body["source_run_id"] = source_id
            with httpx.Client(base_url=str(user.client.base_url)) as anonymous:
                expect_status(anonymous.get(route + "/parameters"), 401, "Anonymous candidates")
            expect_status(
                user.client.post(route + "/extract-parameters", json=body),
                403,
                "Missing extraction CSRF",
            )
            expect_status(
                other.write("POST", route + "/extract-parameters", body),
                404,
                "Cross-user extraction",
            )
            response = user.write("POST", route + "/extract-parameters", body)
            expect_status(response, 200, "Extract real candidates")
            run = object_body(response)
            assert run["status"] == "completed" and run["candidate_count"] == 10
            run_id = str(run["id"])
            replay = user.write("POST", route + "/extract-parameters", body)
            expect_status(replay, 200, "Extraction replay")
            assert object_body(replay)["id"] == run_id
            response = user.client.get(route + "/parameters")
            expect_status(response, 200, "Read owner candidates")
            assert response.headers["cache-control"] == "no-store"
            candidates = response.json()["candidates"]
            candidate = candidates[0]
            candidate_id = candidate["id"]
            machine = candidate["content"]
            assert machine["fields"]["raw_value"] == "13.20"
            assert machine["fields"]["parsing_version"] == run["extractor_version"]
            assert machine["fields"]["alias_version"] == run["rules_version"]
            assert machine["fields"]["raw_reference"] == "12-15"
            assert [c["content"]["page_number"] for c in candidates] == [1] * 5 + [2] * 5
            page_response = user.client.get(route + f"/extraction?run_id={source_id}")
            expect_status(page_response, 200, "Source remains accessible")
            source_text = page_response.json()["pages"][0]["text"]
            assert (
                source_text[machine["source_start"] : machine["source_end"]]
                == machine["source_text"]
            )
            review_route = route + f"/parameters/{candidate_id}"
            correction: dict[str, object] = {
                "idempotency_key": str(uuid4()),
                "expected_revision": 0,
                "action": "corrected",
                "correction": {
                    "original_label": "Hemoglobin",
                    "raw_value": "13.21",
                    "original_unit": "g/dL",
                    "raw_reference": "12-15",
                },
            }
            for suffix in (
                "parameters",
                "parameter-processing",
                f"parameters/{candidate_id}/revisions",
            ):
                expect_status(
                    other.client.get(route + "/" + suffix), 404, "Cross-user candidate read"
                )
            expect_status(
                other.write("PATCH", review_route, correction), 404, "Cross-user correction"
            )
            expect_status(
                user.client.patch(review_route, json=correction), 403, "Missing review CSRF"
            )
            expect_status(
                user.write("PATCH", review_route, {**correction, "user_id": other.user_id}),
                422,
                "No browser actor authority",
            )
            response = user.write("PATCH", review_route, correction)
            expect_status(response, 200, "Owner correction")
            assert response.json()["revision"] == 1 and response.json()["actor_id"] == user.user_id
            expect_status(user.write("PATCH", review_route, correction), 200, "Correction replay")
            stale = {**correction, "idempotency_key": str(uuid4())}
            expect_status(user.write("PATCH", review_route, stale), 409, "Stale edit rejected")
            for revision, action in ((1, "confirmed"), (2, "rejected")):
                response = user.write(
                    "PATCH",
                    review_route,
                    {
                        "idempotency_key": str(uuid4()),
                        "expected_revision": revision,
                        "action": action,
                    },
                )
                expect_status(response, 200, "Append personal review")
                assert response.json()["fields"]["raw_value"] == "13.21"
            history = user.client.get(review_route + "/revisions")
            expect_status(history, 200, "Review history")
            assert [r["revision"] for r in history.json()] == [3, 2, 1]
            response = user.client.get(route + "/parameters")
            expect_status(response, 200, "Machine result after reviews")
            assert response.json()["candidates"][0]["content"] == machine
            assert user.client.get(route + "/extraction").json()["pages"][0]["text"] == source_text
            for table, field, identifier in (
                ("report_parameter_runs", "report_id", report),
                ("report_parameter_candidates", "run_id", run_id),
                ("report_parameter_reviews", "candidate_id", candidate_id),
            ):
                expect_empty(
                    live.data(other, "GET", f"{table}?{field}=eq.{identifier}"),
                    "Candidate RLS isolation",
                )
                expect_status(
                    live.data(user, "POST", table, {field: identifier}), 403, "No direct writes"
                )
                expect_status(live.database.get(table), 401, "Anonymous table denied")
            expect_status(
                live.data(
                    user,
                    "POST",
                    "rpc/parameter_history",
                    {"p_report_id": report, "p_worker_secret": "forged"},
                ),
                403,
                "No worker impersonation",
            )
            for attempt in (2, 3):
                response = user.write(
                    "POST",
                    route + "/extract-parameters",
                    {"source_run_id": source_id, "idempotency_key": str(uuid4())},
                )
                expect_status(response, 200, "Explicit new versioned attempt")
                assert response.json()["attempt"] == attempt
            expect_status(
                user.write(
                    "POST",
                    route + "/extract-parameters",
                    {"source_run_id": source_id, "idempotency_key": str(uuid4())},
                ),
                409,
                "Bounded retries",
            )
            old = user.client.get(route + f"/parameters?run_id={run_id}")
            expect_status(old, 200, "Prior successful attempt retained")
            assert old.json()["candidates"][0]["reviews"][0]["action"] == "rejected"
            completed.append((report, run_id, candidate_id, source_id))

        # A genuinely revoked session cannot read surviving candidate or review rows.
        values = dotenv_values(Path(__file__).resolve().parents[2] / ".env.integration")
        first = live.users[0]
        with httpx.Client(
            base_url=str(first.client.base_url),
            headers={"Origin": values.get("TEST_APP_ORIGIN") or "http://127.0.0.1:5173"},
            timeout=20,
        ) as client:
            csrf = str(object_body(client.get("/auth/csrf"))["csrf_token"])
            expect_status(
                client.post(
                    "/auth/login",
                    json={
                        "email": values["TEST_USER_A_EMAIL"],
                        "password": values["TEST_USER_A_PASSWORD"],
                    },
                    headers={"X-CSRF-Token": csrf},
                ),
                200,
                "Extra review session",
            )
            access = client.cookies.get("sl_access")
            assert access
            revoked = SignedInUser(
                client,
                str(object_body(client.get("/auth/csrf"))["csrf_token"]),
                access,
                first.user_id,
            )
            report, run_id, candidate_id, source_id = completed[0]
            expect_status(revoked.write("POST", "/auth/logout", {}), 200, "Revoke review session")
            client.cookies.set("sl_access", access)
            expect_status(
                client.get(f"/reports/{report}/parameters"), 401, "Revoked candidate read"
            )
            expect_status(
                revoked.write(
                    "POST",
                    f"/reports/{report}/extract-parameters",
                    {"source_run_id": source_id, "idempotency_key": str(uuid4())},
                ),
                401,
                "Revoked extraction",
            )
            expect_status(
                revoked.write(
                    "PATCH",
                    f"/reports/{report}/parameters/{candidate_id}",
                    {
                        "idempotency_key": str(uuid4()),
                        "expected_revision": 3,
                        "action": "confirmed",
                    },
                ),
                401,
                "Revoked review",
            )
            for table, field, identifier in (
                ("report_parameter_runs", "id", run_id),
                ("report_parameter_candidates", "run_id", run_id),
                ("report_parameter_reviews", "candidate_id", candidate_id),
            ):
                expect_empty(
                    live.data(revoked, "GET", f"{table}?{field}=eq.{identifier}"),
                    "Revoked direct RLS",
                )

        for user, (report, run_id, candidate_id, source_id) in zip(
            live.users, completed, strict=True
        ):
            expect_status(
                user.write("DELETE", f"/reports/{report}", {}), 200, "Delete derived report"
            )
            for suffix in (
                "parameters",
                "parameter-processing",
                f"parameters/{candidate_id}/revisions",
            ):
                expect_status(
                    user.client.get(f"/reports/{report}/{suffix}"), 404, "Deleted derived access"
                )
            for table, field, identifier in (
                ("report_parameter_runs", "report_id", report),
                ("report_parameter_candidates", "run_id", run_id),
                ("report_parameter_reviews", "candidate_id", candidate_id),
            ):
                expect_empty(
                    live.data(user, "GET", f"{table}?{field}=eq.{identifier}"),
                    "Deleted derived rows",
                )
            expect_status(
                user.write(
                    "POST",
                    f"/reports/{report}/extract-parameters",
                    {"source_run_id": source_id, "idempotency_key": str(uuid4())},
                ),
                404,
                "Deleted report cannot reprocess",
            )
        # An explicitly failed Phase 4 attempt is never accepted as parser input.
        owner = live.users[0]
        corrupt = extraction_fixtures.document(())
        response = owner.write(
            "POST", "/reports", metadata("zero-page.pdf", "application/pdf", corrupt)
        )
        expect_status(response, 201, "Reserve failed-source fixture")
        report = str(object_body(response)["id"])
        created.append((owner, report))
        expect_status(
            put_file(owner, report, corrupt, "application/pdf"), 200, "Upload failed-source fixture"
        )
        expect_status(
            owner.write("POST", f"/reports/{report}/process", {"idempotency_key": str(uuid4())}),
            202,
            "Extract corrupt source",
        )
        failed = finish(owner, report)
        assert failed["status"] == "failed"
        expect_status(
            owner.write(
                "POST",
                f"/reports/{report}/extract-parameters",
                {"source_run_id": str(failed["id"]), "idempotency_key": str(uuid4())},
            ),
            404,
            "Failed text attempt cannot produce candidates",
        )
    finally:
        for user, report in created:
            expect_status(
                user.write("DELETE", f"/reports/{report}", {}), 200, "Synthetic report cleanup"
            )
