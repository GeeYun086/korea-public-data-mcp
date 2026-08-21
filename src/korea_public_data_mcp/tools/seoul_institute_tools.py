"""서울연구원(si.re.kr) 연구자료 MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import seoul_institute as si_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def si_search_reports(
        query: str = "", content_type: str = "research_report", limit: int = 20, page: int = 1
    ) -> dict:
        """서울연구원 연구보고서·정책연구자료 메타데이터를 조회한다.
        제목·설명·발행일·원문 링크를 반환한다.

        content_type: 콘텐츠 카테고리 (검색어가 아니라 카테고리를 고르는 것). 하나를 지정해야 한다.
            'research_report'(연구보고서, 기본값) | 'policy_report'(정책리포트) |
            'world_trends'(세계도시동향) | 'studies'(서울도시연구) | 'infographics'(서울인포그래픽스) |
            'cardnews'(카드뉴스) | 'small_report'(작은연구 좋은서울) | 'pr_video'(영상이야기) |
            'collection'(학술행사자료집) | 'si_competition'(서울연구논문 공모전) | 'other'(단행본).
        query: 검색어. 제목·설명·저자·주제에서 찾는다. 공백으로 나눈 여러 단어는 AND 조건.
               API 가 자유검색을 지원하지 않아, 지정한 카테고리를 페이지 단위로 순회하며
               이쪽에서 걸러낸다. 비우면 순회 없이 최근 목록 한 페이지만 반환한다.
        limit: 반환할 '매칭 건수' (최대 100). 이 수를 채우면 남은 페이지는 받지 않는다.
        page: 조회를 시작할 페이지 (1부터 시작). 검색어가 있으면 여기서부터 순회한다.

        응답의 total 은 카테고리 전체 건수, scanned 는 실제로 확인한 건수다.
        note 에 전수 확인 여부가 적히므로, 'X건 중 0건'을 결과 없음으로 단정하지 말 것.
        """
        key = f"si:{query}:{content_type}:{limit}:{page}"
        try:
            return await cached_call(
                key, lambda: si_client.search_reports(query, content_type, limit, page)
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
