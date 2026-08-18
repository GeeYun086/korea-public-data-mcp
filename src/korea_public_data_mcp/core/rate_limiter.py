"""아주 단순한 호스트별 토큰버킷 레이트리미터.

공공 API들은 초당/일당 호출 제한이 있고, 이를 넘기면 일시 차단(IP 밴)되는 경우가 있다.
그래서 클라이언트 쪽에서 먼저 스스로 속도를 늦춰 차단을 예방한다.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from korea_public_data_mcp.config import RATE_LIMIT_PER_SECOND


class _TokenBucket:
    def __init__(self, rate_per_second: float):
        self.rate = max(rate_per_second, 0.1)
        self.capacity = max(self.rate, 1.0)
        self.tokens = self.capacity
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.updated_at
                self.updated_at = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait)


_buckets: dict[str, _TokenBucket] = defaultdict(lambda: _TokenBucket(RATE_LIMIT_PER_SECOND))


async def throttle(host_key: str) -> None:
    """host_key(예: 'dart', 'ecos') 별로 초당 RATE_LIMIT_PER_SECOND 요청으로 속도를 제한한다."""
    await _buckets[host_key].acquire()
