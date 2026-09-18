"""One stateless, tool-free OpenAI request; no implicit retries or fallback."""

import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx

from app.core.ai_config import AISettings
from app.core.errors import ApiProblem
from app.core.explanation_context import (
    MODEL,
    SYSTEM_PROMPT,
    invalid_output,
    model_input,
    validate_output,
)
from app.schemas.explanations import ModelExplanation, ModelFact

MAX_REQUEST_BYTES = 48000
MAX_OUTPUT_TOKENS = 4000
# Database reserves 25 cents permanently BEFORE invocation. No refund, even on error.
# <48K UTF-8 request bytes + 5K framing tokens at $2.50/M (cache-write premium)
# + 4K output at $12/M is <$0.181. Reservation includes additional margin.
RESERVATION_CENTS = 25


def context_digest(context: list[ModelFact]) -> str:
    return hashlib.sha256(
        json.dumps([f.model_dump() for f in context], sort_keys=True).encode()
    ).hexdigest()


@dataclass(frozen=True)
class GenerationPermit:
    generation_id: UUID
    context_digest: str
    synthetic_enrolled: bool
    reserved_cents: int


@dataclass(frozen=True)
class GenerationResult:
    output: ModelExplanation
    input_tokens: int
    output_tokens: int


class ExplanationProvider(Protocol):
    name: str

    @property
    def available(self) -> bool: ...

    async def generate(
        self, context: list[ModelFact], permit: GenerationPermit
    ) -> GenerationResult: ...


def request_body(context: list[ModelFact]) -> dict[str, object]:
    return {
        "model": MODEL,
        "store": False,
        "stream": False,
        "background": False,
        "tools": [],
        "tool_choice": "none",
        "parallel_tool_calls": False,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "reasoning": {"effort": "none"},
        "service_tier": "default",
        "instructions": SYSTEM_PROMPT,
        "input": [
            {"role": "user", "content": [{"type": "input_text", "text": model_input(context)}]}
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "report_education_v1",
                "strict": True,
                "schema": ModelExplanation.model_json_schema(),
            }
        },
    }


class OpenAIExplanationProvider:
    name = "openai"

    def __init__(
        self, settings: AISettings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings = settings
        self._transport = transport

    @property
    def available(self) -> bool:
        return os.environ.get("RUN_AI_INTEGRATION") == "1" and self.settings.ai_api_key is not None

    async def generate(
        self, context: list[ModelFact], permit: GenerationPermit
    ) -> GenerationResult:
        if not self.available:
            raise ApiProblem(
                503, "explanation_disabled", "Live explanation evaluation is not enabled."
            )
        if (
            not permit.synthetic_enrolled
            or permit.reserved_cents != RESERVATION_CENTS
            or permit.context_digest != context_digest(context)
            or not permit.generation_id.int
        ):
            raise ApiProblem(
                403,
                "explanation_evaluation_only",
                "Only enrolled synthetic evaluation reports are enabled.",
            )
        body = json.dumps(request_body(context), ensure_ascii=False, separators=(",", ":")).encode()
        if len(body) > MAX_REQUEST_BYTES:
            raise ApiProblem(
                413, "explanation_evidence", "The explanation request exceeds its size limit."
            )
        assert self.settings.ai_api_key is not None
        try:
            async with asyncio.timeout(45):
                async with httpx.AsyncClient(
                    transport=self._transport,
                    timeout=httpx.Timeout(40, connect=5),
                    follow_redirects=False,
                    trust_env=False,
                ) as client:
                    async with client.stream(
                        "POST",
                        "https://api.openai.com/v1/responses",
                        content=body,
                        headers={
                            "Authorization": "Bearer "
                            + self.settings.ai_api_key.get_secret_value(),
                            "Content-Type": "application/json",
                        },
                    ) as response:
                        if response.status_code != 200:
                            category = {
                                401: "authentication",
                                403: "authentication",
                                429: "rate_limit",
                            }.get(response.status_code, "provider_failure")
                            raise ApiProblem(
                                503,
                                "explanation_" + category,
                                "The explanation service is temporarily unavailable.",
                            )
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > 131072:
                                raise ValueError
        except (TimeoutError, httpx.TimeoutException):
            raise ApiProblem(
                504, "explanation_timeout", "Explanation generation timed out. Please try again."
            ) from None
        except httpx.HTTPError:
            raise ApiProblem(
                503, "explanation_network", "The explanation service could not be reached."
            ) from None
        except ValueError:
            raise invalid_output() from None
        try:
            raw = json.loads(content)
            if not isinstance(raw, dict) or raw.get("status") != "completed" or raw.get("error"):
                raise ValueError
            if raw.get("model") != MODEL or raw.get("store") is not False:
                raise ValueError
            output = raw.get("output")
            if not isinstance(output, list) or len(output) != 1:
                raise ValueError
            message = output[0]
            if (
                message.get("type") != "message"
                or message.get("role") != "assistant"
                or message.get("status") != "completed"
            ):
                raise ValueError
            parts = message.get("content")
            if (
                not isinstance(parts, list)
                or len(parts) != 1
                or parts[0].get("type") != "output_text"
            ):
                raise ValueError
            parsed = validate_output(json.loads(parts[0]["text"]), context)
            usage = raw["usage"]
            input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
            if (
                type(input_tokens) is not int
                or type(output_tokens) is not int
                or not 0 <= input_tokens <= 53000
                or not 0 <= output_tokens <= MAX_OUTPUT_TOKENS
            ):
                raise ValueError
            return GenerationResult(parsed, input_tokens, output_tokens)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ApiProblem(
                502,
                "explanation_invalid",
                "The explanation could not be verified. Please try again.",
            ) from None
