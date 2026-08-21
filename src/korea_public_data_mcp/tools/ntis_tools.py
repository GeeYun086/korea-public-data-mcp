"""NTIS 국가R&D 과제정보 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import ntis as ntis_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def ntis_search_projects(query: str, limit: int = 20, start: int = 1) -> dict:
        """국가 R&D 과제를 키워드로 검색한다 (NTIS, 대국민 공개 정보).
        과제명·과제고유번호·연구책임자·주관연구기관·연구기간·연구비·요약을 반환한다.

        query: 검색어 (예: '이차전지', '자율주행').
        limit: 최대 반환 건수 (최대 100).
        start: 시작 위치 (다음 페이지를 볼 때 사용, 1부터 시작).
        """
        key = f"ntis:{query}:{limit}:{start}"
        try:
            return await cached_call(key, lambda: ntis_client.search_projects(query, limit, start))
        except MissingApiKeyError as e:
            return {"error": str(e)}
