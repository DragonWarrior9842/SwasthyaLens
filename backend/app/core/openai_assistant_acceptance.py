"""Explicit one-use live Phase 9 capability. Normal factories never select it."""

import asyncio
import hashlib
import json
import os
from pathlib import Path

import httpx

from app.core.ai_config import AISettings
from app.core.assistant_context import PROMPT
from app.core.errors import ApiProblem
from app.core.explanation_provider import AssistantRequest
from app.core.openai_acceptance import (
    ACCEPTANCE_MODEL,
    ACCEPTANCE_OUTPUT_TOKENS,
    ACCEPTANCE_REQUEST_BYTES,
    OneShotOpenAITransport,
)
from app.schemas.assistant import MultilingualModelAnswer


class OpenAIAssistantAcceptance:
    name = "openai"
    model = ACCEPTANCE_MODEL

    def __init__(self, settings: AISettings, marker: Path) -> None:
        if settings.ai_provider != self.name or settings.ai_model != self.model:
            raise ValueError("Explicit OpenAI acceptance configuration required")
        if settings.ai_api_key is None or marker.exists():
            raise ValueError("Private key and unused authorization required")
        self.settings = settings
        self.transport = OneShotOpenAITransport(marker)
        self.expected_input_digest: str | None = None
        self.http_status: int | None = None
        self.model_confirmed = False
        self.usage: dict[str, int] = {}
        self.error_code: str | None = None

    @property
    def assistant_available(self) -> bool:
        return os.environ.get("RUN_AI_INTEGRATION") == "1" and self.transport.calls == 0

    async def generate_assistant(self, request: AssistantRequest) -> object:
        if (
            not self.assistant_available
            or self.expected_input_digest is None
            or hashlib.sha256(request.input_json.encode()).hexdigest() != self.expected_input_digest
            or request.instructions != PROMPT
            or request.output_schema != MultilingualModelAnswer.model_json_schema()
            or request.store is not False
            or request.tools != ()
            or type(self.transport) is not OneShotOpenAITransport
        ):
            raise ApiProblem(503, "assistant_unavailable", "Acceptance context is not authorized.")
        self.expected_input_digest = None
        body = json.dumps(
            {
                "model": self.settings.ai_model,
                "store": False,
                "stream": False,
                "background": False,
                "tools": [],
                "tool_choice": "none",
                "parallel_tool_calls": False,
                "max_output_tokens": ACCEPTANCE_OUTPUT_TOKENS,
                "reasoning": {"effort": "low"},
                "service_tier": "default",
                "instructions": request.instructions,
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": request.input_json}],
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "assistant_education_v2",
                        "strict": True,
                        "schema": request.output_schema,
                    }
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        if len(body) > ACCEPTANCE_REQUEST_BYTES:
            raise ApiProblem(413, "assistant_capacity", "Acceptance request exceeds its bound.")
        assert self.settings.ai_api_key is not None
        try:
            async with (
                asyncio.timeout(40),
                httpx.AsyncClient(
                    transport=self.transport,
                    timeout=httpx.Timeout(35, connect=5),
                    follow_redirects=False,
                    trust_env=False,
                ) as client,
            ):
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/responses",
                    content=body,
                    headers={
                        "Authorization": "Bearer " + self.settings.ai_api_key.get_secret_value(),
                        "Content-Type": "application/json",
                    },
                ) as response:
                    self.http_status = response.status_code
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > 131072:
                            raise ValueError
            raw = json.loads(content)
            if self.http_status != 200:
                code = raw.get("error", {}).get("code")
                if code in (
                    "model_not_found",
                    "invalid_api_key",
                    "insufficient_quota",
                    "rate_limit_exceeded",
                ):
                    self.error_code = code
                raise ApiProblem(
                    429 if self.http_status == 429 else 503,
                    "assistant_unavailable",
                    "Provider request failed.",
                )
            if (
                raw.get("status") != "completed"
                or raw.get("error")
                or raw.get("store") is not False
            ):
                raise ValueError
            if raw.get("model") != self.settings.ai_model:
                raise ValueError
            self.model_confirmed = True
            output = raw["output"]
            if not isinstance(output, list) or not 1 <= len(output) <= 2:
                raise ValueError
            if len(output) == 2 and output[0].get("type") != "reasoning":
                raise ValueError
            message = output[-1]
            if (
                message.get("type") != "message"
                or message.get("role") != "assistant"
                or message.get("status") != "completed"
            ):
                raise ValueError
            parts = message["content"]
            if len(parts) != 1 or parts[0].get("type") != "output_text":
                raise ValueError
            usage = raw["usage"]
            for key, maximum in (
                ("input_tokens", 14096),
                ("output_tokens", ACCEPTANCE_OUTPUT_TOKENS),
            ):
                value = usage[key]
                if type(value) is not int or not 0 <= value <= maximum:
                    raise ValueError
                self.usage[key] = value
            total = usage.get("total_tokens")
            if type(total) is not int or total != sum(self.usage.values()):
                raise ValueError
            self.usage["total_tokens"] = total
            # The real service still validates exact context/language and renders
            # server-owned facts before the normal atomic persistence finish RPC.
            return MultilingualModelAnswer.model_validate_json(parts[0]["text"]).model_dump()
        except (TimeoutError, httpx.TimeoutException):
            raise ApiProblem(504, "assistant_unavailable", "Provider request timed out.") from None
        except httpx.HTTPError:
            raise ApiProblem(503, "assistant_unavailable", "Provider network failure.") from None
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ApiProblem(
                502, "assistant_invalid", "Provider output failed validation."
            ) from None
