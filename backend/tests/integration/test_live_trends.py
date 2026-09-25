"""Explicit Supabase acceptance with dedicated users and synthetic observations. No AI."""

import os
from datetime import date, timedelta
from uuid import uuid4

import httpx
import pytest

from tests import extraction_fixtures
from tests.integration.test_live_extraction import finish
from tests.integration.test_live_ownership import LiveContext, SignedInUser, expect_status
from tests.integration.test_live_ownership import live as live
from tests.integration.test_live_reports import metadata, put_file
from tests.parameter_fixtures import NATIVE_LINES

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real Supabase opt-in"
)


def read(
    user: SignedInUser, metric: str = "weight", unit: str = "kg", window: str = "7d"
) -> dict[str, object]:
    response = user.client.get(
        f"/trends/{metric}", params={"unit": unit, "window": window, "end": "2020-01-14"}
    )
    expect_status(response, 200, "Bounded owner trend")
    return dict(response.json())


def test_live_two_user_trends_correction_report_deletion_and_revocation(
    live: LiveContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    manuals: list[tuple[SignedInUser, str]] = []
    reports: list[tuple[SignedInUser, str]] = []
    settings: list[tuple[SignedInUser, dict[str, object]]] = []
    try:
        for index, user in enumerate(live.users):
            response = user.client.get("/settings")
            expect_status(response, 200, "Read original settings")
            settings.append((user, dict(response.json())))
            expect_status(
                user.write("PATCH", "/settings", {"timezone": "UTC"}), 200, "Fixture timezone"
            )
            ids = []
            for offset in range(14):
                value = (
                    ("70.250" if offset < 7 else "72.750")
                    if index == 0
                    else ("90.250" if offset < 7 else "88.750")
                )
                body: dict[str, object] = {
                    "metric": "weight",
                    "unit": "kg",
                    "raw_value": value,
                    "idempotency_key": str(uuid4()),
                    "measured_at": (date(2020, 1, 1) + timedelta(days=offset)).isoformat()
                    + "T12:00:00Z",
                }
                response = user.write("POST", "/observations/manual", body)
                expect_status(response, 200, "Create synthetic longitudinal point")
                identifier = response.json()["id"]
                ids.append(identifier)
                manuals.append((user, identifier))
            actual = read(user)
            assert actual["status"] == ("increasing" if index == 0 else "decreasing")
            points = actual["points"]
            assert isinstance(points, list)
            assert {p["observation_id"] for p in points} == set(ids)
            assert actual["timezone"] == "UTC"
            thirty = read(user, window="30d")
            assert thirty["status"] == "insufficient_data"
            assert (
                user.client.get(
                    "/trends/weight?unit=kg&user_id=" + live.users[1 - index].user_id
                ).status_code
                == 422
            )
            assert user.client.get("/trends/correlations").json()["pairs"] == []
            response = user.write(
                "PATCH",
                "/observations/" + ids[-1],
                {
                    "expected_revision": 1,
                    "idempotency_key": str(uuid4()),
                    "metric": "weight",
                    "unit": "kg",
                    "raw_value": "73.125",
                    "measured_at": "2020-01-14T12:00:00Z",
                },
            )
            expect_status(response, 200, "Correct latest synthetic measurement")
            points = read(user)["points"]
            assert isinstance(points, list)
            corrected = [p for p in points if p["observation_id"] == ids[-1]]
            assert (
                len(corrected) == 1
                and corrected[0]["revision"] == 2
                and corrected[0]["raw_value"] == "73.125"
            )
            expect_status(
                user.write("DELETE", "/observations/" + ids[-1], {"expected_revision": 2}),
                200,
                "Delete corrected measurement",
            )
            assert len(read(user)["points"]) == 13  # type: ignore[arg-type]

        user, other = live.users
        monkeypatch.setattr(extraction_fixtures, "LINES", NATIVE_LINES)
        data = extraction_fixtures.document(("native",))
        response = user.write(
            "POST", "/reports", metadata("synthetic-trends.pdf", "application/pdf", data)
        )
        expect_status(response, 201, "Reserve synthetic report")
        report = response.json()["id"]
        reports.append((user, report))
        expect_status(
            put_file(user, report, data, "application/pdf"), 200, "Upload synthetic report"
        )
        route = "/reports/" + report
        expect_status(
            user.write("POST", route + "/process", {"idempotency_key": str(uuid4())}),
            202,
            "Extract synthetic text",
        )
        source = finish(user, report)
        response = user.write(
            "POST",
            route + "/extract-parameters",
            {"source_run_id": source["id"], "idempotency_key": str(uuid4())},
        )
        expect_status(response, 200, "Extract synthetic candidates")
        candidates = user.client.get(route + "/parameters").json()["candidates"]
        candidate = next(
            c for c in candidates if c["content"]["fields"]["canonical_metric"] == "hemoglobin"
        )
        review = route + "/parameters/" + candidate["id"]
        assert read(user, "hemoglobin", "g/dL")["points"] == []
        expect_status(
            user.write(
                "PATCH",
                review,
                {"action": "confirmed", "expected_revision": 0, "idempotency_key": str(uuid4())},
            ),
            200,
            "Review source",
        )
        assert read(user, "hemoglobin", "g/dL")["points"] == []  # Review alone is not publication.
        expect_status(
            user.write(
                "POST",
                review + "/publish",
                {"expected_revision": 1, "measurement_date": "2020-01-14"},
            ),
            200,
            "Publish source",
        )
        assert len(read(user, "hemoglobin", "g/dL")["points"]) == 1  # type: ignore[arg-type]
        assert read(other, "hemoglobin", "g/dL")["points"] == []
        expect_status(
            user.write(
                "PATCH",
                review,
                {
                    "action": "corrected",
                    "expected_revision": 1,
                    "idempotency_key": str(uuid4()),
                    "correction": {
                        "original_label": "Hemoglobin",
                        "raw_value": "13.21",
                        "original_unit": "g/dL",
                    },
                },
            ),
            200,
            "Correct published source",
        )
        assert read(user, "hemoglobin", "g/dL")["points"] == []
        expect_status(
            user.write(
                "POST",
                review + "/publish",
                {"expected_revision": 2, "measurement_date": "2020-01-14"},
            ),
            200,
            "Republish correction",
        )
        points = read(user, "hemoglobin", "g/dL")["points"]
        assert isinstance(points, list)
        assert points[0]["raw_value"] == "13.21" and points[0]["revision"] == 2
        expect_status(
            user.write("DELETE", route, {}), 200, "Delete source and derived observations"
        )
        assert read(user, "hemoglobin", "g/dL")["points"] == []
        assert len(read(user)["points"]) == 13  # type: ignore[arg-type]
        # Restore settings before revoking sessions; cleanup of values happens below.
    finally:
        for user, report in reports:
            expect_status(
                user.write("DELETE", "/reports/" + report, {}), 200, "Synthetic report cleanup"
            )
        for user, identifier in manuals:
            response = user.client.get("/observations/" + identifier)
            if response.status_code == 200:
                expect_status(
                    user.write(
                        "DELETE",
                        "/observations/" + identifier,
                        {"expected_revision": response.json()["current"]["revision"]},
                    ),
                    200,
                    "Synthetic manual cleanup",
                )
        for user, original in settings:
            expect_status(
                user.write("PATCH", "/settings", {"timezone": original["timezone"]}),
                200,
                "Restore timezone",
            )
    user = live.users[0]
    access = user.access
    expect_status(user.write("POST", "/auth/logout", {}), 200, "Revoke session")
    with httpx.Client(base_url=str(user.client.base_url), cookies={"sl_access": access}) as revoked:
        for route in ["/trends/catalog", "/trends/weight?unit=kg", "/trends/correlations"]:
            expect_status(revoked.get(route), 401, "Revoked trend access denied")
    denied = live.data(user, "POST", "rpc/trend_context", {"p_metric": "weight", "p_unit": "kg"})
    expect_status(denied, 403, "Revoked direct trend RPC denied")
    assert denied.json().get("code") == "28000"
