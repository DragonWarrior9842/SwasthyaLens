"""Real two-user API and Data API isolation. Never runs in the ordinary test suite.

Requires two dedicated, confirmed development accounts, a running local API and
the applied migration. Credentials are read only from ignored .env.integration.
No emails are sent or accounts created by this suite. It changes and restores the
two test accounts' display names and exercises current-session logout.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

import httpx
import pytest
from dotenv import dotenv_values

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1",
    reason="Real Supabase tests require explicit RUN_SUPABASE_INTEGRATION=1 opt-in",
)


def expect_status(response: httpx.Response, expected: int, label: str) -> None:
    """Never include provider response bodies or credential-bearing requests in failures."""
    if response.status_code != expected:
        raise AssertionError(f"{label}: expected HTTP {expected}, received {response.status_code}")


def object_body(response: httpx.Response) -> dict[str, object]:
    body: object = response.json()
    if not isinstance(body, dict) or not all(isinstance(key, str) for key in body):
        raise AssertionError("Expected a JSON object")
    return cast(dict[str, object], body)


def expect_empty(response: httpx.Response, label: str) -> None:
    expect_status(response, 200, label)
    body: object = response.json()
    if body != []:
        raise AssertionError(f"{label}: an unrelated user's records were returned")


@dataclass(repr=False)
class SignedInUser:
    client: httpx.Client
    csrf: str = field(repr=False)
    access: str = field(repr=False)
    user_id: str

    def write(self, method: str, route: str, body: dict[str, object]) -> httpx.Response:
        return self.client.request(method, route, json=body, headers={"X-CSRF-Token": self.csrf})

    def close_session(self) -> None:
        """Best effort cleanup even if a later account's login fails."""
        try:
            self.write("POST", "/auth/logout", {})
        except httpx.HTTPError:
            pass


@dataclass(repr=False)
class LiveContext:
    users: tuple[SignedInUser, SignedInUser]
    database: httpx.Client

    def data(
        self, user: SignedInUser, method: str, route: str, body: dict[str, object] | None = None
    ) -> httpx.Response:
        return self.database.request(
            method,
            route,
            json=body,
            headers={"Authorization": f"Bearer {user.access}", "Prefer": "return=representation"},
        )


@pytest.fixture
def live() -> Iterator[LiveContext]:
    backend = Path(__file__).resolve().parents[2]
    values = dotenv_values(backend / ".env.integration")
    if values.get("DISPOSABLE_TEST_ACCOUNTS_CONFIRMED") != "1":
        pytest.fail("Set DISPOSABLE_TEST_ACCOUNTS_CONFIRMED=1 in ignored .env.integration")
    runtime = dotenv_values(backend / ".env")
    base_url = values.get("TEST_API_BASE_URL") or "http://127.0.0.1:8000"
    origin = values.get("TEST_APP_ORIGIN") or "http://127.0.0.1:5173"
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        pytest.fail("Live tests accept only a loopback development API")
    project = runtime.get("SUPABASE_URL") or ""
    key = runtime.get("SUPABASE_PUBLISHABLE_KEY") or ""
    if not project.startswith("https://") or not key.startswith("sb_publishable_"):
        pytest.fail("Real backend provider configuration is required")

    with ExitStack() as stack:
        authenticated: list[SignedInUser] = []
        for account in ("A", "B"):
            email = values.get(f"TEST_USER_{account}_EMAIL")
            password = values.get(f"TEST_USER_{account}_PASSWORD")
            if not email or not password:
                pytest.fail("Both dedicated test accounts must be configured locally")
            client = stack.enter_context(
                httpx.Client(base_url=base_url, headers={"Origin": origin}, timeout=20)
            )
            response = client.get("/auth/csrf")
            expect_status(response, 200, "CSRF bootstrap")
            csrf = object_body(response).get("csrf_token")
            if not isinstance(csrf, str):
                pytest.fail("Missing CSRF token")
            response = client.post(
                "/auth/login",
                json={"email": email, "password": password},
                headers={"X-CSRF-Token": csrf},
            )
            expect_status(response, 200, "Real account login")
            identity = object_body(response).get("user")
            if not isinstance(identity, dict) or not isinstance(identity.get("id"), str):
                pytest.fail("Missing verified identity")
            access = client.cookies.get("sl_access")
            if not access:
                pytest.fail("Missing HttpOnly access cookie")
            # Authentication may rotate the CSRF nonce, so obtain its current token.
            response = client.get("/auth/csrf")
            expect_status(response, 200, "Authenticated CSRF bootstrap")
            csrf = object_body(response).get("csrf_token")
            if not isinstance(csrf, str):
                pytest.fail("Missing authenticated CSRF token")
            user = SignedInUser(client, csrf, access, identity["id"])
            authenticated.append(user)
            stack.callback(user.close_session)
        if authenticated[0].user_id == authenticated[1].user_id:
            pytest.fail("A and B must be distinct real Supabase users")
        database = stack.enter_context(
            httpx.Client(
                base_url=project.rstrip("/") + "/rest/v1/",
                headers={"apikey": key},
                timeout=20,
            )
        )
        yield LiveContext((authenticated[0], authenticated[1]), database)


def test_real_two_user_ownership_and_revocation(live: LiveContext) -> None:
    original_profiles: list[dict[str, object]] = []
    for user in live.users:
        response = user.client.get("/profile")
        expect_status(response, 200, "Owner profile read")
        profile = object_body(response)
        if profile.get("id") != user.user_id:
            raise AssertionError("Profile identity mismatch")
        original_profiles.append(profile)
        response = user.client.get("/settings")
        expect_status(response, 200, "Owner settings read")
        if object_body(response).get("user_id") != user.user_id:
            raise AssertionError("Settings identity mismatch")
        response = user.write("POST", "/auth/refresh", {})
        expect_status(response, 200, "Real provider token refresh")
        refreshed = object_body(response)
        if set(refreshed) != {"user", "expires_at"}:
            raise AssertionError("Authentication response contains unexpected fields")
        access = user.client.cookies.get("sl_access")
        if not access:
            raise AssertionError("Refresh did not preserve the HttpOnly access cookie")
        user.access = access
        response = user.client.get("/auth/csrf")
        expect_status(response, 200, "CSRF after refresh")
        csrf = object_body(response).get("csrf_token")
        if not isinstance(csrf, str):
            raise AssertionError("Missing CSRF after refresh")
        user.csrf = csrf

    try:
        for index, user in enumerate(live.users):
            other = live.users[1 - index]
            response = user.write("PATCH", "/profile", {"display_name": f"Isolation test {index}"})
            expect_status(response, 200, "Owner profile update")
            response = user.write("PATCH", "/profile", {"id": other.user_id})
            expect_status(response, 422, "API rejects supplied owner")
            response = user.write("PATCH", "/settings", {"user_id": other.user_id})
            expect_status(response, 422, "Settings API rejects supplied owner")

            for table, owner_key in (("profiles", "id"), ("user_settings", "user_id")):
                own_route = f"{table}?{owner_key}=eq.{user.user_id}"
                other_route = f"{table}?{owner_key}=eq.{other.user_id}"
                own = live.data(user, "GET", own_route)
                expect_status(own, 200, "Direct owner read")
                rows: object = own.json()
                if not isinstance(rows, list) or len(rows) != 1:
                    raise AssertionError("Owner must see exactly their own row")
                before = live.data(other, "GET", other_route)
                expect_status(before, 200, "Capture other user's row")
                expect_empty(live.data(user, "GET", other_route), "Cross-user direct read")
                patch: dict[str, object] = (
                    {"display_name": "Unauthorized change"}
                    if table == "profiles"
                    else {"preferred_language": "hi"}
                )
                expect_empty(live.data(user, "PATCH", other_route, patch), "Cross-user update")
                expect_empty(live.data(user, "DELETE", other_route), "Cross-user delete")
                after = live.data(other, "GET", other_route)
                expect_status(after, 200, "Verify other user's unchanged row")
                if before.json() != after.json():
                    raise AssertionError("Cross-user mutation changed stored data")

                forged = live.data(user, "POST", table, {owner_key: other.user_id})
                expect_status(forged, 403, "Forged-owner insert")
                if object_body(forged).get("code") != "42501":
                    raise AssertionError("Forged insert must fail a database permission/RLS check")
                for forbidden in ({owner_key: other.user_id}, {"created_at": "2000-01-01"}):
                    expect_status(
                        live.data(user, "PATCH", own_route, forbidden),
                        403,
                        "Database rejects owner/audit mass assignment",
                    )
                expect_status(live.database.get(table), 401, "Anonymous table read")

        # Revoke A's real provider session, then replay its previously valid access JWT.
        first = live.users[0]
        for user, original in zip(live.users, original_profiles, strict=True):
            expect_status(
                user.write("PATCH", "/profile", {"display_name": original.get("display_name")}),
                200,
                "Restore original test profile",
            )
        expect_status(first.write("POST", "/auth/logout", {}), 200, "Provider session logout")
        expect_status(first.client.get("/auth/me"), 401, "Logged-out API access")
        replay = live.data(first, "GET", f"profiles?id=eq.{first.user_id}")
        expect_empty(replay, "Revoked JWT direct Data API replay")
        session = live.data(first, "POST", "rpc/session_context", {})
        expect_status(session, 200, "Revoked session check")
        if object_body(session).get("active") is not False:
            raise AssertionError("Revoked provider session remained active")
        expect_status(
            live.users[1].client.get("/auth/me"), 200, "Other user's session remains valid"
        )
    finally:
        for user, original in zip(live.users, original_profiles, strict=True):
            try:
                user.write("PATCH", "/profile", {"display_name": original.get("display_name")})
            except httpx.HTTPError:
                pass
