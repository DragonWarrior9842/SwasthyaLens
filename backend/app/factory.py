"""FastAPI application composition without import-time configuration side effects."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.accounts import router as accounts_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.core.auth_service import AuthService
from app.core.browser_security import clear_session_cookies
from app.core.config import Settings
from app.core.errors import ApiProblem
from app.core.http_security import BrowserSecurityMiddleware
from app.core.provider import SupabaseGateway
from app.core.reports import ReportsService


def create_app(
    settings: Settings | None = None,
    *,
    provider_transport: httpx.BaseTransport | None = None,
) -> FastAPI:
    """Construct the API with validated configuration and a bounded CORS policy."""
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        with httpx.Client(
            timeout=httpx.Timeout(10, connect=5),
            follow_redirects=False,
            trust_env=False,
            transport=provider_transport,
            limits=httpx.Limits(max_connections=20),
        ) as client:
            application.state.auth_service = (
                AuthService(config, SupabaseGateway(config, client))
                if config.auth_enabled
                else None
            )
            application.state.reports_service = (
                ReportsService(SupabaseGateway(config, client), config.report_max_upload_bytes)
                if config.auth_enabled
                else None
            )
            application.state.report_upload_slots = asyncio.Semaphore(4)
            yield

    application = FastAPI(
        title="SwasthyaLens API",
        version="0.1.0",
        description="Private reports and authentication. OCR and analysis are not implemented.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allowed_origins),
        allow_credentials=config.auth_enabled,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"] if config.auth_enabled else ["GET"],
        allow_headers=["Content-Type", "X-CSRF-Token"] if config.auth_enabled else [],
    )
    application.add_middleware(
        BrowserSecurityMiddleware, report_max_upload_bytes=config.report_max_upload_bytes
    )

    @application.exception_handler(ApiProblem)
    async def public_problem(request: Request, error: ApiProblem) -> JSONResponse:
        response = JSONResponse(
            status_code=error.status,
            content={"code": error.code, "message": error.message},
        )
        if error.status == 429:
            response.headers["Retry-After"] = "60"
        if error.clear_session:
            clear_session_cookies(response, config)
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": "Check the submitted fields and try again.",
            },
        )

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(accounts_router)
    application.include_router(reports_router)
    return application
