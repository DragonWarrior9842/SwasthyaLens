"""Validated server configuration with explicit local development defaults."""

import os
import re
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


class Settings(BaseSettings):
    """Load backend/.env and environment overrides without accepting blank overrides."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="forbid",
        hide_input_in_errors=True,
    )

    cors_allowed_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    environment: Literal["development", "test", "staging", "production"] = "development"
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver")
    app_origin: str = "http://127.0.0.1:5173"
    supabase_url: str | None = None
    supabase_publishable_key: SecretStr | None = None
    csrf_signing_key: SecretStr | None = None
    auth_rate_limit_mode: Literal["local", "edge"] = "local"
    report_max_upload_bytes: int = Field(default=5_242_880, ge=1, le=5_242_880)
    report_processing_max_pages: int = Field(default=20, ge=1, le=20)
    report_processing_timeout_seconds: int = Field(default=120, ge=5, le=120)
    ocr_tessdata_dir: str | None = None
    report_processing_key: SecretStr | None = None

    @property
    def auth_enabled(self) -> bool:
        return self.supabase_url is not None

    @property
    def secure_cookies(self) -> bool:
        return self.environment in {"staging", "production"}

    @field_validator("allowed_hosts")
    @classmethod
    def validate_hosts(cls, hosts: tuple[str, ...]) -> tuple[str, ...]:
        if not hosts or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host) or ".." in host
            for host in hosts
        ):
            raise ValueError("ALLOWED_HOSTS requires exact lowercase hostnames without ports")
        return hosts

    @model_validator(mode="after")
    def validate_release(self) -> Self:
        if not self.secure_cookies:
            return self
        if any(
            name in os.environ
            for name in (
                "RUN_AI_INTEGRATION",
                "RUN_SUPABASE_INTEGRATION",
                "RUN_OCR_EVALUATION",
                "DISPOSABLE_TEST_ACCOUNTS_CONFIRMED",
            )
        ):
            raise ValueError("Release environments cannot enable integration test flags")
        host = urlsplit(self.app_origin).hostname
        if host not in self.allowed_hosts or any(
            item in {"localhost", "127.0.0.1", "testserver"}
            or item.endswith((".localhost", ".example", ".invalid", ".test"))
            or item in {"example.com", "example.org", "example.net"}
            for item in self.allowed_hosts
        ):
            raise ValueError(
                "Release ALLOWED_HOSTS must include the chosen public application host"
            )
        for secret in (
            self.supabase_publishable_key,
            self.csrf_signing_key,
            self.report_processing_key,
        ):
            value = secret.get_secret_value() if secret else ""
            if (
                len(value) < 40
                or any(
                    marker in value.lower()
                    for marker in (
                        "placeholder",
                        "replace",
                        "change-me",
                        "changeme",
                        "your-",
                        "your_",
                        "example",
                        "isolated",
                        "synthetic",
                        "<",
                        ">",
                    )
                )
                or len(set(value)) < 12
            ):
                raise ValueError("Release credentials must be configured non-placeholder values")
        if not self.ocr_tessdata_dir or not Path(self.ocr_tessdata_dir).is_absolute():
            raise ValueError("Release OCR_TESSDATA_DIR must be an absolute model directory")
        return self

    @field_validator("app_origin")
    @classmethod
    def validate_app_origin(cls, origin: str) -> str:
        cls.validate_cors_origins((origin,))
        return origin

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or value != f"https://{parsed.netloc}"
            or parsed.port not in (None, 443)
        ):
            raise ValueError("SUPABASE_URL must be an exact HTTPS project origin")
        return value

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> Self:
        configured = (self.supabase_url, self.supabase_publishable_key, self.csrf_signing_key)
        if any(item is not None for item in configured):
            if not all(item is not None for item in configured):
                raise ValueError("All three Supabase and CSRF settings must be configured together")
            assert self.supabase_publishable_key is not None
            assert self.csrf_signing_key is not None
            if not self.supabase_publishable_key.get_secret_value().startswith("sb_publishable_"):
                raise ValueError("Only a Supabase publishable key is accepted")
            if len(self.csrf_signing_key.get_secret_value()) < 43:
                raise ValueError(
                    "CSRF_SIGNING_KEY requires at least 32 random bytes encoded as text"
                )
            parsed = urlsplit(self.app_origin)
            if self.environment in {"development", "test"} and (
                parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            ):
                raise ValueError(
                    "Development authentication is restricted to an HTTP loopback origin"
                )
            if self.secure_cookies and (
                parsed.scheme != "https" or self.auth_rate_limit_mode != "edge"
            ):
                raise ValueError(
                    "Production requires HTTPS and externally enforced auth rate limits"
                )
            if set(self.cors_allowed_origins) - {self.app_origin}:
                raise ValueError("Authenticated CORS origins must match APP_ORIGIN exactly")
        elif self.secure_cookies:
            raise ValueError("Production requires authentication configuration")
        return self

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, origins: tuple[str, ...]) -> tuple[str, ...]:
        """Accept exact browser origins, never wildcards or URLs containing a path."""
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or "*" in origin
                or any(character.isspace() for character in origin)
                or parsed.username is not None
                or parsed.password is not None
                or origin != f"{parsed.scheme}://{parsed.netloc}"
                or (parsed.port is not None and not 1 <= parsed.port <= 65535)
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
        return origins
