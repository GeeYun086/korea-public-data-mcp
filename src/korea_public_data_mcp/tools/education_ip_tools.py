"""교육(나이스)·지식재산권(KIPRIS) MCP 도구 등록.

두 기관은 담는 데이터가 서로 완전히 달라(학교 명부 vs 특허 서지) 통합 검색으로 묶지 않고
각각 개별 도구로 노출한다. 여러 기관이 같은 종류의 자료를 주는 경우에만 묶는다
(gov_search 가 그 사례).
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import kipris as kipris_client
from korea_public_data_mcp.clients import neis as neis_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def neis_search_schools(
        region: str = "",
        school_name: str = "",
        school_kind: str = "",
        limit: int = 100,
    ) -> dict:
        """전국 초·중·고·특수학교의 기본정보를 조회한다.
        학교명·학교급·교육청·지역·설립구분·주소·전화·홈페이지를 반환한다.

        region: 시도 이름 (예: '서울', '경기', '부산'). 지정하면 해당 교육청 소속만 조회한다.
                범위를 좁히지 않으면 응답이 지나치게 커지므로 가급적 지정할 것.
        school_name: 학교명 부분 검색 (예: '대전고').
        school_kind: '초등학교' | '중학교' | '고등학교' | '특수학교' | '각종학교'.
        limit: 최대 반환 건수 (최대 1000).
        """
        try:
            key = f"neis:{region}:{school_name}:{school_kind}:{limit}"
            return await cached_call(
                key,
                lambda: neis_client.search_schools(region, school_name, school_kind, limit),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}

    @mcp.tool()
    async def ip_search(query: str, limit: int = 20, page: int = 1) -> dict:
        """국내 특허·실용신안을 키워드로 검색한다 (KIPRIS Plus).
        발명명칭·출원번호·출원일·출원인·등록상태·IPC 분류·초록을 반환한다.

        query: 검색어. 발명명칭과 초록에서 찾는다 (예: '인공지능', '이차전지').
        limit: 최대 반환 건수 (최대 100).
        page: 페이지 번호. 뒤쪽 결과를 볼 때 사용한다.

        호출 한도가 월 1,000회로 빠듯하므로 같은 검색을 반복하지 말 것.
        """
        try:
            return await cached_call(
                f"kipris:{query}:{limit}:{page}",
                lambda: kipris_client.search_patents(query, limit, page),
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
