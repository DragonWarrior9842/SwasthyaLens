"""Report metadata contracts separate public fields from storage/lease internals."""

import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.report_validation import MEDIA_EXTENSIONS, safe_filename
from app.schemas.accounts import InputModel

MediaType = Literal["application/pdf", "image/jpeg", "image/png"]
ReportStatus = Literal["pending_upload", "uploading", "uploaded", "upload_failed", "deleting"]


class ReportReserve(InputModel):
    original_filename: str
    media_type: MediaType
    size_bytes: Annotated[int, Field(ge=1, le=5_242_880)]
    idempotency_key: UUID

    @field_validator("original_filename")
    @classmethod
    def filename(cls, value: str) -> str:
        return safe_filename(value)

    @field_validator("idempotency_key", mode="before")
    @classmethod
    def key(cls, value: object) -> UUID:
        if not isinstance(value, str):
            raise ValueError("Use a canonical UUID idempotency key")
        parsed = UUID(value)
        if str(parsed) != value or not parsed.int:
            raise ValueError("Use a canonical UUID idempotency key")
        return parsed

    @model_validator(mode="after")
    def media_agrees(self) -> "ReportReserve":
        if (
            self.original_filename.rsplit(".", 1)[-1].lower()
            not in MEDIA_EXTENSIONS[self.media_type]
        ):
            raise ValueError("Filename and MIME type must agree")
        return self


class PublicReport(BaseModel):
    id: UUID
    original_filename: str
    media_type: MediaType
    size_bytes: int
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    error_category: str | None


class InternalReport(BaseModel):
    id: UUID
    user_id: UUID
    idempotency_key: UUID
    storage_path: str
    original_filename: str | None
    media_type: MediaType | None
    size_bytes: int | None
    sha256: str | None
    status: Literal[
        "pending_upload", "uploading", "uploaded", "upload_failed", "deleting", "deleted"
    ]
    lease_token: UUID | None
    upload_lease_expires_at: datetime | None
    error_category: str | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def safe_storage_key(self) -> "InternalReport":
        if (
            re.fullmatch(
                re.escape(f"{self.user_id}/{self.id}/")
                + r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(pdf|jpg|jpeg|png)",
                self.storage_path,
            )
            is None
        ):
            raise ValueError("Unexpected storage key")
        return self


class ReportList(BaseModel):
    reports: list[PublicReport]
    next_cursor: str | None


class ReportConfig(BaseModel):
    max_upload_bytes: int
    allowed_media_types: list[MediaType]


class DeleteResult(BaseModel):
    report_id: UUID
    status: Literal["deleting", "deleted"]


class CleanupResult(BaseModel):
    pending: int
    cleaned: int
