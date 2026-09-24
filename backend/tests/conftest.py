"""Isolated backend test configuration."""

from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.factory import create_app


@pytest.fixture(autouse=True)
def clear_cors_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "CORS_ALLOWED_ORIGINS",
        "ENVIRONMENT",
        "APP_ORIGIN",
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "CSRF_SIGNING_KEY",
        "AUTH_RATE_LIMIT_MODE",
        "REPORT_MAX_UPLOAD_BYTES",
        "REPORT_PROCESSING_KEY",
        "REPORT_PROCESSING_MAX_PAGES",
        "REPORT_PROCESSING_TIMEOUT_SECONDS",
        "OCR_TESSDATA_DIR",
        "AI_PROVIDER",
        "AI_MODEL",
        "AI_API_KEY",
        "RUN_AI_INTEGRATION",
    ):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


@pytest.fixture(autouse=True)
def forbid_ai_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Normal pytest can NEVER spend credits, even when live flags leak into its shell."""
    sync_send = httpx.HTTPTransport.handle_request
    async_send = httpx.AsyncHTTPTransport.handle_async_request

    def checked_sync(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        assert request.url.host not in {"api.openai.com", "generativelanguage.googleapis.com"}, (
            "AI network forbidden in pytest"
        )
        return sync_send(self, request)

    async def checked_async(
        self: httpx.AsyncHTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        assert request.url.host not in {"api.openai.com", "generativelanguage.googleapis.com"}, (
            "AI network forbidden in pytest"
        )
        return await async_send(self, request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", checked_sync)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", checked_async)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(Settings(_env_file=None))) as test_client:
        yield test_client
