"""Further-derived candidates; exact decimal strings, never observations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RawFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    original_label: str = Field(min_length=1, max_length=160)
    raw_value: str | None = Field(default=None, max_length=100)
    original_unit: str | None = Field(default=None, max_length=60)
    raw_reference: str | None = Field(default=None, max_length=160)

    @field_validator("original_label")
    @classmethod
    def nonblank_label(cls, value: str) -> str:
        if not value.strip() or any(ord(c) < 32 and c != "\n" for c in value):
            raise ValueError("A visible label is required")
        return value


class ParameterFields(RawFields):
    parsing_version: str | None = None
    alias_version: str | None = None
    canonical_metric: str | None = None
    numeric_value: str | None = None
    comparator: Literal["<", ">", "<=", ">=", "=", "≤", "≥"] | None = None
    value_kind: Literal[
        "numeric", "qualitative", "titre", "interval", "ordinal", "unparsed", "missing"
    ]
    qualitative_result: str | None = None
    reference_low: str | None = None
    reference_high: str | None = None
    reference_low_inclusive: bool | None = None
    reference_high_inclusive: bool | None = None
    source_flag: str | None = None
    calculated_range_status: Literal["unknown"] = "unknown"


class CandidateContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fields: ParameterFields
    page_number: int = Field(ge=1, le=20)
    source_text: str = Field(min_length=1, max_length=1024)
    source_start: int = Field(ge=0, le=20000)
    source_end: int = Field(ge=1, le=20000)
    span_indices: list[int] = Field(max_length=200)
    source_method: Literal["native_text", "ocr"]
    ocr_confidence: float | None = Field(default=None, ge=0, le=100)
    certainty: Literal["needs_review"] = "needs_review"
    warnings: list[str] = Field(max_length=12)


class ParameterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_run_id: UUID
    idempotency_key: UUID


class ParameterRun(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    report_id: UUID
    source_run_id: UUID
    status: Literal["processing", "completed", "failed"]
    attempt: int = Field(ge=1, le=3)
    extractor_version: str
    rules_version: str
    created_at: datetime
    finished_at: datetime | None
    deadline_at: datetime
    error_category: Literal["interrupted", "parser_failure", "resource_limit"] | None
    candidate_count: int | None = Field(default=None, ge=0, le=200)
    warnings: list[str]


class ParameterHistory(BaseModel):
    runs: list[ParameterRun]


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID
    expected_revision: int = Field(ge=0, le=20)
    action: Literal["confirmed", "corrected", "rejected"]
    correction: RawFields | None = None

    @model_validator(mode="after")
    def correction_required(self) -> "ReviewInput":
        if (self.action == "corrected") != (self.correction is not None):
            raise ValueError("Only corrections require fields")
        return self


class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    revision: int = Field(ge=1, le=20)
    action: Literal["confirmed", "corrected", "rejected"]
    fields: ParameterFields
    actor_id: UUID
    created_at: datetime


class ParameterCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    run_id: UUID
    ordinal: int
    content: CandidateContent
    reviews: list[Review] = Field(max_length=20)


class ParameterResult(BaseModel):
    run: ParameterRun
    candidates: list[ParameterCandidate] = Field(max_length=200)
