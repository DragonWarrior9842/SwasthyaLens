"""Bound bodies by the exact upload route; retain small authentication JSON limits."""

import re

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyTooLarge(Exception):
    pass


class BrowserSecurityMiddleware:
    def __init__(self, app: ASGIApp, report_max_upload_bytes: int = 5_242_880) -> None:
        self.app = app
        self.report_max_upload_bytes = report_max_upload_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        consumed = 0
        is_upload = scope.get("method") == "PUT" and re.fullmatch(
            r"/reports/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/file",
            scope.get("path", ""),
        )
        body_limit = self.report_max_upload_bytes if is_upload else 16_384

        async def bounded_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > body_limit:
                    raise BodyTooLarge
            return message

        async def security_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-content-type-options", b"nosniff"),
                    ]
                )
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
            response = JSONResponse(
                {
                    "code": "validation_error",
                    "message": "The request body is too large or invalid.",
                },
                status_code=413,
            )
            await response(scope, receive, security_send)
