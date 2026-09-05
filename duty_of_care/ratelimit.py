"""Per-caller sliding-window limits for the routes that spend model tokens.

The store is in-process on purpose. A Cloud Run instance or a Replit Autoscale
machine enforces its own window, which is enough to stop one caller from
draining the Google Cloud credit before judging ends without adding a shared
cache that the anonymous judge path would then depend on.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class LimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class SlidingWindow:
    def __init__(self, window_seconds: int = 60) -> None:
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, bucket: str, limit: int, *, now: float | None = None) -> LimitDecision:
        moment = time.monotonic() if now is None else now
        hits = self._hits[bucket]
        while hits and moment - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            retry = int(self.window_seconds - (moment - hits[0])) + 1
            return LimitDecision(False, limit, 0, max(retry, 1))
        hits.append(moment)
        return LimitDecision(True, limit, limit - len(hits), 0)

    def reset(self) -> None:
        self._hits.clear()
