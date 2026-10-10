import asyncio
from typing import Any, cast
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.explanation_context import CATALOG_VERSION, MODEL, PROMPT_VERSION, SCHEMA_VERSION
from app.core.explanations import ExplanationService
from app.core.identity import VerifiedIdentity
from app.schemas.explanations import ExplanationInput
from tests.explanation_fixtures import MockExplanationProvider, synthetic_sources


class RepositoryFixture(ExplanationService):
    def __init__(self) -> None:
        observations = Mock()
        observations.parameters.extraction.settings.secure_cookies = False
        super().__init__(observations, MockExplanationProvider())
        self.owner, self.report = uuid4(), uuid4()
        self.current = AuthenticatedRequest(
            VerifiedIdentity(self.owner, uuid4(), "synthetic@example.invalid", 1), "synthetic", 1
        )
        self.value: dict[str, Any] = {
            "user_id": str(self.owner),
            "report_id": str(self.report),
            "evidence": [s.model_dump(mode="json") for s in synthetic_sources()[:2]],
            "evaluation_enrolled": True,
            "created": False,
            "reserved_cents": 0,
            "record": None,
        }
        self.operations: list[str] = []
        self.finish_stale = False

    def rpc(
        self,
        operation: str,
        report: UUID,
        current: AuthenticatedRequest,
        payload: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        self.operations.append(operation)
        if operation == "request" and self.value["record"] is None:
            self.value["created"] = True
            self.value["record"] = {
                "id": str(uuid4()),
                "report_id": str(self.report),
                "user_id": str(self.owner),
                "status": "generating",
                "provider": "mock-test",
                "model": MODEL,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "catalog_version": CATALOG_VERSION,
                "created_at": "2026-09-18T00:00:00Z",
                "expires_at": "2026-10-18T00:00:00Z",
                "finished_at": None,
                "error_category": None,
                "output": None,
                "evidence": self.value["evidence"],
            }
        elif operation == "finish":
            assert payload is not None
            self.value["record"].update(payload)
            self.value["record"].update(status="ready", finished_at="2026-09-18T00:00:01Z")
            if self.finish_stale:
                self.value["record"].update(status="stale", output=None, evidence=[])
                self.value["evidence"] = []
            self.value["created"] = False
        return self.value


def test_generation_snapshot_validation_and_idempotent_reuse() -> None:
    service = RepositoryFixture()
    body = ExplanationInput(idempotency_key=uuid4(), consent=True)
    result = asyncio.run(service.generate(service.report, body, service.current))
    assert result.record and result.record.status == "ready" and len(result.record.items) == 2
    replay = asyncio.run(service.generate(service.report, body, service.current))
    assert replay.record == result.record
    assert cast(MockExplanationProvider, service.provider).calls == 1
    assert service.operations == ["state", "request", "finish", "state", "request"]


def test_release_rejects_stored_mock_record() -> None:
    service = RepositoryFixture()
    asyncio.run(
        service.generate(
            service.report, ExplanationInput(idempotency_key=uuid4(), consent=True), service.current
        )
    )
    cast(Mock, service.observations).parameters.extraction.settings.secure_cookies = True
    with pytest.raises(ApiProblem):
        service.get(service.report, service.current)


def test_concurrent_source_correction_never_returns_stale_items() -> None:
    service = RepositoryFixture()
    service.finish_stale = True
    result = asyncio.run(
        service.generate(
            service.report, ExplanationInput(idempotency_key=uuid4(), consent=True), service.current
        )
    )
    assert result.record and result.record.status == "stale" and result.record.items == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("user_id", str(uuid4())),
        ("report_id", str(uuid4())),
        ("model", "unapproved"),
        ("prompt_version", "old"),
    ],
)
def test_stored_record_identity_and_version_revalidated(field: str, value: str) -> None:
    service = RepositoryFixture()
    asyncio.run(
        service.generate(
            service.report, ExplanationInput(idempotency_key=uuid4(), consent=True), service.current
        )
    )
    service.value["record"][field] = value
    with pytest.raises(ApiProblem):
        service.get(service.report, service.current)


def test_stored_result_rechecked_against_current_evidence() -> None:
    service = RepositoryFixture()
    asyncio.run(
        service.generate(
            service.report, ExplanationInput(idempotency_key=uuid4(), consent=True), service.current
        )
    )
    service.value["record"]["output"]["items"][0]["fact"]["value"] = "132"
    with pytest.raises(ApiProblem):
        service.get(service.report, service.current)


def test_unenrolled_does_not_invoke_or_reserve() -> None:
    service = RepositoryFixture()
    service.value["evaluation_enrolled"] = False
    with pytest.raises(ApiProblem):
        asyncio.run(
            service.generate(
                service.report,
                ExplanationInput(idempotency_key=uuid4(), consent=True),
                service.current,
            )
        )
    assert service.operations == ["state"]
    assert cast(MockExplanationProvider, service.provider).calls == 0


class ConfiguredOpenAIMock(MockExplanationProvider):
    """Explicit offline injection, never used by an application factory."""

    name = "openai"
    model = "gpt-6.1-sol"


class ModelRepositoryFixture(RepositoryFixture):
    provider: ConfiguredOpenAIMock

    def __init__(self, *, legacy_reservation: bool = False) -> None:
        super().__init__()
        self.provider = ConfiguredOpenAIMock()
        self.legacy_reservation = legacy_reservation

    def rpc(
        self,
        operation: str,
        report: UUID,
        current: AuthenticatedRequest,
        payload: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        value = super().rpc(operation, report, current, payload)
        if operation == "request":
            assert payload is not None
            assert payload["provider"] == "openai"
            assert payload["model"] == "gpt-6.1-sol"
            value["record"]["provider"] = "openai"
            value["record"]["model"] = MODEL if self.legacy_reservation else payload["model"]
        return value


def test_selected_model_persists_reloads_and_stale_content_stays_hidden() -> None:
    service = ModelRepositoryFixture()
    result = asyncio.run(
        service.generate(
            service.report, ExplanationInput(idempotency_key=uuid4(), consent=True), service.current
        )
    )
    assert result.record and result.record.model == "gpt-6.1-sol"
    assert service.get(service.report, service.current).record == result.record
    assert service.provider.calls == 1
    # Mock database invalidation; SQL lifecycle remains independently verified.
    service.value["record"].update(status="stale", output=None, evidence=[])
    service.value["evidence"] = []
    stale = service.get(service.report, service.current)
    assert stale.record and stale.record.status == "stale" and stale.record.items == []
    assert service.provider.calls == 1


def test_legacy_database_reservation_stops_before_provider() -> None:
    service = ModelRepositoryFixture(legacy_reservation=True)
    with pytest.raises(ApiProblem):
        asyncio.run(
            service.generate(
                service.report,
                ExplanationInput(idempotency_key=uuid4(), consent=True),
                service.current,
            )
        )
    assert service.provider.calls == 0
    assert "finish" not in service.operations


@pytest.mark.parametrize(
    "provider,model",
    [
        ("openai", "gpt-5.6-terra"),
        ("openai", "gpt-6.1-sol"),
        ("gemini", "gemini-3.8-flash"),
        ("mock-test", "gpt-5.6-terra"),
    ],
)
def test_historical_and_selected_model_records_remain_readable(provider: str, model: str) -> None:
    service = RepositoryFixture()
    asyncio.run(
        service.generate(
            service.report, ExplanationInput(idempotency_key=uuid4(), consent=True), service.current
        )
    )
    service.value["record"].update(provider=provider, model=model)
    result = service.get(service.report, service.current)
    assert result.record and result.record.model == model
