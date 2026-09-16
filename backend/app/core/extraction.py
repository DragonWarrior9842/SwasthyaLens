"""Bounded execution and durable owner-scoped processing. No persisted user tokens."""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
from pathlib import Path
from threading import BoundedSemaphore
from typing import get_args
from uuid import UUID

from pydantic import ValidationError

from app.core.auth_service import AuthenticatedRequest
from app.core.config import Settings
from app.core.errors import ApiProblem
from app.core.reports import ReportsService, not_found, report_unavailable
from app.schemas.extraction import (
    ExtractedPage,
    ExtractionOutput,
    ExtractionResult,
    Failure,
    ProcessingHistory,
    ProcessingRun,
)

logger = logging.getLogger("swasthyalens.extraction")


class ProcessingFailure(Exception):
    def __init__(self, category: Failure) -> None:
        self.category = category


def extract(data: bytes, media_type: str, settings: Settings) -> ExtractionOutput:
    # Temporary content is scoped to this attempt and removed on normal/failure exit.
    # Abrupt host death requires the documented temp-directory retention cleanup.
    with tempfile.TemporaryDirectory(prefix="swasthyalens-extraction-") as temporary:
        root = Path(temporary)
        source, output, config = (
            root / name for name in ("source.bin", "result.json", "config.json")
        )
        source.write_bytes(data)
        config.write_text(
            json.dumps(
                {
                    "media_type": media_type,
                    "max_pages": settings.report_processing_max_pages,
                    "models": settings.ocr_tessdata_dir,
                }
            ),
            encoding="utf-8",
        )
        # Deliberately exclude provider/session/signing credentials from child env.
        environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG"}
        }
        environment.update(OMP_THREAD_LIMIT="1", PYTHONIOENCODING="utf-8")
        command = [
            sys.executable,
            "-m",
            "app.core.extraction_process",
            str(source),
            str(output),
            str(config),
        ]
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        deadline = time.monotonic() + settings.report_processing_timeout_seconds
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    raise ProcessingFailure("timeout")
                if (
                    sum(file.stat().st_size for file in root.iterdir() if file.is_file())
                    > 64 * 1024 * 1024
                ):
                    raise ProcessingFailure("resource_limit_exceeded")
                time.sleep(0.05)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        if process.returncode or not output.exists():
            raise ProcessingFailure("extractor_failure")
        if output.stat().st_size > 750000:
            raise ProcessingFailure("resource_limit_exceeded")
        try:
            value = json.loads(output.read_text(encoding="utf-8"))
            if isinstance(value, dict) and value.get("failure") in get_args(Failure):
                raise ProcessingFailure(value["failure"])
            result = ExtractionOutput.model_validate(value)
            if [page.page_number for page in result.pages] != list(range(1, len(result.pages) + 1)):
                raise ValueError
            return result
        except (ValidationError, ValueError, OSError):
            raise ProcessingFailure("extractor_failure") from None


class ExtractionService:
    def __init__(self, reports: ReportsService, settings: Settings) -> None:
        self.reports = reports
        self.settings = settings
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="report-extraction")
        self.slots = BoundedSemaphore(2)

    def close(self) -> None:
        self.pool.shutdown(wait=True, cancel_futures=True)

    def rpc(self, name: str, current: AuthenticatedRequest, payload: dict[str, object]) -> object:
        if self.settings.report_processing_key is None:
            raise ApiProblem(
                503, "processing_unavailable", "Text extraction has not been configured."
            )
        return self.reports.gateway.request(
            "POST",
            f"/rest/v1/rpc/processing_{name}",
            access_token=current.access_token,
            purpose="reports",
            payload={
                **payload,
                "p_worker_secret": self.settings.report_processing_key.get_secret_value(),
            },
        )

    def history(self, report_id: UUID, current: AuthenticatedRequest) -> ProcessingHistory:
        value = self.rpc("history", current, {"p_report_id": str(report_id)})
        try:
            if not isinstance(value, list) or len(value) > 3:
                raise ValueError
            runs = [ProcessingRun.model_validate(row) for row in value]
            if any(run.report_id != report_id for run in runs):
                raise ValueError
            return ProcessingHistory(runs=runs)
        except ValueError:
            raise report_unavailable() from None

    def request(self, report_id: UUID, key: UUID, current: AuthenticatedRequest) -> ProcessingRun:
        if not self.slots.acquire(blocking=False):
            raise ApiProblem(429, "rate_limited", "Extraction is busy. Try again shortly.")
        scheduled = False
        try:
            value = self.rpc(
                "request_configured",
                current,
                {
                    "p_report_id": str(report_id),
                    "p_idempotency_key": str(key),
                    "p_processor": (
                        f"native-first-v1; pypdfium2 {version('pypdfium2')}; "
                        f"Pillow {version('Pillow')}; tesserocr {version('tesserocr')} (planned)"
                    ),
                    "p_configuration": {
                        "max_pages": self.settings.report_processing_max_pages,
                        "timeout_seconds": self.settings.report_processing_timeout_seconds,
                        "languages": "eng+hin",
                        "dpi": 250,
                        "strategy": "native-first-v1",
                    },
                },
            )
            run = ProcessingRun.model_validate(value)
            if run.report_id != report_id:
                raise report_unavailable()
            if run.status == "queued":
                self.pool.submit(self._work, run, current)
                scheduled = True
            logger.info("processing_requested")
            return run
        except ValidationError:
            raise report_unavailable() from None
        finally:
            if not scheduled:
                self.slots.release()

    def _work(self, run: ProcessingRun, current: AuthenticatedRequest) -> None:
        params: dict[str, object] = {"p_report_id": str(run.report_id), "p_run_id": str(run.id)}
        try:
            if self.rpc("start", current, params) is not True:
                return
            logger.info("processing_started")
            result: ExtractionOutput | None = None
            failure: Failure | None = None
            try:
                row = self.reports.get(run.report_id, current)
                stored = self.reports.download(row, current)
                result = extract(stored.data, stored.media_type, self.settings)
            except ProcessingFailure as error:
                failure = error.category
            except ApiProblem:
                failure = "source_unavailable"
            except Exception:
                failure = "extractor_failure"
            # RPC locks/rechecks source status, owner, active session, hash and deadline.
            committed = self.rpc(
                "finish",
                current,
                {
                    **params,
                    "p_result": result.model_dump(mode="json") if result else None,
                    "p_error": failure,
                },
            )
            if committed is True and result is not None:
                for page in result.pages:
                    logger.info(
                        "native_extraction_completed"
                        if page.method == "native_text"
                        else "ocr_fallback_used"
                    )
                logger.info("processing_completed")
            else:
                logger.info("processing_failed")
        except Exception:
            # No tracebacks/provider messages/text. The durable deadline recovers an
            # unacknowledged outcome after restart, revocation or network interruption.
            logger.warning("processing_outcome_unconfirmed")
        finally:
            self.slots.release()

    def result(
        self, report_id: UUID, current: AuthenticatedRequest, run_id: UUID | None
    ) -> ExtractionResult:
        history = self.history(report_id, current)
        run = next(
            (
                run
                for run in history.runs
                if run.status == "completed" and (run_id is None or run.id == run_id)
            ),
            None,
        )
        if run is None:
            raise ApiProblem(
                404, "extraction_not_found", "No completed text extraction is available."
            )
        value = self.reports.gateway.request(
            "GET",
            "/rest/v1/report_pages",
            access_token=current.access_token,
            params={
                "run_id": f"eq.{run.id}",
                "select": "content",
                "order": "page_number.asc",
                "limit": "20",
            },
            purpose="reports",
        )
        try:
            if not isinstance(value, list):
                raise ValueError
            pages = [ExtractedPage.model_validate(row["content"]) for row in value]
            if len(pages) != run.page_count or [p.page_number for p in pages] != list(
                range(1, len(pages) + 1)
            ):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise report_unavailable() from None
        if self.reports.get(report_id, current).status != "uploaded":
            raise not_found()
        return ExtractionResult(run=run, pages=pages)
