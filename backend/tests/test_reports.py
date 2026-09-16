"""Full local BFF path, replacing only external provider HTTP transport."""

import base64
import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from tests.auth_support import ORIGIN, auth_settings
from tests.report_fixtures import valid_jpeg, valid_pdf, valid_png
from tests.reports_support import ReportsProvider


@pytest.fixture
def provider() -> ReportsProvider:
    return ReportsProvider()


@pytest.fixture
def client(provider: ReportsProvider) -> Iterator[TestClient]:
    with TestClient(
        create_app(auth_settings(), provider_transport=httpx.MockTransport(provider.handle))
    ) as test_client:
        yield test_client


def csrf(client: TestClient) -> dict[str, str]:
    return {"Origin": ORIGIN, "X-CSRF-Token": client.get("/auth/csrf").json()["csrf_token"]}


def login(client: TestClient) -> None:
    assert (
        client.post(
            "/auth/login",
            headers=csrf(client),
            json={
                "email": "account@example.com",
                "password": "isolated-test-password",
            },
        ).status_code
        == 200
    )


def reserve(
    client: TestClient,
    *,
    filename: str = "neutral.pdf",
    data: bytes | None = None,
    media_type: str = "application/pdf",
    key: str | None = None,
) -> dict[str, object]:
    response = client.post(
        "/reports",
        headers=csrf(client),
        json={
            "original_filename": filename,
            "size_bytes": len(data if data is not None else valid_pdf()),
            "media_type": media_type,
            "idempotency_key": key or str(uuid4()),
        },
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def upload(
    client: TestClient,
    row: dict[str, object],
    data: bytes | None = None,
    media_type: str = "application/pdf",
) -> httpx.Response:
    return cast(
        httpx.Response,
        client.put(
            f"/reports/{row['id']}/file",
            headers={**csrf(client), "Content-Type": media_type},
            content=valid_pdf() if data is None else data,
        ),
    )


def test_private_upload_list_download_delete_full_path(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    assert client.get("/reports/config").json() == {
        "max_upload_bytes": 5_242_880,
        "allowed_media_types": ["application/pdf", "image/jpeg", "image/png"],
    }
    assert client.get("/reports").json() == {"reports": [], "next_cursor": None}
    row = reserve(client)
    assert row["status"] == "pending_upload"
    assert set(row) == {
        "id",
        "original_filename",
        "size_bytes",
        "media_type",
        "status",
        "created_at",
        "updated_at",
        "error_category",
    }
    assert client.get(f"/reports/{row['id']}/file").status_code == 404
    response = upload(client, row)
    assert response.status_code == 200 and response.json()["status"] == "uploaded"
    assert client.get("/reports").json()["reports"][0]["id"] == row["id"]
    download = client.get(f"/reports/{row['id']}/file")
    assert download.status_code == 200 and download.content == valid_pdf()
    assert download.headers["content-disposition"].startswith("attachment;")
    assert "sandbox" in download.headers["content-security-policy"]
    assert download.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in download.headers["cache-control"]
    deleted = client.request("DELETE", f"/reports/{row['id']}", headers=csrf(client), json={})
    assert deleted.status_code == 200 and deleted.json()["status"] == "deleted"
    assert not provider.objects
    assert client.get(f"/reports/{row['id']}").status_code == 404
    assert client.get("/reports").json()["reports"] == []


def test_png_upload_is_real_binary_not_json(client: TestClient, provider: ReportsProvider) -> None:
    login(client)
    row = reserve(client, filename="neutral.png", data=valid_png(), media_type="image/png")
    assert upload(client, row, valid_png(), "image/png").status_code == 200
    request = next(
        item
        for item in provider.requests
        if item.url.path.startswith("/storage/") and item.method == "POST"
    )
    assert request.content == valid_png() and request.headers["content-type"] == "image/png"


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/reports"),
        ("GET", "/reports/config"),
        ("GET", f"/reports/{uuid4()}"),
        ("GET", f"/reports/{uuid4()}/file"),
        ("POST", "/reports"),
        ("PUT", f"/reports/{uuid4()}/file"),
        ("DELETE", f"/reports/{uuid4()}"),
        ("POST", "/reports/cleanup"),
    ],
)
def test_report_endpoints_require_session(
    client: TestClient, provider: ReportsProvider, method: str, path: str
) -> None:
    headers = {
        **csrf(client),
        "Content-Type": "application/pdf" if method == "PUT" else "application/json",
    }
    response = client.request(method, path, headers=headers, content=b"{}")
    assert response.status_code == 401
    assert not provider.requests


@pytest.mark.parametrize("attack", ["missing", "origin", "signature", "type"])
def test_binary_csrf_not_exempted(
    client: TestClient, provider: ReportsProvider, attack: str
) -> None:
    login(client)
    row = reserve(client)
    provider.requests.clear()
    headers = {**csrf(client), "Content-Type": "application/pdf"}
    if attack == "missing":
        headers.pop("X-CSRF-Token")
    elif attack == "origin":
        headers["Origin"] = "https://foreign.example"
    elif attack == "signature":
        headers["X-CSRF-Token"] += "0"
    else:
        headers["Content-Type"] = "application/octet-stream"
    response = client.put(f"/reports/{row['id']}/file", headers=headers, content=valid_pdf())
    assert response.status_code == 403
    assert not provider.requests


@pytest.mark.parametrize(
    "path,method",
    [("/reports", "POST"), ("/reports/cleanup", "POST"), (f"/reports/{uuid4()}", "DELETE")],
)
def test_json_report_writes_retain_csrf(
    client: TestClient, provider: ReportsProvider, path: str, method: str
) -> None:
    response = client.request(method, path, json={})
    assert response.status_code == 403 and not provider.requests


@pytest.mark.parametrize(
    "field,value",
    [
        ("original_filename", "../secret.pdf"),
        ("original_filename", "C:\\report.pdf"),
        ("original_filename", "report\u202epdf.png"),
        ("original_filename", "NUL.pdf"),
        ("original_filename", "report.exe"),
        ("original_filename", "x" * 121 + ".pdf"),
        ("media_type", "text/html"),
        ("media_type", "image/png"),
        ("size_bytes", 0),
        ("size_bytes", 5_242_881),
        ("user_id", str(uuid4())),
        ("ownerId", str(uuid4())),
        ("storage_path", "other/path.pdf"),
        ("idempotency_key", "not-a-uuid"),
    ],
)
def test_invalid_metadata_rejected_before_write(
    client: TestClient, provider: ReportsProvider, field: str, value: object
) -> None:
    login(client)
    provider.requests.clear()
    body: dict[str, object] = {
        "original_filename": "neutral.pdf",
        "media_type": "application/pdf",
        "size_bytes": len(valid_pdf()),
        "idempotency_key": str(uuid4()),
    }
    body[field] = value
    response = client.post("/reports", headers=csrf(client), json=body)
    assert response.status_code == 422
    assert not any(item.url.path.endswith("report_reserve") for item in provider.requests)
    assert "input" not in response.json()


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"MZrenamed executable",
        b"%PDF-1.4\n1 0 obj\nendobj\nstartxref\n0\n%%EOF\n",
        valid_png(),
    ],
)
def test_invalid_bytes_never_reach_storage(
    client: TestClient, provider: ReportsProvider, data: bytes
) -> None:
    login(client)
    row = reserve(client, data=data or b"x")
    response = upload(client, row, data)
    assert response.status_code == 422
    assert not provider.objects
    assert not any(item.url.path.startswith("/storage/") for item in provider.requests)
    assert provider.rows[str(row["id"])]["status"] == "upload_failed"


def test_size_mismatch_and_wrong_mime_rejected(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    assert upload(client, row, valid_pdf() + b" ").status_code == 422
    assert upload(client, row, valid_pdf(), "image/png").status_code == 422
    assert not provider.objects


def test_global_json_limit_preserved_and_file_limit_enforced(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    provider.requests.clear()
    assert client.post("/reports", headers=csrf(client), content=b"x" * 16_385).status_code == 413
    assert upload(client, row, b"x" * 5_242_881).status_code == 413
    assert not provider.requests


def test_reservation_and_file_retry_are_idempotent(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    key = str(uuid4())
    row = reserve(client, key=key)
    assert reserve(client, key=key)["id"] == row["id"]
    assert upload(client, row).status_code == 200
    assert upload(client, row).status_code == 200
    assert len(provider.objects) == 1
    assert (
        len(
            [
                item
                for item in provider.requests
                if item.url.path.startswith("/storage/") and item.method == "POST"
            ]
        )
        == 1
    )


def test_upload_timeout_after_storage_commit_recovers_exact_bytes(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    provider.commit_then_timeout = True
    assert upload(client, row).status_code == 200
    assert provider.rows[str(row["id"])]["status"] == "uploaded"
    assert len(provider.objects) == 1


def test_storage_failure_retains_recoverable_metadata(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    provider.storage_failure = True
    response = upload(client, row)
    assert response.status_code == 503 and "private" not in response.text
    internal = provider.rows[str(row["id"])]
    assert internal["status"] == "upload_failed" and internal["upload_lease_expires_at"] is not None
    assert not provider.objects


def test_metadata_failure_then_retry_preserves_one_immutable_file(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    provider.finish_failure = True
    assert upload(client, row).status_code == 503
    assert len(provider.objects) == 1
    assert upload(client, row).status_code == 409
    provider.finish_failure = False
    provider.rows[str(row["id"])]["upload_lease_expires_at"] = (
        datetime.now(UTC) - timedelta(seconds=1)
    ).isoformat()
    assert upload(client, row).status_code == 200
    assert len(provider.objects) == 1


def test_delete_storage_failure_is_pending_and_retryable(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    assert upload(client, row).status_code == 200
    provider.delete_failure = True
    response = client.request("DELETE", f"/reports/{row['id']}", headers=csrf(client), json={})
    assert response.status_code == 202 and response.json()["status"] == "deleting"
    assert len(provider.objects) == 1
    assert client.get(f"/reports/{row['id']}/file").status_code == 404
    provider.delete_failure = False
    result = client.post("/reports/cleanup", headers=csrf(client), json={})
    assert result.json() == {"pending": 0, "cleaned": 1} and not provider.objects


def test_delete_waits_for_live_upload_lease(client: TestClient, provider: ReportsProvider) -> None:
    login(client)
    row = reserve(client)
    internal = provider.rows[str(row["id"])]
    internal["upload_lease_expires_at"] = (datetime.now(UTC) + timedelta(seconds=120)).isoformat()
    response = client.request("DELETE", f"/reports/{row['id']}", headers=csrf(client), json={})
    assert response.status_code == 202
    assert not any(
        item.method == "DELETE" and item.url.path.startswith("/storage/")
        for item in provider.requests
    )


@pytest.mark.parametrize(
    "method,suffix", [("GET", ""), ("GET", "/file"), ("DELETE", ""), ("PUT", "/file")]
)
def test_missing_or_other_report_is_indistinguishable(
    client: TestClient, provider: ReportsProvider, method: str, suffix: str
) -> None:
    login(client)
    response = client.request(
        method,
        f"/reports/{uuid4()}{suffix}",
        headers={
            **csrf(client),
            "Content-Type": "application/pdf" if method == "PUT" else "application/json",
        },
        content=b"{}",
    )
    assert response.status_code == 404
    assert response.json() == {"code": "report_not_found", "message": "Report not found."}
    assert not provider.objects


@pytest.mark.parametrize(
    "cursor",
    [
        "not base64!",
        "a" * 257,
        base64.urlsafe_b64encode(json.dumps(["2026-01-01", str(uuid4())]).encode()).decode(),
        base64.urlsafe_b64encode(b'["x),or(user_id.neq.null)","x"]').decode(),
    ],
)
def test_cursor_injection_is_rejected(
    client: TestClient, provider: ReportsProvider, cursor: str
) -> None:
    login(client)
    provider.requests.clear()
    assert client.get("/reports", params={"cursor": cursor}).status_code == 422
    assert not any(item.url.path == "/rest/v1/reports" for item in provider.requests)


def test_download_verifies_integrity_before_returning_bytes(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    assert upload(client, row).status_code == 200
    internal = provider.rows[str(row["id"])]
    provider.objects[str(internal["storage_path"])] = b"tampered", "application/pdf"
    response = client.get(f"/reports/{row['id']}/file")
    assert response.status_code == 503 and b"tampered" not in response.content
    assert internal["sha256"] == hashlib.sha256(valid_pdf()).hexdigest()


def test_deleted_manifest_reconciles_late_storage_artifact(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    assert upload(client, row).status_code == 200
    assert (
        client.request("DELETE", f"/reports/{row['id']}", headers=csrf(client), json={}).status_code
        == 200
    )
    key = str(provider.rows[str(row["id"])]["storage_path"])
    provider.objects[key] = valid_pdf(), "application/pdf"
    assert client.post("/reports/cleanup", headers=csrf(client), json={}).json()["cleaned"] == 1
    assert not provider.objects


def test_real_jpeg_container_round_trip(client: TestClient, provider: ReportsProvider) -> None:
    login(client)
    data = valid_jpeg()
    row = reserve(client, filename="neutral.jpeg", data=data, media_type="image/jpeg")
    assert upload(client, row, data, "image/jpeg").status_code == 200
    assert client.get(f"/reports/{row['id']}/file").content == data


def test_storage_reads_force_fresh_origin_authorization(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    assert upload(client, row).status_code == 200
    for _ in range(2):
        assert client.get(f"/reports/{row['id']}/file").status_code == 200
    reads = [
        r for r in provider.requests if r.url.path.startswith("/storage/") and r.method == "GET"
    ]
    assert len(reads) == 2
    nonces = [str(r.url.params["cacheNonce"]) for r in reads]
    assert len(set(nonces)) == 2 and all(len(nonce) == 36 for nonce in nonces)
    assert all(r.headers["cache-control"] == "no-cache, no-store" for r in reads)


def test_matching_hash_does_not_bypass_download_format_validation(
    client: TestClient, provider: ReportsProvider
) -> None:
    login(client)
    row = reserve(client)
    assert upload(client, row).status_code == 200
    internal = provider.rows[str(row["id"])]
    data = b"MZ harmless synthetic invalid PDF"
    internal["size_bytes"], internal["sha256"] = len(data), hashlib.sha256(data).hexdigest()
    provider.objects[str(internal["storage_path"])] = data, "application/pdf"
    response = client.get(f"/reports/{row['id']}/file")
    assert response.status_code == 503 and data not in response.content
