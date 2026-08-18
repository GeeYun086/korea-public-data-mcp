"""공공데이터포털(data.go.kr) 기반 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import data_go_kr as data_go_kr_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def data_go_kr_check_business_status(business_numbers: list[str]) -> dict:
        """사업자등록번호(하이픈 없이 10자리) 상태를 최대 100건까지 한 번에 배치 조회한다.
        예: business_numbers=['1234567890', '0987654321']."""
        try:
            key = "data_go_kr:biz:" + ",".join(sorted(business_numbers))
            return await cached_call(
                key, lambda: data_go_kr_client.check_business_status(business_numbers)
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def data_go_kr_generic_get(base_url: str, path: str, params: dict) -> dict:
        """공공데이터포털의 다른 서비스(사전에 클라이언트 코드가 없는 것)를 호출할 때 쓰는 범용 도구.
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
