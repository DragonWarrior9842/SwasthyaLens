"""Private Storage I/O uses the current user's JWT, never an unrestricted key."""

import json
from dataclasses import dataclass, field
from uuid import uuid4

import httpx

from app.core.errors import ApiProblem
from app.core.provider import SupabaseGateway


def storage_unavailable() -> ApiProblem:
    return ApiProblem(503, "storage_unavailable", "Report storage is temporarily unavailable.")


@dataclass(frozen=True)
class StoredFile:
    data: bytes = field(repr=False)
    media_type: str


class ReportStorage:
    def __init__(self, gateway: SupabaseGateway, max_bytes: int) -> None:
        self.gateway = gateway
        self.max_bytes = max_bytes

    def _request(
        self,
        method: str,
        path: str,
        token: str,
        *,
        data: bytes | None = None,
        media_type: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> StoredFile:
        headers = {
            "apikey": self.gateway.publishable_key,
            "Authorization": f"Bearer {token}",
            "Cookie": "",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache, no-store",
        }
        if media_type is not None:
            headers["Content-Type"] = media_type
            headers["x-upsert"] = "false"
            headers["cache-control"] = "no-store"
        try:
            with self.gateway.client.stream(
                method,
                self.gateway.origin + path,
                headers=headers,
                content=data,
                json=payload,
                timeout=httpx.Timeout(30, connect=5),
                follow_redirects=False,
            ) as response:
                status = response.status_code
                result = bytearray()
                limit = self.max_bytes if method == "GET" and status == 200 else 65_536
                for chunk in response.iter_bytes(chunk_size=16_384):
                    if len(result) + len(chunk) > limit:
                        raise storage_unavailable()
                    result.extend(chunk)
                content_type = response.headers.get("content-type", "").split(";")[0].lower()
        except httpx.HTTPError:
            raise storage_unavailable() from None
        if status >= 400:
            code: object = ""
            try:
                error: object = json.loads(result)
                if isinstance(error, dict):
                    code = error.get("code", error.get("statusCode"))
            except ValueError:
                pass
            if not isinstance(code, (str, int)):
                code = ""
            if status == 404 or code in {"404", 404, "NoSuchKey", "ObjectNotFound", "not_found"}:
                raise ApiProblem(404, "storage_not_found", "Report file not found.")
            if status == 409 or code in {"409", 409, "Duplicate", "ResourceAlreadyExists"}:
                raise ApiProblem(409, "storage_conflict", "A report file already exists.")
            raise storage_unavailable()
        if not 200 <= status < 300:
            raise storage_unavailable()
        return StoredFile(bytes(result), content_type)

    def upload(self, path: str, token: str, data: bytes, media_type: str) -> None:
        self._request(
            "POST", f"/storage/v1/object/reports/{path}", token, data=data, media_type=media_type
        )

    def download(self, path: str, token: str) -> StoredFile:
        # Provider edge caching can retain a previously authorized URL even after
        # deletion. A fresh documented cacheNonce forces an origin/RLS check.
        return self._request(
            "GET", f"/storage/v1/object/authenticated/reports/{path}?cacheNonce={uuid4()}", token
        )

    def delete(self, path: str, token: str) -> None:
        self._request("DELETE", "/storage/v1/object/reports", token, payload={"prefixes": [path]})
