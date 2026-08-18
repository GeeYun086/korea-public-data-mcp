"""통계청 KOSIS 기반 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import kosis as kosis_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def kosis_search_statistics(keyword: str) -> dict:
        """키워드로 KOSIS 통계표(org_id/tbl_id)를 검색한다. 예: '실업률', '인구', '출생아수'."""
        try:
            matches = await cached_call(
                f"kosis:search:{keyword}", lambda: kosis_client.search_statistics(keyword)
            )
            return {"matches": matches}
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def kosis_get_statistics_data(
        org_id: str,
        tbl_id: str,
        prd_se: str = "Y",
        start_prd: str = "",
        end_prd: str = "",
        item_ids: str = "",
    ) -> dict:
        """kosis_search_statistics로 찾은 org_id/tbl_id의 통계자료를 표 단위로 일괄 조회한다.
        prd_se: 'Y'(연)|'Q'(분기)|'M'(월). start_prd~end_prd로 기간 범위를 지정하면
        여러 연도/월을 한 번의 호출로 받아올 수 있다 (개별 호출 반복 금지)."""
        try:
            return await cached_call(
                f"kosis:data:{org_id}:{tbl_id}:{prd_se}:{start_prd}:{end_prd}:{item_ids}",
                lambda: kosis_client.get_statistics_data(
                    org_id, tbl_id, prd_se, start_prd, end_prd, item_ids
                ),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
