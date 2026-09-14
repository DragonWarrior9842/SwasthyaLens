"""Local API liveness contract."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["service"])
async def health() -> HealthResponse:
    """Confirm that the API process responds; no external services are checked."""
    return HealthResponse(status="ok", service="swasthyalens-api")
