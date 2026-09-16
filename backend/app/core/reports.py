"""Owned report repository and recoverable metadata/storage state transitions."""

import base64
import hashlib
import json
import logging
from datetime import UTC, datetime
from threading import BoundedSemaphore
from uuid import UUID

from pydantic import ValidationError

from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.provider import SupabaseGateway
from app.core.report_storage import ReportStorage, StoredFile
from app.core.report_validation import safe_filename, validate_file
from app.schemas.reports import (
    CleanupResult,
    DeleteResult,
    InternalReport,
    PublicReport,
    ReportList,
    ReportReserve,
)

logger = logging.getLogger("swasthyalens.reports")


def report_unavailable() -> ApiProblem:
    return ApiProblem(503, "service_unavailable", "The report service is temporarily unavailable.")


def not_found() -> ApiProblem:
    return ApiProblem(404, "report_not_found", "Report not found.")


class ReportsService:
    def __init__(self, gateway: SupabaseGateway, max_bytes: int) -> None:
        self.gateway = gateway
        self.max_bytes = max_bytes
        self.storage = ReportStorage(gateway, 5_242_880)
        self._download_slots = BoundedSemaphore(4)

    @staticmethod
    def _row(value: object, current: AuthenticatedRequest) -> InternalReport:
        try:
            row = InternalReport.model_validate(value)
            if row.user_id != current.identity.user_id:
                raise report_unavailable()
            return row
        except ValidationError:
            raise report_unavailable() from None

    @staticmethod
    def public(row: InternalReport) -> PublicReport:
        if row.status == "deleted":
            raise not_found()
        try:
            return PublicReport.model_validate(row.model_dump())
        except ValidationError:
            raise report_unavailable() from None

    def rpc(
        self, name: str, current: AuthenticatedRequest, payload: dict[str, object]
    ) -> InternalReport:
        value = self.gateway.request(
            "POST",
            f"/rest/v1/rpc/{name}",
            payload=payload,
            access_token=current.access_token,
            purpose="reports",
        )
        return self._row(value, current)

    def get(self, report_id: UUID, current: AuthenticatedRequest) -> InternalReport:
        result = self.gateway.request(
            "GET",
            "/rest/v1/reports",
            access_token=current.access_token,
            params={
                "id": f"eq.{report_id}",
                "user_id": f"eq.{current.identity.user_id}",
                "select": "*",
            },
            purpose="reports",
        )
        if not isinstance(result, list):
            raise report_unavailable()
        if not result:
            raise not_found()
        if len(result) != 1:
            raise report_unavailable()
        return self._row(result[0], current)

    def reserve(self, body: ReportReserve, current: AuthenticatedRequest) -> PublicReport:
        if body.size_bytes > self.max_bytes:
            raise ApiProblem(413, "file_too_large", "The selected file exceeds the upload limit.")
        row = self.rpc(
            "report_reserve",
            current,
            {
                "p_filename": body.original_filename,
                "p_media_type": body.media_type,
                "p_size_bytes": body.size_bytes,
                "p_idempotency_key": str(body.idempotency_key),
            },
        )
        return self.public(row)

    def list(self, current: AuthenticatedRequest, cursor: str | None) -> ReportList:
        params = {
            "user_id": f"eq.{current.identity.user_id}",
            "status": "neq.deleted",
            "select": "*",
            "order": "created_at.desc,id.desc",
            "limit": "21",
        }
        if cursor is not None:
            try:
                if not 1 <= len(cursor) <= 256 or not cursor.isascii():
                    raise ValueError
                decoded: object = json.loads(
                    base64.b64decode(cursor, altchars=b"-_", validate=True)
                )
                if not isinstance(decoded, list) or len(decoded) != 2:
                    raise ValueError
                timestamp, identifier = decoded
                if not isinstance(timestamp, str) or not isinstance(identifier, str):
                    raise ValueError
                date = datetime.fromisoformat(timestamp)
                parsed_id = UUID(identifier)
                if date.tzinfo is None or str(parsed_id) != identifier:
                    raise ValueError
                canonical = date.astimezone(UTC).isoformat()
                params["or"] = (
                    f"(created_at.lt.{canonical},and(created_at.eq.{canonical},id.lt.{parsed_id}))"
                )
            except (ValueError, TypeError, OverflowError):
                raise ApiProblem(
                    422, "validation_error", "The report list cursor is invalid."
                ) from None
        value = self.gateway.request(
            "GET",
            "/rest/v1/reports",
            access_token=current.access_token,
            params=params,
            purpose="reports",
        )
        if not isinstance(value, list) or len(value) > 21:
            raise report_unavailable()
        reports = [self.public(self._row(item, current)) for item in value[:20]]
        next_cursor = None
        if len(value) == 21:
            last = reports[-1]
            next_cursor = base64.urlsafe_b64encode(
                json.dumps(
                    [last.created_at.astimezone(UTC).isoformat(), str(last.id)],
                    separators=(",", ":"),
                ).encode()
            ).decode()
        return ReportList(reports=reports, next_cursor=next_cursor)

    def fail(self, row: InternalReport, current: AuthenticatedRequest, category: str) -> None:
        try:
            self.rpc(
                "report_fail_upload",
                current,
                {
                    "p_report_id": str(row.id),
                    "p_lease_token": str(row.lease_token) if row.lease_token else None,
                    "p_error_category": category,
                },
            )
        except ApiProblem:
            logger.warning("report_metadata_failure")

    def upload(
        self, row: InternalReport, current: AuthenticatedRequest, data: bytes, media_type: str
    ) -> PublicReport:
        logger.info("report_upload_started")
        try:
            if (
                row.original_filename is None
                or row.size_bytes is None
                or media_type != row.media_type
            ):
                raise ValueError
            validate_file(data, media_type, row.original_filename, row.size_bytes)
        except ValueError:
            logger.info("report_upload_validation_failure")
            self.fail(row, current, "invalid_file")
            raise ApiProblem(
                422, "invalid_file", "The file content, type or size is invalid."
            ) from None
        digest = hashlib.sha256(data).hexdigest()
        lease = self.rpc(
            "report_begin_upload", current, {"p_report_id": str(row.id), "p_sha256": digest}
        )
        if lease.status == "uploaded":
            return self.public(lease)
        if lease.status != "uploading" or lease.lease_token is None:
            raise report_unavailable()
        try:
            try:
                self.storage.upload(lease.storage_path, current.access_token, data, media_type)
            except ApiProblem as error:
                if error.status not in {409, 503}:
                    raise
                # Storage can commit before a timeout. Recover only an exact immutable match.
                stored = self.storage.download(lease.storage_path, current.access_token)
                if (
                    len(stored.data) != len(data)
                    or stored.media_type != media_type
                    or hashlib.sha256(stored.data).hexdigest() != digest
                ):
                    self.fail(lease, current, "integrity_mismatch")
                    raise ApiProblem(
                        409, "report_conflict", "The stored file does not match this upload."
                    ) from None
        except ApiProblem as error:
            logger.warning("report_storage_failure")
            self.fail(lease, current, "storage_unavailable")
            if error.status == 404:
                raise ApiProblem(
                    503,
                    "storage_unavailable",
                    "The upload could not be confirmed. Retry after the current attempt expires.",
                ) from None
            raise
        try:
            finished = self.rpc(
                "report_finish_upload",
                current,
                {
                    "p_report_id": str(row.id),
                    "p_lease_token": str(lease.lease_token),
                },
            )
        except ApiProblem:
            logger.warning("report_metadata_failure")
            self.fail(lease, current, "metadata_unavailable")
            raise
        logger.info("report_upload_success")
        return self.public(finished)

    def download(self, row: InternalReport, current: AuthenticatedRequest) -> StoredFile:
        if not self._download_slots.acquire(blocking=False):
            raise ApiProblem(429, "rate_limited", "Too many file downloads. Try again shortly.")
        try:
            return self._download(row, current)
        finally:
            self._download_slots.release()

    def _download(self, row: InternalReport, current: AuthenticatedRequest) -> StoredFile:
        if row.status != "uploaded":
            raise not_found()
        stored = self.storage.download(row.storage_path, current.access_token)
        if (
            len(stored.data) != row.size_bytes
            or stored.media_type != row.media_type
            or hashlib.sha256(stored.data).hexdigest() != row.sha256
        ):
            logger.warning("report_download_integrity_failure")
            raise report_unavailable()
        try:
            if row.original_filename is None or row.size_bytes is None:
                raise ValueError
            safe_filename(row.original_filename)
            validate_file(stored.data, stored.media_type, row.original_filename, row.size_bytes)
        except ValueError:
            logger.warning("report_download_validation_failure")
            raise report_unavailable() from None
        # Recheck the active-session/RLS-protected manifest after provider I/O;
        # a concurrent cancellation must not return an already buffered file.
        latest = self.get(row.id, current)
        if latest.status != "uploaded" or latest.sha256 != row.sha256:
            raise not_found()
        return stored

    def delete(self, report_id: UUID, current: AuthenticatedRequest) -> DeleteResult:
        row = self.rpc("report_begin_delete", current, {"p_report_id": str(report_id)})
        return self._delete(row, current)

    def _delete(self, row: InternalReport, current: AuthenticatedRequest) -> DeleteResult:
        if row.upload_lease_expires_at and row.upload_lease_expires_at > datetime.now(UTC):
            return DeleteResult(report_id=row.id, status="deleting")
        try:
            self.storage.delete(row.storage_path, current.access_token)
            finished = self.rpc("report_finish_delete", current, {"p_report_id": str(row.id)})
            if finished.status != "deleted":
                raise report_unavailable()
            return DeleteResult(report_id=row.id, status="deleted")
        except ApiProblem:
            logger.warning("report_delete_failure")
            return DeleteResult(report_id=row.id, status="deleting")

    def cleanup(self, current: AuthenticatedRequest) -> CleanupResult:
        result = self.gateway.request(
            "POST",
            "/rest/v1/rpc/report_cleanup_candidates",
            payload={"p_limit": 10},
            access_token=current.access_token,
            purpose="reports",
        )
        if not isinstance(result, list) or len(result) > 10:
            raise report_unavailable()
        cleaned, pending = 0, 0
        for item in result:
            row = self._row(item, current)
            if row.status not in {"deleting", "deleted"}:
                raise report_unavailable()
            status = self._delete(row, current)
            if status.status == "deleted":
                cleaned += 1
            else:
                pending += 1
            # Rotate failed attempts too so one unavailable object cannot starve the batch.
            self.gateway.request(
                "POST",
                "/rest/v1/rpc/report_touch_cleanup",
                payload={"p_report_id": str(row.id)},
                access_token=current.access_token,
                purpose="reports",
            )
        return CleanupResult(pending=pending, cleaned=cleaned)
