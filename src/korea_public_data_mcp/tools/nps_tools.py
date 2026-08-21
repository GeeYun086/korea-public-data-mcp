"""국민연금공단 사업장 가입자 내역 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import nps as nps_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def nps_search_employee_count(company_name: str, limit: int = 5) -> dict:
        """회사명으로 국민연금 사업장을 찾아 가입자수(재직자수 근사치)를 조회한다.
        같은 회사명으로 여러 사업장(본사·지사)이 잡힐 수 있어 상한을 둔다.

        company_name: 회사명 (예: '삼성전자').
        limit: 최대 반환 사업장 수 (기본 5).

        가입자수는 국민연금 가입자 기준이라 실제 임직원수와 정확히 일치하지 않을 수 있다.
        큰 그룹사명을 넣으면 "OO건설/일용/[삼성전자] ..." 처럼 그 회사 현장에서 일하는
        협력업체명까지 잡힐 수 있다 — 사업장명이 회사명과 정확히 일치하는 항목을 우선
        확인할 것. 추이(입퇴사 흐름)를 보려면 이 결과의 사업장코드로
        nps_get_employee_trend 를 호출한다.
        """
        key = f"nps:count:{company_name}:{limit}"

        async def _run():
            workplaces = await nps_client.search_workplace(company_name, limit)
            results = []
            for wp in workplaces:
                seq = wp.get("사업장코드")
                detail = await nps_client.get_employee_count(seq) if seq else {}
                results.append({**wp, "가입자수": detail.get("가입자수"), "당월고지금액": detail.get("당월고지금액")})
            return {"query": company_name, "count": len(results), "workplaces": results}

        try:
            return await cached_call(key, _run)
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def nps_get_employee_trend(seq: str, year_month: str = "") -> dict:
        """사업장코드(seq)로 신규취득자수·상실가입자수(해당월 입퇴사 흐름)를 조회한다.
        seq는 nps_search_employee_count 결과의 '사업장코드' 값을 그대로 쓴다.

        year_month: 조회할 기준월 (YYYYMM). 비우면 최신 기준월로 조회한다.
        """
        key = f"nps:trend:{seq}:{year_month}"
        try:
            return await cached_call(key, lambda: nps_client.get_employee_trend(seq, year_month))
        except MissingApiKeyError as e:
            return {"error": str(e)}
