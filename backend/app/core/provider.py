"""Supabase REST boundary: request-scoped credentials, bounded I/O, safe errors."""

import json
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
        headers = {"apikey": self.publishable_key, "Accept": "application/json", "Cookie": ""}
        if access_token is not None:
            headers["Authorization"] = f"Bearer {access_token}"
        if prefer is not None:
            headers["Prefer"] = prefer
        try:
            with self.client.stream(
                method,
                self.origin + path,
                json=payload,
                params=params,
                headers=headers,
            ) as response:
                status = response.status_code
                content = bytearray()
                for chunk in response.iter_bytes(chunk_size=16_384):
                    if len(content) + len(chunk) > 1_000_000:
                        raise unavailable()
                    content.extend(chunk)
        except httpx.HTTPError:
            raise unavailable() from None
        if status == 429:
            raise ApiProblem(429, "rate_limited", "Too many attempts. Try again later.")
        if status >= 500 or 300 <= status < 400:
            raise unavailable()
        if status >= 400:
            code = ""
            error: object = None
            try:
                error = json.loads(content)
                if isinstance(error, dict):
                    candidate = error.get("error_code", error.get("code"))
                    if isinstance(candidate, str):
                        code = candidate
            except ValueError:
                pass
            if purpose == "reports":
                if code == "28000":
                    raise unauthenticated()
                if code == "P0001" and isinstance(error, dict):
                    message = error.get("message")
                    report_errors = {
                        "processing_limit": (
                            409,
                            "This report has reached its three-attempt extraction limit.",
                        ),
                        "report_not_found": (404, "Report not found."),
                        "report_conflict": (
                            409,
                            "This operation is in progress or conflicts with an earlier request.",
                        ),
                        "invalid_file": (422, "The file or report metadata is invalid."),
                    }
                    if isinstance(message, str) and message in report_errors:
                        status_code, public_message = report_errors[message]
                        raise ApiProblem(status_code, message, public_message)
            if purpose == "login":
                if code == "email_not_confirmed":
                    raise ApiProblem(
                        401, "email_not_confirmed", "Confirm your email before signing in."
                    )
                if status in (400, 401, 403, 422) and code in {
                    "invalid_credentials",
                    "invalid_grant",
                }:
                    raise ApiProblem(401, "invalid_credentials", "Email or password is incorrect.")
            if (
                purpose == "verify"
                and status in (400, 401, 403, 422)
                and code in {"otp_expired", "invalid_token", "access_denied"}
            ):
                raise ApiProblem(
                    400, "invalid_code", "The verification code is invalid or expired."
                )
            if purpose in {"signup", "resend"}:
                if code in {"user_already_exists", "email_exists"}:
                    return {}
                if code == "email_address_not_authorized":
                    raise ApiProblem(
                        503,
                        "service_unavailable",
                        "Email delivery is restricted in this development environment.",
                    )
                raise unavailable()
            if purpose == "logout" and code == "session_not_found":
                return None
            if purpose == "refresh" and code in {
                "refresh_token_not_found",
                "refresh_token_already_used",
                "session_not_found",
                "session_expired",
                "invalid_grant",
            }:
                raise unauthenticated()
            if (
                purpose in {"data", "reports"}
                and status == 401
                and code in {"PGRST301", "PGRST303"}
            ):
                raise unauthenticated()
            raise unavailable()
        if not content:
            return None
        try:
            result: object = json.loads(content)
            return result
        except ValueError:
            raise unavailable() from None

    def object(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, object] | None = None,
        access_token: str | None = None,
        params: dict[str, str] | None = None,
        purpose: str = "data",
    ) -> dict[str, object]:
        value = self.request(
            method,
            path,
            payload=payload,
            access_token=access_token,
            params=params,
            purpose=purpose,
        )
        if not isinstance(value, dict):
            raise unavailable()
        return cast(dict[str, object], value)
