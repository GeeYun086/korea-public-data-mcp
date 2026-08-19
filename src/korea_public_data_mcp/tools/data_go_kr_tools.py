"""공공데이터포털(data.go.kr) 기반 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import data_go_kr as data_go_kr_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def data_go_kr_generic_get(base_url: str, path: str, params: dict) -> dict:
        """공공데이터포털의 서비스를 호출하는 범용 도구.
        base_url/path는 해당 서비스의 활용신청 상세페이지에 나온 End Point를 그대로 넣고,
        params에는 serviceKey를 제외한 나머지 파라미터만 넣는다(serviceKey는 자동으로 채워짐).
        자주 쓰는 서비스는 전용 client/tool을 새로 만드는 것을 권장 (README 확장 가이드 참고)."""
        try:
            return await cached_call(
                f"data_go_kr:generic:{base_url}:{path}:{sorted(params.items())}",
                lambda: data_go_kr_client.generic_get(base_url, path, params),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
