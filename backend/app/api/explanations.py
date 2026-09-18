from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import CurrentUser, protect_write
from app.api.reports import limit_report
from app.core.explanations import ExplanationService, unavailable
from app.schemas.explanations import ExplanationInput, ExplanationView

router = APIRouter(tags=["Report explanations"], dependencies=[Depends(limit_report)])


def service(request: Request) -> ExplanationService:
    value = getattr(request.app.state, "explanation_service", None)
    if not isinstance(value, ExplanationService):
        raise unavailable()
    return value


Explanations = Annotated[ExplanationService, Depends(service)]


@router.get("/reports/{report_id}/explanations", response_model=ExplanationView)
def state(report_id: UUID, current: CurrentUser, explanations: Explanations) -> ExplanationView:
    return explanations.get(report_id, current)


@router.get("/reports/{report_id}/explanations/{identifier}", response_model=ExplanationView)
def detail(
    report_id: UUID, identifier: UUID, current: CurrentUser, explanations: Explanations
) -> ExplanationView:
    return explanations.get(report_id, current, identifier)


@router.post(
    "/reports/{report_id}/explanations",
    response_model=ExplanationView,
    dependencies=[Depends(protect_write)],
)
async def generate(
    report_id: UUID, body: ExplanationInput, current: CurrentUser, explanations: Explanations
) -> ExplanationView:
    return await explanations.generate(report_id, body, current)
