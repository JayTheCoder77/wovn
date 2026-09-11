from __future__ import annotations

import time
from collections import defaultdict, deque


class JobRateLimiter:
    def __init__(self, limit: int = 10, window_seconds: float = 3600) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def check(self, user_id: str) -> bool:
        now = time.monotonic()
        queue = self._hits[user_id]
        while queue and now - queue[0] > self.window_seconds:
            queue.popleft()
        if len(queue) >= self.limit:
            return False
        queue.append(now)
        return True


job_rate_limiter = JobRateLimiter()
