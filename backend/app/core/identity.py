"""ES256 verification against a fixed issuer's bounded public-key cache."""

import time
from dataclasses import dataclass
from threading import Lock
from uuid import UUID

import jwt

from app.core.errors import unauthenticated, unavailable
from app.core.provider import SupabaseGateway


@dataclass(frozen=True)
class VerifiedIdentity:
    user_id: UUID
    session_id: UUID
    email: str
    expires_at: int


class TokenVerifier:
    def __init__(self, gateway: SupabaseGateway) -> None:
        self.gateway = gateway
        self.issuer = gateway.origin + "/auth/v1"
        self._keys: dict[str, jwt.PyJWK] = {}
        self._loaded_at = 0.0
        self._last_attempt = 0.0
        self._lock = Lock()

    def _key(self, kid: str) -> jwt.PyJWK:
        with self._lock:
            now = time.monotonic()
            expired = not self._keys or now - self._loaded_at >= 600
            if expired or (kid not in self._keys and now - self._last_attempt >= 30):
                if self._last_attempt and now - self._last_attempt < 30:
                    raise unavailable()
                self._last_attempt = now
                response = self.gateway.object("GET", "/auth/v1/.well-known/jwks.json")
                raw_keys = response.get("keys")
                if not isinstance(raw_keys, list) or not 1 <= len(raw_keys) <= 20:
                    raise unavailable()
                keys: dict[str, jwt.PyJWK] = {}
                for raw in raw_keys:
                    if not isinstance(raw, dict):
                        continue
                    raw_kid = raw.get("kid")
                    if (
                        not isinstance(raw_kid, str)
                        or not 1 <= len(raw_kid) <= 128
                        or raw.get("alg") != "ES256"
                        or raw.get("kty") != "EC"
                        or raw.get("crv") != "P-256"
                        or raw.get("use", "sig") != "sig"
                        or "d" in raw
                    ):
                        continue
                    try:
                        keys[raw_kid] = jwt.PyJWK.from_dict(raw, algorithm="ES256")
                    except (jwt.PyJWTError, ValueError, TypeError):
                        raise unavailable() from None
                if not keys:
                    raise unavailable()
                self._keys = keys
                self._loaded_at = now
            key = self._keys.get(kid)
            if key is None:
                raise unauthenticated()
            return key

    def verify(self, token: str, *, allow_expired: bool = False) -> VerifiedIdentity:
        if not 1 <= len(token) <= 16_384:
            raise unauthenticated()
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if (
                header.get("alg") != "ES256"
                or not isinstance(kid, str)
                or not 1 <= len(kid) <= 128
                or not kid.isascii()
                or any(name in header for name in ("jku", "x5u", "jwk", "crit"))
            ):
                raise unauthenticated()
            key = self._key(kid)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["ES256"],
                issuer=self.issuer,
                audience="authenticated",
                options={
                    "require": ["exp", "iat", "sub", "iss", "aud", "session_id", "email"],
                    "verify_exp": not allow_expired,
                    "strict_aud": True,
                },
            )
            expiration, issued = claims["exp"], claims["iat"]
            subject, session = claims["sub"], claims["session_id"]
            email = claims["email"]
            if (
                type(expiration) is not int
                or type(issued) is not int
                or expiration <= issued
                or claims.get("role") != "authenticated"
                or claims.get("is_anonymous") is not False
                or not isinstance(subject, str)
                or not isinstance(session, str)
                or not isinstance(email, str)
                or not 3 <= len(email) <= 254
                or "@" not in email
            ):
                raise unauthenticated()
            user_id, session_id = UUID(subject), UUID(session)
            if (
                str(user_id) != subject
                or str(session_id) != session
                or not user_id.int
                or not session_id.int
            ):
                raise unauthenticated()
            return VerifiedIdentity(user_id, session_id, email, expiration)
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise unauthenticated() from None
