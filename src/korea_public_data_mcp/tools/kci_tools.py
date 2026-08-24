"""KCI(한국학술지인용색인) 학술논문 검색 MCP 도구 등록.

키 발급에 사업자등록증 심사가 필요해 실제 키로 검증하지 못한 채 코드만 미리 얹어둔
상태다 (clients/kci.py 상단 주석 참고). 그래서 다른 도구들과 달리 MissingApiKeyError
외의 예외도 여기서 한 번 더 감싼다 — 응답 구조가 예상과 달라도 크래시 대신 안내 메시지가
담긴 dict를 돌려주기 위함이다. 키를 넣은 뒤 첫 호출 결과가 비정상이면 clients/kci.py 의
필드 후보를 실제 태그명으로 조정하면 된다.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import kci as kci_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def kci_search_articles(
        query: str, author: str = "", year: str = "", limit: int = 20, page: int = 1
    ) -> dict:
        """KCI(한국학술지인용색인)에 등재된 국내 학술논문을 키워드로 검색한다.
        논문명·저자·저널명·발행연도·DOI·키워드·초록을 반환한다.

        query: 검색어 (논문 제목 또는 키워드).
        author: 저자명으로 좁히고 싶을 때 (선택).
        year: 발행연도(YYYY)로 좁히고 싶을 때 (선택).
        limit: 최대 반환 건수 (최대 100).
        page: 페이지 번호 (1부터 시작).
        """
        key = f"kci:{query}:{author}:{year}:{limit}:{page}"
        try:
            return await cached_call(
                key, lambda: kci_client.search_articles(query, author, year, limit, page)
            )
        except MissingApiKeyError as e:
            return {"error": str(e)}
        except Exception as e:  # noqa: BLE001 - 실호출로 검증되지 않은 소스라 방어적으로 감싼다.
            return {"error": f"KCI 호출 중 예기치 못한 오류: {e}"}
