"""Isolated provider state machine; real RLS/Storage policies are tested separately."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from tests.auth_support import ProviderFixture


@dataclass
class ReportsProvider(ProviderFixture):
    rows: dict[str, dict[str, object]] = field(default_factory=dict)
    objects: dict[str, tuple[bytes, str]] = field(default_factory=dict)
    storage_failure: bool = False
    commit_then_timeout: bool = False
    delete_failure: bool = False
    finish_failure: bool = False

    @staticmethod
    def conflict(message: str = "report_conflict") -> httpx.Response:
        return httpx.Response(400, json={"code": "P0001", "message": message})

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if not (
            path.startswith("/rest/v1/rpc/report_")
            or path == "/rest/v1/reports"
            or path.startswith("/storage/")
        ):
            return super().handle(request)
        self.requests.append(request)
        assert request.headers.get("authorization", "").startswith("Bearer ")
        if path in self.failures:
            code, body = self.failures[path]
            return httpx.Response(code, json=body)
        if path == "/rest/v1/reports":
            assert request.url.params["user_id"] == f"eq.{self.user_id}"
            identifier = request.url.params.get("id", "")[3:]
            rows = [self.rows[identifier]] if identifier in self.rows else []
            if not identifier:
                rows = [row for row in self.rows.values() if row["status"] != "deleted"]
            return httpx.Response(200, json=rows)
        if path.startswith("/storage/"):
            if request.method == "POST":
                key = path.removeprefix("/storage/v1/object/reports/")
                assert request.headers["x-upsert"] == "false"
                assert request.headers.get("cookie", "") == ""
                if self.storage_failure:
                    return httpx.Response(500, json={"message": "private provider detail"})
                if key in self.objects:
                    return httpx.Response(400, json={"statusCode": "409", "error": "Duplicate"})
                self.objects[key] = request.content, request.headers["content-type"]
                if self.commit_then_timeout:
                    raise httpx.ReadTimeout("private network detail", request=request)
                return httpx.Response(200, json={"Key": key})
            if request.method == "GET":
                key = path.removeprefix("/storage/v1/object/authenticated/reports/")
                if key not in self.objects:
                    return httpx.Response(400, json={"statusCode": "404"})
                content, content_type = self.objects[key]
                return httpx.Response(200, content=content, headers={"Content-Type": content_type})
            if request.method == "DELETE":
                if self.delete_failure:
                    return httpx.Response(503, json={"message": "private deletion detail"})
                for key in json.loads(request.content)["prefixes"]:
                    self.objects.pop(key, None)
                return httpx.Response(200, json=[])
        operation = path.rsplit("/", 1)[-1]
        body = json.loads(request.content)
        now = datetime.now(UTC).isoformat()
        if operation == "report_reserve":
            for row in self.rows.values():
                if row["idempotency_key"] == body["p_idempotency_key"]:
                    if row["status"] == "deleted" or row["original_filename"] != body["p_filename"]:
                        return self.conflict()
                    return httpx.Response(200, json=row)
            identifier = str(uuid4())
            extension = body["p_filename"].rsplit(".", 1)[-1].lower()
            row = {
                "id": identifier,
                "user_id": self.user_id,
                "idempotency_key": body["p_idempotency_key"],
                "storage_path": f"{self.user_id}/{identifier}/{uuid4()}.{extension}",
                "original_filename": body["p_filename"],
                "media_type": body["p_media_type"],
                "size_bytes": body["p_size_bytes"],
                "sha256": None,
                "status": "pending_upload",
                "lease_token": None,
                "upload_lease_expires_at": None,
                "error_category": None,
                "created_at": now,
                "updated_at": now,
            }
            self.rows[identifier] = row
            return httpx.Response(200, json=row)
        if operation == "report_cleanup_candidates":
            return httpx.Response(
                200,
                json=[
                    row for row in self.rows.values() if row["status"] in {"deleting", "deleted"}
                ][:10],
            )
        identifier = body["p_report_id"]
        if identifier not in self.rows:
            return self.conflict("report_not_found")
        row = self.rows[identifier]
        if operation == "report_begin_upload":
            if row["status"] in {"deleting", "deleted"} or (
                row["sha256"] is not None and row["sha256"] != body["p_sha256"]
            ):
                return self.conflict()
            if row["status"] == "uploaded":
                return httpx.Response(200, json=row)
            expiry = row["upload_lease_expires_at"]
            if isinstance(expiry, str) and datetime.fromisoformat(expiry) > datetime.now(UTC):
                return self.conflict()
            row.update(
                {
                    "status": "uploading",
                    "sha256": body["p_sha256"],
                    "lease_token": str(uuid4()),
                    "upload_lease_expires_at": (
                        datetime.now(UTC) + timedelta(seconds=120)
                    ).isoformat(),
                }
            )
        elif operation == "report_finish_upload":
            if self.finish_failure:
                return httpx.Response(503, json={"message": "private database detail"})
            assert row["storage_path"] in self.objects
            row.update(
                {
                    "status": "uploaded",
                    "lease_token": None,
                    "upload_lease_expires_at": None,
                    "error_category": None,
                }
            )
        elif operation == "report_fail_upload":
            if row["status"] != "deleting":
                row.update({"status": "upload_failed", "error_category": body["p_error_category"]})
        elif operation == "report_begin_delete":
            if row["status"] != "deleted":
                row["status"] = "deleting"
        elif operation == "report_finish_delete":
            assert row["storage_path"] not in self.objects
            row.update(
                {
                    "status": "deleted",
                    "original_filename": None,
                    "media_type": None,
                    "size_bytes": None,
                    "sha256": None,
                    "lease_token": None,
                    "upload_lease_expires_at": None,
                }
            )
        elif operation == "report_touch_cleanup":
            return httpx.Response(204)
        else:
            raise AssertionError(f"Unexpected isolated report operation {operation}")
        return httpx.Response(200, json=row)
