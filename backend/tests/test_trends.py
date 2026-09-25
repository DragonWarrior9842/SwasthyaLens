from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.trend_rules import analyze, classification, pearson_days
from app.factory import create_app
from app.schemas.trends import Metric, TrendResult
from tests.auth_support import ProviderFixture, auth_settings
from tests.trend_fixtures import AS_OF, END, observation


def result(
    values: list[str], *, days: int = 7, metric: Metric = "weight", unit: str = "kg"
) -> TrendResult:
    return analyze(
        [
            observation(
                v, (END - timedelta(days=len(values) - 1 - i)).isoformat(), metric=metric, unit=unit
            )
            for i, v in enumerate(values)
        ],
        metric=metric,
        unit=unit,
        window=f"{days}d",
        end=END,
        as_of=AS_OF,
        timezone="UTC",
    )


@pytest.mark.parametrize("days", [7, 30])
def test_equal_windows_exact_medians_counts_and_boundaries(days: int) -> None:
    values = ["70.250"] * days + ["72.750"] * days
    actual = result(values, days=days)
    assert actual.current.start == END - timedelta(days=days - 1)
    assert actual.previous.start == END - timedelta(days=2 * days - 1)
    assert actual.previous.end == actual.current.start - timedelta(days=1)
    assert actual.current.sample_count == actual.previous.sample_count == days
    assert actual.current.coverage_percent == "100.000000"
    assert actual.current.median == "72.750" and actual.previous.median == "70.250"
    assert actual.change and actual.change.absolute == "2.500"
    assert actual.status == "increasing"
    assert actual.pattern == "stable_sequence"
    assert len(actual.points) == 2 * days
    outside = observation("999", (actual.previous.start - timedelta(days=1)).isoformat())
    edge = observation("1", actual.previous.start.isoformat())
    future = observation("999", (END + timedelta(days=1)).isoformat())
    bounded = analyze(
        [outside, edge, future],
        metric="weight",
        unit="kg",
        window=f"{days}d",
        end=END,
        as_of=AS_OF,
        timezone="UTC",
    )
    assert len(bounded.points) == 1 and bounded.points[0].value == "1"


@pytest.mark.parametrize(
    "values,status,pattern",
    [
        (
            ["100"] * 7 + ["120", "124", "128", "132", "136", "140", "144"],
            "increasing",
            "consistent_increase",
        ),
        (
            ["100"] * 7 + ["90", "86", "82", "78", "74", "70", "66"],
            "decreasing",
            "consistent_decrease",
        ),
        (["100"] * 14, "stable", "stable_sequence"),
        (
            ["100"] * 7 + ["100", "100.1", "99.9", "100", "100.1", "100", "99.9"],
            "stable",
            "stable_sequence",
        ),
        (
            ["100"] * 7 + ["60", "140", "100", "135", "75", "150", "50"],
            "stable",
            "no_clear_pattern",
        ),
    ],
)
def test_direction_stability_noise_and_no_false_pattern(
    values: list[str], status: str, pattern: str
) -> None:
    actual = result(values)
    assert actual.status == status and actual.pattern == pattern
    assert len(actual.points) == len(values)  # No outlier removal or smoothing.


@pytest.mark.parametrize(
    "values,reason",
    [
        ([], "no_numeric_observations"),
        (["70"], "current_coverage"),
        (["70"] * 4, "previous_coverage"),
    ],
)
def test_insufficient_data_first_class(values: list[str], reason: str) -> None:
    actual = result(values)
    assert actual.status == "insufficient_data" and actual.reason == reason
    assert actual.change is None and actual.tolerance is None


@pytest.mark.parametrize(
    "value",
    [
        "<5",
        ">10",
        "<=5",
        "≥5",
        "=5",
        "Negative",
        "Positive",
        "Trace",
        "1:80",
        "1-5",
        "2+",
        "NaN",
        "1e2",
        "",
    ],
)
def test_nonscalar_not_coerced(value: str) -> None:
    actual = result([value] * 14)
    assert not actual.points and actual.excluded_history_count == 14
    assert actual.current.sample_count == 0 and actual.current.excluded_count == 7
    assert actual.current.median is None


def test_sparse_labs_unknown_date_units_and_publication_time_are_separate() -> None:
    rows = [
        observation("18", "2026-01-10", metric="vitamin_d_unspecified", unit="ng/mL"),
        observation("20", "2026-04-10", metric="vitamin_d_unspecified", unit="ng/mL"),
        observation("999", None, metric="vitamin_d_unspecified", unit="ng/mL"),
        observation("50", "2026-04-09", metric="vitamin_d_unspecified", unit="nmol/L"),
    ]
    actual = analyze(
        rows,
        metric="vitamin_d_unspecified",
        unit="ng/mL",
        window="30d",
        end=END,
        as_of=AS_OF,
        timezone="UTC",
    )
    assert actual.current.sample_count == 1 and actual.previous.sample_count == 0
    assert actual.current.median is None and actual.current.coverage_percent is None
    assert actual.reason == "occasional_metric" and actual.pattern == "not_applicable"
    assert actual.unknown_date_count == 1 and len(actual.points) == 2
    assert actual.latest_comparison.change and actual.latest_comparison.change.absolute == "2"
    assert actual.latest_comparison.previous and actual.latest_comparison.previous.day == date(
        2026, 1, 10
    )


def test_mixed_glucose_units_never_combined() -> None:
    rows = [
        observation("90", "2026-04-09", metric="glucose_unspecified", unit="mg/dL"),
        observation("5", "2026-04-10", metric="glucose_unspecified", unit="mmol/L"),
    ]
    actual = analyze(
        rows,
        metric="glucose_unspecified",
        unit="mg/dL",
        window="7d",
        end=END,
        as_of=AS_OF,
        timezone="UTC",
    )
    assert len(actual.points) == 1 and actual.latest_comparison.change is None


def test_duplicates_preserved_equal_day_weight_and_latest_ambiguity() -> None:
    rows = [
        observation("70", "2026-04-09"),
        observation("72", "2026-04-10"),
        observation("74", "2026-04-10"),
    ]
    actual = analyze(
        rows, metric="weight", unit="kg", window="7d", end=END, as_of=AS_OF, timezone="UTC"
    )
    assert actual.current.median == "71.5"  # median(day medians 70,73), not median(70,72,74).
    assert actual.current.sample_count == 3 and actual.current.observed_days == 2
    assert actual.latest_comparison.reason == "ambiguous_same_day"
    assert actual.latest_comparison.change is None
    with pytest.raises(ValueError, match="Duplicate identity"):
        analyze(
            [rows[0], rows[0]],
            metric="weight",
            unit="kg",
            window="7d",
            end=END,
            as_of=AS_OF,
            timezone="UTC",
        )


@pytest.mark.parametrize(
    "zone,instant,day",
    [
        ("Asia/Kolkata", "2026-04-03T18:30:00Z", date(2026, 4, 4)),
        ("Asia/Kolkata", "2026-04-03T18:29:59Z", date(2026, 4, 3)),
        ("America/New_York", "2026-03-08T06:59:59Z", date(2026, 3, 8)),
        ("America/New_York", "2026-03-08T07:00:00Z", date(2026, 3, 8)),
        ("America/New_York", "2026-11-01T05:30:00Z", date(2026, 11, 1)),
        ("America/New_York", "2026-11-01T06:30:00Z", date(2026, 11, 1)),
    ],
)
def test_timezone_and_dst_measurement_days(zone: str, instant: str, day: date) -> None:
    end = day + timedelta(days=1)
    actual = analyze(
        [observation("70", None, instant=instant)],
        metric="weight",
        unit="kg",
        window="7d",
        end=end,
        as_of=datetime(2026, 12, 1, tzinfo=UTC),
        timezone=zone,
    )
    assert actual.points[0].day == day


def test_future_instant_current_day_and_unknown_report_day() -> None:
    as_of = datetime(2026, 4, 10, 12, tzinfo=UTC)
    actual = analyze(
        [
            observation("70", None, instant="2026-04-10T11:59:59Z"),
            observation("80", None, instant="2026-04-10T12:00:00Z"),
        ],
        metric="weight",
        unit="kg",
        window="7d",
        end=END,
        as_of=as_of,
        timezone="UTC",
    )
    assert len(actual.points) == 1 and actual.partial_end_day


@pytest.mark.parametrize("old", ["0", "-1"])
def test_no_percentage_for_nonpositive_denominator(old: str) -> None:
    actual = result([old, "2"], metric="crp", unit="mg/L")
    assert actual.latest_comparison.change and actual.latest_comparison.change.percent is None


def test_exact_decimal_extremes_and_tolerance_inclusive() -> None:
    actual = result(
        ["0.000000000001", "99999999999999999999.999999999999"], metric="crp", unit="mg/L"
    )
    assert actual.latest_comparison.change
    assert actual.latest_comparison.change.absolute == "99999999999999999999.999999999998"
    assert classification(Decimal("101"), Decimal("100"), Decimal(".1")) == "stable"
    assert (
        classification(Decimal("101.000000000001"), Decimal("100"), Decimal(".1")) == "increasing"
    )
    assert classification(Decimal(".1"), Decimal("0"), Decimal(".1")) == "stable"


def test_correction_inactive_and_deletion_change_current_results() -> None:
    active = observation("70", "2026-04-10")
    old = observation("999", "2026-04-09", status="superseded")
    deleted = observation("999", "2026-04-08", status="invalidated")
    kwargs = dict(metric="weight", unit="kg", window="7d", end=END, as_of=AS_OF, timezone="UTC")
    a = analyze([active, old, deleted], **kwargs)  # type: ignore[arg-type]
    b = analyze([], **kwargs)  # type: ignore[arg-type]
    assert len(a.points) == 1 and not b.points and b.current.median is None


@pytest.mark.parametrize("sign,expected", [(1, "1.000000"), (-1, "-1.000000")])
def test_dimensionless_correlation_fixture(sign: int, expected: str) -> None:
    left = {END - timedelta(days=i): Decimal(i) for i in range(14)}
    right = {d: sign * x + 2 for d, x in left.items()}
    assert pearson_days(left, right)["coefficient"] == expected


def test_correlation_missing_misaligned_constant_and_zero_association() -> None:
    left = {END - timedelta(days=i): Decimal(i) for i in range(15)}
    assert pearson_days(left, dict(list(left.items())[:3]))["status"] == "insufficient_data"
    assert (
        pearson_days(left, {d + timedelta(days=30): v for d, v in left.items()})["pair_count"] == 0
    )
    assert pearson_days(left, {d: Decimal(1) for d in left})["status"] == "constant_series"
    right = {d: (x - 7) ** 2 for d, x in left.items()}
    assert pearson_days(left, right)["coefficient"] == "0.000000"
    assert pearson_days(left, dict(list(right.items())[1:]))["pair_count"] == 14


def test_authenticated_api_strict_queries_and_no_enabled_pairs() -> None:
    provider = ProviderFixture()
    with TestClient(
        create_app(auth_settings(), provider_transport=httpx.MockTransport(provider.handle))
    ) as client:
        assert client.get("/trends/weight?unit=kg").status_code == 401
        client.cookies.set("sl_access", provider.token())
        for path in [
            "/trends/unknown?unit=kg",
            "/trends/weight?unit=kg&window=90d",
            "/trends/weight?unit=kg&user_id=" + str(uuid4()),
            "/trends/weight?unit=lb",
            "/trends/weight?unit=kg&end=bad",
            "/trends/correlations?pair=weight,heart_rate",
        ]:
            assert client.get(path).status_code == 422
        actual = client.get("/trends/correlations")
        assert actual.status_code == 200 and actual.json()["pairs"] == []
        assert actual.json()["minimum_pairs"] == 14
        provider.active = False
        assert client.get("/trends/correlations").status_code == 401
