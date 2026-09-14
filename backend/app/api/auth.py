"""Small, CSRF-protected browser auth API backed by real Supabase Auth."""

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import Auth, CurrentUser, auth_attempt
from app.core.browser_security import clear_session_cookies
from app.core.errors import ApiProblem, unavailable
from app.schemas.accounts import (
    CsrfResponse,
    EmailInput,
    EmptyInput,
    LoginInput,
    MessageResponse,
    SessionResponse,
    SignupInput,
    VerificationInput,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
writes = [Depends(auth_attempt)]


@router.get("/csrf", response_model=CsrfResponse)
def csrf(request: Request, response: Response, auth: Auth) -> CsrfResponse:
    peer = request.client.host if request.client is not None else "unknown"
    auth.limiter.check(f"{peer}:csrf", limit=120)
    return CsrfResponse(csrf_token=auth.csrf.issue(request, response))


@router.post("/signup", status_code=202, response_model=MessageResponse, dependencies=writes)
def signup(body: SignupInput, auth: Auth) -> MessageResponse:
    data = auth.gateway.object(
        "POST",
        "/auth/v1/signup",
        payload={"email": str(body.email), "password": body.password.get_secret_value()},
        purpose="signup",
    )
    if data.get("access_token") is not None:
        # The approved product flow requires email confirmation before account access.
        raise unavailable()
    return MessageResponse(
        message="If this address can register, a confirmation code will be sent. Check your email."
    )


@router.post(
    "/resend-verification",
    status_code=202,
    response_model=MessageResponse,
    dependencies=writes,
)
def resend(body: EmailInput, auth: Auth) -> MessageResponse:
    auth.gateway.object(
        "POST",
        "/auth/v1/resend",
        payload={"type": "signup", "email": str(body.email)},
        purpose="resend",
    )
    return MessageResponse(message="If confirmation is pending, a new code will be sent.")


@router.post("/login", response_model=SessionResponse, dependencies=writes)
def login(body: LoginInput, response: Response, auth: Auth) -> SessionResponse:
    data = auth.gateway.object(
        "POST",
        "/auth/v1/token",
        payload={"email": str(body.email), "password": body.password.get_secret_value()},
        params={"grant_type": "password"},
        purpose="login",
    )
    return auth.set_session(response, auth.accept_tokens(data))


@router.post("/verify-email", response_model=SessionResponse, dependencies=writes)
def verify_email(body: VerificationInput, response: Response, auth: Auth) -> SessionResponse:
    data = auth.gateway.object(
        "POST",
        "/auth/v1/verify",
        payload={"type": "email", "email": str(body.email), "token": body.token},
        purpose="verify",
    )
    return auth.set_session(response, auth.accept_tokens(data))


@router.post("/refresh", response_model=SessionResponse, dependencies=writes)
def refresh(body: EmptyInput, request: Request, response: Response, auth: Auth) -> SessionResponse:
    try:
        return auth.set_session(response, auth.refresh(request))
    except ApiProblem as error:
        if error.status == 401:
            error.clear_session = True
        raise


@router.post("/logout", response_model=MessageResponse, dependencies=writes)
def logout(body: EmptyInput, request: Request, response: Response, auth: Auth) -> MessageResponse:
    try:
        auth.logout(request)
    except ApiProblem:
        # Drop browser credentials while distinguishing uncertain remote revocation.
        raise ApiProblem(
            503,
            "logout_incomplete",
            "Local sign-out completed. Remote session revocation could not be confirmed.",
            clear_session=True,
        ) from None
    clear_session_cookies(response, auth.settings)
    return MessageResponse(message="You have signed out.")


@router.get("/me", response_model=SessionResponse)
def me(current: CurrentUser, auth: Auth) -> SessionResponse:
    return auth.session_response(current.identity, current.session_expires_at)
