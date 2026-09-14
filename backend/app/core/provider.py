"""Supabase REST boundary: request-scoped credentials, bounded I/O, safe errors."""

from typing import cast

import httpx

from app.core.config import Settings
from app.core.errors import ApiProblem, unauthenticated, unavailable


class SupabaseGateway:
    def __init__(self, settings: Settings, client: httpx.Client) -> None:
        assert settings.supabase_url is not None
        assert settings.supabase_publishable_key is not None
        self.origin = settings.supabase_url
        self.publishable_key = settings.supabase_publishable_key.get_secret_value()
        self.client = client

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, object] | None = None,
        access_token: str | None = None,
        params: dict[str, str] | None = None,
        prefer: str | None = None,
        purpose: str = "data",
    ) -> object:
        headers = {"apikey": self.publishable_key, "Accept": "application/json"}
        if access_token is not None:
            headers["Authorization"] = f"Bearer {access_token}"
        if prefer is not None:
            headers["Prefer"] = prefer
        try:
            response = self.client.request(
                method, self.origin + path, json=payload, params=params, headers=headers,
            )
        except httpx.HTTPError:
            raise unavailable() from None
        if response.status_code == 429:
            raise ApiProblem(429, "rate_limited", "Too many attempts. Try again later.")
        if response.status_code >= 500 or response.is_redirect:
            raise unavailable()
        if response.status_code >= 400:
            code = ""
            try:
                error: object = response.json()
                if isinstance(error, dict):
                    candidate = error.get("error_code", error.get("code"))
                    if isinstance(candidate, str):
                        code = candidate
            except ValueError:
                pass
            if purpose == "login":
                if code == "email_not_confirmed":
                    raise ApiProblem(401, "email_not_confirmed", "Confirm your email before signing in.")
                if response.status_code in (400, 401, 403, 422):
                    raise ApiProblem(401, "invalid_credentials", "Email or password is incorrect.")
            if purpose == "verify" and response.status_code in (400, 401, 403, 422):
                raise ApiProblem(400, "invalid_code", "The verification code is invalid or expired.")
            if purpose in {"signup", "resend"}:
                if code in {"user_already_exists", "email_exists"}:
                    return {}
                if code == "email_address_not_authorized":
                    raise ApiProblem(
                        503, "service_unavailable",
                        "Email delivery is restricted in this development environment.",
                    )
                raise unavailable()
            if purpose in {"refresh", "logout"} and response.status_code in (400, 401, 403):
                raise unauthenticated()
            if purpose == "data" and response.status_code == 401:
                raise unauthenticated()
            raise unavailable()
        if not response.content:
            return None
        if len(response.content) > 1_000_000:
            raise unavailable()
        try:
            result: object = response.json()
            return result
        except ValueError:
            raise unavailable() from None

    def object(
        self, method: str, path: str, *, payload: dict[str, object] | None = None,
        access_token: str | None = None, params: dict[str, str] | None = None,
        purpose: str = "data",
    ) -> dict[str, object]:
        value = self.request(
            method, path, payload=payload, access_token=access_token, params=params, purpose=purpose,
        )
        if not isinstance(value, dict):
            raise unavailable()
        return cast(dict[str, object], value)
