"""Explicit CSRF-protected private download, bounded even during slow upstream I/O."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import Auth, CurrentUser, protect_write
from app.api.observations import Observations
from app.core.errors import ApiProblem
from app.core.exports import ExportService
from app.schemas.accounts import EmptyInput
from app.schemas.exports import ExportInput

router = APIRouter(prefix="/exports", tags=["Private exports"])


@router.post("", dependencies=[Depends(protect_write)])
async def export(
    body: ExportInput,
    current: CurrentUser,
    auth: Auth,
    observations: Observations,
    request: Request,
    query: Annotated[EmptyInput, Query()],
) -> Response:
    auth.limiter.check(f"exports:{current.identity.user_id}", limit=6)
    slots: asyncio.Semaphore = request.app.state.export_slots
    try:
        await asyncio.wait_for(slots.acquire(), timeout=0.1)
    except TimeoutError:
        raise ApiProblem(429, "rate_limited", "Export generation is busy.") from None

    def generate() -> bytes:
        data = ExportService(observations).generate(body, current)
        # Recheck the active session before delivering the completed sensitive bytes.
        auth.accounts.session_expiry(current.access_token)
        return data

    task = asyncio.create_task(run_in_threadpool(generate))

    # A timed-out thread retains its concurrency slot until bounded upstream I/O ends.
    def finished(done: asyncio.Task[bytes]) -> None:
        slots.release()
        if not done.cancelled():
            done.exception()

    task.add_done_callback(finished)
    try:
        data = await asyncio.wait_for(asyncio.shield(task), timeout=20)
    except TimeoutError:
        raise ApiProblem(
            504, "export_timeout", "The export took too long. Try a smaller scope."
        ) from None
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8" if body.format == "csv" else "application/json",
        headers={
            "Content-Disposition": f'attachment; filename="swasthyalens-health.{body.format}"',
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )
