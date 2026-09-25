import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from tests.auth_support import ProviderFixture, auth_settings
from tests.trend_fixtures import observation


@pytest.mark.parametrize(
    "failure",
    [
        "owner",
        "row_owner",
        "inactive",
        "metric",
        "unit",
        "duplicate",
        "out_of_range",
        "unknown_count",
        "limit",
        "timezone",
        "missing",
        "date",
    ],
)
def test_query_adapter_rejects_malformed_or_unauthorized_snapshots(failure: str) -> None:
    provider = ProviderFixture()
    row = observation("70.250", "2020-01-14").model_dump(mode="json") | {
        "user_id": provider.user_id
    }
    payload: dict[str, object] = {
        "user_id": provider.user_id,
        "timezone": "UTC",
        "as_of": datetime.now(UTC).isoformat(),
        "period_end": "2020-01-14",
        "history_start": "2020-01-01",
        "unknown_date_count": 0,
        "items": [row],
    }
    if failure == "owner":
        payload["user_id"] = str(uuid4())
    elif failure == "row_owner":
        row["user_id"] = str(uuid4())
    elif failure == "inactive":
        row["current"]["status"] = "superseded"
    elif failure == "metric":
        row["current"]["fields"]["canonical_metric"] = "heart_rate"
    elif failure == "unit":
        row["current"]["fields"]["original_unit"] = "lb"
    elif failure == "duplicate":
        payload["items"] = [row, row]
    elif failure == "out_of_range":
        row["current"]["measured_at"] = "2019-01-01T12:00:00Z"
    elif failure == "unknown_count":
        payload["unknown_date_count"] = False
    elif failure == "limit":
        payload["items"] = [row] * 501
    elif failure == "timezone":
        payload["timezone"] = "Invalid/Zone"
    elif failure == "missing":
        payload.pop("history_start")
    elif failure == "date":
        payload["period_end"] = "2020-01-15"

    def transport(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/rpc/trend_context"):
            assert json.loads(request.content) == {
                "p_metric": "weight",
                "p_unit": "kg",
                "p_window": 7,
                "p_end": "2020-01-14",
            }
            return httpx.Response(200, json=payload)
        return provider.handle(request)

    with TestClient(
        create_app(auth_settings(), provider_transport=httpx.MockTransport(transport))
    ) as client:
        client.cookies.set("sl_access", provider.token())
        response = client.get("/trends/weight?unit=kg&end=2020-01-14")
        assert response.status_code == (422 if failure == "limit" else 503)
        assert response.headers["cache-control"] == "no-store"


def test_query_adapter_success_and_only_owned_read_rpc() -> None:
    provider = ProviderFixture()
    row = observation("70.250", "2020-01-14").model_dump(mode="json") | {
        "user_id": provider.user_id
    }

    def transport(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/rpc/trend_context"):
            return httpx.Response(
                200,
                json={
                    "user_id": provider.user_id,
                    "timezone": "UTC",
                    "as_of": datetime.now(UTC).isoformat(),
                    "period_end": "2020-01-14",
                    "history_start": "2020-01-01",
                    "unknown_date_count": 2,
                    "items": [row],
                },
            )
        return provider.handle(request)

    with TestClient(
        create_app(auth_settings(), provider_transport=httpx.MockTransport(transport))
    ) as client:
        client.cookies.set("sl_access", provider.token())
        response = client.get("/trends/weight?unit=kg&end=2020-01-14")
        assert response.status_code == 200
        assert response.json()["points"][0]["raw_value"] == "70.250"
        assert response.json()["unknown_date_count"] == 2
        assert response.json()["status"] == "insufficient_data"
