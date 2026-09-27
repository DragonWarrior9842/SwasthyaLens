"""Real owned language persistence and frozen multilingual turns; injected mock only."""

import os
from contextlib import ExitStack
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.assistant_language import resolve_language
from app.core.config import Settings
from app.factory import create_app
from tests.assistant_fixtures import MockAssistantProvider
from tests.integration.test_live_ownership import LiveContext, SignedInUser, expect_status
from tests.integration.test_live_ownership import live as live

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real Supabase opt-in"
)


def test_live_language_isolation_frozen_history_and_replay(live: LiveContext) -> None:
    provider = MockAssistantProvider()
    config = Settings()
    created: list[tuple[SignedInUser, str]] = []
    originals: list[tuple[SignedInUser, dict[str, object]]] = []
    manual: str | None = None
    with ExitStack() as stack:
        first = stack.enter_context(
            TestClient(
                create_app(config, assistant_provider=provider), base_url="http://127.0.0.1:8000"
            )
        )
        first.cookies.update(live.users[0].client.cookies)
        first.headers["Origin"] = config.app_origin
        a = SignedInUser(
            cast(httpx.Client, first),
            live.users[0].csrf,
            live.users[0].access,
            live.users[0].user_id,
        )
        b = live.users[1]
        try:
            for user, ui, assistant in [(a, "hi", "hinglish"), (b, "en", "en")]:
                current = user.client.get("/settings").json()
                originals.append(
                    (
                        user,
                        {
                            k: current[k]
                            for k in ("preferred_language", "assistant_language", "timezone")
                        },
                    )
                )
                expect_status(
                    user.write(
                        "PATCH",
                        "/settings",
                        {"preferred_language": ui, "assistant_language": assistant},
                    ),
                    200,
                    "Persist independent language preferences",
                )
                saved = user.client.get("/settings").json()
                assert (
                    saved["preferred_language"] == ui and saved["assistant_language"] == assistant
                )
                assert (
                    user.client.patch("/settings", json={"assistant_language": "hi"}).status_code
                    == 403
                )
                assert (
                    user.write("PATCH", "/settings", {"assistant_language": "fr"}).status_code
                    == 422
                )
                assert (
                    user.write("PATCH", "/settings", {"assistant_language": None}).status_code
                    == 422
                )
                other = b if user is a else a
                denied = live.data(user, "GET", f"user_settings?user_id=eq.{other.user_id}")
                expect_status(denied, 200, "Foreign settings hidden")
                assert denied.json() == []
                denied = live.data(
                    user,
                    "PATCH",
                    f"user_settings?user_id=eq.{other.user_id}",
                    {"assistant_language": "hi"},
                )
                expect_status(denied, 200, "Foreign settings mutation hidden")
                assert denied.json() == []
            assert b.client.get("/settings").json()["assistant_language"] == "en"
            response = a.write(
                "POST",
                "/observations/manual",
                {
                    "metric": "weight",
                    "unit": "kg",
                    "raw_value": "13.20",
                    "measured_at": datetime.now(UTC).isoformat(),
                    "idempotency_key": str(uuid4()),
                },
            )
            expect_status(response, 200, "Synthetic numeric fixture")
            manual = response.json()["id"]
            response = a.write(
                "POST", "/assistant/conversations", {"idempotency_key": str(uuid4())}
            )
            expect_status(response, 200, "Owned multilingual conversation")
            identifier = response.json()["conversation"]["id"]
            created.append((a, identifier))
            route = f"/assistant/conversations/{identifier}"
            history: list[dict[str, object]] = []
            for language, question in [
                ("hinglish", "Mera latest weight samjhao."),
                ("hi", "मेरा नवीनतम वज़न समझाइए।"),
                ("en", "Explain my latest weight."),
            ]:
                expect_status(
                    a.write("PATCH", "/settings", {"assistant_language": language}),
                    200,
                    "Change new-response preference",
                )
                body: dict[str, object] = {"content": question, "idempotency_key": str(uuid4())}
                response = a.write("POST", route + "/messages", body)
                expect_status(response, 200, "Mock multilingual answer")
                messages = response.json()["messages"]
                assert messages[: len(history)] == history
                answer = messages[-1]
                assert answer["status"] == "ready" and answer["response_language"] == language
                assert answer["answer"]["choice"]["response_language"] == language
                fact = next(
                    f
                    for f, source in zip(
                        answer["answer"]["facts"], answer["answer"]["sources"], strict=True
                    )
                    if source["observation_id"] == manual
                )
                assert fact["value"] == "13.20" and fact["unit"] == "kg"
                history = messages
                before = provider.calls
                expect_status(
                    a.write(
                        "PATCH",
                        "/settings",
                        {"preferred_language": "en", "assistant_language": "hinglish"},
                    ),
                    200,
                    "Presentation change only",
                )
                replay = a.write("POST", route + "/messages", body)
                expect_status(replay, 200, "Frozen replay after preference change")
                assert replay.json()["messages"] == history and provider.calls == before
                assert a.client.get(route).json()["messages"] == history
            response = a.write(
                "POST",
                route + "/messages",
                {"content": "Explain my latest weight in Hindi.", "idempotency_key": str(uuid4())},
            )
            expect_status(response, 200, "Explicit current-message override")
            assert response.json()["messages"][-1]["response_language"] == "hi"
            assert resolve_language("in Hindi and in English", "hinglish") == "hinglish"
            assert b.client.get(route).status_code == 404
            assert b.client.get("/settings").json()["assistant_language"] == "en"
            assert provider.calls == 4
        finally:
            for user, identifier in created:
                user.write("DELETE", f"/assistant/conversations/{identifier}", {})
            if manual:
                a.write("DELETE", "/observations/" + manual, {"expected_revision": 1})
            for user, original in originals:
                expect_status(
                    user.write("PATCH", "/settings", original), 200, "Restore original preferences"
                )
