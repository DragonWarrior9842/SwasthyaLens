"""Generic operational event contracts; no medical payload or translated prose."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Notification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    user_id: UUID
    report_id: UUID
    event_type: Literal[
        "upload_completed",
        "extraction_completed",
        "extraction_failed",
        "parameters_ready",
        "parameters_failed",
    ]
    created_at: AwareDatetime
    read_at: AwareDatetime | None

    @model_validator(mode="after")
    def read_time(self) -> "Notification":
        if self.read_at and self.read_at < self.created_at:
            raise ValueError("Invalid read time")
        return self


class NotificationPage(BaseModel):
    user_id: UUID
    items: list[Notification] = Field(max_length=20)
    unread_count: int = Field(strict=True, ge=0, le=100)
    next_offset: int | None = Field(default=None, ge=0, le=100)


class NotificationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    offset: int = Field(default=0, ge=0, le=100)
