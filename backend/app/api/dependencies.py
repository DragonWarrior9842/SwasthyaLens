"""Reusable authentication dependency derives identity only from verified cookies."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.auth_service import AuthenticatedRequest, AuthService
from app.core.errors import unavailable


def auth_service(request: Request) -> AuthService:
    service: object = getattr(request.app.state, "auth_service", None)
    if not isinstance(service, AuthService):
        raise unavailable()
    return service


Auth = Annotated[AuthService, Depends(auth_service)]


def protect_write(request: Request, auth: Auth) -> None:
    auth.csrf.validate(request)


def current_user(request: Request, auth: Auth) -> AuthenticatedRequest:
    return auth.current(request)


CurrentUser = Annotated[AuthenticatedRequest, Depends(current_user)]


def auth_attempt(request: Request, auth: Auth) -> None:
    protect_write(request, auth)
    peer = request.client.host if request.client is not None else "unknown"
    # Ignore caller-supplied forwarding headers. A production edge must independently limit IPs.
    endpoint = request.url.path
    email_flow = endpoint in {"/auth/signup", "/auth/resend-verification"}
    limit = 3 if email_flow else 15
    auth.limiter.check(f"{peer}:{endpoint}", limit=limit)
