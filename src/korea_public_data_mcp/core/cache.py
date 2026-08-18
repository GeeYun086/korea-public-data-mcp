"""메모리 TTL 캐시 + (선택) 디스크 캐시.

같은 질문을 짧은 시간 안에 여러 번 물어봐도 API를 다시 때리지 않도록 해서
- 불필요한 호출로 인한 차단 위험을 줄이고
- 응답 속도도 높인다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Awaitable

from cachetools import TTLCache

from korea_public_data_mcp.config import CACHE_DIR, CACHE_TTL_SECONDS

_memory_cache: TTLCache = TTLCache(maxsize=2048, ttl=CACHE_TTL_SECONDS)


async def cached_call(key: str, fn: Callable[[], Awaitable[Any]]) -> Any:
    """key로 메모리 캐시를 확인하고, 없으면 fn()을 호출해 결과를 캐싱한다."""
    if key in _memory_cache:
        return _memory_cache[key]
    result = await fn()
    _memory_cache[key] = result
    return result


def disk_cache_path(name: str) -> Path:
    return CACHE_DIR / name


def read_disk_json(name: str) -> Any | None:
    path = disk_cache_path(name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_disk_json(name: str, data: Any) -> None:
    disk_cache_path(name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def disk_file_is_fresh(name: str, max_age_seconds: int) -> bool:
    path = disk_cache_path(name)
    if not path.exists():
        return False
    import time

    return (time.time() - path.stat().st_mtime) < max_age_seconds
