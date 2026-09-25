"""Versioned deterministic results; all measurement arithmetic is serialized as text."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Metric = Literal[
    "weight",
    "heart_rate",
    "hemoglobin",
    "tsh",
    "vitamin_d_unspecified",
    "glucose_unspecified",
    "crp",
]
Status = Literal["increasing", "decreasing", "stable", "insufficient_data"]
DecimalText = Annotated[str, Field(pattern=r"^-?[0-9]{1,45}(?:\.[0-9]{1,20})?$", max_length=67)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TrendQuery(Contract):
    unit: str = Field(min_length=1, max_length=60)
    window: Literal["7d", "30d"] = "7d"
    end: date | None = None


class Series(Contract):
    metric: Metric
    unit: str | None = Field(max_length=60)
    observation_count: int = Field(ge=1)
    supported_unit: bool


class CorrelationScope(Contract):
    status: Literal["unsupported_catalog"] = "unsupported_catalog"
    pairs: list[str] = Field(default_factory=list, max_length=0)
    minimum_pairs: Literal[14] = 14
    method: Literal["pearson_same_day_medians"] = "pearson_same_day_medians"
    rules_version: Literal["correlations-v1"] = "correlations-v1"


class TrendCatalog(Contract):
    timezone: str
    as_of: AwareDatetime
    period_end: date
    series: list[Series] = Field(max_length=50)
    correlations: CorrelationScope = Field(default_factory=CorrelationScope)
    rules_version: Literal["trends-v1"] = "trends-v1"


class Point(Contract):
    observation_id: UUID
    revision: int = Field(ge=1, le=100)
    source_type: Literal["report", "manual"]
    report_id: UUID | None
    candidate_id: UUID | None
    review_revision: int | None
    day: date
    measured_at: AwareDatetime | None
    raw_value: str = Field(max_length=100)
    value: DecimalText
    unit: str = Field(min_length=1, max_length=60)


class Period(Contract):
    start: date
    end: date
    sample_count: int = Field(ge=0, le=500)
    excluded_count: int = Field(ge=0, le=500)
    observed_days: int = Field(ge=0, le=30)
    coverage_percent: DecimalText | None
    first_day: date | None
    last_day: date | None
    median: DecimalText | None
    observed_range: DecimalText | None


class Change(Contract):
    absolute: DecimalText
    percent: DecimalText | None


class LatestComparison(Contract):
    latest: Point | None = None
    previous: Point | None = None
    change: Change | None = None
    reason: Literal[
        "no_dated_numeric_data", "fewer_than_two_days", "ambiguous_same_day", "available"
    ]


class TrendResult(Contract):
    rules_version: Literal["trends-v1"] = "trends-v1"
    metric: Metric
    unit: str
    window: Literal["7d", "30d"]
    timezone: str
    as_of: AwareDatetime
    partial_end_day: bool
    history_start: date
    mode: Literal["frequent", "occasional"]
    minimum_days: int | None
    current: Period
    previous: Period
    points: list[Point] = Field(max_length=500)
    unknown_date_count: int = Field(ge=0)
    excluded_history_count: int = Field(ge=0, le=500)
    latest_comparison: LatestComparison
    status: Status
    reason: Literal[
        "available",
        "no_numeric_observations",
        "current_coverage",
        "previous_coverage",
        "occasional_metric",
    ]
    change: Change | None
    tolerance: DecimalText | None
    pattern: Literal[
        "consistent_increase",
        "consistent_decrease",
        "stable_sequence",
        "no_clear_pattern",
        "insufficient_data",
        "not_applicable",
    ]
