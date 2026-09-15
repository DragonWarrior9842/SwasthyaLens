"""Provider I/O does not follow redirects or buffer unbounded responses."""

from collections.abc import Iterator

import httpx
import pytest

from app.core.errors import ApiProblem
from app.core.provider import SupabaseGateway
from tests.auth_support import auth_settings


class LargeStream(httpx.SyncByteStream):
    def __init__(self) -> None:
        self.read_chunks = 0
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for _ in range(200):
            self.read_chunks += 1
            yield b"x" * 16_384

    def close(self) -> None:
        self.closed = True


def test_oversized_response_stopped_during_streaming() -> None:
    stream = LargeStream()
    transport = httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
    with httpx.Client(transport=transport) as client:
        gateway = SupabaseGateway(auth_settings(), client)
        with pytest.raises(ApiProblem) as failure:
            gateway.request("GET", "/auth/v1/.well-known/jwks.json")
    assert failure.value.status == 503
    assert stream.closed and stream.read_chunks < 65


def test_connection_failure_is_generic() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("internal host detail", request=request)

    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        gateway = SupabaseGateway(auth_settings(), client)
        with pytest.raises(ApiProblem) as failure:
            gateway.request("POST", "/auth/v1/token", payload={"password": "test-only-value"})
    assert failure.value.status == 503
    assert "internal" not in failure.value.message and "test-only" not in failure.value.message


def test_redirects_do_not_forward_credentials() -> None:
    visited: list[str] = []

    def redirect(request: httpx.Request) -> httpx.Response:
        visited.append(request.url.host)
        return httpx.Response(302, headers={"Location": "https://untrusted.example"})

    with httpx.Client(transport=httpx.MockTransport(redirect), follow_redirects=False) as client:
        gateway = SupabaseGateway(auth_settings(), client)
        with pytest.raises(ApiProblem):
            gateway.request("GET", "/rest/v1/profiles", access_token="test-only-token")
    assert visited == ["unit-test-project.supabase.co"]


def test_shared_provider_cookie_jar_is_not_forwarded() -> None:
    sent: list[str] = []

    def capture(request: httpx.Request) -> httpx.Response:
        sent.append(request.headers.get("cookie", ""))
        return httpx.Response(200, json={})

    with httpx.Client(
        transport=httpx.MockTransport(capture), cookies={"session": "unrelated"}
    ) as client:
        SupabaseGateway(auth_settings(), client).request("GET", "/auth/v1/settings")
    assert sent == [""]
