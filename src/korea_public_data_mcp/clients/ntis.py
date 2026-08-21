"""NTIS(국가과학기술지식정보서비스) Open API 클라이언트.

엔드포인트·파라미터·응답 구조는 실제 키로 호출한 원본 XML로 확인했다 (2026-08).
루트는 <RESULT><RESULTSET><HIT NO="n">... 형태이고, 총건수는 <TOTALHITS>에 있다.
필드는 <ProjectTitle><Korean>/<English></ProjectTitle>, <Manager><Name>,
<ResearchAgency><Name>, <OrderAgency><Name>, <ProjectPeriod><Start>/<End>,
<GovernmentFunds>, <TotalFunds>, <Abstract><Full>/<Teaser> 처럼 중첩된 태그다.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.rate_limiter import throttle

_BASE = "https://www.ntis.go.kr"
_PROJECT_SEARCH = "/rndopen/openApi/public_project"


def _text(node: ET.Element, *paths: str) -> str:
    for path in paths:
        found = node.findtext(path)
        if found and found.strip():
            return found.strip()
    return ""


async def search_projects(query: str, limit: int = 20, start: int = 1) -> dict:
    """국가 R&D 과제를 키워드로 검색한다 (대국민 공개 과제 정보)."""
    await throttle("ntis")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{_BASE}{_PROJECT_SEARCH}",
            params={
                "apprvKey": get_api_key("ntis"),
                "collection": "project",
                "SRWR": query,
                "startPosition": max(start, 1),
                "displayCnt": max(1, min(limit, 100)),
            },
        )
    if resp.status_code >= 400:
        return {"error": f"NTIS HTTP {resp.status_code}: {resp.text[:200]}"}

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        return {"error": f"NTIS 응답 파싱 실패: {e}. raw={resp.text[:300]}"}

    # NTIS는 인증키 오류·IP 미등록 같은 실패도 HTTP 200 + 정상 XML(<error>메시지</error>)로 돌려준다.
    # 그대로 아래 파싱을 타면 HIT/TOTALHITS 가 없어 '검색 결과 0건'으로 위장되므로 여기서 먼저 걸러낸다.
    # (Element 는 자식이 없으면 falsy 라서 `find(..) or find(..)` 로 묶으면 안 된다 — is not None 으로 판정.)
    err_node = root if root.tag.lower() == "error" else None
    if err_node is None:
        for tag in ("error", "ERROR", "Error"):
            found = root.find(f".//{tag}")
            if found is not None:
                err_node = found
                break
    if err_node is not None:
        return {"error": f"NTIS: {(err_node.text or '').strip() or '알 수 없는 오류'}"}

    hits = root.findall(".//HIT") or root.findall(".//hit")
    total = _text(root, ".//TOTALHITS", ".//totalHits") or str(len(hits))

    projects = [
        {
            "과제명": _text(h, "ProjectTitle/Korean", "ProjectTitle", "TITLE"),
            "과제고유번호": _text(h, "ProjectNumber", "PROJECT_NUMBER"),
            "연구책임자": _text(h, "Manager/Name", "Manager", "MANAGER_NAME"),
            "주관연구기관": _text(h, "ResearchAgency/Name", "ResearchAgency", "RESEARCH_AGENCY_NAME"),
            "관리기관": _text(h, "OrderAgency/Name", "OrderAgency", "ORDER_AGENCY_NAME"),
            "연구기간_시작": _text(h, "ProjectPeriod/Start", "PROJECT_START_DATE"),
            "연구기간_종료": _text(h, "ProjectPeriod/End", "PROJECT_END_DATE"),
            "정부투자금": _text(h, "GovernmentFunds", "GOVERNMENT_FUNDS"),
            "총연구비": _text(h, "TotalFunds", "TOTAL_FUNDS"),
            "요약": _text(h, "Abstract/Full", "Abstract", "GOAL_ABSTRACT"),
        }
        for h in hits
    ]
    return {"query": query, "total": total, "count": len(projects), "projects": projects}
