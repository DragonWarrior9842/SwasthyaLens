"""Host-only cookies and signed, nonce-bound CSRF tokens."""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from fastapi import Request, Response

from app.core.config import Settings
from app.core.errors import ApiProblem

CSRF_LIFETIME = 3600


@dataclass(frozen=True)
class CookieNames:
    access: str
    refresh: str
    nonce: str


def cookie_names(settings: Settings) -> CookieNames:
    prefix = "__Host-sl_" if settings.secure_cookies else "sl_"
    return CookieNames(prefix + "access", prefix + "refresh", prefix + "csrf")


def set_cookie(response: Response, settings: Settings, name: str, value: str, age: int) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max(0, age),
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    names = cookie_names(settings)
    for name in (names.access, names.refresh):
        response.delete_cookie(
            name, path="/", secure=settings.secure_cookies, httponly=True, samesite="lax"
        )


class CsrfProtection:
    def __init__(self, settings: Settings) -> None:
        assert settings.csrf_signing_key is not None
        self.settings = settings
        self.key = settings.csrf_signing_key.get_secret_value().encode()

    def issue(self, request: Request, response: Response) -> str:
        names = cookie_names(self.settings)
        nonce = request.cookies.get(names.nonce, "")
        if len(nonce) != 43 or not all(
            character.isalnum() or character in "-_" for character in nonce
        ):
            nonce = secrets.token_urlsafe(32)
        set_cookie(response, self.settings, names.nonce, nonce, CSRF_LIFETIME)
        timestamp = str(int(time.time()))
        return f"{timestamp}.{self._signature(nonce, timestamp)}"

    def _signature(self, nonce: str, timestamp: str) -> str:
        return hmac.new(self.key, f"csrf:{nonce}:{timestamp}".encode(), hashlib.sha256).hexdigest()

    def validate(self, request: Request) -> None:
        failure = ApiProblem(403, "csrf_failed", "Reload this page and try again.")
        if request.headers.get("origin") != self.settings.app_origin:
            raise failure
        if (
            request.headers.get("content-type", "").split(";")[0].strip().lower()
            != "application/json"
        ):
            raise failure
        token = request.headers.get("x-csrf-token", "")
        nonce = request.cookies.get(cookie_names(self.settings).nonce, "")
        if len(token) > 100 or len(nonce) != 43:
            raise failure
        parts = token.split(".")
        if (
            len(parts) != 2 or not parts[0].isascii() or not parts[0].isdigit()
            or len(parts[1]) != 64 or any(character not in "0123456789abcdef" for character in parts[1])
        ):
            raise failure
        timestamp = int(parts[0])
        age = int(time.time()) - timestamp
        if age < -5 or age > CSRF_LIFETIME:
            raise failure
        if not hmac.compare_digest(self._signature(nonce, parts[0]), parts[1]):
            raise failure
