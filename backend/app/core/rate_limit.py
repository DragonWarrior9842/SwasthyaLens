"""Bounded single-process development limiter; production requires edge limits."""

import time
from collections import deque
from threading import Lock

from app.core.errors import ApiProblem


class RateLimiter:
    def __init__(self) -> None:
        self._entries: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str, *, limit: int, seconds: int = 60) -> None:
        now = time.monotonic()
        with self._lock:
            if len(self._entries) >= 10_000:
                self._entries = {
                    entry: timestamps
                    for entry, timestamps in self._entries.items()
                    if timestamps and timestamps[-1] > now - 3600
                }
                if len(self._entries) >= 10_000 and key not in self._entries:
                    raise ApiProblem(429, "rate_limited", "Too many requests. Try again later.")
            timestamps = self._entries.setdefault(key, deque())
            while timestamps and timestamps[0] <= now - seconds:
                timestamps.popleft()
            if len(timestamps) >= limit:
                raise ApiProblem(429, "rate_limited", "Too many requests. Try again later.")
            timestamps.append(now)
