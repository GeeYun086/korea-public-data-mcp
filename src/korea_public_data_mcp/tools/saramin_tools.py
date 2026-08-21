"""사람인(Saramin) 채용정보 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import saramin as saramin_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def saramin_search_jobs(keywords: str = "", limit: int = 10, start: int = 0) -> dict:
        """사람인에서 채용공고를 검색한다. 회사명이나 직무명으로 찾을 수 있다.
        회사명·포지션·직무·지역·경력·학력·공고URL·등록일·마감일을 반환한다.

        keywords: 검색어 (예: '삼성전자', '백엔드 개발자'). 비우면 최근 공고를 그대로 반환한다.
        limit: 최대 반환 건수 (최대 110).
        start: 시작 위치 (0부터 시작, 다음 페이지를 볼 때 사용).

        일일 호출 한도가 500회로 제한되니 같은 검색을 반복하지 말 것.
        """
        key = f"saramin:{keywords}:{limit}:{start}"
        try:
            return await cached_call(key, lambda: saramin_client.search_jobs(keywords, limit, start))
        except MissingApiKeyError as e:
            return {"error": str(e)}
