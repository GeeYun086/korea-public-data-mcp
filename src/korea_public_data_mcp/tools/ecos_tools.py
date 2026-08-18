"""한국은행 ECOS 기반 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import ecos as ecos_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def ecos_get_key_indicator(indicator: str, start: str, end: str) -> dict:
        """자주 찾는 거시경제 지표를 이름으로 바로 조회한다.
        indicator: '기준금리' | '원달러환율' | 'GDP성장률' | '소비자물가지수'.
        start/end 형식은 지표의 주기에 맞춰야 함(월간=YYYYMM, 분기=YYYYQn, 일간=YYYYMMDD)."""
        try:
            return await cached_call(
                f"ecos:key:{indicator}:{start}:{end}",
                lambda: ecos_client.get_key_indicator(indicator, start, end),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def ecos_search_statistics(keyword: str) -> dict:
        """키워드로 ECOS 통계표(stat_code)를 검색한다. 사전 등록되지 않은 지표를 찾을 때 사용."""
        try:
            tables = await cached_call(
                f"ecos:tables:{keyword}", lambda: ecos_client.search_statistic_tables(keyword)
            )
            return {"tables": tables}
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def ecos_get_statistic_data(
        stat_code: str, cycle: str, start: str, end: str, item_code1: str = "", item_code2: str = ""
    ) -> dict:
        """ecos_search_statistics로 찾은 stat_code로 실제 수치 데이터를 조회한다.
        cycle: D(일)/M(월)/Q(분기)/A(연)."""
        try:
            return await cached_call(
                f"ecos:data:{stat_code}:{cycle}:{start}:{end}:{item_code1}:{item_code2}",
                lambda: ecos_client.get_statistic_search(stat_code, cycle, start, end, item_code1, item_code2),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
