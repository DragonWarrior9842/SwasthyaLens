"""Kill a disposable API worker after claim; verify durable deadline and authenticated retry."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from tests.extraction_fixtures import document
from tests.integration.test_live_extraction import finish
from tests.integration.test_live_ownership import LiveContext, expect_status
from tests.integration.test_live_ownership import live as live
from tests.integration.test_live_reports import metadata, put_file

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1", reason="Real provider opt-in required"
)


def test_worker_death_expires_then_retry_succeeds(live: LiveContext) -> None:
    user = live.users[0]
    data = document()
    response = user.write(
        "POST", "/reports", metadata("restart-fixture.pdf", "application/pdf", data)
    )
    expect_status(response, 201, "Reserve restart fixture")
    report_id = response.json()["id"]
    process = None
    try:
        expect_status(
            put_file(user, report_id, data, "application/pdf"), 200, "Upload restart fixture"
        )
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        # Only this disposable test API stalls the parser. The ordinary API is unchanged.
        script = (
            "import time, uvicorn; from app.core import extraction; "
            "extraction.extract=lambda *args: time.sleep(300); "
            "uvicorn.run('app.main:app',host='127.0.0.1',port=" + str(port) + ")"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[2],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            cookies=user.client.cookies,
            headers={"Origin": user.client.headers["Origin"], "X-CSRF-Token": user.csrf},
            timeout=20,
        ) as temporary:
            for _ in range(30):
                try:
                    if temporary.get("/health").status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                time.sleep(0.5)
            accepted = temporary.post(
                f"/reports/{report_id}/process", json={"idempotency_key": str(uuid4())}
            )
            expect_status(accepted, 202, "Disposable worker accepts extraction")
        for _ in range(10):
            history = user.client.get(f"/reports/{report_id}/processing")
            expect_status(history, 200, "Read durable claim")
            if history.json()["runs"][0]["status"] == "processing":
                break
            time.sleep(1)
        assert history.json()["runs"][0]["status"] == "processing"
        process.kill()
        process.wait(timeout=10)
        deadline = time.monotonic() + 195
        while time.monotonic() < deadline:
            history = user.client.get(f"/reports/{report_id}/processing")
            expect_status(history, 200, "Read after worker death")
            run = history.json()["runs"][0]
            if run["status"] == "failed":
                break
            time.sleep(6)
        assert run["status"] == "failed" and run["error_category"] == "interrupted"
        assert run["processor"] and run["finished_at"]
        expect_status(
            user.write("POST", f"/reports/{report_id}/process", {"idempotency_key": str(uuid4())}),
            202,
            "Retry on surviving API",
        )
        retried = finish(user, report_id)
        assert retried["status"] == "completed" and retried["attempt"] == 2
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        user.write("DELETE", f"/reports/{report_id}", {})
