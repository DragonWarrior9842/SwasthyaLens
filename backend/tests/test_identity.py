"""Real asymmetric signatures: malformed claims never establish identity."""

import time
from collections.abc import Iterator

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.errors import ApiProblem
from app.core.identity import TokenVerifier
from app.core.provider import SupabaseGateway
from tests.auth_support import ProviderFixture, auth_settings


@pytest.fixture
def verification() -> Iterator[tuple[ProviderFixture, TokenVerifier]]:
    provider = ProviderFixture()
    with httpx.Client(transport=httpx.MockTransport(provider.handle)) as client:
        yield provider, TokenVerifier(SupabaseGateway(auth_settings(), client))


def test_valid_signature_yields_typed_authoritative_identity(
    verification: tuple[ProviderFixture, TokenVerifier],
) -> None:
    provider, verifier = verification
    identity = verifier.verify(provider.token())
    assert str(identity.user_id) == provider.user_id
    assert str(identity.session_id) == provider.session_id


@pytest.mark.parametrize(
    "change",
    [
        {"sub": "not-a-uuid"},
        {"session_id": "not-a-uuid"},
        {"session_id": None},
        {"sub": "00000000-0000-0000-0000-000000000000"},
        {"iss": "https://unrelated-project.supabase.co/auth/v1"},
        {"aud": "service_role"},
        {"aud": ["authenticated"]},
        {"exp": 1},
        {"exp": "9999999999"},
        {"exp": True},
        {"iat": "1"},
        {"iat": True},
        {"iat": 9999999999},
        {"nbf": 9999999999},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"is_anonymous": "false"},
        {"email": None},
        {"email": ""},
    ],
)
def test_invalid_claims_fail_closed(
    verification: tuple[ProviderFixture, TokenVerifier],
    change: dict[str, object],
) -> None:
    provider, verifier = verification
    with pytest.raises(ApiProblem) as failure:
        verifier.verify(provider.token(change))
    assert failure.value.status == 401


@pytest.mark.parametrize(
    "claim", ["exp", "iat", "sub", "iss", "aud", "session_id", "email", "is_anonymous"]
)
def test_required_claims_cannot_be_omitted(
    verification: tuple[ProviderFixture, TokenVerifier],
    claim: str,
) -> None:
    provider, verifier = verification
    claims = provider.claims()
    del claims[claim]
    token = jwt.encode(claims, provider.key, algorithm="ES256", headers={"kid": provider.kid})
    with pytest.raises(ApiProblem) as failure:
        verifier.verify(token)
    assert failure.value.status == 401


def test_forged_signature_and_symmetric_algorithm_are_rejected(
    verification: tuple[ProviderFixture, TokenVerifier],
) -> None:
    provider, verifier = verification
    other_key = ec.generate_private_key(ec.SECP256R1())
    tokens = [
        jwt.encode(provider.claims(), other_key, algorithm="ES256", headers={"kid": provider.kid}),
        jwt.encode(
            provider.claims(),
            "isolated-test-secret-" * 4,
            algorithm="HS256",
            headers={"kid": provider.kid},
        ),
        "malformed",
        "x" * 16_385,
    ]
    for token in tokens:
        with pytest.raises(ApiProblem) as failure:
            verifier.verify(token)
        assert failure.value.status == 401


def test_token_supplied_key_urls_are_never_followed(
    verification: tuple[ProviderFixture, TokenVerifier],
) -> None:
    provider, verifier = verification
    token = jwt.encode(
        provider.claims(),
        provider.key,
        algorithm="ES256",
        headers={"kid": provider.kid, "jku": "https://untrusted.example/keys"},
    )
    with pytest.raises(ApiProblem):
        verifier.verify(token)
    assert not provider.requests


def test_unknown_key_refresh_is_bounded_and_recovers_after_rotation(
    verification: tuple[ProviderFixture, TokenVerifier],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, verifier = verification
    now = time.monotonic()
    monkeypatch.setattr("app.core.identity.time.monotonic", lambda: now)
    verifier.verify(provider.token())
    provider.kid = "rotated-key"
    provider.key = ec.generate_private_key(ec.SECP256R1())
    for _ in range(3):
        with pytest.raises(ApiProblem) as failure:
            verifier.verify(provider.token())
        assert failure.value.status == 401
    assert len(provider.requests) == 1
    monkeypatch.setattr("app.core.identity.time.monotonic", lambda: now + 31)
    assert str(verifier.verify(provider.token()).user_id) == provider.user_id
    assert len(provider.requests) == 2


def test_jwks_failure_is_unavailable_and_not_anonymous(
    verification: tuple[ProviderFixture, TokenVerifier],
) -> None:
    provider, verifier = verification
    provider.failures["/auth/v1/.well-known/jwks.json"] = (503, {"message": "private key detail"})
    for _ in range(2):
        with pytest.raises(ApiProblem) as failure:
            verifier.verify(provider.token())
        assert failure.value.status == 503
        assert "private key detail" not in failure.value.message
    assert len(provider.requests) == 1


@pytest.mark.parametrize(("seconds_ahead", "accepted"), [(0, True), (5, True), (6, False)])
def test_issued_at_clock_difference_is_bounded_to_five_seconds(
    verification: tuple[ProviderFixture, TokenVerifier],
    monkeypatch: pytest.MonkeyPatch,
    seconds_ahead: int,
    accepted: bool,
) -> None:
    provider, verifier = verification
    now = int(time.time())
    monkeypatch.setattr("app.core.identity.time.time", lambda: float(now))
    token = provider.token({"iat": now + seconds_ahead})
    if accepted:
        assert str(verifier.verify(token).user_id) == provider.user_id
    else:
        with pytest.raises(ApiProblem) as failure:
            verifier.verify(token)
        assert failure.value.status == 401


@pytest.mark.parametrize("claim", ["exp", "nbf"])
def test_issued_at_tolerance_never_extends_expiration_or_not_before(
    verification: tuple[ProviderFixture, TokenVerifier],
    claim: str,
) -> None:
    provider, verifier = verification
    now = int(time.time())
    claims: dict[str, object] = {"iat": now - 10, claim: now - 1 if claim == "exp" else now + 3}
    with pytest.raises(ApiProblem) as failure:
        verifier.verify(provider.token(claims))
    assert failure.value.status == 401
