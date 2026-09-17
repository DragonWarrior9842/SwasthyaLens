"""Owner-scoped observations; database derives all report values from reviews."""

from uuid import UUID

from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.parameters import ParameterService
from app.schemas.observations import (
    Dashboard,
    DeleteInput,
    ManualEdit,
    ManualInput,
    Observation,
    ObservationPage,
    PublishInput,
    RecentReport,
)
from app.schemas.parameters import ParameterFields

CATALOG_VERSION = "observations-v1"
METRICS = [
    {"id": "hemoglobin", "label": "Hemoglobin", "manual_unit": None},
    {"id": "tsh", "label": "TSH", "manual_unit": None},
    {"id": "vitamin_d_unspecified", "label": "Vitamin D (unspecified)", "manual_unit": None},
    {"id": "glucose_unspecified", "label": "Glucose (unspecified)", "manual_unit": None},
    {"id": "crp", "label": "CRP", "manual_unit": None},
    {"id": "weight", "label": "Weight", "manual_unit": "kg"},
    {"id": "heart_rate", "label": "Heart rate", "manual_unit": "bpm"},
]


def unavailable() -> ApiProblem:
    return ApiProblem(503, "service_unavailable", "Health history is temporarily unavailable.")


def manual_fields(body: ManualInput) -> ParameterFields:
    return ParameterFields(
        original_label="Weight" if body.metric == "weight" else "Heart rate",
        raw_value=body.raw_value,
        numeric_value=body.raw_value,
        original_unit=body.unit,
        canonical_metric=body.metric,
        value_kind="numeric",
    )


class ObservationService:
    def __init__(self, parameters: ParameterService) -> None:
        self.parameters = parameters

    def rpc(
        self, operation: str, payload: dict[str, object], current: AuthenticatedRequest
    ) -> object:
        extraction = self.parameters.extraction
        secret = extraction.settings.report_processing_key
        if secret is None:
            raise unavailable()
        return extraction.reports.gateway.request(
            "POST",
            "/rest/v1/rpc/observation_call",
            access_token=current.access_token,
            purpose="reports",
            payload={
                "p_operation": operation,
                "p_payload": payload,
                "p_worker_secret": secret.get_secret_value(),
            },
        )

    @staticmethod
    def row(value: object, current: AuthenticatedRequest) -> Observation:
        try:
            if not isinstance(value, dict) or UUID(value["user_id"]) != current.identity.user_id:
                raise ValueError
            return Observation.model_validate(value)
        except (ValueError, KeyError, TypeError):
            raise unavailable() from None

    def get(self, identifier: UUID, current: AuthenticatedRequest) -> Observation:
        row = self.row(self.rpc("get", {"id": str(identifier)}, current), current)
        if (
            row.id != identifier
            or not row.revisions
            or (row.source_type == "report" and not row.evidence)
        ):
            raise unavailable()
        return row

    def publish(
        self, report: UUID, candidate: UUID, body: PublishInput, current: AuthenticatedRequest
    ) -> Observation:
        self.parameters.extraction.reports.get(report, current)
        payload = {
            **body.model_dump(mode="json"),
            "report_id": str(report),
            "candidate_id": str(candidate),
        }
        row = self.row(self.rpc("publish", payload, current), current)
        if (
            row.report_id != report
            or row.candidate_id != candidate
            or row.current.review_revision != body.expected_revision
        ):
            raise unavailable()
        return row

    def manual(
        self, body: ManualInput, current: AuthenticatedRequest, identifier: UUID | None = None
    ) -> Observation:
        payload = body.model_dump(mode="json", exclude={"metric", "raw_value", "unit"})
        payload["fields"] = manual_fields(body).model_dump(mode="json")
        if identifier is not None:
            existing = self.get(identifier, current)
            if existing.source_type != "manual" or not isinstance(body, ManualEdit):
                raise ApiProblem(
                    409,
                    "observation_conflict",
                    "Report values must be corrected at their source review.",
                )
            payload["id"] = str(identifier)
        row = self.row(
            self.rpc("manual_edit" if identifier else "manual_create", payload, current), current
        )
        if row.source_type != "manual" or (identifier is not None and row.id != identifier):
            raise unavailable()
        return row

    def delete(
        self, identifier: UUID, body: DeleteInput, current: AuthenticatedRequest
    ) -> dict[str, str]:
        # The RPC performs an explicit owner check even for an already-deleted tombstone.
        value = self.rpc("manual_delete", {"id": str(identifier), **body.model_dump()}, current)
        if value != {"message": "Observation deleted."}:
            raise unavailable()
        return {"message": "Observation deleted."}

    def list(self, filters: dict[str, object], current: AuthenticatedRequest) -> ObservationPage:
        value = self.rpc("list", filters, current)
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("items"), list)
            or len(value["items"]) > 21
        ):
            raise unavailable()
        rows = [self.row(v, current) for v in value["items"]]
        offset = filters.get("offset", 0)
        if not isinstance(offset, int) or value.get("offset") != offset:
            raise unavailable()
        if len({r.id for r in rows}) != len(rows):
            raise unavailable()
        for row in rows:
            if (
                (not filters.get("include_inactive") and row.current.status != "active")
                or (filters.get("source_type") and row.source_type != filters["source_type"])
                or (
                    filters.get("metric")
                    and row.current.fields.canonical_metric != filters["metric"]
                )
                or (filters.get("report_id") and str(row.report_id) != filters["report_id"])
            ):
                raise unavailable()
        return ObservationPage(
            items=rows[:20], next_offset=offset + 20 if len(rows) > 20 and offset < 10000 else None
        )

    def dashboard(self, current: AuthenticatedRequest) -> Dashboard:
        value = self.rpc("dashboard", {}, current)
        try:
            if not isinstance(value, dict) or UUID(value["user_id"]) != current.identity.user_id:
                raise ValueError
            raw = value["observations"]
            if not isinstance(raw, list) or len(raw) > 21:
                raise ValueError
            rows = [self.row(v, current) for v in raw]
            if any(row.current.status != "active" for row in rows):
                raise ValueError
            return Dashboard(
                uploaded_reports=value["uploaded_reports"],
                reviewed_parameters=value["reviewed_parameters"],
                active_observations=value["active_observations"],
                observations=rows[:5],
                reports=[RecentReport.model_validate(r) for r in value["reports"]],
            )
        except (ValueError, KeyError, TypeError):
            raise unavailable() from None
