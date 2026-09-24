"""Separate backend-only evaluation settings; never read by Vite or default tests."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env.ai",
        extra="forbid",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        hide_input_in_errors=True,
    )
    ai_provider: Literal["openai"] = "openai"
    ai_model: Literal["gpt-5.6-terra"] = "gpt-5.6-terra"
    ai_api_key: SecretStr | None = None


class GeminiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env.ai.gemini",
        extra="forbid",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        hide_input_in_errors=True,
    )
    ai_provider: Literal["gemini"] = "gemini"
    ai_model: Literal["gemini-3.8-flash"] = "gemini-3.8-flash"
    ai_api_key: SecretStr | None = None
