"""OpenDART 기반 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import dart as dart_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def dart_search_company(company_name: str, limit: int = 10) -> dict:
        """회사명으로 OpenDART corp_code를 검색한다. 재무제표/공시 조회 전에 먼저 호출해서
        정확한 corp_code를 확인하는 용도. 예: company_name='삼성전자'."""
        try:
            matches = await cached_call(
                f"dart:search:{company_name}:{limit}",
                lambda: dart_client.search_company(company_name, limit),
            )
            return {"matches": matches}
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def dart_get_financial_statements(
        corp_code: str, year: int, report: str = "사업보고서", fs_div: str = "CFS"
    ) -> dict:
        """OpenDART 단일회사 전체 재무제표를 조회한다. corp_code는 dart_search_company로 먼저 찾을 것.
        report: '사업보고서'(연간, 기본값) | '1분기' | '반기' | '3분기'.
        fs_div: 'CFS'(연결재무제표, 기본값) | 'OFS'(별도재무제표)."""
        try:
            return await cached_call(
                f"dart:fs:{corp_code}:{year}:{report}:{fs_div}",
                lambda: dart_client.get_financial_statements(corp_code, year, report, fs_div),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def dart_get_company_disclosures(
        corp_code: str, start_date: str, end_date: str
    ) -> dict:
        """기간 내 회사 공시 목록을 조회한다. 날짜는 YYYYMMDD 형식 (예: 20240101)."""
        try:
            return await cached_call(
                f"dart:disc:{corp_code}:{start_date}:{end_date}",
                lambda: dart_client.get_company_disclosures(corp_code, start_date, end_date),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
