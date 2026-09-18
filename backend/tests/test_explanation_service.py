import asyncio
from typing import Any, cast
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
        super().__init__(cast(Any, None), MockExplanationProvider())
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
