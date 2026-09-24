"""Authorized evidence -> reserved generation -> validation -> current owned record."""

import asyncio
import logging
import time
from typing import Any, Literal, cast
from uuid import UUID

from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.explanation_context import (
    CATALOG_VERSION,
    PROMPT_VERSION,
    PROVIDER_MODELS,
    SCHEMA_VERSION,
    facts,
    render_output,
    validate_output,
)
from app.core.explanation_provider import ExplanationProvider, GenerationPermit, context_digest
from app.core.observations import ObservationService
from app.schemas.explanations import (
    ExplanationInput,
    ExplanationRecord,
    ExplanationView,
    SourceEvidence,
)

logger = logging.getLogger("swasthyalens.explanations")


def unavailable() -> ApiProblem:
    return ApiProblem(
        503, "explanation_unavailable", "Report explanations are temporarily unavailable."
    )


class ExplanationService:
    def __init__(self, observations: ObservationService, provider: ExplanationProvider) -> None:
        self.observations, self.provider = observations, provider

    def rpc(
        self,
        operation: str,
        report: UUID,
        current: AuthenticatedRequest,
        payload: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        extraction = self.observations.parameters.extraction
        secret = extraction.settings.report_processing_key
        if secret is None:
            raise unavailable()
        value = extraction.reports.gateway.request(
            "POST",
            "/rest/v1/rpc/explanation_call",
            access_token=current.access_token,
            purpose="reports",
            payload={
                "p_operation": operation,
                "p_payload": {**(payload or {}), "report_id": str(report)},
                "p_worker_secret": secret.get_secret_value(),
            },
        )
        try:
            if (
                not isinstance(value, dict)
                or UUID(value["user_id"]) != current.identity.user_id
                or UUID(value["report_id"]) != report
                or type(value["evaluation_enrolled"]) is not bool
                or type(value["created"]) is not bool
                or not isinstance(value["evidence"], list)
                or len(value["evidence"]) > 21
            ):
                raise ValueError
            return value
        except (KeyError, TypeError, ValueError, AttributeError):
            raise unavailable() from None

    def view(
        self, value: dict[str, Any], report: UUID, current: AuthenticatedRequest
    ) -> ExplanationView:
        record = None
        try:
            source = [SourceEvidence.model_validate(item) for item in value["evidence"]]
            raw = value["record"]
            if raw is not None:
                if (
                    UUID(raw["user_id"]) != current.identity.user_id
                    or UUID(raw["report_id"]) != report
                    or raw["model"] != PROVIDER_MODELS[raw["provider"]]
                    or raw["prompt_version"] != PROMPT_VERSION
                    or raw["schema_version"] != SCHEMA_VERSION
                    or raw["catalog_version"] != CATALOG_VERSION
                ):
                    raise ValueError
                items = []
                if raw["status"] == "ready":
                    stored = [SourceEvidence.model_validate(item) for item in raw["evidence"]]
                    if stored != source:
                        raise ValueError
                    parsed = validate_output(raw["output"], facts(source))
                    items = render_output(parsed, source)
                elif raw["output"] is not None:
                    raise ValueError
                record = ExplanationRecord.model_validate({**raw, "items": items})
            return ExplanationView(
                report_id=report,
                eligible_count=len(source),
                evaluation_enrolled=value["evaluation_enrolled"],
                provider_available=self.provider.available,
                provider=cast(Literal["openai", "mock-test", "gemini"], self.provider.name),
                record=record,
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            raise unavailable() from None

    def get(
        self, report: UUID, current: AuthenticatedRequest, identifier: UUID | None = None
    ) -> ExplanationView:
        value = self.rpc("state", report, current, {"id": str(identifier)} if identifier else None)
        result = self.view(value, report, current)
        if identifier and (result.record is None or result.record.id != identifier):
            raise unavailable()
        return result

    async def generate(
        self, report: UUID, body: ExplanationInput, current: AuthenticatedRequest
    ) -> ExplanationView:
        # Authorize and construct bounded context before even attempting a reservation.
        state = await asyncio.to_thread(self.rpc, "state", report, current)
        if not self.provider.available:
            raise ApiProblem(
                503, "explanation_disabled", "Live explanation evaluation is not enabled."
            )
        if not state["evaluation_enrolled"]:
            raise ApiProblem(
                403,
                "explanation_evaluation_only",
                "Only enrolled synthetic evaluation reports are enabled.",
            )
        source = [SourceEvidence.model_validate(item) for item in state["evidence"]]
        facts(source)
        value = await asyncio.to_thread(
            self.rpc,
            "request",
            report,
            current,
            {"idempotency_key": str(body.idempotency_key), "provider": self.provider.name},
        )
        if not value["created"]:
            return self.view(value, report, current)
        # The atomic request may select a newer snapshot. Never invoke with the earlier one.
        source = [SourceEvidence.model_validate(item) for item in value["evidence"]]
        context = facts(source)
        view = self.view(value, report, current)
        if (
            view.record is None
            or view.record.status != "generating"
            or view.record.provider != self.provider.name
        ):
            raise unavailable()
        identifier = view.record.id
        permit = GenerationPermit(
            identifier,
            context_digest(context),
            value["evaluation_enrolled"],
            value["reserved_cents"],
            value.get("evaluation_attempt", 0),
        )
        started = time.monotonic()
        logger.info(
            "explanation_started provider=%s evidence_count=%d", self.provider.name, len(context)
        )
        finish: dict[str, object] = {"id": str(identifier)}
        try:
            result = await self.provider.generate(context, permit)
            # All adapters, including mocks, cross the same independent validator.
            validated = validate_output(result.output.model_dump(), context)
            finish.update(
                output=validated.model_dump(),
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                error_category=None,
            )
        except ApiProblem as error:
            category = error.code.removeprefix("explanation_")
            if category not in {
                "timeout",
                "invalid",
                "authentication",
                "rate_limit",
                "network",
                "provider_failure",
            }:
                category = "provider_failure"
            finish["error_category"] = category
        except Exception:
            finish["error_category"] = "provider_failure"
        finish["duration_ms"] = min(90000, round((time.monotonic() - started) * 1000))
        # DB rechecks the active JWT session, report lock and exact source revision set.
        completed = await asyncio.to_thread(self.rpc, "finish", report, current, finish)
        result_view = self.view(completed, report, current)
        logger.info(
            "explanation_finished provider=%s status=%s duration_ms=%d",
            self.provider.name,
            result_view.record.status if result_view.record else "unavailable",
            finish["duration_ms"],
        )
        return result_view
