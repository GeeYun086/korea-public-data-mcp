"""서울연구원(si.re.kr) 연구자료 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import seoul_institute as si_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def si_search_reports(
        query: str = "", content_type: str = "research_report", limit: int = 20, page: int = 0
    ) -> dict:
        """서울연구원 연구보고서·정책연구자료 메타데이터를 조회한다.
        제목·설명·발행일·원문 링크를 반환한다.

        content_type: 콘텐츠 카테고리 (검색어가 아니라 카테고리를 고르는 것). 하나를 지정해야 한다.
            'research_report'(연구보고서, 기본값) | 'policy_report'(정책리포트) |
            'world_trends'(세계도시동향) | 'studies'(서울도시연구) | 'infographics'(서울인포그래픽스) |
            'cardnews'(카드뉴스) | 'small_report'(작은연구 좋은서울) | 'pr_video'(영상이야기) |
            'collection'(학술행사자료집) | 'si_competition'(서울연구논문 공모전) | 'other'(단행본).
        query: 검색어. 지정한 카테고리 안에서 제목/설명에 포함된 단어로 걸러낸다
               (API 자체는 자유검색을 지원하지 않아 이쪽에서 필터링한다). 비우면 카테고리 전체를 반환한다.
        limit: 최대 반환 건수 (최대 100).
        page: 페이지 번호 (0부터 시작).
        """
        key = f"si:{query}:{content_type}:{limit}:{page}"
        try:
            return await cached_call(
                key, lambda: si_client.search_reports(query, content_type, limit, page)
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
