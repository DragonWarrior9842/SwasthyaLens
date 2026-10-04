"""Explicit one-request acceptance capability; never selected by normal app startup."""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from app.core.ai_config import AISettings

if TYPE_CHECKING:
    from app.core.explanation_provider import OpenAIExplanationProvider

ACCEPTANCE_MODEL = "gpt-6.1-sol"
ACCEPTANCE_OUTPUT_TOKENS = 1536
ACCEPTANCE_REQUEST_BYTES = 10000


class OneShotOpenAITransport(httpx.AsyncHTTPTransport):
    """No redirects/retries; exclusive durable marker fences repeat invocations."""

    def __init__(self, marker: Path) -> None:
        super().__init__(retries=0, trust_env=False)
        self.marker = marker
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if (
            os.environ.get("RUN_AI_INTEGRATION") != "1"
            or self.calls != 0
            or request.method != "POST"
            or str(request.url) != "https://api.openai.com/v1/responses"
        ):
            raise RuntimeError("Single-request acceptance boundary rejected request")
        body = json.loads(request.content)
        if (
            len(request.content) > ACCEPTANCE_REQUEST_BYTES
            or body.get("model") != ACCEPTANCE_MODEL
            or body.get("max_output_tokens") != ACCEPTANCE_OUTPUT_TOKENS
            or body.get("reasoning") != {"effort": "low"}
            or body.get("store") is not False
            or body.get("tools") != []
            or body.get("tool_choice") != "none"
            or body.get("service_tier") != "default"
        ):
            raise RuntimeError("Acceptance model, cost or tool boundary rejected request")
        # Create BEFORE dispatch; an indeterminate failure still consumes authorization.
        # Never delete this marker to retry. Another attempt needs fresh authorization.
        with self.marker.open("x", encoding="utf-8") as output:
            output.write('"Single OpenAI acceptance authorization reserved before dispatch"\n')
            output.flush()
            os.fsync(output.fileno())
        self.calls += 1
        return await super().handle_async_request(request)


def create_acceptance_provider(settings: AISettings, marker: Path) -> "OpenAIExplanationProvider":
    from app.core.explanation_provider import OpenAIExplanationProvider

    if settings.ai_provider != "openai" or settings.ai_model != ACCEPTANCE_MODEL:
        raise ValueError("Acceptance requires the explicitly selected OpenAI model")
    if settings.ai_api_key is None:
        raise ValueError("Acceptance requires a private server-side credential")
    if marker.exists():
        raise ValueError("Acceptance authorization already consumed; no retry permitted")
    return OpenAIExplanationProvider(
        settings,
        OneShotOpenAITransport(marker),
        max_output_tokens=ACCEPTANCE_OUTPUT_TOKENS,
    )
