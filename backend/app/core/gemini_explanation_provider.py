"""Synthetic-only Gemini transport. No SDK, tools, history, retries or fallback."""

import asyncio
import json
import os
import re
from collections.abc import Callable
from typing import Any

import httpx

from app.core.ai_config import GeminiSettings
from app.core.errors import ApiProblem
from app.core.explanation_context import SYSTEM_PROMPT, invalid_output, model_input, validate_output
from app.core.explanation_provider import (
    MAX_OUTPUT_TOKENS,
    MAX_REQUEST_BYTES,
    GenerationPermit,
    GenerationResult,
    context_digest,
)
from app.schemas.explanations import ModelExplanation, ModelFact

GEMINI_MODEL = "gemini-3.8-flash"
MAX_GEMINI_ATTEMPTS = 20


def provider_error_detail(status: int, content: bytes, secret: str) -> dict[str, object]:
    """Preserve provider messages/quota fields, never headers, keys or arbitrary metadata."""

    def redact(value: str) -> str:
        value = value.replace(secret, "[REDACTED]") if secret else value
        return re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED]", value)[:8192]

    result: dict[str, object] = {"http_status": status}
    try:
        error = json.loads(content)["error"]
        if type(error.get("code")) is int:
            result["code"] = error["code"]
        for field in ("status", "message"):
            if isinstance(error.get(field), str):
                result[field] = redact(error[field])
        details = []
        for item in error.get("details", [])[:20]:
            kind = item.get("@type")
            detail: dict[str, object] = {}
            if kind == "type.googleapis.com/google.rpc.QuotaFailure":
                violations = []
                for violation in item.get("violations", [])[:20]:
                    selected: dict[str, object] = {}
                    for key in ("quotaMetric", "quotaId", "quotaValue", "description"):
                        value = violation.get(key)
                        if isinstance(value, str):
                            selected[key] = redact(value)
                        elif type(value) is int:
                            selected[key] = value
                    dimensions = violation.get("quotaDimensions", {})
                    selected["quotaDimensions"] = {
                        key: redact(dimensions[key])
                        for key in ("model", "location")
                        if isinstance(dimensions.get(key), str)
                    }
                    violations.append(selected)
                detail["violations"] = violations
            elif kind == "type.googleapis.com/google.rpc.RetryInfo":
                if isinstance(item.get("retryDelay"), str):
                    detail["retryDelay"] = redact(item["retryDelay"])
            elif kind == "type.googleapis.com/google.rpc.ErrorInfo":
                for key in ("reason", "domain"):
                    if isinstance(item.get(key), str):
                        detail[key] = redact(item[key])
            if detail:
                details.append({"@type": kind, **detail})
        if details:
            result["details"] = details
    except (ValueError, KeyError, TypeError, AttributeError):
        result["diagnostic_note"] = "Provider error was not a supported JSON error envelope."
    return result


def gemini_schema(value: Any) -> Any:
    """Translate only wire-schema keywords; local strict validation stays unchanged."""
    if isinstance(value, list):
        return [gemini_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key in {"pattern", "minLength", "maxLength"}:
            continue
        if key == "const":
            result["enum"] = [item]
        else:
            result[key] = gemini_schema(item)
    return result


def gemini_request_body(context: list[ModelFact]) -> dict[str, object]:
    return {
        "store": False,
        "tools": [],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": model_input(context)}]}],
        "generationConfig": {
            "candidateCount": 1,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "responseModalities": ["TEXT"],
            "responseMimeType": "application/json",
            "responseJsonSchema": gemini_schema(ModelExplanation.model_json_schema()),
            "thinkingConfig": {"thinkingLevel": "LOW", "includeThoughts": False},
        },
    }


class GeminiExplanationProvider:
    name = "gemini"

    def __init__(
        self,
        settings: GeminiSettings,
        transport: httpx.AsyncBaseTransport | None = None,
        *,
        error_observer: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self.settings = settings
        self._transport = transport
        self._error_observer = error_observer

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
            or permit.reserved_cents != 0
            or type(permit.evaluation_attempt) is not int
            or not 1 <= permit.evaluation_attempt <= MAX_GEMINI_ATTEMPTS
            or permit.context_digest != context_digest(context)
            or not permit.generation_id.int
        ):
            raise ApiProblem(
                403,
                "explanation_evaluation_only",
                "Only enrolled synthetic evaluation reports are enabled.",
            )
        body = json.dumps(
            gemini_request_body(context), ensure_ascii=False, separators=(",", ":")
        ).encode()
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
                        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
                        content=body,
                        headers={
                            "x-goog-api-key": self.settings.ai_api_key.get_secret_value(),
                            "Content-Type": "application/json",
                        },
                    ) as response:
                        if response.status_code != 200:
                            if self._error_observer is not None:
                                error_content = bytearray()
                                async for chunk in response.aiter_bytes():
                                    error_content.extend(chunk)
                                    if len(error_content) > 131072:
                                        error_content.clear()
                                        break
                                self._error_observer(
                                    provider_error_detail(
                                        response.status_code,
                                        bytes(error_content),
                                        self.settings.ai_api_key.get_secret_value(),
                                    )
                                )
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
                504, "explanation_timeout", "Explanation generation timed out."
            ) from None
        except httpx.HTTPError:
            raise ApiProblem(
                503, "explanation_network", "The explanation service could not be reached."
            ) from None
        except ValueError:
            raise invalid_output() from None
        try:
            raw = json.loads(content)
            if raw.get("modelVersion") != GEMINI_MODEL or raw.get("promptFeedback", {}).get(
                "blockReason"
            ):
                raise ValueError
            candidates = raw["candidates"]
            if not isinstance(candidates, list) or len(candidates) != 1:
                raise ValueError
            candidate = candidates[0]
            if (
                candidate.get("finishReason") != "STOP"
                or "groundingMetadata" in candidate
                or "urlContextMetadata" in candidate
                or any(r.get("blocked") for r in candidate.get("safetyRatings", []))
                or candidate["content"].get("role") != "model"
            ):
                raise ValueError
            parts = candidate["content"]["parts"]
            if (
                not isinstance(parts, list)
                or len(parts) != 1
                or not isinstance(parts[0], dict)
                or set(parts[0]) - {"text", "thoughtSignature"}
                or not isinstance(parts[0].get("text"), str)
            ):
                raise ValueError
            parsed = validate_output(json.loads(parts[0]["text"]), context)
            usage = raw["usageMetadata"]
            inputs, outputs, thoughts, total = (
                usage["promptTokenCount"],
                usage["candidatesTokenCount"],
                usage.get("thoughtsTokenCount", 0),
                usage["totalTokenCount"],
            )
            if (
                any(type(n) is not int or n < 0 for n in (inputs, outputs, thoughts, total))
                or inputs > 53000
                or outputs + thoughts > MAX_OUTPUT_TOKENS
                or total != inputs + outputs + thoughts
                or usage.get("cachedContentTokenCount", 0) != 0
                or usage.get("toolUsePromptTokenCount", 0) != 0
            ):
                raise ValueError
            # Account for hidden thinking as well as the visible structured result.
            return GenerationResult(parsed, inputs, outputs + thoughts)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise invalid_output() from None
