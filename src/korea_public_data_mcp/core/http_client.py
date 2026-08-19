"""재시도/백오프가 붙은 공용 HTTP 클라이언트.

- 429/5xx 응답이나 네트워크 오류 시 지수 백오프로 재시도 (최대 3회)
- 호출 전 rate_limiter로 속도 제한
- 응답 바디는 최대 길이를 넘으면 잘라서 LLM에게 던질 때 토큰을 낭비하지 않도록 함(각 client에서 후처리)
"""
from __future__ import annotations

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from korea_public_data_mcp.core.rate_limiter import throttle

# httpx는 INFO 레벨에서 요청 URL을 통째로 찍는데, 공공 API는 인증키를 쿼리스트링으로
# 받으므로 로그에 serviceKey/crtfcKey가 평문으로 남는다. MCP는 stderr가 클라이언트로
# 수집될 수 있어 그대로 두면 키가 새어나간다. 경고 이상만 남긴다.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

_TIMEOUT = httpx.Timeout(15.0, connect=10.0)


class UpstreamError(RuntimeError):
    """공공 API가 비정상 응답(4xx/5xx)을 준 경우."""


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((httpx.TransportError, UpstreamError)),
)
async def get_json(
    host_key: str,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
) -> dict:
    await throttle(host_key)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=headers)
    if resp.status_code == 429 or resp.status_code >= 500:
        raise UpstreamError(f"{url} -> HTTP {resp.status_code}: {resp.text[:200]}")
    if resp.status_code >= 400:
        # 4xx(429 제외)는 재시도해도 소용없는 경우가 많음 (키 오류, 파라미터 오류 등)
        raise RuntimeError(f"{url} -> HTTP {resp.status_code}: {resp.text[:500]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise RuntimeError(f"{url} -> JSON 파싱 실패: {resp.text[:500]}") from exc


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((httpx.TransportError, UpstreamError)),
)
async def get_bytes(host_key: str, url: str, *, params: dict | None = None) -> bytes:
    await throttle(host_key)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params)
    if resp.status_code == 429 or resp.status_code >= 500:
        raise UpstreamError(f"{url} -> HTTP {resp.status_code}")
    if resp.status_code >= 400:
        raise RuntimeError(f"{url} -> HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.content
