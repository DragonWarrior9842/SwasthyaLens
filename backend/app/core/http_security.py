"""Bound small JSON bodies and prevent authentication responses being cached."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyTooLarge(Exception):
    pass


class BrowserSecurityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        consumed = 0

        async def bounded_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > 16_384:
                    raise BodyTooLarge
            return message

        async def security_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"cache-control", b"no-store"), (b"referrer-policy", b"no-referrer"),
                    (b"x-content-type-options", b"nosniff"),
                ])
                message["headers"] = headers
            await send(message)

        length = next((value for key, value in scope["headers"] if key == b"content-length"), b"0")
        try:
            if int(length) > 16_384:
                raise BodyTooLarge
            await self.app(scope, bounded_receive, security_send)
        except (BodyTooLarge, ValueError):
            response = JSONResponse(
                {"code": "validation_error", "message": "The request body is too large or invalid."},
                status_code=413,
            )
            await response(scope, receive, security_send)
