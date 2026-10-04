"""Bound bodies by the exact upload route; retain small authentication JSON limits."""

import asyncio
import logging
import re
import secrets
import time

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyTooLarge(Exception):
    pass


class BodyReadTimeout(HTTPException):
    def __init__(self) -> None:
        super().__init__(408, "The request body timed out.")


JSON_READ_SECONDS = 30.0
UPLOAD_READ_SECONDS = 60.0
logger = logging.getLogger("swasthyalens.http")


class BrowserSecurityMiddleware:
    def __init__(
        self, app: ASGIApp, report_max_upload_bytes: int = 5_242_880, secure: bool = False
    ) -> None:
        self.app = app
        self.report_max_upload_bytes = report_max_upload_bytes
        self.secure = secure

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        consumed = 0
        started = False
        status = 500
        request_id = secrets.token_hex(16)
        begin = time.monotonic()
        deadline: float | None = None
        is_upload = scope.get("method") == "PUT" and re.fullmatch(
            r"/reports/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/file",
            scope.get("path", ""),
        )
        body_limit = self.report_max_upload_bytes if is_upload else 16_384

        async def bounded_receive() -> Message:
            nonlocal consumed, deadline
            if deadline is None:
                deadline = time.monotonic() + (
                    UPLOAD_READ_SECONDS if is_upload else JSON_READ_SECONDS
                )
            try:
                async with asyncio.timeout(max(0, deadline - time.monotonic())):
                    message = await receive()
            except TimeoutError:
                raise BodyReadTimeout from None
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > body_limit:
                    raise BodyTooLarge
            return message

        async def security_send(message: Message) -> None:
            nonlocal started, status
            if message["type"] == "http.response.start":
                started, status = True, message["status"]
                policy = {
                    b"cache-control": b"no-store",
                    b"referrer-policy": b"no-referrer",
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=(), payment=()",
                    b"x-request-id": request_id.encode(),
                }
                if self.secure and scope.get("scheme") == "https":
                    policy[b"strict-transport-security"] = b"max-age=31536000"
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() not in policy]
                if not any(k.lower() == b"content-security-policy" for k, _ in headers) and (
                    self.secure or scope.get("path") not in {"/docs", "/redoc"}
                ):
                    policy[b"content-security-policy"] = (
                        b"default-src 'none'; base-uri 'none'; "
                        b"frame-ancestors 'none'; form-action 'none'"
                    )
                headers.extend(policy.items())
                message["headers"] = headers
            await send(message)

        length = next((value for key, value in scope["headers"] if key == b"content-length"), b"0")
        try:
            declared_length = int(length)
        except ValueError:
            declared_length = -1
        try:
            if not 0 <= declared_length <= body_limit:
                raise BodyTooLarge
            await self.app(scope, bounded_receive, security_send)
        except BodyTooLarge:
            if started:
                return
            response = JSONResponse(
                {
                    "code": "validation_error",
                    "message": "The request body is too large or invalid.",
                },
                status_code=413,
            )
            await response(scope, receive, security_send)
        except Exception:
            # Never log exception text/tracebacks: dependencies may embed report data or tokens.
            logger.error("request_failure request_id=%s category=unexpected", request_id)
            if not started:
                await JSONResponse(
                    {
                        "code": "service_unavailable",
                        "message": "The request could not be completed.",
                    },
                    status_code=500,
                )(scope, receive, security_send)
            else:
                # End a partially written response without injecting sensitive diagnostics.
                await send({"type": "http.response.body", "body": b"", "more_body": False})
        finally:
            # Route templates are application-owned; never log raw paths, query strings or owners.
            route = getattr(scope.get("route"), "path", "unmatched")
            method = scope.get("method")
            method = (
                method
                if method in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
                else "other"
            )
            logger.info(
                "request_complete request_id=%s method=%s route=%s status=%d duration_ms=%d",
                request_id,
                method,
                route,
                status,
                int((time.monotonic() - begin) * 1000),
            )
