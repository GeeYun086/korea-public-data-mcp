"""원티드(Wanted) 채용정보 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import wanted as wanted_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def wanted_search_company(query: str, limit: int = 10) -> dict:
        """원티드에 등록된 회사를 이름(또는 사업자등록번호)으로 검색한다.
        회사ID를 얻는 게 목적이며, 이 값으로 wanted_get_company_jobs 를 호출한다.

        query: 회사명 (예: '토스', '당근마켓').
        limit: 최대 반환 건수 (최대 100).
        """
        key = f"wanted:company:{query}:{limit}"
        try:
            return await cached_call(key, lambda: wanted_client.search_company(query, limit))
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def wanted_get_company_jobs(company_id: str, limit: int = 20) -> dict:
        """회사ID로 그 회사가 현재 채용 중인 포지션 목록을 조회한다.
        company_id는 wanted_search_company 결과의 '회사ID' 값을 그대로 쓴다.
        """
        key = f"wanted:jobs:{company_id}:{limit}"
        try:
            return await cached_call(key, lambda: wanted_client.get_company_jobs(company_id, limit))
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def wanted_search_positions(query: str, limit: int = 20) -> dict:
        """직무·포지션 키워드로 채용공고를 검색한다 (특정 회사에 한정하지 않음).

        query: 검색어 (예: '백엔드 개발자', '데이터 분석').
        limit: 최대 반환 건수 (최대 100).
        """
        key = f"wanted:pos:{query}:{limit}"
        try:
            return await cached_call(key, lambda: wanted_client.search_positions(query, limit))
        except MissingApiKeyError as e:
            return {"error": str(e)}
