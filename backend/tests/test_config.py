from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pydantic_settings import SettingsError

from app.core.config import DEFAULT_CORS_ORIGINS, Settings
from app.main import create_app


def test_default_origins_are_local_and_explicit() -> None:
    assert Settings(_env_file=None).cors_allowed_origins == DEFAULT_CORS_ORIGINS


def test_blank_env_file_keeps_defaults(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CORS_ALLOWED_ORIGINS=\n", encoding="utf-8")

    assert Settings(_env_file=env_file).cors_allowed_origins == DEFAULT_CORS_ORIGINS


def test_environment_overrides_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('CORS_ALLOWED_ORIGINS=["http://localhost:4173"]\n', encoding="utf-8")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["https://app.example"]')

    settings = Settings(_env_file=env_file)

    with TestClient(create_app(settings)) as client:
        allowed = client.get("/health", headers={"Origin": "https://app.example"})
        excluded = client.get("/health", headers={"Origin": "http://localhost:4173"})

    assert allowed.headers["access-control-allow-origin"] == "https://app.example"
    assert "access-control-allow-origin" not in excluded.headers


def test_empty_array_disables_cross_origin_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "[]")

    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        '"http://localhost:5173"',
        '["*"]',
        '["http://*.example"]',
        '["http://localhost:5173/path"]',
        '["http://localhost:5173/"]',
        '["http://localhost:5173?query=1"]',
        '["http://localhost:5173#fragment"]',
        '["http://user:password@localhost:5173"]',
        '["http://localhost:99999"]',
        '["http://localhost:0"]',
        '["http://local host:5173"]',
        '["file://localhost"]',
        '[123]',
    ],
)
def test_invalid_origin_configuration_fails_startup(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", value)

    with pytest.raises((ValidationError, SettingsError)):
        create_app()
