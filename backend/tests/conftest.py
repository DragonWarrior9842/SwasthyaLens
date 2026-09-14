"""Isolated backend test configuration."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.factory import create_app


@pytest.fixture(autouse=True)
def clear_cors_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "CORS_ALLOWED_ORIGINS", "ENVIRONMENT", "APP_ORIGIN", "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY", "CSRF_SIGNING_KEY", "AUTH_RATE_LIMIT_MODE",
    ):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(Settings(_env_file=None))) as test_client:
        yield test_client
