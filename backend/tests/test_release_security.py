"""Release boundaries without provider network or live integration flags."""

import asyncio
import logging
import secrets
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from starlette.types import Message

from app.core.config import Settings
from app.core.http_security import BrowserSecurityMiddleware
from app.factory import create_app
from tests.explanation_fixtures import MockExplanationProvider


@pytest.fixture(autouse=True)
def isolate_release_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "RUN_SUPABASE_INTEGRATION",
        "RUN_OCR_EVALUATION",
        "DISPOSABLE_TEST_ACCOUNTS_CONFIRMED",
    ):
        monkeypatch.delenv(name, raising=False)


def release_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = dict(
        environment="production",
        app_origin="https://app.release-unit.org",
        allowed_hosts=("app.release-unit.org",),
        cors_allowed_origins=("https://app.release-unit.org",),
        supabase_url="https://abcdefghijklmnopqrst.supabase.co",
        supabase_publishable_key=SecretStr("sb_publishable_" + secrets.token_urlsafe(32)),
        csrf_signing_key=SecretStr(secrets.token_urlsafe(32)),
        report_processing_key=SecretStr(secrets.token_urlsafe(32)),
        ocr_tessdata_dir=str(Path.cwd().resolve()),
        auth_rate_limit_mode="edge",
    )
    return Settings(_env_file=None, **(values | overrides))


@pytest.mark.parametrize("environment", ["staging", "production"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("allowed_hosts", ("*",)),
        ("allowed_hosts", ("localhost",)),
        ("allowed_hosts", ("app.release-unit.org:443",)),
        ("app_origin", "http://app.release-unit.org"),
        ("auth_rate_limit_mode", "local"),
        ("csrf_signing_key", SecretStr("replace-me-" * 8)),
        ("report_processing_key", None),
        ("ocr_tessdata_dir", "relative/models"),
        ("cors_allowed_origins", ("https://foreign.release-unit.org",)),
    ],
)
def test_release_invalid_configuration(environment: str, field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        release_settings(environment=environment, **{field: value})


@pytest.mark.parametrize(
    "flag",
    [
        "RUN_AI_INTEGRATION",
        "RUN_SUPABASE_INTEGRATION",
        "RUN_OCR_EVALUATION",
        "DISPOSABLE_TEST_ACCOUNTS_CONFIRMED",
    ],
)
def test_release_rejects_test_flags_even_when_zero(
    monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    monkeypatch.setenv(flag, "0")
    with pytest.raises(ValidationError):
        release_settings()


def test_release_rejects_provider_injection() -> None:
    with pytest.raises(ValueError, match="injected"):
        create_app(release_settings(), explanation_provider=MockExplanationProvider())
    with pytest.raises(ValueError, match="injected"):
        create_app(
            release_settings(),
            provider_transport=httpx.MockTransport(lambda _: httpx.Response(200)),
        )


def test_release_headers_host_debug_and_disabled_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_API_KEY", "synthetic-environment-key-never-used")
    app = create_app(release_settings())
    assert not app.debug
    with TestClient(app, base_url="https://app.release-unit.org") as client:
        response = client.get("/health", headers={"X-Request-ID": "untrusted"})
        assert response.status_code == 200
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert len(response.headers["x-request-id"]) == 32
        assert response.headers["x-request-id"] != "untrusted"
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404
        assert client.get("/health", headers={"host": "foreign.org"}).status_code == 400
        assert not app.state.explanation_service.provider.available
        assert app.state.explanation_service.provider.settings.ai_api_key is None
        assert not app.state.assistant_service.provider.assistant_available


def test_http_never_trusts_forwarded_https_or_host() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health", headers={"X-Forwarded-Proto": "https"})
        assert "strict-transport-security" not in response.headers
        assert (
            client.get(
                "/health", headers={"Host": "attacker.org", "X-Forwarded-Host": "localhost"}
            ).status_code
            == 400
        )


def test_unexpected_error_is_private_and_logs_only_route(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(Settings(_env_file=None))

    @app.get("/failure/{identifier}")
    def fail(identifier: str) -> None:
        raise RuntimeError("synthetic-private-measurement-and-cookie")

    with caplog.at_level(logging.INFO, logger="swasthyalens.http"), TestClient(app) as client:
        response = client.get("/failure/private-owner?token=secret-query")
    assert response.status_code == 500
    assert response.json()["code"] == "service_unavailable"
    logs = " ".join(r.message for r in caplog.records if r.name.startswith("swasthyalens"))
    assert "/failure/{identifier}" in logs
    for private in (
        "private-owner",
        "secret-query",
        "synthetic-private-measurement",
        "RuntimeError",
    ):
        assert private not in logs + response.text


def test_slow_body_deadline_is_total_not_per_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.http_security import BodyReadTimeout

    monkeypatch.setattr("app.core.http_security.UPLOAD_READ_SECONDS", 0.2)
    received = 0
    output: list[Message] = []

    async def receive() -> Message:
        nonlocal received
        await asyncio.sleep(0.12)
        received += 1
        return {"type": "http.request", "body": b"x", "more_body": True}

    async def consume(scope: Any, recv: Any, send: Any) -> None:
        with pytest.raises(BodyReadTimeout):
            await recv()
            await recv()

    async def send(message: Message) -> None:
        output.append(message)

    asyncio.run(
        BrowserSecurityMiddleware(consume)(
            {
                "type": "http",
                "method": "PUT",
                "path": "/reports/11111111-1111-4111-8111-111111111111/file",
                "headers": [],
            },
            receive,
            send,
        )
    )
    assert received == 1
