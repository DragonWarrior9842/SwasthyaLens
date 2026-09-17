"""Phase 6 acceptance with real owner sessions and disposable synthetic reports."""

import os
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest

from tests import extraction_fixtures
from tests.integration.test_live_extraction import finish
from tests.integration.test_live_ownership import (
    LiveContext,
    SignedInUser,
    expect_empty,
    expect_status,
)
from tests.integration.test_live_ownership import live as live
from tests.integration.test_live_reports import metadata, put_file
from tests.parameter_fixtures import NATIVE_LINES

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real provider opt-in required"
)


@pytest.fixture(scope="module", autouse=True)
def preserve_account_rate_window() -> Iterator[None]:
    yield
    # These dense lifecycle/pagination fixtures share the existing per-account
    # write budget with later suites. Let the real 60-second window expire;
    # never increase/reset the application limiter to make acceptance pass.
    if os.environ.get("RUN_SUPABASE_INTEGRATION") == "1":
        time.sleep(60)


def test_live_manual_pagination_and_measurement_order(live: LiveContext) -> None:
    user, other = live.users
    created: list[str] = []
    # Deliberately insert in reverse measurement order: insertion time must not win.
    try:
        for minute in range(21, -1, -1):
            response = user.write(
                "POST",
                "/observations/manual",
                {
                    "idempotency_key": str(uuid4()),
                    "metric": "heart_rate",
                    "unit": "bpm",
                    "raw_value": "060",
                    "measured_at": f"2010-02-03T12:{minute:02}:00Z",
                },
            )
            expect_status(response, 200, "Create pagination fixture")
            created.append(response.json()["id"])
        route = (
            "/observations?metric=heart_rate&source_type=manual"
            "&date_from=2010-02-03&date_to=2010-02-03"
        )
        response = user.client.get(route)
        expect_status(response, 200, "Read first bounded page")
        first = response.json()
        assert [row["id"] for row in first["items"]] == created[:20]
        assert first["next_offset"] == 20
        second = user.client.get(route + "&offset=20").json()
        assert [row["id"] for row in second["items"]] == created[20:]
        assert second["next_offset"] is None
        assert other.client.get(route).json()["items"] == []
    finally:
        for identifier in created:
            expect_status(
                user.write("DELETE", f"/observations/{identifier}", {"expected_revision": 1}),
                200,
                "Pagination fixture cleanup",
            )


def test_live_history_trust_dates_units_isolation_and_deletion(
    live: LiveContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extraction_fixtures, "LINES", NATIVE_LINES)
    data = extraction_fixtures.document(("native", "native"))
    reports: list[tuple[SignedInUser, str]] = []
    manuals: list[tuple[SignedInUser, str]] = []
    try:
        with httpx.Client(base_url=str(live.users[0].client.base_url)) as anonymous:
            for route in ("/observations", "/dashboard", "/observations/catalog"):
                expect_status(anonymous.get(route), 401, "Anonymous history denied")
        for index, user in enumerate(live.users):
            other = live.users[1 - index]
            baseline = user.client.get("/dashboard")
            expect_status(baseline, 200, "Read real dashboard")
            start = baseline.json()
            response = user.write(
                "POST", "/reports", metadata("synthetic-history.pdf", "application/pdf", data)
            )
            expect_status(response, 201, "Reserve source")
            report = response.json()["id"]
            reports.append((user, report))
            expect_status(put_file(user, report, data, "application/pdf"), 200, "Upload source")
            route = f"/reports/{report}"
            expect_status(
                user.write("POST", route + "/process", {"idempotency_key": str(uuid4())}),
                202,
                "Extract text",
            )
            source = finish(user, report)
            expect_status(
                user.write(
                    "POST",
                    route + "/extract-parameters",
                    {"idempotency_key": str(uuid4()), "source_run_id": source["id"]},
                ),
                200,
                "Extract candidates",
            )
            candidates = user.client.get(route + "/parameters").json()["candidates"]
            candidate = candidates[0]["id"]
            review_route = route + f"/parameters/{candidate}"
            publish = review_route + "/publish"
            body: dict[str, object] = {"expected_revision": 1, "measurement_date": None}
            expect_status(user.write("POST", publish, body), 409, "Machine candidate never trusted")
            expect_status(
                user.write(
                    "PATCH",
                    review_route,
                    {
                        "idempotency_key": str(uuid4()),
                        "expected_revision": 0,
                        "action": "confirmed",
                    },
                ),
                200,
                "Confirm reviewed candidate",
            )
            assert (
                user.client.get("/dashboard").json()["active_observations"]
                == start["active_observations"]
            )
            expect_status(user.client.post(publish, json=body), 403, "Publish CSRF")
            expect_status(other.write("POST", publish, body), 404, "Cross-owner publish")
            expect_status(
                user.write("POST", publish, {**body, "user_id": other.user_id}),
                422,
                "No forged owner",
            )
            expect_status(
                user.write("POST", publish, {**body, "raw_value": "999"}), 422, "No forged value"
            )
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = [pool.submit(user.write, "POST", publish, body) for _ in range(2)]
                replies = [future.result() for future in pending]
            for reply in replies:
                expect_status(reply, 200, "Concurrent idempotent publication")
            observation = replies[0].json()
            identifier = observation["id"]
            assert replies[1].json()["id"] == identifier
            assert observation["current"]["fields"]["raw_value"] == "13.20"
            assert observation["current"]["measurement_date"] is None
            assert observation["current"]["measured_at"] is None
            assert observation["evidence"]["content"] == candidates[0]["content"]
            assert len(observation["revisions"]) == 1
            expect_status(
                user.write("POST", publish, {**body, "measurement_date": "2020-01-01"}),
                409,
                "Idempotency date conflict",
            )
            expect_status(
                other.client.get(f"/observations/{identifier}"), 404, "Cross-owner detail"
            )
            expect_status(
                other.client.get(f"/observations?report_id={report}"),
                404,
                "Cross-owner report filter",
            )
            for table, field in (
                ("health_observations", "id"),
                ("health_observation_revisions", "observation_id"),
            ):
                expect_empty(
                    live.data(other, "GET", f"{table}?{field}=eq.{identifier}"),
                    "Direct cross-owner RLS",
                )
                expect_status(
                    live.data(
                        user,
                        "PATCH",
                        f"{table}?{field}=eq.{identifier}",
                        {"source_type": "manual"}
                        if table == "health_observations"
                        else {"status": "active"},
                    ),
                    403,
                    "Direct updates forbidden",
                )
                expect_status(
                    live.data(user, "DELETE", f"{table}?{field}=eq.{identifier}"),
                    403,
                    "Direct deletes forbidden",
                )
            expect_status(
                live.data(
                    user,
                    "POST",
                    "health_observations",
                    {
                        "user_id": other.user_id,
                        "source_type": "manual",
                        "idempotency_key": str(uuid4()),
                    },
                ),
                403,
                "Forged direct creation forbidden",
            )
            correction: dict[str, object] = {
                "idempotency_key": str(uuid4()),
                "expected_revision": 1,
                "action": "corrected",
                "correction": {
                    "original_label": "Hemoglobin",
                    "raw_value": "13.21",
                    "original_unit": "g/dL",
                    "raw_reference": "12-15",
                },
            }
            with ThreadPoolExecutor(max_workers=2) as pool:
                review_future = pool.submit(user.write, "PATCH", review_route, correction)
                publish_future = pool.submit(user.write, "POST", publish, body)
                expect_status(review_future.result(), 200, "Concurrent review update")
                assert publish_future.result().status_code in (200, 409)
            assert (
                user.client.get("/dashboard").json()["active_observations"]
                == start["active_observations"]
            )
            old = user.client.get(f"/observations/{identifier}").json()
            assert (
                old["current"]["status"] == "superseded"
                and old["current"]["fields"]["raw_value"] == "13.20"
            )
            expect_status(user.write("POST", publish, body), 409, "Stale publication denied")
            body = {"expected_revision": 2, "measurement_date": "2020-01-02"}
            response = user.write("POST", publish, body)
            expect_status(response, 200, "Explicit corrected revision publication")
            corrected = response.json()
            assert corrected["id"] == identifier and len(corrected["revisions"]) == 2
            assert corrected["current"]["fields"]["raw_value"] == "13.21"
            assert corrected["current"]["measurement_date"] == "2020-01-02"
            assert corrected["evidence"]["report_created_at"][:10] != "2020-01-02"
            expect_status(
                user.write(
                    "PATCH",
                    review_route,
                    {"idempotency_key": str(uuid4()), "expected_revision": 2, "action": "rejected"},
                ),
                200,
                "Reject published candidate",
            )
            assert (
                user.client.get(f"/observations/{identifier}").json()["current"]["status"]
                == "invalidated"
            )
            expect_status(
                user.write("POST", publish, {"expected_revision": 3}),
                409,
                "Rejected candidate denied",
            )

            # Values and units survive unchanged, even when not comparable.
            forms = [
                ("Negative", None),
                ("Positive", None),
                ("Trace", "unknown-unit"),
                ("<5", "mg/dL"),
                (">10", "mg/dL"),
                ("1:80", None),
                ("5.00", "mmol/L"),
                ("5.00", "mg/dL"),
            ]
            for c, (raw, unit) in zip(candidates[1:], forms, strict=False):
                r = route + f"/parameters/{c['id']}"
                expect_status(
                    user.write(
                        "PATCH",
                        r,
                        {
                            "idempotency_key": str(uuid4()),
                            "expected_revision": 0,
                            "action": "corrected",
                            "correction": {
                                "original_label": "Glucose",
                                "raw_value": raw,
                                "original_unit": unit,
                            },
                        },
                    ),
                    200,
                    "Review representation fixture",
                )
                response = user.write("POST", r + "/publish", {"expected_revision": 1})
                expect_status(response, 200, "Publish representation fixture")
                fields = response.json()["current"]["fields"]
                assert fields["raw_value"] == raw and fields["original_unit"] == unit
                if raw == "1:80":
                    assert fields["numeric_value"] is None and fields["value_kind"] == "titre"
                if raw in ("<5", ">10"):
                    assert fields["comparator"] == raw[0] and fields["numeric_value"] == raw[1:]
            filtered = user.client.get(
                f"/observations?report_id={report}&metric=glucose_unspecified"
            ).json()
            assert len(filtered["items"]) == len(forms)
            assert (
                user.client.get(f"/observations?report_id={report}&date_from=2020-01-01").json()[
                    "items"
                ]
                == []
            )

            manual: dict[str, object] = {
                "idempotency_key": str(uuid4()),
                "metric": "weight",
                "raw_value": "70.250",
                "unit": "kg",
                "measured_at": "2020-01-02T00:15:00+05:30",
            }
            expect_status(user.client.post("/observations/manual", json=manual), 403, "Manual CSRF")
            response = user.write("POST", "/observations/manual", manual)
            expect_status(response, 200, "Manual entry")
            entry = response.json()
            mid = entry["id"]
            manuals.append((user, mid))
            assert entry["source_type"] == "manual" and entry["evidence"] is None
            assert entry["current"]["fields"]["numeric_value"] == "70.250"
            assert entry["current"]["measured_at"].startswith("2020-01-01T18:45:00")
            assert user.client.get("/observations").json()["items"][0]["id"] == mid
            assert user.write("POST", "/observations/manual", manual).json()["id"] == mid
            expect_status(
                user.write("POST", "/observations/manual", {**manual, "unit": "bpm"}),
                422,
                "Wrong unit rejected",
            )
            expect_status(
                user.write("POST", "/observations/manual", {**manual, "user_id": other.user_id}),
                422,
                "Manual owner forgery rejected",
            )
            edited = {
                **manual,
                "idempotency_key": str(uuid4()),
                "expected_revision": 1,
                "raw_value": "71.250",
            }
            for method, payload in (("PATCH", edited), ("DELETE", {"expected_revision": 1})):
                expect_status(
                    other.write(method, f"/observations/{mid}", dict(payload)),
                    404,
                    "Cross-owner manual mutation",
                )
            expect_status(other.client.get(f"/observations/{mid}"), 404, "Cross-owner manual read")
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = [
                    pool.submit(
                        user.write,
                        "PATCH",
                        f"/observations/{mid}",
                        {**edited, "idempotency_key": str(uuid4()), "raw_value": f"7{n}.250"},
                    )
                    for n in range(2)
                ]
                edits = [future.result() for future in pending]
            assert sorted(r.status_code for r in edits) == [200, 409]
            entry = user.client.get(f"/observations/{mid}").json()
            assert len(entry["revisions"]) == 2 and entry["revisions"][1]["status"] == "superseded"
            expect_status(
                user.write("DELETE", f"/observations/{mid}", {"expected_revision": 1}),
                409,
                "Stale delete denied",
            )
            dashboard = user.client.get("/dashboard").json()
            assert dashboard["active_observations"] == start["active_observations"] + len(forms) + 1
            assert dashboard["uploaded_reports"] == start["uploaded_reports"] + 1
            assert dashboard["reviewed_parameters"] == start["reviewed_parameters"] + len(forms)
            expect_status(
                user.write("DELETE", route, {}), 200, "Delete report and derived observations"
            )
            expect_status(
                user.client.get(f"/observations/{identifier}"),
                404,
                "Deleted report observation inaccessible",
            )
            expect_status(user.client.get(f"/observations/{mid}"), 200, "Unrelated manual survives")
            assert (
                user.client.get("/dashboard").json()["active_observations"]
                == start["active_observations"] + 1
            )
            expect_empty(
                live.data(user, "GET", f"health_observations?report_id=eq.{report}"),
                "Derived observation erasure",
            )
            expect_status(
                user.write("DELETE", f"/observations/{mid}", {"expected_revision": 2}),
                200,
                "Delete manual revisions",
            )
            expect_status(
                user.write("DELETE", f"/observations/{mid}", {"expected_revision": 2}),
                200,
                "Idempotent delete",
            )
            expect_status(
                user.write("POST", "/observations/manual", manual),
                404,
                "Creation replay cannot resurrect",
            )
            expect_empty(
                live.data(user, "GET", f"health_observation_revisions?observation_id=eq.{mid}"),
                "Manual value erasure",
            )
            assert (
                user.client.get("/dashboard").json()["active_observations"]
                == start["active_observations"]
            )
        # Replay a revoked JWT cookie, and check Data API RLS independently.
        user = live.users[0]
        token = user.access
        expect_status(user.write("POST", "/auth/logout", {}), 200, "Revoke fixture session")
        with httpx.Client(
            base_url=str(user.client.base_url), cookies={"sl_access": token}
        ) as revoked:
            for route in ("/observations", "/dashboard"):
                expect_status(revoked.get(route), 401, "Revoked history read")
        expect_empty(
            live.data(user, "GET", "health_observations"), "Revoked direct observation read"
        )
    finally:
        for user, report in reports:
            response = user.write("DELETE", f"/reports/{report}", {})
            if response.status_code not in (200, 401):
                raise AssertionError("Synthetic source cleanup failed")
        for user, identifier in manuals:
            response = user.client.get(f"/observations/{identifier}")
            if response.status_code == 200:
                expect_status(
                    user.write(
                        "DELETE",
                        f"/observations/{identifier}",
                        {"expected_revision": response.json()["current"]["revision"]},
                    ),
                    200,
                    "Manual fixture cleanup",
                )
