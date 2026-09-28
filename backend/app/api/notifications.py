from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import Auth, CurrentUser, protect_write
from app.api.observations import Observations
from app.core.notifications import NotificationService
from app.schemas.accounts import EmptyInput
from app.schemas.notifications import NotificationPage, NotificationQuery


def limit(auth: Auth, current: CurrentUser) -> None:
    auth.limiter.check(f"notifications:{current.identity.user_id}", limit=60)


router = APIRouter(
    prefix="/notifications", tags=["Operational notifications"], dependencies=[Depends(limit)]
)


@router.get("", response_model=NotificationPage)
def listing(
    current: CurrentUser, observations: Observations, query: Annotated[NotificationQuery, Query()]
) -> NotificationPage:
    return NotificationService(observations).call("list", current, offset=query.offset)


@router.post("/read-all", response_model=NotificationPage, dependencies=[Depends(protect_write)])
def read_all(
    body: EmptyInput,
    current: CurrentUser,
    observations: Observations,
    query: Annotated[EmptyInput, Query()],
) -> NotificationPage:
    return NotificationService(observations).call("read_all", current)


@router.patch(
    "/{identifier}", response_model=NotificationPage, dependencies=[Depends(protect_write)]
)
def read(
    identifier: UUID,
    body: EmptyInput,
    current: CurrentUser,
    observations: Observations,
    query: Annotated[EmptyInput, Query()],
) -> NotificationPage:
    return NotificationService(observations).call("read", current, identifier)


@router.delete(
    "/{identifier}", response_model=NotificationPage, dependencies=[Depends(protect_write)]
)
def dismiss(
    identifier: UUID,
    body: EmptyInput,
    current: CurrentUser,
    observations: Observations,
    query: Annotated[EmptyInput, Query()],
) -> NotificationPage:
    return NotificationService(observations).call("delete", current, identifier)
