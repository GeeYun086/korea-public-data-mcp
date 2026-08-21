"""고용24(work24.go.kr) K-디지털 트레이닝(KDT) MCP 도구 등록."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import work24 as work24_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def work24_search_kdt_courses(
        course_type: str = "kdt", keyword: str = "", days_ahead: int = 180, limit: int = 20
    ) -> dict:
        """국민내일배움카드 훈련과정을 검색한다. K-디지털 트레이닝(KDT)이 기본값이다.
        과정명·훈련기관·훈련기간·수강비·정원·취업률·만족도를 반환한다.

        course_type: 'kdt'(K-디지털 트레이닝, 기본값) | 'kdt_basic'(K-디지털 기초역량훈련).
        keyword: 훈련과정명 부분검색 (예: 'AI', '백엔드').
        days_ahead: 오늘부터 며칠 뒤까지 시작하는 과정을 볼지 (기본 180일).
        limit: 최대 반환 건수 (최대 100).

        주의: 인증키 신청 시 사업자등록번호가 필요한 기업회원 전용 서비스다.
        """
        key = f"work24:{course_type}:{keyword}:{days_ahead}:{limit}"
        try:
            return await cached_call(
                key, lambda: work24_client.search_courses(course_type, keyword, days_ahead, limit)
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
