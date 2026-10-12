"""Closed staging registration never reaches the provider; confirmed login survives."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.factory import create_app
from tests.auth_support import ProviderFixture, auth_settings
from tests.test_auth import headers, login
from tests.test_release_security import release_settings


def test_public_registration_defaults_closed() -> None:
    assert not Settings(_env_file=None).public_signup_enabled


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_release_registration_and_recovery_do_not_dispatch(
    environment: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbid_network(*args: object, **kwargs: object) -> httpx.Response:
        pytest.fail("Restricted auth must not contact any external service")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbid_network)
    settings = release_settings(environment=environment)
    with TestClient(create_app(settings), base_url=settings.app_origin) as client:
        policy = client.get("/auth/policy")
        assert policy.status_code == 200
        assert policy.json() == {
            "public_signup_enabled": False,
            "public_recovery_enabled": False,
        }
        assert policy.headers["cache-control"] == "no-store"
        csrf = client.get("/auth/csrf").json()["csrf_token"]
        secure_headers = {"Origin": settings.app_origin, "X-CSRF-Token": csrf}
        for path, body in (
            ("signup", {"email": "synthetic@example.test", "password": "test-only-passphrase"}),
            ("resend-verification", {"email": "synthetic@example.test"}),
            ("verify-email", {"email": "synthetic@example.test", "token": "123456"}),
        ):
            response = client.post(f"/auth/{path}", json=body, headers=secure_headers)
            assert response.status_code == 403
            assert response.json()["code"] == "public_auth_disabled"
            assert "set-cookie" not in response.headers
        for path in ("recover", "recovery", "reset-password"):
            assert client.post(f"/auth/{path}", json={}, headers=secure_headers).status_code == 404
        assert client.get("/health").json() == {"status": "ok", "service": "swasthyalens-api"}


def test_restricted_confirmed_login_refresh_and_logout_still_work() -> None:
    provider = ProviderFixture()
    with TestClient(
        create_app(
            auth_settings(public_signup_enabled=False),
            provider_transport=httpx.MockTransport(provider.handle),
        )
    ) as client:
        assert login(client).status_code == 200
        assert client.get("/auth/me").status_code == 200
        assert client.post("/auth/refresh", json={}, headers=headers(client)).status_code == 200
        assert client.post("/auth/logout", json={}, headers=headers(client)).status_code == 200
        assert client.get("/auth/me").status_code == 401
    assert not any(r.url.path in {"/auth/v1/signup", "/auth/v1/resend"} for r in provider.requests)


def test_development_explicit_opt_in_policy_is_truthful() -> None:
    provider = ProviderFixture()
    with TestClient(
        create_app(auth_settings(), provider_transport=httpx.MockTransport(provider.handle))
    ) as client:
        assert client.get("/auth/policy").json()["public_signup_enabled"] is True
        assert not provider.requests
