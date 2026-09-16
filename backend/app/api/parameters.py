from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import Auth, CurrentUser, protect_write
from app.api.reports import limit_report
from app.core.parameters import ParameterService
from app.core.reports import report_unavailable
from app.schemas.parameters import (
    ParameterHistory,
    ParameterInput,
    ParameterResult,
    ParameterRun,
    Review,
    ReviewInput,
)

router = APIRouter(prefix="/reports", tags=["Parameter candidates"])


def service(request: Request) -> ParameterService:
    value = getattr(request.app.state, "parameter_service", None)
    if not isinstance(value, ParameterService):
        raise report_unavailable()
    return value


Parameters = Annotated[ParameterService, Depends(service)]


@router.post(
    "/{report_id}/extract-parameters",
    response_model=ParameterRun,
    dependencies=[Depends(protect_write), Depends(limit_report)],
)
def extract(
    report_id: UUID, body: ParameterInput, current: CurrentUser, auth: Auth, parameters: Parameters
) -> ParameterRun:
    auth.limiter.check(f"parameters:{current.identity.user_id}", limit=10)
    return parameters.request(report_id, body, current)


@router.get(
    "/{report_id}/parameter-processing",
    response_model=ParameterHistory,
    dependencies=[Depends(limit_report)],
)
def history(report_id: UUID, current: CurrentUser, parameters: Parameters) -> ParameterHistory:
    return parameters.history(report_id, current)


@router.get(
    "/{report_id}/parameters", response_model=ParameterResult, dependencies=[Depends(limit_report)]
)
def result(
    report_id: UUID, current: CurrentUser, parameters: Parameters, run_id: UUID | None = None
) -> ParameterResult:
    return parameters.result(report_id, run_id, current)


@router.patch(
    "/{report_id}/parameters/{candidate_id}",
    response_model=Review,
    dependencies=[Depends(protect_write), Depends(limit_report)],
)
def review(
    report_id: UUID,
    candidate_id: UUID,
    body: ReviewInput,
    current: CurrentUser,
    parameters: Parameters,
) -> Review:
    return parameters.review(report_id, candidate_id, body, current)


@router.get(
    "/{report_id}/parameters/{candidate_id}/revisions",
    response_model=list[Review],
    dependencies=[Depends(limit_report)],
)
def revisions(
    report_id: UUID, candidate_id: UUID, current: CurrentUser, parameters: Parameters
) -> list[Review]:
    return parameters.reviews(report_id, candidate_id, current)
