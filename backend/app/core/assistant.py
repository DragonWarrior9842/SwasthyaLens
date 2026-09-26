"""Persistent owned turns, explicit generation, fresh context and verified output."""

import asyncio
from typing import Any
from uuid import UUID

from app.core.assistant_context import COPY, Context, ContextBuilder, render, validate_answer
from app.core.assistant_language import explicit_language, wording
from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.explanation_provider import AssistantProvider, assistant_request
from app.core.observations import ObservationService
from app.schemas.assistant import ConversationList, MultilingualModelAnswer, SendMessage, Thread


class AssistantService:
    def __init__(self, observations: ObservationService, provider: AssistantProvider) -> None:
        self.observations, self.provider = observations, provider
        self.builder = ContextBuilder(observations)

    def rpc(
        self, operation: str, payload: dict[str, object], current: AuthenticatedRequest
    ) -> dict[str, Any]:
        extraction = self.observations.parameters.extraction
        secret = extraction.settings.report_processing_key
        if secret is None:
            raise ApiProblem(503, "assistant_unavailable", "Conversations are unavailable.")
        value = extraction.reports.gateway.object(
            "POST",
            "/rest/v1/rpc/assistant_call",
            access_token=current.access_token,
            purpose="reports",
            payload={
                "p_operation": operation,
                "p_payload": payload,
                "p_worker_secret": secret.get_secret_value(),
            },
        )
        if value.get("user_id") != str(current.identity.user_id):
            raise ApiProblem(503, "assistant_unavailable", "Conversations are unavailable.")
        return value

    def thread(
        self, value: dict[str, Any], current: AuthenticatedRequest, identifier: UUID | None = None
    ) -> Thread:
        try:
            result = Thread.model_validate(
                value | {"provider_available": self.provider.assistant_available}
            )
            if identifier and result.conversation.id != identifier:
                raise ValueError
            if len({m.id for m in result.messages}) != len(result.messages):
                raise ValueError
            for raw, message in zip(value["messages"], result.messages, strict=True):
                legacy = message.schema_version == "assistant-closed-v1"
                if message.prompt_version != ("assistant-evidence-v1" if legacy else "assistant-evidence-v2") or (legacy and message.response_language != "en"):
                    raise ValueError
                if (
                    raw["user_id"] != str(current.identity.user_id)
                    or message.conversation_id != result.conversation.id
                ):
                    raise ValueError
                if message.role == "assistant":
                    if message.status == "ready":
                        answer = message.answer
                        if answer is None or message.content is not None:
                            raise ValueError
                        context = Context(
                            "",
                            [],
                            answer.choice.explanation_code,
                            answer.selection,
                            answer.facts,
                            answer.calculation,
                            answer.sources,
                            message.response_language,
                        )
                        if legacy == isinstance(answer.choice, MultilingualModelAnswer):
                            raise ValueError
                        choice = answer.choice.model_dump()
                        if legacy:
                            choice["response_language"] = "en"
                        validate_answer(choice, context)
                        if answer.text != wording(answer.choice.explanation_code, message.response_language, COPY):
                            raise ValueError
                        if [s.evidence_id for s in answer.sources] != [
                            f.evidence_id for f in answer.facts
                        ]:
                            raise ValueError
                        for fact, source in zip(answer.facts, answer.sources, strict=True):
                            if (
                                fact.value != source.fields.raw_value
                                or fact.unit != source.fields.original_unit
                                or fact.reference != source.fields.raw_reference
                                or fact.source_flag != source.fields.source_flag
                                or fact.label != source.fields.original_label
                                or fact.page_number != source.page_number
                                or fact.comparator != source.fields.comparator
                                or fact.value_kind != source.fields.value_kind
                            ):
                                raise ValueError
                    elif message.answer is not None:
                        raise ValueError
                elif message.status != "received" or not message.content or message.answer:
                    raise ValueError
            return result
        except (ValueError, KeyError, TypeError):
            raise ApiProblem(
                503, "assistant_unavailable", "The conversation could not be verified."
            ) from None

    def list(self, current: AuthenticatedRequest) -> ConversationList:
        return ConversationList.model_validate(
            self.rpc("list", {}, current)
            | {"provider_available": self.provider.assistant_available}
        )

    def get(self, identifier: UUID, current: AuthenticatedRequest) -> Thread:
        return self.thread(self.rpc("get", {"id": str(identifier)}, current), current, identifier)

    def create(self, key: UUID, current: AuthenticatedRequest) -> Thread:
        return self.thread(self.rpc("create", {"idempotency_key": str(key)}, current), current)

    def delete(self, identifier: UUID, current: AuthenticatedRequest) -> dict[str, str]:
        value = self.rpc("delete", {"id": str(identifier)}, current)
        if value.get("deleted") != str(identifier):
            raise ApiProblem(
                503, "assistant_unavailable", "Conversation deletion could not be verified."
            )
        return {"message": "Conversation deleted."}

    async def send(
        self, identifier: UUID, body: SendMessage, current: AuthenticatedRequest
    ) -> Thread:
        value = await asyncio.to_thread(
            self.rpc, "request", {"id": str(identifier), **body.model_dump(mode="json"), "response_language": explicit_language(body.content)}, current
        )
        thread = self.thread(value, current, identifier)
        if value.get("created") is not True:
            return thread  # Replay never starts a second generation, even after failure.
        language = next(m.response_language for m in thread.messages if str(m.id) == value["message_id"])
        history = [m.content for m in thread.messages if m.role == "user" and m.content][:-1][-4:]
        payload: dict[str, object] = {
            "id": str(identifier),
            "message_id": value["message_id"],
            "answer": None,
            "error_category": None,
            "provider": "rules",
            "model": "rules-v1",
        }
        try:
            async with asyncio.timeout(60):
                context = await asyncio.to_thread(
                    self.builder.build, body.content, history, current, language
                )
                if context.code in (
                    "sources",
                    "increasing",
                    "decreasing",
                    "stable",
                    "insufficient_data",
                ):
                    payload.update(provider="gemini", model="gemini-3.8-flash")
                    if not self.provider.assistant_available:
                        raise ApiProblem(
                            503,
                            "assistant_unavailable",
                            "Live assistant generation is unavailable.",
                        )
                    # No product mock selector/env flag; tests inject it explicitly.
                    payload.update(
                        provider=self.provider.name,
                        model="deterministic-test"
                        if self.provider.name == "mock-test"
                        else "gemini-3.8-flash",
                    )
                    async with asyncio.timeout(45):
                        output = await self.provider.generate_assistant(assistant_request(context))
                    choice = validate_answer(output, context)
                else:
                    choice = (
                        context.expected()
                    )  # Clearly labeled deterministic guard/clarification.
                payload["answer"] = render(context, choice).model_dump(mode="json")
        except TimeoutError:
            payload["error_category"] = "timeout"
        except ApiProblem as error:
            payload["error_category"] = {
                "assistant_invalid": "invalid_output",
                "assistant_source": "source_changed",
            }.get(error.code, "rate_limit" if error.status == 429 else "unavailable")
        value = await asyncio.to_thread(self.rpc, "finish", payload, current)
        return self.thread(value, current, identifier)
