"""Synthetic longitudinal observations only; no external I/O."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.core.parameter_parser import fields
from app.schemas.observations import Observation
from app.schemas.parameters import RawFields


def observation(
    value: str,
    day: str | None,
    *,
    metric: str = "weight",
    unit: str = "kg",
    instant: str | None = None,
    status: str = "active",
) -> Observation:
    manual = metric in ("weight", "heart_rate")
    candidate = None if manual else uuid4()
    report = None if manual else uuid4()
    parsed = fields(RawFields(original_label="Synthetic", raw_value=value, original_unit=unit))
    parsed.canonical_metric = metric
    v = dict(
        revision=1,
        status=status,
        fields=parsed,
        catalog_version="observations-v1",
        measurement_date=None if manual else day,
        measured_at=(instant or f"{day}T12:00:00Z") if manual else None,
        candidate_id=candidate,
        review_revision=None if manual else 1,
        created_at=datetime(2026, 9, 25, tzinfo=UTC),
        status_changed_at=datetime(2026, 9, 25, tzinfo=UTC),
    )
    return Observation.model_validate(
        dict(
            id=uuid4(),
            source_type="manual" if manual else "report",
            report_id=report,
            candidate_id=candidate,
            created_at=datetime(2026, 9, 25, tzinfo=UTC),
            current=v,
            revisions=[],
            evidence=None,
        )
    )


END = date(2026, 4, 10)
AS_OF = datetime(2026, 4, 11, tzinfo=UTC)
