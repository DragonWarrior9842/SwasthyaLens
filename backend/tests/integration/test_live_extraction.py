"""Real dedicated-user extraction isolation. No real patient documents."""

import os
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from dotenv import dotenv_values

from tests.extraction_fixtures import TOKENS, document, image_bytes
from tests.integration.test_live_ownership import (
    LiveContext,
    SignedInUser,
    expect_empty,
    expect_status,
    object_body,
)
from tests.integration.test_live_ownership import live as live
from tests.integration.test_live_reports import metadata, put_file

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real provider opt-in required"
)


def finish(user: SignedInUser, report_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        response = user.client.get(f"/reports/{report_id}/processing")
        expect_status(response, 200, "Owner processing history")
        runs = response.json()["runs"]
        if runs and runs[0]["status"] in {"completed", "failed"}:
            return dict(runs[0])
        time.sleep(3)
    raise AssertionError("Extraction did not reach a terminal state")


def test_live_extraction_ownership_retry_and_delete(live: LiveContext) -> None:
    created: list[tuple[SignedInUser, str]] = []
    completed: list[tuple[str, str]] = []

    def upload(user: SignedInUser, data: bytes, name: str, media: str) -> str:
        response = user.write("POST", "/reports", metadata(name, media, data))
        expect_status(response, 201, "Reserve extraction fixture")
        identifier = str(object_body(response)["id"])
        created.append((user, identifier))
        expect_status(put_file(user, identifier, data, media), 200, "Upload extraction fixture")
        return identifier

    try:
        for index, user in enumerate(live.users):
            report_id = upload(
                user, document(("native", "native")), "synthetic-native.pdf", "application/pdf"
            )
            other = live.users[1 - index]
            key = str(uuid4())
            with httpx.Client(base_url=str(user.client.base_url)) as anonymous:
                expect_status(
                    anonymous.get(f"/reports/{report_id}/processing"),
                    401,
                    "Anonymous extraction read",
                )
            expect_status(
                user.client.post(f"/reports/{report_id}/process", json={"idempotency_key": key}),
                403,
                "Missing CSRF",
            )
            expect_status(
                other.write(
                    "POST", f"/reports/{report_id}/process", {"idempotency_key": str(uuid4())}
                ),
                404,
                "Cross-user processing",
            )
            response = user.write("POST", f"/reports/{report_id}/process", {"idempotency_key": key})
            expect_status(response, 202, "Owner processing accepted")
            run_id = str(object_body(response)["id"])
            again = user.write("POST", f"/reports/{report_id}/process", {"idempotency_key": key})
            expect_status(again, 202, "Idempotent retry")
            assert object_body(again)["id"] == run_id
            run = finish(user, report_id)
            assert run["status"] == "completed", "Native extraction failed"
            response = user.client.get(f"/reports/{report_id}/extraction")
            expect_status(response, 200, "Owner extracted text")
            pages = response.json()["pages"]
            assert [page["page_number"] for page in pages] == [1, 2]
            assert all(
                page["method"] == "native_text" and all(token in page["text"] for token in TOKENS)
                for page in pages
            )
            for suffix in ("processing", "extraction"):
                expect_status(
                    other.client.get(f"/reports/{report_id}/{suffix}"),
                    404,
                    "Cross-user extraction denied",
                )
            for table, field, identifier in (
                ("report_processing_runs", "report_id", report_id),
                ("report_pages", "run_id", run_id),
            ):
                expect_empty(
                    live.data(other, "GET", f"{table}?{field}=eq.{identifier}"),
                    "Derived RLS isolation",
                )
                expect_status(
                    live.data(user, "POST", table, {field: identifier}),
                    403,
                    "No direct machine-output writes",
                )
                expect_status(live.database.get(table), 401, "Anonymous derived table denied")
            expect_status(
                live.data(
                    user,
                    "POST",
                    "rpc/processing_request",
                    {
                        "p_report_id": report_id,
                        "p_idempotency_key": str(uuid4()),
                        "p_worker_secret": "forged",
                    },
                ),
                403,
                "Owner JWT cannot impersonate worker",
            )
            completed.append((report_id, run_id))

        # Explicit failure and retry preserve history, original bytes and bounded attempts.
        first = live.users[0]
        corrupt_id = upload(first, document(()), "zero-page.pdf", "application/pdf")
        for attempt in range(1, 4):
            expect_status(
                first.write(
                    "POST", f"/reports/{corrupt_id}/process", {"idempotency_key": str(uuid4())}
                ),
                202,
                "Retry accepted",
            )
            run = finish(first, corrupt_id)
            assert run["status"] == "failed" and run["error_category"] == "corrupt_document"
            assert run["attempt"] == attempt
        expect_status(
            first.write(
                "POST", f"/reports/{corrupt_id}/process", {"idempotency_key": str(uuid4())}
            ),
            409,
            "Bounded retry limit",
        )
        expect_status(
            first.client.get(f"/reports/{corrupt_id}/file"), 200, "Failure preserves original"
        )

        # Real image OCR must preserve the evaluated numeric/unit tokens.
        image_id = upload(first, image_bytes(), "synthetic-image.png", "image/png")
        expect_status(
            first.write("POST", f"/reports/{image_id}/process", {"idempotency_key": str(uuid4())}),
            202,
            "Image processing accepted",
        )
        image_run = finish(first, image_id)
        assert image_run["status"] == "completed", "Live OCR did not complete"
        image_result = first.client.get(f"/reports/{image_id}/extraction")
        expect_status(image_result, 200, "Read live OCR output")
        assert all(token in image_result.json()["pages"][0]["text"] for token in TOKENS)

        # Revoke a separate genuine session while the owner's extracted pages still exist.
        # Keep the original owner session active so cleanup remains possible on failure.
        values = dotenv_values(Path(__file__).resolve().parents[2] / ".env.integration")
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
                "Extra session for revocation",
            )
            access = client.cookies.get("sl_access")
            assert access
            revoked = SignedInUser(
                client,
                str(object_body(client.get("/auth/csrf"))["csrf_token"]),
                access,
                first.user_id,
            )
            try:
                report_id, run_id = completed[0]
                route = f"report_pages?run_id=eq.{run_id}"
                before = live.data(revoked, "GET", route)
                expect_status(before, 200, "Pre-revocation page access")
                assert len(before.json()) == 2
                expect_status(revoked.write("POST", "/auth/logout", {}), 200, "Revoke session")
                client.cookies.set("sl_access", access)
                expect_status(
                    client.get(f"/reports/{report_id}/extraction"), 401, "Revoked text read"
                )
                expect_status(
                    revoked.write(
                        "POST", f"/reports/{report_id}/process", {"idempotency_key": str(uuid4())}
                    ),
                    401,
                    "Revoked processing request",
                )
                expect_empty(live.data(revoked, "GET", route), "Revoked derived-data JWT")
                after = live.data(first, "GET", route)
                expect_status(after, 200, "Other owner session remains active")
                assert len(after.json()) == 2
            finally:
                revoked.close_session()

        for user, (report_id, run_id) in zip(live.users, completed, strict=True):
            expect_status(
                user.write("DELETE", f"/reports/{report_id}", {}), 200, "Delete extracted report"
            )
            expect_empty(
                live.data(user, "GET", f"report_pages?run_id=eq.{run_id}"),
                "Deleted pages inaccessible",
            )
            expect_empty(
                live.data(user, "GET", f"report_processing_runs?report_id=eq.{report_id}"),
                "Deleted runs inaccessible",
            )
            expect_status(
                user.client.get(f"/reports/{report_id}/extraction"),
                404,
                "Deleted extraction denied",
            )
            expect_status(
                user.write(
                    "POST", f"/reports/{report_id}/process", {"idempotency_key": str(uuid4())}
                ),
                404,
                "Deleted processing denied",
            )

        # Remove remaining failed/image fixtures as well.
        for user, identifier in created:
            expect_status(
                user.write("DELETE", f"/reports/{identifier}", {}), 200, "Fixture cleanup"
            )
    finally:
        for user, identifier in created:
            user.write("DELETE", f"/reports/{identifier}", {})
