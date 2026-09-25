"""Closed assistant output. The model selects wording; the server supplies all facts."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.schemas.explanations import StrictModel
from app.schemas.parameters import ParameterFields
from app.schemas.trends import Change, Metric, Period, Status

Code = Literal[
    "sources",
    "increasing",
    "decreasing",
    "stable",
    "insufficient_data",
    "clarify",
    "no_data",
    "unsupported_units",
    "unsupported_correlation",
    "safety",
    "emergency",
]


class NewConversation(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    idempotency_key: UUID

    @field_validator("idempotency_key")
    @classmethod
    def nonzero(cls, value: UUID) -> UUID:
        if not value.int:
            raise ValueError("A request key is required")
        return value


class SendMessage(NewConversation):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def visible(cls, value: str) -> str:
        if not value.strip() or any(ord(c) < 32 and c not in "\n\t" for c in value):
            raise ValueError("Enter a question of at most 2000 characters")
        return value


class AssistantFact(StrictModel):
    evidence_id: str = Field(pattern=r"^e(?:[1-9]|1[0-9]|20)$")
    label: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=100)
    unit: str | None = Field(max_length=60)
    reference: str | None = Field(max_length=160)
    source_flag: str | None = Field(max_length=100)
    value_kind: str = Field(max_length=20)
    comparator: str | None = Field(max_length=2)
    canonical_metric: str | None = Field(max_length=80)
    measurement_date: str | None
    measured_at: str | None
    source_type: Literal["report", "manual"]
    page_number: int | None = Field(ge=1, le=20)
    calculated_range_status: Literal["unknown"] = "unknown"


class Calculation(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    evidence_id: Literal["t1"] = "t1"
    rules_version: Literal["trends-v1"] = "trends-v1"
    metric: Metric
    unit: str
    window: Literal["7d", "30d"]
    timezone: str
    as_of: AwareDatetime
    history_start: date
    status: Status
    reason: str
    current: Period
    previous: Period
    change: Change | None
    minimum_days: int | None
    unknown_date_count: int
    excluded_history_count: int
    latest_reason: str
    latest_value: str | None
    latest_day: date | None
    previous_value: str | None
    previous_day: date | None
    latest_change: Change | None


class ModelAnswer(StrictModel):
    scope: Literal["educational"]
    evidence_ids: list[str] = Field(max_length=21)
    explanation_code: Code
    limitation: Literal["bounded_current_evidence_not_diagnosis"]
    follow_up: Literal["professional_context"]


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    observation_id: UUID
    revision: int = Field(ge=1, le=100)
    report_id: UUID | None
    candidate_id: UUID | None
    review_revision: int | None
    page_number: int | None
    fields: ParameterFields


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    selection: Literal["latest_uploaded_report", "recent_metric", "period", "none"]
    choice: ModelAnswer
    facts: list[AssistantFact] = Field(max_length=20)
    calculation: Calculation | None
    sources: list[Provenance] = Field(max_length=20)
    text: str = Field(max_length=1000)


class Conversation(BaseModel):
    id: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime


class Message(BaseModel):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    status: Literal["received", "generating", "ready", "failed", "stale"]
    content: str | None
    answer: Answer | None
    error_category: str | None
    provider: Literal["gemini", "mock-test", "rules"] | None
    model: Literal["gemini-3.8-flash", "deterministic-test", "rules-v1"] | None
    prompt_version: Literal["assistant-evidence-v1"]
    schema_version: Literal["assistant-closed-v1"]
    created_at: AwareDatetime


class ConversationList(BaseModel):
    conversations: list[Conversation] = Field(max_length=20)
    provider_available: bool = False


class Thread(BaseModel):
    conversation: Conversation
    messages: list[Message] = Field(max_length=50)
    provider_available: bool = False
