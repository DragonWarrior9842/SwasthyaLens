"""Deterministic, invented facts only. No provider connection exists in this mock."""

from uuid import uuid4

from app.core.explanation_context import allowed_codes, required_notes
from app.core.explanation_provider import GenerationPermit, GenerationResult
from app.core.parameter_parser import fields
from app.schemas.explanations import ModelExplanation, ModelFact, ModelItem, SourceEvidence
from app.schemas.parameters import RawFields
from tests.parameter_fixtures import ROWS


def synthetic_sources() -> list[SourceEvidence]:
    result = []
    for label, value, unit, reference, kind, _ in ROWS:
        if kind == "missing":
            continue
        result.append(
            SourceEvidence(
                observation_id=uuid4(),
                revision=1,
                candidate_id=uuid4(),
                review_revision=1,
                source_run_id=uuid4(),
                parameter_run_id=uuid4(),
                page_number=1,
                source_start=0,
                source_end=20,
                fields=fields(
                    RawFields(
                        original_label=label,
                        raw_value=value,
                        original_unit=unit or None,
                        raw_reference=reference or None,
                    )
                ),
            )
        )
    return result


def mock_output(context: list[ModelFact]) -> ModelExplanation:
    return ModelExplanation(
        scope="educational",
        limitation="selected_findings_only",
        follow_up="professional_context",
        items=[
            ModelItem(fact=f, explanation_code=allowed_codes(f)[0], notes=required_notes(f))
            for f in context
        ],
    )


class MockExplanationProvider:
    name = "mock-test"
    available = True

    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self, context: list[ModelFact], permit: GenerationPermit
    ) -> GenerationResult:
        self.calls += 1
        return GenerationResult(mock_output(context), 0, 0)
