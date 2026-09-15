"""Private report endpoints preserve the BFF session and signed CSRF boundary."""

import asyncio
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from app.api.dependencies import Auth, CurrentUser, protect_write
from app.core.errors import ApiProblem
from app.core.report_validation import ALLOWED_MEDIA_TYPES
from app.core.reports import ReportsService, report_unavailable
from app.schemas.accounts import EmptyInput
from app.schemas.reports import (
    CleanupResult,
    DeleteResult,
    PublicReport,
    ReportConfig,
    ReportList,
    ReportReserve,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


def report_service(request: Request) -> ReportsService:
    service: object = getattr(request.app.state, "reports_service", None)
    if not isinstance(service, ReportsService):
        raise report_unavailable()
    return service


Reports = Annotated[ReportsService, Depends(report_service)]


def protect_file_write(request: Request, auth: Auth) -> None:
    auth.csrf.validate(request, media_types=ALLOWED_MEDIA_TYPES)


def limit_report(request: Request, auth: Auth, current: CurrentUser) -> None:
    # The verified identity bounds resources per account; caller forwarding headers are ignored.
    auth.limiter.check(f"reports:{current.identity.user_id}:{request.method}", limit=60)


@router.get("/config", response_model=ReportConfig)
def report_config(current: CurrentUser, service: Reports) -> ReportConfig:
    return ReportConfig(
        max_upload_bytes=service.max_bytes,
        allowed_media_types=["application/pdf", "image/jpeg", "image/png"],
    )


@router.post("/cleanup", response_model=CleanupResult, dependencies=[Depends(protect_write)])
def cleanup_reports(
    body: EmptyInput, current: CurrentUser, auth: Auth, service: Reports
) -> CleanupResult:
    auth.limiter.check(f"reports:{current.identity.user_id}:cleanup", limit=5)
    return service.cleanup(current)


@router.post(
    "",
    response_model=PublicReport,
    status_code=201,
    dependencies=[Depends(protect_write), Depends(limit_report)],
)
def reserve_report(body: ReportReserve, current: CurrentUser, service: Reports) -> PublicReport:
    return service.reserve(body, current)


@router.get("", response_model=ReportList, dependencies=[Depends(limit_report)])
def list_reports(
    current: CurrentUser,
    service: Reports,
    cursor: Annotated[str | None, Query(max_length=256)] = None,
) -> ReportList:
    return service.list(current, cursor)


@router.get("/{report_id}", response_model=PublicReport, dependencies=[Depends(limit_report)])
def get_report(report_id: UUID, current: CurrentUser, service: Reports) -> PublicReport:
    return service.public(service.get(report_id, current))


@router.put(
    "/{report_id}/file",
    response_model=PublicReport,
    dependencies=[Depends(protect_file_write), Depends(limit_report)],
)
async def upload_report(
    report_id: UUID,
    request: Request,
    current: CurrentUser,
    service: Reports,
) -> PublicReport:
    # Request is deliberately read manually after all auth/CSRF dependencies have passed.
    row = await run_in_threadpool(service.get, report_id, current)
    if row.status in {"deleting", "deleted"}:
        raise ApiProblem(404, "report_not_found", "Report not found.")
    media_type = request.headers.get("content-type", "").strip().lower()
    if media_type != row.media_type:
        raise ApiProblem(422, "invalid_file", "The file MIME type must match the reserved report.")
    slots: asyncio.Semaphore = request.app.state.report_upload_slots
    try:
        await asyncio.wait_for(slots.acquire(), timeout=0.1)
    except TimeoutError:
        raise ApiProblem(429, "rate_limited", "Too many file uploads. Try again shortly.") from None
    try:
        data = bytearray()
        try:
            async for chunk in request.stream():
                if len(data) + len(chunk) > service.max_bytes:
                    raise ApiProblem(413, "file_too_large", "The file exceeds the upload limit.")
                data.extend(chunk)
        except ClientDisconnect:
            await run_in_threadpool(service.fail, row, current, "upload_interrupted")
            raise ApiProblem(400, "upload_interrupted", "The upload was interrupted.") from None
        return await run_in_threadpool(service.upload, row, current, bytes(data), media_type)
    finally:
        slots.release()


@router.get("/{report_id}/file", dependencies=[Depends(limit_report)])
def download_report(report_id: UUID, current: CurrentUser, service: Reports) -> Response:
    row = service.get(report_id, current)
    stored = service.download(row, current)
    filename = quote(row.original_filename or "report", safe="")
    return Response(
        content=stored.data,
        media_type=stored.media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"report\"; filename*=UTF-8''{filename}",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )


@router.delete(
    "/{report_id}",
    response_model=DeleteResult,
    dependencies=[Depends(protect_write), Depends(limit_report)],
)
def delete_report(
    report_id: UUID,
    body: EmptyInput,
    response: Response,
    current: CurrentUser,
    service: Reports,
) -> DeleteResult:
    result = service.delete(report_id, current)
    response.status_code = 200 if result.status == "deleted" else 202
    return result
