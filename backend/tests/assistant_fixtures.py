"""Explicit test injection only. The product never imports this module."""

import json

from app.core.explanation_provider import AssistantRequest
from tests.explanation_fixtures import MockExplanationProvider


class MockAssistantProvider(MockExplanationProvider):
    assistant_available = True

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[AssistantRequest] = []
        self.output_override: object | None = None
        self.error: Exception | None = None

    async def generate_assistant(self, request: AssistantRequest) -> object:
        self.calls += 1
        assert request.store is False and request.tools == ()
        assert request.output_schema["additionalProperties"] is False
        self.requests.append(request)
        if self.error:
            raise self.error
        return (
            self.output_override
            if self.output_override is not None
            else json.loads(request.input_json)["permitted_answer"]
        )
