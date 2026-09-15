"""Opt-in real private Storage and database tests using dedicated Phase 2 accounts.

Only neutral generated files are uploaded. Credentials, response bodies and object
paths are never logged. Each created report is deleted through its owner's API;
minimal deletion manifests intentionally remain for late-write reconciliation.
"""

from __future__ import annotations

import hashlib
import os
from uuid import uuid4

import httpx
import pytest

from tests.integration.test_live_ownership import (
    LiveContext,
    SignedInUser,
    expect_empty,
    expect_status,
    live as live,
    object_body,
)
from tests.report_fixtures import valid_jpeg, valid_pdf, valid_png

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1",
    reason="Real Supabase tests require explicit RUN_SUPABASE_INTEGRATION=1 opt-in",
)

PUBLIC_FIELDS = {
    "id", "original_filename", "media_type", "size_bytes", "status",
    "created_at", "updated_at", "error_category",
}


def metadata(name: str, media_type: str, data: bytes) -> dict[str, object]:
    return {
        "original_filename": name,
        "media_type": media_type,
        "size_bytes": len(data),
        "idempotency_key": str(uuid4()),
    }


def public_report(response: httpx.Response, status: int, label: str) -> dict[str, object]:
    expect_status(response, status, label)
    body = object_body(response)
    if set(body) != PUBLIC_FIELDS:
        raise AssertionError(f"{label}: unexpected public report fields")
    return body


def put_file(user: SignedInUser, report_id: str, data: bytes, media_type: str) -> httpx.Response:
    return user.client.put(
        f"/reports/{report_id}/file", content=data,
        headers={"X-CSRF-Token": user.csrf, "Content-Type": media_type},
    )


def internal_report(live: LiveContext, user: SignedInUser, report_id: str) -> dict[str, object]:
    response = live.data(user, "GET", f"reports?id=eq.{report_id}&select=*")
    expect_status(response, 200, "Owner Data API report read")
    body = response.json()
    if not isinstance(body, list) or len(body) != 1 or not isinstance(body[0], dict):
        raise AssertionError("Owner report row missing")
    return body[0]


def denied(response: httpx.Response, label: str) -> None:
    if response.status_code not in {400, 401, 403, 404}:
        raise AssertionError(f"{label}: expected denial, received HTTP {response.status_code}")


def test_real_private_reports_and_storage_isolation(live: LiveContext) -> None:
    created: list[tuple[SignedInUser, str]] = []
    stored: list[tuple[SignedInUser, str, str, bytes, str]] = []
    storage_origin = str(live.database.base_url).split("/rest/v1")[0] + "/storage/v1/"

    def reserve(user: SignedInUser, body: dict[str, object]) -> str:
        report = public_report(user.write("POST", "/reports", body), 201, "Reserve owner report")
        report_id = str(report["id"])
        created.append((user, report_id))
        if report["status"] != "pending_upload":
            raise AssertionError("New report must start pending")
        return report_id

    with httpx.Client(
        base_url=storage_origin, headers={"apikey": live.database.headers["apikey"]}, timeout=35,
    ) as storage:

        def store_request(
            user: SignedInUser, method: str, route: str, *,
            data: bytes | None = None, media_type: str | None = None,
            body: dict[str, object] | None = None,
        ) -> httpx.Response:
            headers = {"Authorization": f"Bearer {user.access}"}
            if media_type:
                headers["Content-Type"] = media_type
                headers["x-upsert"] = "false"
            return storage.request(method, route, headers=headers, content=data, json=body)

        try:
            fixtures = [("neutral.pdf", "application/pdf", valid_pdf()),
                        ("neutral.png", "image/png", valid_png()),
                        ("neutral.jpeg", "image/jpeg", valid_jpeg())]
            for index, user in enumerate(live.users):
                other = live.users[1 - index]
                expect_status(user.client.get("/reports/config"), 200, "Authenticated upload config")
                for name, media_type, data in fixtures:
                    body = metadata(name, media_type, data)
                    report_id = reserve(user, body)
                    repeated = public_report(user.write("POST", "/reports", body), 201, "Retry reservation")
                    if repeated["id"] != report_id:
                        raise AssertionError("Idempotent reservation created a duplicate")
                    expect_status(user.write("POST", "/reports", {**body, "original_filename": "different.pdf"}),
                                  409 if media_type == "application/pdf" else 422, "Conflicting reservation")
                    uploaded = public_report(put_file(user, report_id, data, media_type), 200, "Real upload")
                    if uploaded["status"] != "uploaded":
                        raise AssertionError("Real upload was not confirmed")
                    public_report(put_file(user, report_id, data, media_type), 200, "Completed upload retry")
                    row = internal_report(live, user, report_id)
                    path = str(row["storage_path"])
                    if not path.startswith(f"{user.user_id}/{report_id}/") or name in path:
                        raise AssertionError("Storage path must be generated and owned")
                    stored.append((user, report_id, path, data, media_type))
                    public_report(user.client.get(f"/reports/{report_id}"), 200, "Owner metadata")
                    download = user.client.get(f"/reports/{report_id}/file")
                    expect_status(download, 200, "Owner private download")
                    if download.content != data:
                        raise AssertionError("Downloaded bytes differ from upload")
                    for key, expected in {"cache-control": "no-store", "x-content-type-options": "nosniff"}.items():
                        if download.headers.get(key) != expected:
                            raise AssertionError("Missing safe download headers")
                    if not download.headers.get("content-disposition", "").startswith("attachment;"):
                        raise AssertionError("Download must use attachment disposition")
                    if "sandbox" not in download.headers.get("content-security-policy", ""):
                        raise AssertionError("Download must be sandboxed")
                    for route in (f"/reports/{report_id}", f"/reports/{report_id}/file"):
                        expect_status(other.client.get(route), 404, "Cross-owner API read")
                    expect_status(other.write("DELETE", f"/reports/{report_id}", {}), 404, "Cross-owner delete")
                    expect_status(put_file(other, report_id, data, media_type), 404, "Cross-owner API upload")
                    expect_empty(live.data(other, "GET", f"reports?id=eq.{report_id}&select=*"), "Cross-owner RLS")
                    for actor in (user, other):
                        expect_status(live.data(actor, "PATCH", f"reports?id=eq.{report_id}", {"user_id": other.user_id}),
                                      403, "Direct metadata mutation denied")
                        expect_status(live.data(actor, "DELETE", f"reports?id=eq.{report_id}"),
                                      403, "Direct manifest deletion denied")
                    denied(store_request(other, "GET", f"object/authenticated/reports/{path}"), "Cross-owner Storage download")
                    denied(store_request(other, "PUT", f"object/reports/{path}", data=data, media_type=media_type),
                           "Cross-owner Storage overwrite")
                    removed = store_request(other, "DELETE", "object/reports", body={"prefixes": [path]})
                    if removed.status_code == 200:
                        if removed.json() != []:
                            raise AssertionError("Cross-owner Storage deletion returned a removed object")
                    else:
                        denied(removed, "Cross-owner Storage deletion")
                    if store_request(user, "GET", f"object/authenticated/reports/{path}").content != data:
                        raise AssertionError("Cross-owner request changed the owner's bytes")
                    denied(store_request(user, "POST", f"object/sign/reports/{path}", body={"expiresIn": 60}),
                           "Reusable signed links disabled")
                    denied(storage.get(f"object/public/reports/{path}"), "Public download disabled")

                response = user.client.get("/reports")
                expect_status(response, 200, "Real owner history")
                history = object_body(response)["reports"]
                if not isinstance(history, list):
                    raise AssertionError("Invalid report history")
                own_ids = {report_id for owner, report_id in created if owner is user}
                other_ids = {report_id for owner, report_id in created if owner is other}
                ids = {item["id"] for item in history}
                if not own_ids.issubset(ids) or ids.intersection(other_ids):
                    raise AssertionError("Report history did not isolate owners")

                # Ownership is tested while the target has a valid upload lease, so
                # denial cannot be accidentally explained by a closed lifecycle.
                data = valid_png()
                report_id = reserve(user, metadata("direct-neutral.png", "image/png", data))
                lease = live.data(user, "POST", "rpc/report_begin_upload", {
                    "p_report_id": report_id, "p_sha256": hashlib.sha256(data).hexdigest(),
                })
                expect_status(lease, 200, "Owner upload lease")
                row = object_body(lease)
                path = str(row["storage_path"])
                denied(store_request(other, "POST", f"object/reports/{path}", data=data, media_type="image/png"),
                       "Cross-owner upload to a currently valid path")
                expect_status(store_request(user, "POST", f"object/reports/{path}", data=data, media_type="image/png"),
                              200, "Owner direct Storage upload positive control")
                expect_status(live.data(user, "POST", "rpc/report_finish_upload", {
                    "p_report_id": report_id, "p_lease_token": row["lease_token"],
                }), 200, "Owner completion positive control")
                denied(live.data(other, "POST", "rpc/report_begin_delete", {"p_report_id": report_id}),
                       "Cross-owner lifecycle RPC")

            # Bad requests use synthetic harmless data and never need malware.
            user = live.users[0]
            data = valid_pdf()
            baseline = metadata("valid.pdf", "application/pdf", data)
            for changes in (
                {"original_filename": "../report.pdf"}, {"original_filename": "C:\\report.pdf"},
                {"original_filename": "report.exe"}, {"original_filename": "report\u202epdf.pdf"},
                {"original_filename": "CON.pdf"}, {"media_type": "text/html"},
                {"media_type": "image/png"}, {"size_bytes": 0}, {"size_bytes": 5_242_881},
                {"user_id": live.users[1].user_id},
            ):
                expect_status(user.write("POST", "/reports", {**baseline, **changes}), 422, "Invalid metadata rejected")
            report_id = reserve(user, baseline)
            route = f"/reports/{report_id}/file"
            expect_status(user.client.put(route, content=data, headers={"Content-Type": "application/pdf"}),
                          403, "Binary upload missing CSRF")
            expect_status(user.client.put(route, content=data, headers={
                "Content-Type": "application/pdf", "X-CSRF-Token": user.csrf,
                "Origin": "https://untrusted.invalid",
            }), 403, "Binary upload wrong origin")
            expect_status(put_file(user, report_id, b"", "application/pdf"), 422, "Empty binary rejected")
            expect_status(put_file(user, report_id, b"MZ" + b"x" * (len(data) - 2), "application/pdf"),
                          422, "Executable signature disguised as PDF rejected")
            expect_status(put_file(user, report_id, b"x" * 5_242_881, "application/pdf"),
                          413, "Oversized streamed body rejected")
            expect_status(user.client.request("DELETE", f"/reports/{report_id}", json={}),
                          403, "Delete missing CSRF")
            with httpx.Client(base_url=str(user.client.base_url), timeout=20) as anonymous:
                expect_status(anonymous.get("/reports"), 401, "Anonymous report history")
                response = anonymous.put(route, content=data, headers={"Content-Type": "application/pdf"})
                if response.status_code not in {401, 403}:
                    raise AssertionError("Anonymous binary upload was not denied")
            row = internal_report(live, user, report_id)
            denied(store_request(user, "GET", f"object/authenticated/reports/{row['storage_path']}"),
                   "Rejected content created no readable object")

            for owner, report_id in created:
                response = owner.write("DELETE", f"/reports/{report_id}", {})
                expect_status(response, 200, "Owner deletion including pending upload cancellation")
                if object_body(response).get("status") != "deleted":
                    raise AssertionError("Deletion was not confirmed")
                expect_status(owner.write("DELETE", f"/reports/{report_id}", {}), 200, "Idempotent deletion")
                expect_status(owner.client.get(f"/reports/{report_id}"), 404, "Deleted metadata hidden")
                row = internal_report(live, owner, report_id)
                if row["status"] != "deleted" or any(row[key] is not None for key in (
                    "original_filename", "media_type", "size_bytes", "sha256", "lease_token",
                )):
                    raise AssertionError("Deletion did not scrub sensitive metadata")
                expect_status(put_file(owner, report_id, data, "application/pdf"), 404, "Late upload cannot resurrect cancellation")
            for owner, _, path, _, _ in stored:
                denied(store_request(owner, "GET", f"object/authenticated/reports/{path}"), "Deleted file unavailable")
            for owner in live.users:
                expect_status(owner.write("POST", "/reports/cleanup", {}), 200, "Owner reconciliation endpoint")

            # A new short-lived fixture verifies revoked JWT denial on real stored bytes.
            user, other = live.users
            report_id = reserve(user, metadata("revocation.pdf", "application/pdf", data))
            public_report(put_file(user, report_id, data, "application/pdf"), 200, "Revocation fixture upload")
            path = str(internal_report(live, user, report_id)["storage_path"])
            # Remove bytes before ending this session; all resource cleanup stays owner scoped.
            expect_status(user.write("DELETE", f"/reports/{report_id}", {}), 200, "Revocation fixture cleanup")
            expect_status(user.write("POST", "/auth/logout", {}), 200, "Owner logout")
            denied(store_request(user, "GET", f"object/authenticated/reports/{path}"), "Revoked Storage token denied")
            expect_empty(live.data(user, "GET", "reports?select=id"), "Revoked JWT report RLS")
            expect_status(other.client.get("/reports"), 200, "Other owner session unaffected")
        finally:
            failures = 0
            for owner, report_id in created:
                try:
                    response = owner.write("DELETE", f"/reports/{report_id}", {})
                    # Logout above already cleaned that owner's resources.
                    if response.status_code not in {200, 401}:
                        failures += 1
                except httpx.HTTPError:
                    failures += 1
            if failures:
                raise AssertionError(f"Owner cleanup needs retry for {failures} test report(s)")
