"""Bounded source facts and a closed educational language contract."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.parameters import ParameterFields


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class ExplanationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    idempotency_key: UUID
    consent: Literal[True]

    @field_validator("consent", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Explicit consent is required")
        return value

    @field_validator("idempotency_key")
    @classmethod
    def nonzero(cls, value: UUID) -> UUID:
        if not value.int:
            raise ValueError("A request key is required")
        return value


class SourceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    observation_id: UUID
    revision: int = Field(ge=1, le=100)
    candidate_id: UUID
    review_revision: int = Field(ge=1, le=20)
    source_run_id: UUID
    parameter_run_id: UUID
    page_number: int = Field(ge=1, le=20)
    source_start: int = Field(ge=0, le=20000)
    source_end: int = Field(ge=1, le=20000)
    fields: ParameterFields


class ModelFact(StrictModel):
    evidence_id: str = Field(pattern=r"^e(?:[1-9]|1[0-9]|20)$")
    label: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=100)
    unit: str | None = Field(max_length=60)
    reference: str | None = Field(max_length=160)
    source_flag: str | None = Field(max_length=100)
    value_kind: Literal["numeric", "qualitative", "titre", "interval", "ordinal", "unparsed"]
    comparator: Literal["<", ">", "<=", ">=", "=", "≤", "≥"] | None
    canonical_metric: str | None = Field(max_length=80)
    page_number: int = Field(ge=1, le=20)
    calculated_range_status: Literal["unknown"]


ExplanationCode = Literal[
    "hemoglobin_brief",
    "hemoglobin_plain",
    "tsh_brief",
    "tsh_plain",
    "vitamin_d_brief",
    "vitamin_d_plain",
    "glucose_brief",
    "glucose_plain",
    "crp_brief",
    "crp_plain",
    "unmapped",
]
NoteCode = Literal[
    "range_supplied",
    "range_missing",
    "unit_missing",
    "flag_supplied",
    "comparison_unknown",
    "comparator",
    "qualitative",
    "titre",
    "unparsed",
]


class ModelItem(StrictModel):
    fact: ModelFact
    explanation_code: ExplanationCode
    notes: list[NoteCode] = Field(min_length=1, max_length=8)


class ModelExplanation(StrictModel):
    scope: Literal["educational"]
    items: list[ModelItem] = Field(min_length=1, max_length=20)
    limitation: Literal["selected_findings_only"]
    follow_up: Literal["professional_context"]


class ExplainedItem(BaseModel):
    fact: ModelFact
    source: SourceEvidence
    explanation: str
    notes: list[str]
    educational_source_url: str | None


class ExplanationRecord(BaseModel):
    id: UUID
    report_id: UUID
    status: Literal["generating", "ready", "failed", "stale"]
    provider: Literal["openai", "mock-test", "gemini"]
    model: str
    prompt_version: str
    schema_version: str
    catalog_version: str
    created_at: datetime
    expires_at: datetime
    finished_at: datetime | None
    error_category: str | None
    items: list[ExplainedItem]
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None


class ExplanationView(BaseModel):
    report_id: UUID
    eligible_count: int
    evaluation_enrolled: bool
    provider: Literal["openai", "mock-test", "gemini"]
    provider_available: bool
    record: ExplanationRecord | None
