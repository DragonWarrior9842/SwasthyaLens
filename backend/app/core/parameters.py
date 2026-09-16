"""Owner-scoped, bounded structured parsing and append-only review operations."""

import logging
from threading import BoundedSemaphore
from uuid import UUID

from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.extraction import ExtractionService
from app.core.parameter_parser import EXTRACTOR_VERSION, RULES_VERSION, ParserLimit, fields, parse
from app.core.reports import report_unavailable
from app.schemas.parameters import (
    ParameterHistory,
    ParameterInput,
    ParameterResult,
    ParameterRun,
    Review,
    ReviewInput,
)

logger = logging.getLogger("swasthyalens.parameters")


class ParameterService:
    def __init__(self, extraction: ExtractionService) -> None:
        self.extraction = extraction
        self.slots = BoundedSemaphore(2)

    def rpc(self, name: str, current: AuthenticatedRequest, payload: dict[str, object]) -> object:
        secret = self.extraction.settings.report_processing_key
        if secret is None:
            raise report_unavailable()
        return self.extraction.reports.gateway.request(
            "POST",
            f"/rest/v1/rpc/parameter_{name}",
            access_token=current.access_token,
            purpose="reports",
            payload={**payload, "p_worker_secret": secret.get_secret_value()},
        )

    def history(self, report_id: UUID, current: AuthenticatedRequest) -> ParameterHistory:
        value = self.rpc("history", current, {"p_report_id": str(report_id)})
        try:
            if not isinstance(value, list) or len(value) > 9:
                raise ValueError
            result = ParameterHistory(runs=[ParameterRun.model_validate(row) for row in value])
            if any(run.report_id != report_id for run in result.runs):
                raise ValueError
            return result
        except ValueError:
            raise report_unavailable() from None

    def request(
        self, report_id: UUID, body: ParameterInput, current: AuthenticatedRequest
    ) -> ParameterRun:
        if not self.slots.acquire(blocking=False):
            raise ApiProblem(429, "rate_limited", "Extraction is busy. Try again shortly.")
        try:
            # Reads only persisted Phase 4 pages under the verified owner/session.
            source = self.extraction.result(report_id, current, body.source_run_id)
            reply = self.rpc(
                "request",
                current,
                {
                    "p_report_id": str(report_id),
                    "p_source_run_id": str(body.source_run_id),
                    "p_idempotency_key": str(body.idempotency_key),
                    "p_extractor_version": EXTRACTOR_VERSION,
                    "p_rules_version": RULES_VERSION,
                },
            )
            if not isinstance(reply, dict) or not isinstance(reply.get("created"), bool):
                raise report_unavailable()
            run = ParameterRun.model_validate(reply.get("run"))
            if run.report_id != report_id or run.source_run_id != source.run.id:
                raise report_unavailable()
            if not reply["created"]:
                return run
            logger.info("parameter_extraction_started")
            error: str | None = None
            content: list[object] = []
            warnings: list[str] = []
            try:
                candidates, warnings = parse(source.pages)
                content = [candidate.model_dump(mode="json") for candidate in candidates]
            except ParserLimit:
                error = "resource_limit"
            except Exception:
                error = "parser_failure"
            self.rpc(
                "finish",
                current,
                {
                    "p_report_id": str(report_id),
                    "p_run_id": str(run.id),
                    "p_candidates": content,
                    "p_warnings": warnings,
                    "p_error": error,
                },
            )
            result = next(
                (item for item in self.history(report_id, current).runs if item.id == run.id), None
            )
            if result is None:
                raise report_unavailable()
            logger.info("parameter_extraction_%s", result.status)
            return result
        finally:
            self.slots.release()

    def result(
        self, report_id: UUID, run_id: UUID | None, current: AuthenticatedRequest
    ) -> ParameterResult:
        value = self.rpc(
            "result",
            current,
            {"p_report_id": str(report_id), "p_run_id": str(run_id) if run_id else None},
        )
        try:
            result = ParameterResult.model_validate(value)
            if (
                result.run.report_id != report_id
                or (run_id and result.run.id != run_id)
                or any(c.run_id != result.run.id for c in result.candidates)
                or result.run.candidate_count != len(result.candidates)
            ):
                raise ValueError
            return result
        except ValueError:
            raise report_unavailable() from None

    def reviews(
        self, report_id: UUID, candidate_id: UUID, current: AuthenticatedRequest
    ) -> list[Review]:
        value = self.rpc(
            "reviews", current, {"p_report_id": str(report_id), "p_candidate_id": str(candidate_id)}
        )
        if not isinstance(value, list) or len(value) > 20:
            raise report_unavailable()
        return [Review.model_validate(row) for row in value]

    def review(
        self, report_id: UUID, candidate_id: UUID, body: ReviewInput, current: AuthenticatedRequest
    ) -> Review:
        value = self.rpc(
            "review",
            current,
            {
                "p_report_id": str(report_id),
                "p_candidate_id": str(candidate_id),
                "p_idempotency_key": str(body.idempotency_key),
                "p_expected_revision": body.expected_revision,
                "p_action": body.action,
                "p_fields": fields(body.correction).model_dump(mode="json")
                if body.correction
                else None,
            },
        )
        return Review.model_validate(value)
