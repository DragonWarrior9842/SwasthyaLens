"""Personal history contracts: exact strings, explicit dates, immutable revisions."""

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.parameters import CandidateContent, ParameterFields


class PublishInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(strict=True, ge=1, le=20)
    measurement_date: date | None = None

    @field_validator("measurement_date", mode="before")
    @classmethod
    def day_only(cls, value: object) -> object:
        if value is not None and (
            not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None
        ):
            raise ValueError("Use a calendar day")
        return value

    @field_validator("measurement_date")
    @classmethod
    def supported_day(cls, value: date | None) -> date | None:
        if value is not None and not 1900 <= value.year <= 2100:
            raise ValueError("Unsupported date")
        return value


class ManualInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    metric: Literal["weight", "heart_rate"]
    raw_value: str = Field(min_length=1, max_length=12)
    unit: Literal["kg", "bpm"]
    measured_at: AwareDatetime

    @field_validator("idempotency_key")
    @classmethod
    def nonzero(cls, value: UUID) -> UUID:
        if not value.int:
            raise ValueError("A request key is required")
        return value

    @field_validator("measured_at", mode="before")
    @classmethod
    def timestamp_text(cls, value: object) -> object:
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("Use an ISO timestamp with an offset")
        return value

    @field_validator("measured_at")
    @classmethod
    def supported_instant(cls, value: datetime) -> datetime:
        value = value.astimezone(UTC)
        if not 1900 <= value.year <= 2100:
            raise ValueError("Unsupported date")
        return value

    @model_validator(mode="after")
    def metric_value(self) -> "ManualInput":
        pattern = r"[0-9]{1,4}(?:\.[0-9]{1,3})?" if self.metric == "weight" else r"[0-9]{1,4}"
        if self.unit != ("kg" if self.metric == "weight" else "bpm") or not re.fullmatch(
            pattern, self.raw_value
        ):
            raise ValueError("Unsupported metric, value or unit")
        if not Decimal(0) < Decimal(self.raw_value) < Decimal(10000):
            raise ValueError("Value exceeds technical bounds")
        return self


class ManualEdit(ManualInput):
    expected_revision: int = Field(strict=True, ge=1, le=100)


class DeleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(strict=True, ge=1, le=100)


class ObservationRevision(BaseModel):
    revision: int = Field(ge=1, le=100)
    status: Literal["active", "superseded", "invalidated"]
    fields: ParameterFields
    catalog_version: Literal["observations-v1"]
    measurement_date: date | None
    measured_at: AwareDatetime | None
    candidate_id: UUID | None
    review_revision: int | None = Field(ge=1, le=20)
    created_at: AwareDatetime
    status_changed_at: AwareDatetime


class ObservationEvidence(BaseModel):
    report_name: str = Field(min_length=1, max_length=200)
    report_created_at: AwareDatetime
    source_run_id: UUID
    parameter_run_id: UUID
    content: CandidateContent


class Observation(BaseModel):
    id: UUID
    source_type: Literal["report", "manual"]
    report_id: UUID | None
    candidate_id: UUID | None
    created_at: AwareDatetime
    current: ObservationRevision
    revisions: list[ObservationRevision] = Field(max_length=100)
    evidence: ObservationEvidence | None

    @model_validator(mode="after")
    def coherent(self) -> "Observation":
        revisions = self.revisions or [self.current]
        if self.revisions and self.revisions[0] != self.current:
            raise ValueError("Inconsistent latest revision")
        if len({r.revision for r in revisions}) != len(revisions):
            raise ValueError("Duplicate revision")
        for revision in revisions:
            if self.source_type == "report":
                if (
                    self.report_id is None
                    or self.candidate_id is None
                    or revision.candidate_id != self.candidate_id
                    or revision.review_revision is None
                    or revision.measured_at is not None
                ):
                    raise ValueError("Inconsistent report provenance")
            elif (
                self.report_id is not None
                or self.candidate_id is not None
                or revision.candidate_id is not None
                or revision.review_revision is not None
                or revision.measured_at is None
                or revision.measurement_date is not None
                or self.evidence is not None
            ):
                raise ValueError("Inconsistent manual provenance")
        return self


class ObservationPage(BaseModel):
    items: list[Observation] = Field(max_length=20)
    next_offset: int | None


class RecentReport(BaseModel):
    id: UUID
    original_filename: str
    created_at: AwareDatetime


class Dashboard(BaseModel):
    uploaded_reports: int = Field(ge=0)
    reviewed_parameters: int = Field(ge=0)
    active_observations: int = Field(ge=0)
    observations: list[Observation] = Field(max_length=5)
    reports: list[RecentReport] = Field(max_length=3)
