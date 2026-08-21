"""사람인(Saramin) Open API 클라이언트.

공식 가이드(oapi.saramin.co.kr) 기준 스펙:
  - GET https://oapi.saramin.co.kr/job-search
  - 인증: 쿼리파라미터 access-key (헤더 아님)
  - 기본 응답은 XML, Accept: application/json 헤더로 JSON 요청 가능
  - 일일 최대 500회 호출 제한
  - 에러코드: 1=키없음, 2=키오류, 3=파라미터오류, 4=일일호출초과, 99=시스템오류
"""
from __future__ import annotations

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.rate_limiter import throttle

_URL = "https://oapi.saramin.co.kr/job-search"


async def search_jobs(keywords: str = "", limit: int = 10, start: int = 0) -> dict:
    """채용공고를 키워드로 검색한다. 회사명·직무명 등으로 찾을 수 있다."""
    await throttle("saramin")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            _URL,
            params={
                "access-key": get_api_key("saramin"),
                "keywords": keywords,
                "count": max(1, min(limit, 110)),
                "start": max(start, 0),
            },
            headers={"Accept": "application/json"},
        )
    if resp.status_code >= 400:
        return {"error": f"사람인 HTTP {resp.status_code}: {resp.text[:200]}"}

    try:
        data = resp.json()
    except ValueError:
        return {"error": f"응답 파싱 실패(JSON 아님): {resp.text[:300]}"}

    if "error" in data:
        err = data["error"]
        return {"error": f"사람인 오류 {err.get('code')}: {err.get('msg')}"}

    jobs_block = data.get("jobs") or {}
    raw_jobs = jobs_block.get("job") or []
    if isinstance(raw_jobs, dict):
        raw_jobs = [raw_jobs]

    jobs = []
    for j in raw_jobs:
        company = j.get("company") or {}
        position = j.get("position") or {}
        jobs.append(
            {
                "회사명": (company.get("detail") or {}).get("name") or company.get("name"),
                "포지션": (position.get("title") or {}).get("name") if isinstance(position.get("title"), dict) else position.get("title"),
                "직무": position.get("job-type"),
                "산업": position.get("industry"),
                "지역": position.get("location"),
                "경력": j.get("experience-level"),
                "학력": j.get("required-education-level"),
                "공고URL": j.get("url"),
                "등록일": j.get("posting-date"),
                "마감일": j.get("expiration-date"),
            }
        )
    return {
        "query": keywords,
        "total": jobs_block.get("total"),
        "count": len(jobs),
        "jobs": jobs,
    }
