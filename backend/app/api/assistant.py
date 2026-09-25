from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import Auth, CurrentUser, protect_write
from app.core.assistant import AssistantService
from app.core.errors import unavailable
from app.schemas.assistant import ConversationList, NewConversation, SendMessage, Thread
from app.schemas.trends import Contract


def service(request: Request) -> AssistantService:
    value = getattr(request.app.state, "assistant_service", None)
    if not isinstance(value, AssistantService):
        raise unavailable()
    return value


def limit(auth: Auth, current: CurrentUser) -> None:
    auth.limiter.check(f"assistant:{current.identity.user_id}", limit=60)


Assistant = Annotated[AssistantService, Depends(service)]
router = APIRouter(
    prefix="/assistant/conversations", tags=["Assistant"], dependencies=[Depends(limit)]
)


@router.get("", response_model=ConversationList)
def conversations(
    current: CurrentUser, assistant: Assistant, query: Annotated[Contract, Query()]
) -> ConversationList:
    return assistant.list(current)


@router.post("", response_model=Thread, dependencies=[Depends(protect_write)])
def create(body: NewConversation, current: CurrentUser, assistant: Assistant) -> Thread:
    return assistant.create(body.idempotency_key, current)


@router.get("/{identifier}", response_model=Thread)
def detail(
    identifier: UUID,
    current: CurrentUser,
    assistant: Assistant,
    query: Annotated[Contract, Query()],
) -> Thread:
    return assistant.get(identifier, current)


@router.post("/{identifier}/messages", response_model=Thread, dependencies=[Depends(protect_write)])
async def send(
    identifier: UUID, body: SendMessage, current: CurrentUser, assistant: Assistant
) -> Thread:
    return await assistant.send(identifier, body, current)


@router.delete("/{identifier}", dependencies=[Depends(protect_write)])
def delete(
    identifier: UUID, body: Contract, current: CurrentUser, assistant: Assistant
) -> dict[str, str]:
    return assistant.delete(identifier, current)
