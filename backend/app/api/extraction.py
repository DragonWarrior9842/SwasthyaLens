"""Authenticated processing operations; every write retains Origin/CSRF checks."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import Auth, CurrentUser, protect_write
from app.api.reports import limit_report
from app.core.extraction import ExtractionService
from app.core.reports import report_unavailable
from app.schemas.extraction import ExtractionResult, ProcessingHistory, ProcessingRun, ProcessInput

router = APIRouter(prefix="/reports", tags=["Text extraction"])


def service(request: Request) -> ExtractionService:
    result = getattr(request.app.state, "extraction_service", None)
    if not isinstance(result, ExtractionService):
        raise report_unavailable()
    return result


Extraction = Annotated[ExtractionService, Depends(service)]


@router.post(
    "/{report_id}/process",
    response_model=ProcessingRun,
    status_code=202,
    dependencies=[Depends(protect_write), Depends(limit_report)],
)
def process(
    report_id: UUID, body: ProcessInput, current: CurrentUser, auth: Auth, extraction: Extraction
) -> ProcessingRun:
    auth.limiter.check(f"processing:{current.identity.user_id}", limit=10)
    return extraction.request(report_id, body.idempotency_key, current)


@router.get(
    "/{report_id}/processing",
    response_model=ProcessingHistory,
    dependencies=[Depends(limit_report)],
)
def history(report_id: UUID, current: CurrentUser, extraction: Extraction) -> ProcessingHistory:
    return extraction.history(report_id, current)


@router.get(
    "/{report_id}/extraction", response_model=ExtractionResult, dependencies=[Depends(limit_report)]
)
def result(
    report_id: UUID, current: CurrentUser, extraction: Extraction, run_id: UUID | None = None
) -> ExtractionResult:
    return extraction.result(report_id, current, run_id)
