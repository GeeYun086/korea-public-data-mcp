"""원티드(Wanted) Open API 클라이언트.

공식 OpenAPI 스펙(openapi.wanted.jobs/v1/openapi.json, /v2/openapi.json)으로 확인한 스펙:
  - 인증: 쿼리파라미터가 아니라 헤더 3종 — wanted-client-id, wanted-client-secret, Authorization
  - V1 GET /search/company        — query(회사명/사업자번호), offset, limit
  - V1 GET /companies/{id}/jobs   — 회사의 채용중 포지션 목록. offset, limit
  - V1 GET /search/position       — query, years, offset, limit (직무 키워드 검색)
  - 페이지네이션은 offset/limit, 응답에 links.next 가 있다.
"""
from __future__ import annotations

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.rate_limiter import throttle

_BASE = "https://openapi.wanted.jobs/v1"


def _headers() -> dict:
    return {
        "wanted-client-id": get_api_key("wanted_client_id"),
        "wanted-client-secret": get_api_key("wanted_client_secret"),
        "Authorization": get_api_key("wanted_authorization"),
    }


async def _get(path: str, params: dict) -> dict:
    await throttle("wanted")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{_BASE}{path}", params=params, headers=_headers())
    if resp.status_code >= 400:
        return {"error": f"원티드 HTTP {resp.status_code}: {resp.text[:200]}"}
    try:
        return resp.json()
    except ValueError:
        return {"error": f"원티드 응답 파싱 실패(JSON 아님): {resp.text[:300]}"}


def _slim_company(c: dict) -> dict:
    return {
        "회사ID": c.get("id"),
        "회사명": c.get("name"),
        "사업자등록번호": c.get("registration_number"),
        "설명": c.get("description"),
        "주소": c.get("address"),
        "링크": c.get("link") or c.get("url"),
    }


def _slim_position(p: dict) -> dict:
    company = p.get("company") or {}
    address = p.get("address") or {}
    return {
        "포지션ID": p.get("id"),
        "포지션명": p.get("name"),
        "상태": p.get("status"),
        "회사명": company.get("name"),
        "회사ID": company.get("id"),
        "지역": address.get("full_location") or address.get("location"),
        "고용형태": p.get("employment_type"),
        "마감일": p.get("due_time"),
        "공고URL": p.get("url"),
    }


async def search_company(query: str, limit: int = 10) -> dict:
    """회사명(또는 사업자등록번호)으로 원티드에 등록된 회사를 검색한다."""
    data = await _get("/search/company", {"query": query, "offset": 0, "limit": max(1, min(limit, 100))})
    if "error" in data:
        return data
    companies = [_slim_company(c) for c in data.get("companies") or []]
    return {"query": query, "count": len(companies), "companies": companies}


async def get_company_jobs(company_id: str, limit: int = 20) -> dict:
    """회사ID로 그 회사가 현재 채용 중인 포지션 목록을 조회한다.
    company_id는 search_company 결과의 '회사ID' 값을 그대로 쓴다."""
    data = await _get(f"/companies/{company_id}/jobs", {"offset": 0, "limit": max(1, min(limit, 100))})
    if "error" in data:
        return data
    jobs = [_slim_position(j) for j in data.get("jobs") or []]
    return {"company_id": company_id, "count": len(jobs), "jobs": jobs}


async def search_positions(query: str, limit: int = 20) -> dict:
    """직무·포지션 키워드로 채용공고를 검색한다 (특정 회사가 아니라 전체 대상)."""
    data = await _get("/search/position", {"query": query, "offset": 0, "limit": max(1, min(limit, 100))})
    if "error" in data:
        return data
    jobs = [_slim_position(j) for j in data.get("jobs") or []]
    return {"query": query, "count": len(jobs), "jobs": jobs}
