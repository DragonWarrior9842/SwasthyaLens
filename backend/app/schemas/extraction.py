"""Source text only. No medical interpretation fields belong in this contract."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Failure = Literal[
    "corrupt_document",
    "encrypted_document",
    "unsupported_document",
    "page_limit_exceeded",
    "resource_limit_exceeded",
    "extractor_failure",
    "ocr_unavailable",
    "ocr_failure",
    "timeout",
    "interrupted",
    "source_unavailable",
]


class Span(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    text: str = Field(max_length=20000)
    bbox: tuple[float, float, float, float]
    confidence: float | None = Field(default=None, ge=0, le=100)


class ExtractedPage(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    page_number: int = Field(ge=1, le=20)
    text: str = Field(max_length=20000)
    method: Literal["native_text", "ocr"]
    width: float = Field(gt=0, le=10000)
    height: float = Field(gt=0, le=10000)
    coordinate_system: Literal["pdf_points_bottom_left", "oriented_pixels_top_left"]
    rotation: int = Field(default=0, ge=0, le=270, multiple_of=90)
    confidence: float | None = Field(default=None, ge=0, le=100)
    warnings: list[Literal["no_text", "orientation_uncertain", "layout_requires_review"]]
    spans: list[Span] = Field(max_length=2000)


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    processor: str = Field(max_length=500)
    configuration: dict[str, str | int] = Field(max_length=20)
    pages: list[ExtractedPage] = Field(min_length=1, max_length=20)


class ProcessInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: UUID


class ProcessingRun(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    report_id: UUID
    status: Literal["queued", "processing", "completed", "failed"]
    attempt: int = Field(ge=1, le=3)
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    deadline_at: datetime
    error_category: Failure | None
    processor: str | None
    page_count: int | None


class ProcessingHistory(BaseModel):
    runs: list[ProcessingRun]


class ExtractionResult(BaseModel):
    run: ProcessingRun
    pages: list[ExtractedPage]
