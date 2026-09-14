"""Exercise the complete BFF path with only the external transport replaced."""

import json
import time
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from tests.auth_support import ORIGIN, ProviderFixture, auth_settings


@pytest.fixture
def provider() -> ProviderFixture:
    return ProviderFixture()


@pytest.fixture
def account_client(provider: ProviderFixture) -> Iterator[TestClient]:
    with TestClient(create_app(auth_settings(), provider_transport=httpx.MockTransport(provider.handle))) as client:
        yield client


def headers(client: TestClient) -> dict[str, str]:
    response = client.get("/auth/csrf")
    assert response.status_code == 200
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def login(client: TestClient) -> httpx.Response:
    return client.post(
        "/auth/login", headers=headers(client),
        json={"email": "account@example.com", "password": "isolated-test-password"},
    )


def test_login_sets_private_cookies_initializes_owned_rows_and_returns_only_identity(
    account_client: TestClient, provider: ProviderFixture,
) -> None:
    response = login(account_client)
    assert response.status_code == 200
    assert response.json() == {
        "user": {"id": provider.user_id, "email": provider.email}, "expires_at": provider.session_end,
    }
    assert "access_token" not in response.text and "refresh_token" not in response.text
    assert provider.profile_exists and provider.settings_exist
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    for cookie in cookies:
        assert "HttpOnly" in cookie and "Path=/" in cookie and "SameSite=lax" in cookie
        assert "Domain=" not in cookie and "Secure" not in cookie
    assert response.headers["cache-control"] == "no-store"
    assert account_client.get("/auth/me").json() == response.json()
    for request in provider.requests:
        assert request.headers["apikey"].startswith("sb_publishable_")
        if request.url.path.startswith("/rest/"):
            assert request.headers["authorization"].startswith("Bearer ey")


@pytest.mark.parametrize("path", ["/auth/me", "/profile", "/settings"])
def test_missing_session_cannot_access_owned_routes(account_client: TestClient, path: str) -> None:
    response = account_client.get(path)
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


@pytest.mark.parametrize("path", ["/auth/signup", "/auth/login", "/auth/verify-email", "/auth/resend-verification", "/auth/refresh", "/auth/logout", "/profile", "/settings"])
def test_every_write_requires_csrf(account_client: TestClient, provider: ProviderFixture, path: str) -> None:
    method = account_client.patch if path in {"/profile", "/settings"} else account_client.post
    response = method(path, json={})
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    assert not provider.requests


@pytest.mark.parametrize("attack", ["origin", "token", "nonce", "content-type", "expired"])
def test_csrf_rejects_forged_or_expired_requests(account_client: TestClient, attack: str) -> None:
    values = headers(account_client)
    if attack == "origin":
        values["Origin"] = "https://untrusted.example"
    elif attack == "token":
        values["X-CSRF-Token"] += "0"
    elif attack == "nonce":
        account_client.cookies.clear()
    elif attack == "content-type":
        values["Content-Type"] = "text/plain"
    else:
        _, signature = values["X-CSRF-Token"].split(".")
        values["X-CSRF-Token"] = f"{int(time.time()) - 4000}.{signature}"
    assert account_client.post("/auth/refresh", json={}, headers=values).status_code == 403


@pytest.mark.parametrize("body", [
    {"email": "invalid", "password": "secret-input-never-echo"},
    {"email": "account@example.com", "password": "secret-input-never-echo", "userId": "forged"},
    {"email": "account@example.com", "password": 42},
])
def test_validation_errors_never_echo_inputs(account_client: TestClient, body: dict[str, object]) -> None:
    response = account_client.post("/auth/login", headers=headers(account_client), json=body)
    assert response.status_code == 422
    assert response.json() == {"code": "validation_error", "message": "Check the submitted fields and try again."}
    assert "secret-input" not in response.text and "input" not in response.json()


def test_signup_and_resend_return_generic_messages(account_client: TestClient, provider: ProviderFixture) -> None:
    response = account_client.post(
        "/auth/signup", headers=headers(account_client),
        json={"email": "account@example.com", "password": "isolated-test-password"},
    )
    assert response.status_code == 202
    assert "sl_access" not in account_client.cookies
    provider.failures["/auth/v1/resend"] = (422, {"code": "email_exists"})
    response = account_client.post(
        "/auth/resend-verification", headers=headers(account_client), json={"email": "account@example.com"},
    )
    assert response.status_code == 202
    assert "existing" not in response.text


def test_email_code_verification_uses_signup_type(account_client: TestClient, provider: ProviderFixture) -> None:
    response = account_client.post(
        "/auth/verify-email", headers=headers(account_client),
        json={"email": "account@example.com", "token": "123456"},
    )
    assert response.status_code == 200
    request = next(request for request in provider.requests if request.url.path.endswith("verify"))
    assert json.loads(request.content)["type"] == "signup"
    assert "123456" not in response.text


def test_profile_and_settings_are_owned_allowlisted_and_real_transport_updates(
    account_client: TestClient, provider: ProviderFixture,
) -> None:
    assert login(account_client).status_code == 200
    assert account_client.get("/profile").json()["id"] == provider.user_id
    response = account_client.patch("/profile", headers=headers(account_client), json={"display_name": "  Test user  "})
    assert response.status_code == 200
    assert response.json()["display_name"] == "Test user"
    response = account_client.patch("/settings", headers=headers(account_client), json={"preferred_language": "hi", "timezone": "Asia/Kolkata"})
    assert response.status_code == 200
    assert account_client.get("/settings").json()["preferred_language"] == "hi"
    assert provider.timezone == "Asia/Kolkata"


@pytest.mark.parametrize(("path", "body"), [
    ("/profile", {"id": "forged"}), ("/profile", {"created_at": "2026-01-01"}),
    ("/profile", {"display_name": "x" * 81}), ("/profile", {}),
    ("/settings", {"preferred_language": "fr"}), ("/settings", {"timezone": "Not/AZone"}),
    ("/settings", {"user_id": "forged"}), ("/settings", {"updated_at": "2026-01-01"}),
    ("/settings", {"preferred_language": None}), ("/settings", {"timezone": None}),
])
def test_mass_assignment_and_invalid_preferences_rejected(
    account_client: TestClient, provider: ProviderFixture, path: str, body: dict[str, object],
) -> None:
    assert login(account_client).status_code == 200
    provider.requests.clear()
    response = account_client.patch(path, headers=headers(account_client), json=body)
    assert response.status_code == 422
    assert not any(request.method == "PATCH" for request in provider.requests)


def test_refresh_replay_is_bounded_and_logout_invalidates_cached_refresh(
    account_client: TestClient, provider: ProviderFixture,
) -> None:
    assert login(account_client).status_code == 200
    provider.requests.clear()
    csrf_headers = headers(account_client)
    assert account_client.post("/auth/refresh", json={}, headers=csrf_headers).status_code == 200
    assert account_client.post("/auth/refresh", json={}, headers=csrf_headers).status_code == 200
    refreshes = [request for request in provider.requests if request.url.path == "/auth/v1/token"]
    assert len(refreshes) == 1
    old_access, old_refresh = account_client.cookies["sl_access"], account_client.cookies["sl_refresh"]
    assert account_client.post("/auth/logout", json={}, headers=csrf_headers).status_code == 200
    assert "sl_access" not in account_client.cookies and "sl_refresh" not in account_client.cookies
    account_client.cookies.set("sl_access", old_access)
    assert account_client.get("/auth/me").status_code == 401
    account_client.cookies.set("sl_refresh", old_refresh)
    assert account_client.post("/auth/refresh", json={}, headers=csrf_headers).status_code == 401


def test_expired_session_cannot_be_revived_by_refresh(account_client: TestClient, provider: ProviderFixture) -> None:
    assert login(account_client).status_code == 200
    provider.session_end = int(time.time()) - 1
    response = account_client.post("/auth/refresh", json={}, headers=headers(account_client))
    assert response.status_code == 401
    assert "sl_refresh" not in account_client.cookies


def test_provider_failure_preserves_session_but_logout_clears_it_honestly(
    account_client: TestClient, provider: ProviderFixture,
) -> None:
    assert login(account_client).status_code == 200
    provider.failures["/rest/v1/rpc/session_context"] = (500, {"message": "private provider detail"})
    response = account_client.get("/auth/me")
    assert response.status_code == 503
    assert "sl_access" in account_client.cookies
    assert "private provider detail" not in response.text
    provider.failures["/auth/v1/logout"] = (500, {"message": "private provider detail"})
    response = account_client.post("/auth/logout", json={}, headers=headers(account_client))
    assert response.status_code == 503
    assert "could not be confirmed" in response.json()["message"]
    assert "sl_access" not in account_client.cookies and "sl_refresh" not in account_client.cookies


def test_auth_attempt_rate_limit(account_client: TestClient, provider: ProviderFixture) -> None:
    values = headers(account_client)
    for _ in range(3):
        assert account_client.post("/auth/resend-verification", json={"email": "account@example.com"}, headers=values).status_code == 202
    response = account_client.post("/auth/resend-verification", json={"email": "account@example.com"}, headers=values)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_oversized_request_rejected_before_provider_io(account_client: TestClient, provider: ProviderFixture) -> None:
    response = account_client.post("/auth/login", headers=headers(account_client), json={"email": "x" * 17000})
    assert response.status_code == 413
    assert not provider.requests


def test_production_cookies_are_host_only_secure(provider: ProviderFixture) -> None:
    settings = auth_settings(environment="production", app_origin="https://app.example", cors_allowed_origins=("https://app.example",), auth_rate_limit_mode="edge")
    with TestClient(create_app(settings, provider_transport=httpx.MockTransport(provider.handle)), base_url="https://app.example") as client:
        csrf_response = client.get("/auth/csrf")
        response = client.post("/auth/login", json={"email": "account@example.com", "password": "test-password"}, headers={"Origin": "https://app.example", "X-CSRF-Token": csrf_response.json()["csrf_token"]})
    assert response.status_code == 200
    for cookie in response.headers.get_list("set-cookie"):
        assert cookie.startswith("__Host-sl_") and "Secure" in cookie and "Domain=" not in cookie
