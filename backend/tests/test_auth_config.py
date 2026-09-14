"""Unsafe deployment/configuration combinations fail before serving requests."""

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from tests.auth_support import auth_settings


@pytest.mark.parametrize(
    "changes",
    [
        {"supabase_url": None},
        {"supabase_publishable_key": None},
        {"csrf_signing_key": None},
        {"supabase_publishable_key": SecretStr("sb_secret_must_never_be_used")},
        {"csrf_signing_key": SecretStr("too-short")},
        {"supabase_url": "http://unit-test-project.supabase.co"},
        {"supabase_url": "https://user:password@unit-test-project.supabase.co"},
        {"supabase_url": "https://unit-test-project.supabase.co/path"},
        {"app_origin": "http://public.example"},
        {"cors_allowed_origins": ("https://unrelated.example",)},
        {"environment": "production"},
        {
            "environment": "production",
            "app_origin": "https://app.example",
            "cors_allowed_origins": (),
        },
    ],
)
def test_invalid_auth_configuration_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        auth_settings(**changes)


def test_auth_values_do_not_appear_in_configuration_errors() -> None:
    with pytest.raises(ValidationError) as failure:
        auth_settings(csrf_signing_key=SecretStr("private-test-value"))
    assert "private-test-value" not in str(failure.value)


def test_health_only_mode_has_no_credentials() -> None:
    assert not Settings(_env_file=None).auth_enabled
