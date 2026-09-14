"""Strict public contracts: ownership and audit columns are never writable."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class EmailInput(InputModel):
    email: Annotated[EmailStr, Field(max_length=254)]


class LoginInput(EmailInput):
    password: SecretStr = Field(min_length=1, max_length=128)


class SignupInput(LoginInput):
    password: SecretStr = Field(min_length=12, max_length=128)


class VerificationInput(EmailInput):
    token: Annotated[str, Field(pattern=r"^[0-9]{6}$")]


class EmptyInput(InputModel):
    pass


class ProfilePatch(InputModel):
    display_name: Annotated[str | None, Field(max_length=80)] = None

    @field_validator("display_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("Display name must not contain control characters")
        return value or None


class SettingsPatch(InputModel):
    preferred_language: Literal["en", "hi"] | None = None
    timezone: Annotated[str | None, Field(min_length=1, max_length=64)] = None

    @field_validator("preferred_language", "timezone")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Setting cannot be null")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Use a valid IANA timezone") from None
        return value


class Profile(BaseModel):
    id: UUID
    display_name: str | None
    created_at: datetime
    updated_at: datetime


class UserSettings(BaseModel):
    user_id: UUID
    preferred_language: Literal["en", "hi"]
    timezone: str
    created_at: datetime
    updated_at: datetime


class PublicUser(BaseModel):
    id: UUID
    email: str


class SessionResponse(BaseModel):
    user: PublicUser
    expires_at: int


class MessageResponse(BaseModel):
    message: str


class CsrfResponse(BaseModel):
    csrf_token: str
