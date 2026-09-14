"""FastAPI application composition without import-time configuration side effects."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct the API with validated configuration and a bounded CORS policy."""
    config = settings if settings is not None else Settings()
    application = FastAPI(
        title="SwasthyaLens API",
        version="0.1.0",
        description="Local foundation. No health-data services are implemented yet.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=[],
    )
    application.include_router(health_router)
    return application
