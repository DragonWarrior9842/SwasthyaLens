"""Authenticated query adapter. The pure rules receive only validated owned snapshots."""

from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.observations import ObservationService
from app.core.trend_rules import RULES, analyze, measurement_day
from app.schemas.trends import Metric, Series, TrendCatalog, TrendQuery, TrendResult


def unavailable() -> ApiProblem:
    return ApiProblem(503, "trend_unavailable", "Trends are temporarily unavailable.")


def capacity() -> ApiProblem:
    return ApiProblem(
        422, "trend_capacity", "This bounded analysis contains too many observations."
    )


class TrendService:
    def __init__(self, observations: ObservationService) -> None:
        self.observations = observations
        self.gateway = observations.parameters.extraction.reports.gateway

    def context(
        self,
        current: AuthenticatedRequest,
        metric: Metric | None = None,
        query: TrendQuery | None = None,
    ) -> dict[str, object]:
        value = self.gateway.object(
            "POST",
            "/rest/v1/rpc/trend_context",
            access_token=current.access_token,
            purpose="reports",
            payload={
                "p_metric": metric,
                "p_unit": query.unit if query else None,
                "p_window": 30 if query and query.window == "30d" else 7,
                "p_end": query.end.isoformat() if query and query.end else None,
            },
        )
        try:
            if UUID(str(value["user_id"])) != current.identity.user_id:
                raise ValueError
            ZoneInfo(str(value["timezone"]))
            captured = datetime.fromisoformat(str(value["as_of"]))
            end = date.fromisoformat(str(value["period_end"]))
            if (
                captured.tzinfo is None
                or end > captured.astimezone(ZoneInfo(str(value["timezone"]))).date()
            ):
                raise ValueError
            if query and query.end and end != query.end:
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise unavailable() from None
        return value

    def catalog(self, current: AuthenticatedRequest) -> TrendCatalog:
        value = self.context(current)
        rows = value.get("series")
        if not isinstance(rows, list):
            raise unavailable()
        if len(rows) > 50:
            raise capacity()
        try:
            series = [
                Series.model_validate(
                    {
                        **row,
                        "supported_unit": row.get("unit")
                        in RULES.get(str(row.get("metric")), RULES["weight"]).units,
                    }
                )
                for row in rows
                if isinstance(row, dict)
            ]
            if len(series) != len(rows) or len({(s.metric, s.unit) for s in series}) != len(series):
                raise ValueError
            return TrendCatalog.model_validate(
                {k: v for k, v in value.items() if k != "user_id"} | {"series": series}
            )
        except (ValueError, TypeError):
            raise unavailable() from None

    def result(
        self, metric: Metric, query: TrendQuery, current: AuthenticatedRequest
    ) -> TrendResult:
        if query.unit not in RULES[metric].units:
            raise ApiProblem(422, "trend_unit", "This exact unit is not supported for this metric.")
        value = self.context(current, metric, query)
        rows = value.get("items")
        if not isinstance(rows, list):
            raise unavailable()
        if len(rows) > 500:
            raise capacity()
        try:
            end = date.fromisoformat(str(value["period_end"]))
            window = 7 if query.window == "7d" else 30
            start = end - timedelta(days=2 * window - 1 if RULES[metric].floor is not None else 365)
            if value["history_start"] != start.isoformat():
                raise ValueError
            unknown = value["unknown_date_count"]
            if type(unknown) is not int or unknown < 0:
                raise ValueError
            zone = ZoneInfo(str(value["timezone"]))
            captured = datetime.fromisoformat(str(value["as_of"]))
            observations = [self.observations.row(row, current) for row in rows]
            for o in observations:
                day = measurement_day(o, zone)
                if (
                    o.current.status != "active"
                    or o.current.fields.canonical_metric != metric
                    or o.current.fields.original_unit != query.unit
                    or day is None
                    or not start <= day <= end
                    or (o.current.measured_at and o.current.measured_at >= captured)
                ):
                    raise ValueError
            return analyze(
                observations,
                metric=metric,
                unit=query.unit,
                window=query.window,
                end=end,
                as_of=captured,
                timezone=str(value["timezone"]),
                unknown_date_count=unknown,
            )
        except (ValueError, KeyError, TypeError, ValidationError):
            raise unavailable() from None
