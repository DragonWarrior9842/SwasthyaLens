"""Pure, bounded Decimal analysis. Never reads storage, HTTP, OCR, reviews or AI."""

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from zoneinfo import ZoneInfo

from app.schemas.observations import Observation
from app.schemas.trends import Change, LatestComparison, Metric, Period, Point, Status, TrendResult


@dataclass(frozen=True)
class Rule:
    units: tuple[str, ...]
    floor: Decimal | None = None


RULES: dict[str, Rule] = {
    "weight": Rule(("kg",), Decimal("0.1")),
    "heart_rate": Rule(("bpm",), Decimal("1")),
    "hemoglobin": Rule(("g/dL", "g/L")),
    "tsh": Rule(("mIU/L", "uIU/mL", "µIU/mL")),
    "vitamin_d_unspecified": Rule(("ng/mL", "nmol/L")),
    "glucose_unspecified": Rule(("mg/dL", "mmol/L")),
    "crp": Rule(("mg/L", "mg/dL")),
}
NUMBER = re.compile(r"[-+]?(?:[0-9]{1,20}(?:\.[0-9]{1,12})?|\.[0-9]{1,12})")


def text(value: Decimal) -> str:
    return format(value, "f")


def rounded(value: Decimal) -> str:
    return text(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN))


def median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def change(current: Decimal, previous: Decimal) -> Change:
    delta = current - previous
    return Change(
        absolute=text(delta), percent=rounded(delta / previous * 100) if previous > 0 else None
    )


def tolerance(previous: Decimal, floor: Decimal) -> Decimal:
    return max(abs(previous) * Decimal("0.01"), floor)


def classification(current: Decimal, previous: Decimal, floor: Decimal) -> Status:
    delta = current - previous
    if abs(delta) <= tolerance(previous, floor):
        return "stable"
    return "increasing" if delta > 0 else "decreasing"


def numeric(observation: Observation) -> Decimal | None:
    f = observation.current.fields
    if f.value_kind != "numeric" or f.comparator is not None or f.qualitative_result is not None:
        return None
    if not f.numeric_value or not NUMBER.fullmatch(f.numeric_value):
        return None
    raw = (f.raw_value or "").strip().replace("−", "-")
    if not NUMBER.fullmatch(raw) or Decimal(raw) != Decimal(f.numeric_value):
        return None
    return Decimal(f.numeric_value)


def measurement_day(observation: Observation, zone: ZoneInfo) -> date | None:
    v = observation.current
    return v.measured_at.astimezone(zone).date() if v.measured_at else v.measurement_date


def daily(points: list[Point]) -> dict[date, Decimal]:
    groups: dict[date, list[Decimal]] = defaultdict(list)
    for p in points:
        groups[p.day].append(Decimal(p.value))
    return {day: median(values) for day, values in sorted(groups.items())}


def period(
    points: list[Point], excluded: list[date], start: date, end: date, frequent: bool
) -> Period:
    selected = [p for p in points if start <= p.day <= end]
    values = [Decimal(p.value) for p in selected]
    days = daily(selected)
    return Period(
        start=start,
        end=end,
        sample_count=len(selected),
        excluded_count=sum(start <= day <= end for day in excluded),
        observed_days=len(days),
        coverage_percent=rounded(Decimal(len(days)) / ((end - start).days + 1) * 100)
        if frequent
        else None,
        first_day=min(days) if days else None,
        last_day=max(days) if days else None,
        median=text(median(list(days.values()))) if days and frequent else None,
        observed_range=text(max(values) - min(values)) if len(values) >= 2 else None,
    )


def latest(points: list[Point]) -> LatestComparison:
    if not points:
        return LatestComparison(reason="no_dated_numeric_data")
    days = sorted({p.day for p in points}, reverse=True)
    newest = [p for p in points if p.day == days[0]]
    if len(newest) != 1:
        return LatestComparison(reason="ambiguous_same_day")
    if len(days) < 2:
        return LatestComparison(latest=newest[0], reason="fewer_than_two_days")
    prior = [p for p in points if p.day == days[1]]
    if len(prior) != 1:
        return LatestComparison(latest=newest[0], reason="ambiguous_same_day")
    return LatestComparison(
        latest=newest[0],
        previous=prior[0],
        change=change(Decimal(newest[0].value), Decimal(prior[0].value)),
        reason="available",
    )


def analyze(
    observations: list[Observation],
    *,
    metric: Metric,
    unit: str,
    window: str,
    end: date,
    as_of: datetime,
    timezone: str,
    unknown_date_count: int = 0,
) -> TrendResult:
    if window not in ("7d", "30d") or len(observations) > 500 or as_of.tzinfo is None:
        raise ValueError("Invalid analysis bounds")
    rule = RULES[metric]
    if unit not in rule.units:
        raise ValueError("Unsupported unit")
    zone = ZoneInfo(timezone)
    if not date(1901, 1, 1) <= end <= min(as_of.astimezone(zone).date(), date(2100, 12, 31)):
        raise ValueError("Invalid end day")
    if len({o.id for o in observations}) != len(observations):
        raise ValueError("Duplicate identity")
    # Enough precision for exact bounded input sums, halves, differences and thresholds.
    with localcontext() as context:
        context.prec = 80
        days = 7 if window == "7d" else 30
        frequent = rule.floor is not None
        start = end - timedelta(days=days - 1)
        previous_start = start - timedelta(days=days)
        history_start = previous_start if frequent else end - timedelta(days=365)
        points: list[Point] = []
        excluded: list[date] = []
        unknown = unknown_date_count
        for o in observations:
            v = o.current
            if (
                v.status != "active"
                or v.fields.canonical_metric != metric
                or v.fields.original_unit != unit
            ):
                continue
            day = measurement_day(o, zone)
            if day is None:
                unknown += 1
                continue
            if not history_start <= day <= end or (v.measured_at and v.measured_at >= as_of):
                continue
            value = numeric(o)
            if value is None:
                excluded.append(day)
                continue
            points.append(
                Point(
                    observation_id=o.id,
                    revision=v.revision,
                    source_type=o.source_type,
                    report_id=o.report_id,
                    candidate_id=o.candidate_id,
                    review_revision=v.review_revision,
                    day=day,
                    measured_at=v.measured_at,
                    raw_value=v.fields.raw_value or "",
                    value=v.fields.numeric_value or "",
                    unit=unit,
                )
            )
        points.sort(
            key=lambda p: (
                p.day,
                p.measured_at.isoformat() if p.measured_at else "",
                str(p.observation_id),
            )
        )
        current = period(points, excluded, start, end, frequent)
        previous = period(points, excluded, previous_start, start - timedelta(days=1), frequent)
        minimum = (days + 1) // 2
        status: Status = "insufficient_data"
        reason: str = "occasional_metric" if not frequent else "no_numeric_observations"
        delta = None
        threshold = None
        pattern = "not_applicable" if not frequent else "insufficient_data"
        if rule.floor is not None:
            if current.observed_days >= minimum:
                values = list(daily([p for p in points if start <= p.day <= end]).values())
                pairs = list(zip(values[1:], values[:-1], strict=True))
                if all(classification(a, b, rule.floor) == "increasing" for a, b in pairs):
                    pattern = "consistent_increase"
                elif all(classification(a, b, rule.floor) == "decreasing" for a, b in pairs):
                    pattern = "consistent_decrease"
                elif max(values) - min(values) <= tolerance(median(values), rule.floor):
                    pattern = "stable_sequence"
                else:
                    pattern = "no_clear_pattern"
                reason = "previous_coverage"
                if previous.observed_days >= minimum:
                    assert current.median is not None and previous.median is not None
                    a, b = Decimal(current.median), Decimal(previous.median)
                    status = classification(a, b, rule.floor)
                    delta, threshold = change(a, b), text(tolerance(b, rule.floor))
                    reason = "available"
            elif current.sample_count:
                reason = "current_coverage"
        return TrendResult.model_validate(
            dict(
                metric=metric,
                unit=unit,
                window=window,
                timezone=timezone,
                as_of=as_of,
                partial_end_day=end == as_of.astimezone(zone).date(),
                history_start=history_start,
                mode="frequent" if frequent else "occasional",
                minimum_days=minimum if frequent else None,
                current=current,
                previous=previous,
                points=points,
                unknown_date_count=unknown,
                excluded_history_count=len(excluded),
                latest_comparison=latest(points),
                status=status,
                reason=reason,
                change=delta,
                tolerance=threshold,
                pattern=pattern,
            )
        )


def pearson_days(left: dict[date, Decimal], right: dict[date, Decimal]) -> dict[str, object]:
    """Dimensionless primitive only; no product pair is enabled by this function."""
    if len(left) > 500 or len(right) > 500:
        raise ValueError("Bounded series required")
    paired = sorted(left.keys() & right.keys())
    base: dict[str, object] = {
        "pair_count": len(paired),
        "minimum_pairs": 14,
        "method": "pearson_same_day_medians",
    }
    if len(paired) < 14 or (paired[-1] - paired[0]).days < 13:
        return {**base, "status": "insufficient_data", "coefficient": None}
    with localcontext() as context:
        context.prec = 160
        xs, ys = [left[d] for d in paired], [right[d] for d in paired]
        if any(not v.is_finite() or abs(v) >= Decimal("1e20") for v in xs + ys):
            raise ValueError("Bounded finite scalars required")
        n = Decimal(len(paired))
        xx = n * sum(x * x for x in xs) - sum(xs) ** 2
        yy = n * sum(y * y for y in ys) - sum(ys) ** 2
        if xx == 0 or yy == 0:
            return {**base, "status": "constant_series", "coefficient": None}
        xy = n * sum(x * y for x, y in zip(xs, ys, strict=True)) - sum(xs) * sum(ys)
        return {
            **base,
            "status": "available",
            "coefficient": rounded(xy / (xx * yy).sqrt()),
            "first_day": paired[0].isoformat(),
            "last_day": paired[-1].isoformat(),
        }
