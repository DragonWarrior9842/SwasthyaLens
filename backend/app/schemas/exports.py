"""Direct exports have no retained artifact identity or caller-selected owner."""

import re
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.parameters import ParameterFields


class ExportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["csv", "json"]
    language: Literal["en", "hi"]
    date_from: date
    date_to: date
    include_unknown: bool = Field(strict=True, default=False)
    source_type: Literal["report", "manual"] | None = None
    report_id: UUID | None = None

    @field_validator("date_from", "date_to", mode="before")
    @classmethod
    def calendar_day(cls, value: object) -> object:
        if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
            raise ValueError("Use a calendar day")
        return value

    @model_validator(mode="after")
    def bounded(self) -> "ExportInput":
        if (
            not 0 <= (self.date_to - self.date_from).days <= 365
            or self.date_from.year < 1900
            or self.date_to.year > 2100
            or (self.report_id is not None and self.source_type == "manual")
        ):
            raise ValueError("Choose a supported source and at most 366 days")
        return self


class ExportRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    user_id: UUID
    source_type: Literal["report", "manual"]
    report_id: UUID | None
    revision: int = Field(strict=True, ge=1, le=100)
    status: Literal["active"]
    fields: ParameterFields
    measurement_date: date | None
    measured_at: AwareDatetime | None
    review_revision: int | None = Field(default=None, ge=1, le=20)
    review_action: Literal["confirmed", "corrected"] | None
    report_name: str | None = Field(max_length=200)
    report_recorded_at: AwareDatetime | None
    page_number: int | None = Field(ge=1, le=20)
    source_method: Literal["native_text", "ocr"] | None

    @model_validator(mode="after")
    def provenance(self) -> "ExportRow":
        provenance = (
            self.report_id,
            self.review_revision,
            self.review_action,
            self.report_name,
            self.report_recorded_at,
            self.page_number,
            self.source_method,
        )
        if self.source_type == "report":
            if any(v is None for v in provenance) or self.measured_at is not None:
                raise ValueError("Missing report provenance")
        elif (
            any(v is not None for v in provenance)
            or self.measured_at is None
            or self.measurement_date is not None
        ):
            raise ValueError("Invalid manual provenance")
        if self.fields.raw_value is None or not self.fields.raw_value.strip():
            raise ValueError("Missing published value")
        return self


class ExportContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    as_of: AwareDatetime
    items: list[ExportRow] = Field(max_length=200)
