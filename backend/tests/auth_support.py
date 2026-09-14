"""Synthetic identities/keys live only in isolated tests."""

import json
import time
from dataclasses import dataclass, field
from typing import cast
from uuid import uuid4

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import SecretStr

from app.core.config import Settings

ORIGIN = "http://127.0.0.1:5173"
PROJECT = "https://unit-test-project.supabase.co"


def auth_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "cors_allowed_origins": (ORIGIN,), "app_origin": ORIGIN,
        "supabase_url": PROJECT,
        "supabase_publishable_key": SecretStr("sb_publishable_isolated_test_value"),
        "csrf_signing_key": SecretStr("isolated-test-signing-key-" + "x" * 43),
    }
    values.update(overrides)
    # model_validate avoids local .env; fields are always explicit test inputs.
    return Settings.model_validate(values)


@dataclass
class ProviderFixture:
    user_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = field(default_factory=lambda: str(uuid4()))
    email: str = "account@example.com"
    key: ec.EllipticCurvePrivateKey = field(
        default_factory=lambda: ec.generate_private_key(ec.SECP256R1())
    )
    kid: str = "test-signing-key"
    active: bool = True
    session_end: int = field(default_factory=lambda: int(time.time()) + 1800)
    requests: list[httpx.Request] = field(default_factory=list)
    failures: dict[str, tuple[int, object]] = field(default_factory=dict)
    name: str | None = None
    language: str = "en"
    timezone: str = "UTC"
    profile_exists: bool = False
    settings_exist: bool = False

    def claims(self) -> dict[str, object]:
        now = int(time.time())
        return {
            "sub": self.user_id, "session_id": self.session_id,
            "email": self.email, "role": "authenticated", "is_anonymous": False,
            "iss": PROJECT + "/auth/v1", "aud": "authenticated", "iat": now, "exp": now + 3600,
        }

    def token(self, changes: dict[str, object] | None = None) -> str:
        claims = self.claims()
        claims.update(changes or {})
        return jwt.encode(claims, self.key, algorithm="ES256", headers={"kid": self.kid})

    def jwk(self) -> dict[str, object]:
        key = cast(dict[str, object], json.loads(jwt.algorithms.ECAlgorithm.to_jwk(self.key.public_key())))
        key.update({"alg": "ES256", "kid": self.kid, "use": "sig"})
        return key

    def session_payload(self) -> dict[str, object]:
        return {"access_token": self.token(), "refresh_token": "isolated-refresh-token", "token_type": "bearer"}

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert str(request.url).startswith(PROJECT + "/")
        path = request.url.path
        if path in self.failures:
            status, payload = self.failures[path]
            return httpx.Response(status, json=payload)
        if path == "/auth/v1/.well-known/jwks.json":
            return httpx.Response(200, json={"keys": [self.jwk()]})
        if path in {"/auth/v1/signup", "/auth/v1/resend"}:
            return httpx.Response(200, json={})
        if path in {"/auth/v1/token", "/auth/v1/verify"}:
            return httpx.Response(200, json=self.session_payload())
        if path == "/auth/v1/logout":
            self.active = False
            return httpx.Response(204)
        if path == "/rest/v1/rpc/session_context":
            return httpx.Response(200, json={"active": self.active, "expires_at": self.session_end})
        if path in {"/rest/v1/profiles", "/rest/v1/user_settings"}:
            profile = path.endswith("profiles")
            if request.method == "POST":
                if profile:
                    self.profile_exists = True
                else:
                    self.settings_exist = True
                return httpx.Response(201)
            assert request.url.params["id" if profile else "user_id"] == f"eq.{self.user_id}"
            if request.method == "PATCH":
                data = json.loads(request.content)
                if profile:
                    self.name = data["display_name"]
                else:
                    self.language = data.get("preferred_language", self.language)
                    self.timezone = data.get("timezone", self.timezone)
            row: dict[str, object] = {
                "created_at": "2026-09-14T00:00:00Z", "updated_at": "2026-09-14T00:00:00Z",
            }
            row.update(
                {"id": self.user_id, "display_name": self.name} if profile else
                {"user_id": self.user_id, "preferred_language": self.language, "timezone": self.timezone}
            )
            return httpx.Response(200, json=[row])
        raise AssertionError(f"Unexpected provider endpoint {request.method} {path}")
