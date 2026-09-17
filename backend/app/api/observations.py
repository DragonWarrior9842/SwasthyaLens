from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import CurrentUser, protect_write
from app.api.reports import limit_report
from app.core.errors import ApiProblem
from app.core.observations import CATALOG_VERSION, METRICS, ObservationService, unavailable
from app.schemas.observations import (
    Dashboard,
    DeleteInput,
    ManualEdit,
    ManualInput,
    Observation,
    ObservationPage,
    PublishInput,
)

router = APIRouter(tags=["Health history"], dependencies=[Depends(limit_report)])


def service(request: Request) -> ObservationService:
    value = getattr(request.app.state, "observation_service", None)
    if not isinstance(value, ObservationService):
        raise unavailable()
    return value


Observations = Annotated[ObservationService, Depends(service)]


@router.get("/observations/catalog")
def catalog(current: CurrentUser) -> dict[str, object]:
    return {"version": CATALOG_VERSION, "metrics": METRICS}


@router.get("/dashboard", response_model=Dashboard)
def dashboard(current: CurrentUser, observations: Observations) -> Dashboard:
    return observations.dashboard(current)


@router.get("/observations", response_model=ObservationPage)
def history(
    current: CurrentUser,
    observations: Observations,
    metric: Annotated[str | None, Query(pattern=r"^[a-z][a-z0-9_]{0,79}$")] = None,
    source_type: Literal["report", "manual"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    report_id: UUID | None = None,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    include_inactive: bool = False,
) -> ObservationPage:
    if date_from and date_to and date_from > date_to:
        raise ApiProblem(422, "validation_error", "Start date must not follow end date.")
    return observations.list(
        {
            "metric": metric,
            "source_type": source_type,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "report_id": str(report_id) if report_id else None,
            "offset": offset,
            "include_inactive": include_inactive,
        },
        current,
    )


@router.post(
    "/reports/{report_id}/parameters/{candidate_id}/publish",
    response_model=Observation,
    dependencies=[Depends(protect_write)],
)
def publish(
    report_id: UUID,
    candidate_id: UUID,
    body: PublishInput,
    current: CurrentUser,
    observations: Observations,
) -> Observation:
    return observations.publish(report_id, candidate_id, body, current)


@router.post(
    "/observations/manual", response_model=Observation, dependencies=[Depends(protect_write)]
)
def manual(body: ManualInput, current: CurrentUser, observations: Observations) -> Observation:
    return observations.manual(body, current)


@router.get("/observations/{identifier}", response_model=Observation)
def detail(identifier: UUID, current: CurrentUser, observations: Observations) -> Observation:
    return observations.get(identifier, current)


@router.patch(
    "/observations/{identifier}", response_model=Observation, dependencies=[Depends(protect_write)]
)
def edit(
    identifier: UUID, body: ManualEdit, current: CurrentUser, observations: Observations
) -> Observation:
    return observations.manual(body, current, identifier)


@router.delete("/observations/{identifier}", dependencies=[Depends(protect_write)])
def delete(
    identifier: UUID, body: DeleteInput, current: CurrentUser, observations: Observations
) -> dict[str, str]:
    return observations.delete(identifier, body, current)
