"""Synthetic Phase 11 boundaries. No live transport or personal health data."""

import csv
import io
import json
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core import exports
from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.exports import ExportService, serialize
from app.core.identity import VerifiedIdentity
from app.core.notifications import NotificationService
from app.core.parameter_parser import fields
from app.factory import create_app
from app.schemas.accounts import SettingsPatch
from app.schemas.exports import ExportContext, ExportInput
from app.schemas.parameters import RawFields
from tests.auth_support import ProviderFixture, auth_settings
from tests.test_auth import headers, login

OWNER = uuid4()


def body(**overrides: object) -> ExportInput:
    return ExportInput.model_validate(
        {
            "format": "json",
            "language": "en",
            "date_from": "2020-01-01",
            "date_to": "2020-12-31",
            "include_unknown": True,
            **overrides,
        }
    )


def row(value: str = "13.20", **overrides: object) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "user_id": str(OWNER),
        "source_type": "report",
        "report_id": str(uuid4()),
        "revision": 1,
        "status": "active",
        "fields": fields(
            RawFields(
                original_label="Synthetic स्रोत",
                raw_value=value,
                original_unit="ng/mL",
                raw_reference="30–100",
            )
        ).model_dump(),
        "measurement_date": None,
        "measured_at": None,
        "review_revision": 1,
        "review_action": "confirmed",
        "report_name": "synthetic.pdf",
        "report_recorded_at": "2026-09-27T00:00:00Z",
        "page_number": 1,
        "source_method": "native_text",
        **overrides,
    }


def context(*rows: dict[str, object]) -> dict[str, object]:
    return {"user_id": str(OWNER), "as_of": datetime.now(UTC).isoformat(), "items": list(rows)}


def setup_service(value: object) -> tuple[ExportService, AuthenticatedRequest, Mock]:
    observations = Mock()
    gateway = observations.parameters.extraction.reports.gateway
    gateway.object.return_value = value
    current = AuthenticatedRequest(
        VerifiedIdentity(OWNER, uuid4(), "synthetic@example.invalid", 2000000000),
        "synthetic",
        2000000000,
    )
    return ExportService(observations), current, observations


@pytest.mark.parametrize("value", ["13.20", "<5", ">10", "Negative", "Trace", "1:80", "30–100"])
@pytest.mark.parametrize("language", ["en", "hi"])
def test_exact_csv_json_values_units_ranges_unknown_dates_and_no_internal_ids(
    value: str, language: str
) -> None:
    record = row(value)
    parsed = ExportContext.model_validate(context(record))
    data = json.loads(serialize(parsed, body(language=language)))
    finding = data["observations"][0]
    assert finding["raw_value"] == value and finding["original_unit"] == "ng/mL"
    assert finding["raw_reference"] == "30–100" and finding["measurement_date"] is None
    assert finding["date_status"] == "unknown" and finding["report_name"] == "synthetic.pdf"
    assert all(str(record[key]) not in json.dumps(data) for key in ("id", "user_id", "report_id"))
    assert "parsing_version" not in json.dumps(data) and "AI" not in json.dumps(data)
    csv_data = serialize(parsed, body(format="csv", language=language))
    assert csv_data.startswith(b"\xef\xbb\xbf")
    table = list(csv.reader(io.StringIO(csv_data.decode("utf-8-sig"))))
    assert table[1][2:5] == [value, "ng/mL", "30–100"]
    assert table[1][0] == ("रिपोर्ट से" if language == "hi" else "From report")


@pytest.mark.parametrize("value", ["=SUM(1,2)", " +cmd", "-1+2", "@SUM(1)", "\t13.20", "\r1"])
def test_formula_like_source_is_rejected_as_csv_but_preserved_in_json(value: str) -> None:
    parsed = ExportContext.model_validate(context(row(value)))
    with pytest.raises(ApiProblem) as rejected:
        serialize(parsed, body(format="csv"))
    assert rejected.value.code == "export_csv_unsafe"
    assert json.loads(serialize(parsed, body()))["observations"][0]["raw_value"] == value


def test_csv_quotes_unicode_commas_and_newlines_without_changing_source() -> None:
    value = 'Negative, "Trace"\nस्रोत'
    output = serialize(ExportContext.model_validate(context(row(value))), body(format="csv"))
    assert list(csv.reader(io.StringIO(output.decode("utf-8-sig"))))[1][2] == value


@pytest.mark.parametrize(
    "change",
    [
        {"date_to": "2021-01-01"},
        {"date_to": "2019-01-01"},
        {"date_from": "2020-01-01T00:00:00Z"},
        {"date_from": "1899-01-01"},
        {"include_unknown": "true"},
        {"format": "pdf"},
        {"language": "hinglish"},
        {"user_id": str(OWNER)},
        {"source_type": "machine"},
        {"report_id": str(uuid4()), "source_type": "manual"},
    ],
)
def test_export_request_is_closed_and_bounded(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        body(**change)


@pytest.mark.parametrize(
    "change",
    [
        {"user_id": str(uuid4())},
        {"status": "superseded"},
        {"review_action": "rejected"},
        {"page_number": None},
        {"source_type": "manual"},
        {"measurement_date": "2019-01-01"},
    ],
)
def test_export_rejects_foreign_inactive_or_incoherent_source(change: dict[str, object]) -> None:
    service, current, _ = setup_service(context({**row(), **change}))
    with pytest.raises(ApiProblem):
        service.generate(body(), current)


def test_context_identity_duplicate_capacity_and_filter_guards() -> None:
    record = row()
    for payload in [
        context(record, record),
        {**context(record), "user_id": str(uuid4())},
        context(*(row() for _ in range(201))),
        context(*(row() for _ in range(21))),
    ]:
        service, current, _ = setup_service(payload)
        with pytest.raises(ApiProblem):
            service.generate(body(), current)
    service, current, _ = setup_service(context(record))
    for request in [
        body(include_unknown=False),
        body(report_id=str(uuid4())),
        body(source_type="manual"),
    ]:
        with pytest.raises(ApiProblem):
            service.generate(request, current)


def test_manual_utc_day_precision_and_export_size_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    record = row(
        report_id=None,
        source_type="manual",
        review_revision=None,
        review_action=None,
        report_name=None,
        report_recorded_at=None,
        page_number=None,
        source_method=None,
        measured_at="2020-01-02T00:15:00+05:30",
    )
    service, current, _ = setup_service(context(record))
    data = json.loads(service.generate(body(date_to="2020-01-01"), current))
    assert data["observations"][0]["measured_at"] == "2020-01-01T18:45:00+00:00"
    monkeypatch.setattr(exports, "MAX_BYTES", 10)
    with pytest.raises(ApiProblem) as rejected:
        service.generate(body(), current)
    assert rejected.value.code == "export_capacity"
    monkeypatch.setattr(exports, "MAX_BYTES", 2 * 1024 * 1024)
    monkeypatch.setattr("app.core.exports.time.monotonic", Mock(side_effect=[1, 17]))
    with pytest.raises(ApiProblem) as timeout:
        service.generate(body(), current)
    assert timeout.value.code == "export_timeout"


@pytest.mark.parametrize("value", [None, "true", 1, {}, []])
def test_notification_preference_is_a_strict_boolean(value: object) -> None:
    with pytest.raises(ValidationError):
        SettingsPatch(in_app_notifications=value)  # type: ignore[arg-type]


def notification(owner: UUID = OWNER) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "user_id": str(owner),
        "report_id": str(uuid4()),
        "event_type": "upload_completed",
        "created_at": "2026-09-27T00:00:00Z",
        "read_at": None,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"user_id": str(uuid4())},
        {"event_type": "dangerous_result"},
        {"value": "18"},
        {"read_at": "2020-01-01T00:00:00Z"},
    ],
)
def test_notification_response_rejects_foreign_medical_and_invalid_events(
    change: dict[str, object],
) -> None:
    payload = {
        "user_id": str(OWNER),
        "offset": 0,
        "unread_count": 1,
        "items": [{**notification(), **change}],
    }
    _, current, observations = setup_service(payload)
    with pytest.raises(ApiProblem):
        NotificationService(observations).call("list", current)


def test_notification_pagination_no_duplicate_and_strict_counts() -> None:
    payload = {
        "user_id": str(OWNER),
        "offset": 0,
        "unread_count": 21,
        "items": [notification() for _ in range(21)],
    }
    _, current, observations = setup_service(payload)
    service = NotificationService(observations)
    assert len(service.call("list", current).items) == 20
    assert service.call("list", current).next_offset == 20
    changes: list[dict[str, object]] = [
        {"unread_count": True},
        {"offset": 20},
        {"user_id": str(uuid4())},
        {"items": [notification()] * 2},
    ]
    for change in changes:
        observations.parameters.extraction.reports.gateway.object.return_value = {
            **payload,
            **change,
        }
        with pytest.raises(ApiProblem):
            service.call("list", current)


def test_api_auth_csrf_private_headers_no_artifact_and_revocation() -> None:
    provider = ProviderFixture()

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/rpc/export_context":
            return httpx.Response(
                200,
                json={
                    "user_id": provider.user_id,
                    "as_of": datetime.now(UTC).isoformat(),
                    "items": [],
                },
            )
        if request.url.path == "/rest/v1/rpc/notification_call":
            return httpx.Response(
                200, json={"user_id": provider.user_id, "offset": 0, "unread_count": 0, "items": []}
            )
        return provider.handle(request)

    settings = auth_settings(report_processing_key="synthetic-processing-" + "x" * 50)
    with TestClient(create_app(settings, provider_transport=httpx.MockTransport(handle))) as client:
        request_body = body().model_dump(mode="json")
        assert (
            client.post("/exports", json=request_body, headers=headers(client)).status_code == 401
        )
        assert client.get("/notifications").status_code == 401
        assert login(client).status_code == 200
        assert client.post("/exports", json=request_body).status_code == 403
        response = client.post("/exports", json=request_body, headers=headers(client))
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert (
            response.headers["content-disposition"]
            == 'attachment; filename="swasthyalens-health.json"'
        )
        assert response.json()["observations"] == []
        assert client.get(f"/exports/{uuid4()}/download").status_code == 404
        assert client.get("/notifications?user_id=forged").status_code == 422
        assert client.post("/notifications/read-all", json={}).status_code == 403
        assert (
            client.post("/notifications/read-all", json={}, headers=headers(client)).status_code
            == 200
        )
        assert (
            client.patch(
                "/settings", json={"in_app_notifications": False}, headers=headers(client)
            ).json()["in_app_notifications"]
            is False
        )
        provider.active = False
        assert (
            client.post("/exports", json=request_body, headers=headers(client)).status_code == 401
        )
        assert client.get("/notifications").status_code == 401
