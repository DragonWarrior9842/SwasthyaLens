from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import Auth, CurrentUser
from app.api.observations import Observations
from app.core.trends import TrendService
from app.schemas.trends import (
    Contract,
    CorrelationScope,
    Metric,
    TrendCatalog,
    TrendQuery,
    TrendResult,
)


def limit_trends(auth: Auth, current: CurrentUser) -> None:
    auth.limiter.check(f"trends:{current.identity.user_id}", limit=30)


router = APIRouter(
    prefix="/trends", tags=["Deterministic trends"], dependencies=[Depends(limit_trends)]
)


@router.get("/catalog", response_model=TrendCatalog)
def catalog(
    current: CurrentUser, observations: Observations, query: Annotated[Contract, Query()]
) -> TrendCatalog:
    return TrendService(observations).catalog(current)


@router.get("/correlations", response_model=CorrelationScope)
def correlations(current: CurrentUser, query: Annotated[Contract, Query()]) -> CorrelationScope:
    return CorrelationScope()


@router.get("/{metric}", response_model=TrendResult)
def trend(
    metric: Metric,
    query: Annotated[TrendQuery, Query()],
    current: CurrentUser,
    observations: Observations,
) -> TrendResult:
    return TrendService(observations).result(metric, query, current)
