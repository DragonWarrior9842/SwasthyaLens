from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.observations import manual_fields
from app.core.parameter_parser import fields
from app.factory import create_app
from app.schemas.observations import ManualInput, PublishInput
from app.schemas.parameters import RawFields
from tests.auth_support import ProviderFixture, auth_settings


def manual(**overrides: object) -> ManualInput:
    return ManualInput.model_validate(
        {
            "idempotency_key": str(uuid4()),
            "metric": "weight",
            "raw_value": "70.250",
            "unit": "kg",
            "measured_at": "2020-01-02T00:15:00+05:30",
            **overrides,
        }
    )


def test_manual_exact_decimal_and_timezone_boundary() -> None:
    body = manual()
    assert body.measured_at == datetime(2020, 1, 1, 18, 45, tzinfo=UTC)
    result = manual_fields(body)
    assert result.raw_value == result.numeric_value == "70.250"
    assert result.canonical_metric == "weight" and result.comparator is None
    assert result.calculated_range_status == "unknown"
    assert result.parsing_version is None and result.alias_version is None


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "10000",
        "70.0001",
        "1e2",
        "NaN",
        "Infinity",
        "1,2",
        "1_000",
        " 70",
        70.25,
        True,
        "<70",
    ],
)
def test_manual_rejects_unsafe_number_forms(value: object) -> None:
    with pytest.raises(ValidationError):
        manual(raw_value=value)


@pytest.mark.parametrize(
    "override",
    [
        {"unit": "bpm"},
        {"unit": "lb"},
        {"metric": "glucose_unspecified"},
        {"metric": "heart_rate", "unit": "bpm", "raw_value": "60.1"},
        {"measured_at": "2020-01-01T00:00:00"},
        {"measured_at": "2020-01-01"},
        {"measured_at": 1577836800},
        {"measured_at": "1899-12-31T23:59:00Z"},
        {"measured_at": "2101-01-01T00:00:00Z"},
        {"user_id": str(uuid4())},
        {"report_id": str(uuid4())},
        {"idempotency_key": "00000000-0000-0000-0000-000000000000"},
    ],
)
def test_manual_scope(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        manual(**override)


def test_heart_rate_integer() -> None:
    value = manual_fields(manual(metric="heart_rate", unit="bpm", raw_value="060"))
    assert value.raw_value == value.numeric_value == "060"


@pytest.mark.parametrize("day", [None, "2020-02-29", "1900-01-01", "2100-12-31"])
def test_publish_explicit_or_unknown_day(day: str | None) -> None:
    result = PublishInput.model_validate({"expected_revision": 1, "measurement_date": day})
    assert (result.measurement_date.isoformat() if result.measurement_date else None) == day


@pytest.mark.parametrize(
    "extra",
    [
        {"measurement_date": "2020-01-01T00:00:00Z"},
        {"measurement_date": "2021-02-29"},
        {"measurement_date": 0},
        {"measurement_date": "1899-12-31"},
        {"expected_revision": True},
        {"expected_revision": 0},
        {"expected_revision": 21},
        {"raw_value": "5"},
        {"user_id": str(uuid4())},
        {"source_type": "manual"},
    ],
)
def test_publish_rejects_fabricated_authority_or_date(extra: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PublishInput.model_validate({"expected_revision": 1, **extra})


@pytest.mark.parametrize(
    "raw,kind,number,comparator",
    [
        ("Negative", "qualitative", None, None),
        ("Positive", "qualitative", None, None),
        ("Trace", "qualitative", None, None),
        ("1:80", "titre", None, None),
        ("<5", "numeric", "5", "<"),
        (">10", "numeric", "10", ">"),
    ],
)
def test_history_snapshot_forms(
    raw: str, kind: str, number: str | None, comparator: str | None
) -> None:
    parsed = fields(RawFields(original_label="Glucose", raw_value=raw))
    assert parsed.raw_value == raw and parsed.value_kind == kind
    assert parsed.numeric_value == number and parsed.comparator == comparator


def test_api_auth_csrf_revocation_and_filter_bounds() -> None:
    provider = ProviderFixture()
    with TestClient(
        create_app(auth_settings(), provider_transport=httpx.MockTransport(provider.handle))
    ) as client:
        for route in (
            "/observations",
            "/dashboard",
            "/observations/catalog",
            f"/observations/{uuid4()}",
        ):
            assert client.get(route).status_code == 401
        client.cookies.set("sl_access", provider.token())
        for method, route in (
            ("POST", "/observations/manual"),
            ("POST", f"/reports/{uuid4()}/parameters/{uuid4()}/publish"),
            ("PATCH", f"/observations/{uuid4()}"),
            ("DELETE", f"/observations/{uuid4()}"),
        ):
            assert client.request(method, route, json={}).status_code == 403
        client.cookies.set("sl_access", provider.token())
        for query in (
            "offset=-1",
            "offset=10001",
            "metric=bad!",
            "source_type=ai",
            "date_from=2020-02-30",
            "report_id=bad",
            "date_from=2021-01-01&date_to=2020-01-01",
        ):
            assert client.get("/observations?" + query).status_code == 422
        assert client.get("/observations/catalog").status_code == 200
        provider.active = False
        assert client.get("/observations").status_code == 401
