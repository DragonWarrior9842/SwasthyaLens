"""Provider session lifecycle. Tokens remain inside the backend/cookie boundary."""

import hashlib
import time
from dataclasses import dataclass, field
from threading import Lock

from fastapi import Request, Response

from app.core.accounts import AccountsRepository
from app.core.browser_security import CsrfProtection, cookie_names, set_cookie
from app.core.config import Settings
from app.core.errors import ApiProblem, unauthenticated, unavailable
from app.core.identity import TokenVerifier, VerifiedIdentity
from app.core.provider import SupabaseGateway
from app.core.rate_limit import RateLimiter
from app.schemas.accounts import PublicUser, SessionResponse


@dataclass(frozen=True)
class SessionTokens:
    access: str = field(repr=False)
    refresh: str = field(repr=False)
    identity: VerifiedIdentity
    session_expires_at: int


@dataclass(frozen=True)
class AuthenticatedRequest:
    identity: VerifiedIdentity
    access_token: str = field(repr=False)
    session_expires_at: int


class AuthService:
    def __init__(self, settings: Settings, gateway: SupabaseGateway) -> None:
        self.settings = settings
        self.gateway = gateway
        self.verifier = TokenVerifier(gateway)
        self.accounts = AccountsRepository(gateway)
        self.csrf = CsrfProtection(settings)
        self.limiter = RateLimiter()
        # A short bounded replay cache handles a retried refresh after a dropped response.
        # This is a local single-worker coordination aid; active-session RLS remains authoritative.
        self._refresh_lock = Lock()
        self._refreshed: dict[str, tuple[float, SessionTokens]] = {}

    def current(self, request: Request) -> AuthenticatedRequest:
        token = request.cookies.get(cookie_names(self.settings).access)
        if token is None:
            raise unauthenticated()
        identity = self.verifier.verify(token)
        expiry = self.accounts.session_expiry(token)
        return AuthenticatedRequest(identity, token, expiry)

    def accept_tokens(self, data: dict[str, object]) -> SessionTokens:
        access, refresh = data.get("access_token"), data.get("refresh_token")
        if (
            not isinstance(access, str)
            or not isinstance(refresh, str)
            or not 1 <= len(refresh) <= 4096
            or data.get("token_type") != "bearer"
        ):
            raise unavailable()
        identity = self.verifier.verify(access)
        expiry = self.accounts.session_expiry(access)
        self.accounts.ensure_rows(identity, access)
        return SessionTokens(access, refresh, identity, expiry)

    def set_session(self, response: Response, tokens: SessionTokens) -> SessionResponse:
        names = cookie_names(self.settings)
        now = int(time.time())
        if min(tokens.identity.expires_at, tokens.session_expires_at) <= now:
            raise unauthenticated()
        set_cookie(
            response,
            self.settings,
            names.access,
            tokens.access,
            min(tokens.identity.expires_at, tokens.session_expires_at) - now,
        )
        set_cookie(
            response,
            self.settings,
            names.refresh,
            tokens.refresh,
            tokens.session_expires_at - now,
        )
        return self.session_response(tokens.identity, tokens.session_expires_at)

    @staticmethod
    def session_response(identity: VerifiedIdentity, session_expiry: int) -> SessionResponse:
        return SessionResponse(
            user=PublicUser(id=identity.user_id, email=identity.email),
            expires_at=min(identity.expires_at, session_expiry),
        )

    def refresh(self, request: Request) -> SessionTokens:
        token = request.cookies.get(cookie_names(self.settings).refresh)
        if token is None or not 1 <= len(token) <= 4096:
            raise unauthenticated()
        key = hashlib.sha256(token.encode()).hexdigest()
        with self._refresh_lock:
            now = time.monotonic()
            self._refreshed = {
                previous: entry for previous, entry in self._refreshed.items() if entry[0] > now - 8
            }
            cached = self._refreshed.get(key)
            if cached is not None:
                # Never replay a session that was revoked while the response was in flight.
                self.accounts.session_expiry(cached[1].access)
                return cached[1]
            if len(self._refreshed) >= 256:
                raise ApiProblem(429, "rate_limited", "Too many attempts. Try again later.")
            data = self.gateway.object(
                "POST",
                "/auth/v1/token",
                payload={"refresh_token": token},
                params={"grant_type": "refresh_token"},
                purpose="refresh",
            )
            tokens = self.accept_tokens(data)
            self._refreshed[key] = (now, tokens)
            return tokens

    def logout(self, request: Request) -> None:
        names = cookie_names(self.settings)
        access = request.cookies.get(names.access)
        refresh = request.cookies.get(names.refresh)
        if access is None and refresh is None:
            return
        if access is not None:
            try:
                self.verifier.verify(access)
            except ApiProblem as error:
                if error.status != 401:
                    raise
                access = None
        if access is None:
            if not refresh:
                return
            data = self.gateway.object(
                "POST",
                "/auth/v1/token",
                payload={"refresh_token": refresh},
                params={"grant_type": "refresh_token"},
                purpose="refresh",
            )
            candidate = data.get("access_token")
            if not isinstance(candidate, str):
                raise unavailable()
            self.verifier.verify(candidate)
            access = candidate
        self.gateway.request(
            "POST",
            "/auth/v1/logout",
            access_token=access,
            params={"scope": "local"},
            purpose="logout",
        )
