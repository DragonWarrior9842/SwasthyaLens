"""Explicit synthetic acceptance, with owned language preferences restored afterward."""

import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "backend"))
from tests.integration.test_live_ownership import expect_status, live  # noqa: E402

if "RUN_AI_INTEGRATION" in os.environ or os.environ.get("RUN_SUPABASE_INTEGRATION") != "1":
    raise RuntimeError("Browser acceptance requires Supabase opt-in and AI integration unset")
names = (
    "auth",
    "reports",
    "extraction",
    "parameters",
    "observations",
    "explanations",
    "trends",
    "assistant",
    "multilingual",
    "exports_notifications",
    "voice",
)
scripts = sys.argv[1:] or [f"backend/tests/browser_{name}.cjs" for name in names]
generator = live.__wrapped__()
context = next(generator)
originals = []
exit_code = 0
try:
    for user in context.users:
        response = user.client.get("/settings")
        expect_status(response, 200, "Read original preferences")
        originals.append(
            (
                user,
                {
                    key: response.json()[key]
                    for key in ("preferred_language", "assistant_language", "timezone")
                },
            )
        )
        expect_status(
            user.write(
                "PATCH",
                "/settings",
                {
                    "preferred_language": "en",
                    "assistant_language": "en",
                },
            ),
            200,
            "Set English regression preferences",
        )
    for script in scripts:
        print("SUITE: " + script, flush=True)
        result = subprocess.Popen(
            ["node", script],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        assert result.stdout is not None
        for line in result.stdout:
            print(line, end="", flush=True)
        if result.wait():
            exit_code = 1
            break
finally:
    try:
        for user, original in originals:
            expect_status(user.write("PATCH", "/settings", original), 200, "Restore preferences")
    finally:
        generator.close()
sys.exit(exit_code)
