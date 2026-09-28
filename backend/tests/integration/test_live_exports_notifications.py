"""Opt-in real A/B export and operational notices. Synthetic generated reports only."""

import csv
import io
import os
from uuid import uuid4

import pytest

from tests import extraction_fixtures
from tests.integration.test_live_extraction import finish
from tests.integration.test_live_ownership import LiveContext, SignedInUser, expect_status
from tests.integration.test_live_ownership import live as live
from tests.integration.test_live_reports import metadata, put_file
from tests.parameter_fixtures import NATIVE_LINES

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real Supabase opt-in"
)


def test_live_private_exports_notifications_exact_facts_and_two_user_lifecycle(
    live: LiveContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extraction_fixtures, "LINES", NATIVE_LINES)
    pdf = extraction_fixtures.document(("native", "native"))
    created: list[tuple[SignedInUser, str]] = []
    manuals: list[tuple[SignedInUser, str]] = []
    originals: list[tuple[SignedInUser, bool]] = []
    reports: list[str] = []
    values = ["13.20", "<5", ">10", "Negative", "Trace", "1:80", "30–100"]
    export = {
        "format": "json",
        "language": "en",
        "date_from": "2020-01-01",
        "date_to": "2020-12-31",
        "include_unknown": True,
    }
    try:
        for user in live.users:
            original = user.client.get("/settings").json()["in_app_notifications"]
            originals.append((user, original))
            expect_status(
                user.write("PATCH", "/settings", {"in_app_notifications": True}),
                200,
                "Enable synthetic event notices",
            )
            r = user.write(
                "POST",
                "/reports",
                metadata(f"synthetic-phase11-{uuid4()}.pdf", "application/pdf", pdf),
            )
            expect_status(r, 201, "Reserve synthetic report")
            report = r.json()["id"]
            reports.append(report)
            created.append((user, report))
            notices = user.client.get("/notifications").json()["items"]
            assert not any(n["report_id"] == report for n in notices)
            expect_status(
                put_file(user, report, pdf, "application/pdf"), 200, "Actual upload completion"
            )
            expect_status(
                user.write("POST", f"/reports/{report}/process", {"idempotency_key": str(uuid4())}),
                202,
                "Explicit text extraction",
            )
            source = finish(user, report)
            assert source["status"] == "completed"
            request = {"source_run_id": source["id"], "idempotency_key": str(uuid4())}
            route = f"/reports/{report}"
            r = user.write("POST", route + "/extract-parameters", request)
            expect_status(r, 200, "Real parameter completion")
            expect_status(
                user.write("POST", route + "/extract-parameters", request),
                200,
                "Idempotent parameter replay",
            )
            candidates = user.client.get(route + "/parameters").json()["candidates"]
            for candidate, value in zip(candidates, values, strict=False):
                endpoint = route + f"/parameters/{candidate['id']}"
                expect_status(
                    user.write(
                        "PATCH",
                        endpoint,
                        {
                            "idempotency_key": str(uuid4()),
                            "expected_revision": 0,
                            "action": "corrected",
                            "correction": {
                                "original_label": "Synthetic स्रोत",
                                "raw_value": value,
                                "original_unit": "ng/mL",
                                "raw_reference": "30–100",
                            },
                        },
                    ),
                    200,
                    "Synthetic exact source review",
                )
                expect_status(
                    user.write("POST", endpoint + "/publish", {"expected_revision": 1}),
                    200,
                    "Explicit synthetic publication",
                )
            r = user.write(
                "POST",
                "/observations/manual",
                {
                    "idempotency_key": str(uuid4()),
                    "metric": "weight",
                    "raw_value": "72.125",
                    "unit": "kg",
                    "measured_at": "2020-01-02T00:15:00+05:30",
                },
            )
            expect_status(r, 200, "Synthetic manual source")
            manuals.append((user, r.json()["id"]))

        for index, user in enumerate(live.users):
            other = live.users[1 - index]
            report = reports[index]
            notices = user.client.get("/notifications").json()
            assert all(
                n["user_id"] == user.user_id and n["report_id"] != reports[1 - index]
                for n in notices["items"]
            )
            selected = [n for n in notices["items"] if n["report_id"] == report]
            assert sorted(n["event_type"] for n in selected) == [
                "extraction_completed",
                "parameters_ready",
                "upload_completed",
            ]
            assert all(
                set(n) == {"id", "user_id", "report_id", "event_type", "created_at", "read_at"}
                for n in selected
            )
            identifier = selected[0]["id"]
            for method in ("PATCH", "DELETE"):
                expect_status(
                    other.write(method, f"/notifications/{identifier}", {}),
                    404,
                    "Foreign notification denied",
                )
            assert live.data(other, "GET", f"notifications?id=eq.{identifier}").json() == []
            expect_status(
                user.client.patch(f"/notifications/{identifier}", json={}), 403, "Notification CSRF"
            )
            r = user.write("PATCH", f"/notifications/{identifier}", {})
            expect_status(r, 200, "Persist read state")
            assert (
                next(n for n in r.json()["items"] if n["id"] == identifier)["read_at"] is not None
            )
            expect_status(
                user.write("DELETE", f"/notifications/{identifier}", {}),
                200,
                "Dismiss owned notice",
            )
            expect_status(
                user.write("PATCH", f"/notifications/{identifier}", {}),
                404,
                "Dismissed notice unavailable",
            )

            expect_status(user.client.post("/exports", json=export), 403, "Export CSRF")
            expect_status(
                user.write("POST", "/exports", {**export, "user_id": other.user_id}),
                422,
                "Forged export owner",
            )
            r = user.write("POST", "/exports", {**export, "report_id": report})
            expect_status(r, 200, "Exact private JSON export")
            assert (
                r.headers["cache-control"] == "no-store"
                and r.headers["x-content-type-options"] == "nosniff"
            )
            findings = r.json()["observations"]
            assert sorted(f["raw_value"] for f in findings) == sorted(values)
            assert all(
                f["raw_reference"] == "30–100"
                and f["original_unit"] == "ng/mL"
                and f["measurement_date"] is None
                and f["date_status"] == "unknown"
                and f["page_number"] in (1, 2)
                for f in findings
            )
            assert all(
                secret not in r.text
                for secret in [
                    user.user_id,
                    report,
                    other.user_id,
                    "storage_path",
                    "api_key",
                    "parsing_version",
                ]
            )
            r = user.write(
                "POST",
                "/exports",
                {**export, "format": "csv", "language": "hi", "report_id": report},
            )
            expect_status(r, 200, "Hindi CSV export")
            table = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
            assert table[0][2] == "मूल मान" and sorted(record[2] for record in table[1:]) == sorted(
                values
            )
            expect_status(
                user.write("POST", "/exports", {**export, "report_id": reports[1 - index]}),
                404,
                "Foreign report export denied",
            )
            candidates = user.client.get(f"/reports/{report}/parameters").json()["candidates"]
            expect_status(
                user.write(
                    "PATCH",
                    f"/reports/{report}/parameters/{candidates[0]['id']}",
                    {"idempotency_key": str(uuid4()), "expected_revision": 1, "action": "rejected"},
                ),
                200,
                "Invalidate a published source",
            )
            r = user.write("POST", "/exports", {**export, "report_id": report})
            expect_status(r, 200, "Current source regeneration")
            assert "13.20" not in [f["raw_value"] for f in r.json()["observations"]]
            expect_status(
                user.write("DELETE", f"/reports/{report}", {}), 200, "Delete synthetic report"
            )
            created.remove((user, report))
            assert not any(
                n["report_id"] == report for n in user.client.get("/notifications").json()["items"]
            )
            expect_status(
                user.write("POST", "/exports", {**export, "report_id": report}),
                404,
                "Deleted source export denied",
            )
            expect_status(
                user.client.get(f"/exports/{report}/download"),
                404,
                "No retained historical export route",
            )
            manual = next(mid for u, mid in manuals if u is user)
            expect_status(
                user.write("DELETE", f"/observations/{manual}", {"expected_revision": 1}),
                200,
                "Delete synthetic manual",
            )
            manuals.remove((user, manual))
            r = user.write(
                "POST", "/exports", {**export, "source_type": "manual", "include_unknown": False}
            )
            expect_status(r, 200, "Regenerate after manual deletion")
            assert all(f["raw_value"] != "72.125" for f in r.json()["observations"])
        # Restore preferences before testing revocation; never leave altered account settings.
        for user, original in originals:
            expect_status(
                user.write("PATCH", "/settings", {"in_app_notifications": original}),
                200,
                "Restore original notification preference",
            )
        originals.clear()
        for user in live.users:
            user.close_session()
            expect_status(user.write("POST", "/exports", export), 401, "Revoked export denied")
            expect_status(user.client.get("/notifications"), 401, "Revoked notices denied")
            assert live.data(user, "GET", "notifications").json() == []
    finally:
        for user, report in created:
            user.write("DELETE", f"/reports/{report}", {})
        for user, identifier in manuals:
            user.write("DELETE", f"/observations/{identifier}", {"expected_revision": 1})
        for user, original in originals:
            user.write("PATCH", "/settings", {"in_app_notifications": original})
