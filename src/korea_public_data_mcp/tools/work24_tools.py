"""고용24(work24.go.kr) K-디지털 트레이닝(KDT) MCP 도구 등록.

인증키 발급에 사업자등록번호가 필요해(퇴사 시점 기준 미발급) 실제 키로 호출 검증을
못 했다. 그래서 MissingApiKeyError 외의 예외도 한 번 더 감싸서, 응답 구조가 예상과
달라도(clients/work24.py 상단 주석의 _ROW_KEYS 불확실성 참고) 크래시 대신 안내
메시지가 담긴 dict를 돌려주게 했다.
"""
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
        except Exception as e:  # noqa: BLE001 - 실호출로 검증되지 않은 소스라 방어적으로 감싼다.
            return {"error": f"고용24 호출 중 예기치 못한 오류: {e}"}
