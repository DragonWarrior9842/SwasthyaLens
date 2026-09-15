"""Security review regressions exercise real route and transport code."""

import time

import pytest
from fastapi.testclient import TestClient

from tests.auth_support import ORIGIN, ProviderFixture
from tests.test_auth import account_client as account_client
from tests.test_auth import headers, login
from tests.test_auth import provider as provider


def test_unicode_csrf_signature_rejected_without_server_error(account_client: TestClient) -> None:
    values = headers(account_client)
    timestamp, _ = values["X-CSRF-Token"].split(".")
    response = account_client.post(
        "/auth/refresh",
        json={},
        headers=[
            (b"Origin", ORIGIN.encode()),
            (b"X-CSRF-Token", (timestamp + ".").encode() + b"\xe9" * 64),
        ],
    )
    assert response.status_code == 403


def test_expired_access_keeps_refresh_available(
    account_client: TestClient, provider: ProviderFixture
) -> None:
    account_client.cookies.set("sl_refresh", "isolated-refresh-token")
    account_client.cookies.set(
        "sl_access", provider.token({"iat": int(time.time()) - 3600, "exp": int(time.time()) - 1})
    )
    response = account_client.get("/auth/me")
    assert response.status_code == 401
    assert "sl_refresh" in account_client.cookies
    response = account_client.post("/auth/refresh", json={}, headers=headers(account_client))
    assert response.status_code == 200


def test_terminal_refresh_failure_clears_cookies(
    account_client: TestClient, provider: ProviderFixture
) -> None:
    assert login(account_client).status_code == 200
    provider.failures["/auth/v1/token"] = (400, {"error_code": "refresh_token_not_found"})
    response = account_client.post("/auth/refresh", json={}, headers=headers(account_client))
    assert response.status_code == 401
    assert "sl_refresh" not in account_client.cookies and "sl_access" not in account_client.cookies


@pytest.mark.parametrize("status", [400, 401, 403])
def test_bad_provider_key_never_reports_confirmed_logout(
    account_client: TestClient, provider: ProviderFixture, status: int
) -> None:
    assert login(account_client).status_code == 200
    provider.failures["/auth/v1/logout"] = (status, {"message": "Invalid API key"})
    response = account_client.post("/auth/logout", json={}, headers=headers(account_client))
    assert response.status_code == 503
    assert response.json()["code"] == "logout_incomplete"
    assert "sl_refresh" not in account_client.cookies


def test_proven_missing_session_logout_is_idempotent(
    account_client: TestClient, provider: ProviderFixture
) -> None:
    assert login(account_client).status_code == 200
    provider.failures["/auth/v1/logout"] = (403, {"error_code": "session_not_found"})
    response = account_client.post("/auth/logout", json={}, headers=headers(account_client))
    assert response.status_code == 200
    assert "sl_refresh" not in account_client.cookies


def test_signup_cannot_claim_code_sent_when_provider_autoconfirms(
    account_client: TestClient, provider: ProviderFixture
) -> None:
    provider.failures["/auth/v1/signup"] = (200, provider.session_payload())
    response = account_client.post(
        "/auth/signup",
        headers=headers(account_client),
        json={"email": "account@example.com", "password": "isolated-test-password"},
    )
    assert response.status_code == 503
    assert "sl_access" not in account_client.cookies


@pytest.mark.parametrize(
    ("endpoint", "provider_path", "body", "provider_code", "expected_status", "expected_code"),
    [
        (
            "login",
            "token",
            {"email": "account@example.com", "password": "test-password"},
            "invalid_credentials",
            401,
            "invalid_credentials",
        ),
        (
            "login",
            "token",
            {"email": "account@example.com", "password": "test-password"},
            "email_not_confirmed",
            401,
            "email_not_confirmed",
        ),
        (
            "verify-email",
            "verify",
            {"email": "account@example.com", "token": "123456"},
            "otp_expired",
            400,
            "invalid_code",
        ),
    ],
)
def test_provider_auth_errors_safely_mapped(
    account_client: TestClient,
    provider: ProviderFixture,
    endpoint: str,
    provider_path: str,
    body: dict[str, object],
    provider_code: str,
    expected_status: int,
    expected_code: str,
) -> None:
    provider.failures[f"/auth/v1/{provider_path}"] = (
        400,
        {"error_code": provider_code, "message": "internal detail"},
    )
    response = account_client.post(f"/auth/{endpoint}", headers=headers(account_client), json=body)
    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code
    assert "internal detail" not in response.text
