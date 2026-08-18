"""한국수출입은행 기반 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import koreaexim as koreaexim_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def koreaexim_get_exchange_rates(search_date: str = "") -> dict:
        """한국수출입은행 현재환율(매매기준율/전신환매매율)을 조회한다.
        search_date: YYYYMMDD 또는 YYYY-MM-DD, 생략 시 당일 영업일 기준.
        영업일 11시 이전이나 비영업일 조회 시 데이터가 비어 있을 수 있다."""
        try:
            return await cached_call(
                f"koreaexim:exchange:{search_date}",
                lambda: koreaexim_client.get_exchange_rates(search_date),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def koreaexim_get_loan_rates(search_date: str = "") -> dict:
        """한국수출입은행 대출금리(고정기준금리)를 조회한다.
        search_date: YYYYMMDD 또는 YYYY-MM-DD, 생략 시 당일 영업일 기준."""
        try:
            return await cached_call(
                f"koreaexim:loan:{search_date}",
                lambda: koreaexim_client.get_loan_rates(search_date),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def koreaexim_get_international_rates(search_date: str = "") -> dict:
        """한국수출입은행 국제금리(LIBOR 등)를 조회한다.
        search_date: YYYYMMDD 또는 YYYY-MM-DD, 생략 시 당일 영업일 기준."""
        try:
            return await cached_call(
                f"koreaexim:intl:{search_date}",
                lambda: koreaexim_client.get_international_rates(search_date),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
