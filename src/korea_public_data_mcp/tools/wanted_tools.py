"""원티드(Wanted) 채용정보 MCP 도구 등록.

인증키 발급에 사업자등록번호가 필요해(퇴사 시점 기준 미발급) 실제 키로 호출 검증을
못 했다. 그래서 MissingApiKeyError 외의 예외도 한 번 더 감싸서, 응답 구조가 예상과
달라도 크래시 대신 안내 메시지가 담긴 dict를 돌려주게 했다.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients import wanted as wanted_client
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def wanted_search_company(query: str, limit: int = 10) -> dict:
        """원티드에 등록된 회사를 이름(또는 사업자등록번호)으로 검색한다.
        회사ID를 얻는 게 목적이며, 이 값으로 wanted_get_company_jobs 를 호출한다.

        query: 회사명 (예: '토스', '당근마켓').
        limit: 최대 반환 건수 (최대 100).
        """
        key = f"wanted:company:{query}:{limit}"
        try:
            return await cached_call(key, lambda: wanted_client.search_company(query, limit))
        except MissingApiKeyError as e:
            return {"error": str(e)}
        except Exception as e:  # noqa: BLE001 - 실호출로 검증되지 않은 소스라 방어적으로 감싼다.
            return {"error": f"원티드 호출 중 예기치 못한 오류: {e}"}

    @mcp.tool()
    async def wanted_get_company_jobs(company_id: str, limit: int = 20) -> dict:
        """회사ID로 그 회사가 현재 채용 중인 포지션 목록을 조회한다.
        company_id는 wanted_search_company 결과의 '회사ID' 값을 그대로 쓴다.
        """
        key = f"wanted:jobs:{company_id}:{limit}"
        try:
            return await cached_call(key, lambda: wanted_client.get_company_jobs(company_id, limit))
        except MissingApiKeyError as e:
            return {"error": str(e)}
        except Exception as e:  # noqa: BLE001 - 실호출로 검증되지 않은 소스라 방어적으로 감싼다.
            return {"error": f"원티드 호출 중 예기치 못한 오류: {e}"}

    @mcp.tool()
    async def wanted_search_positions(query: str, limit: int = 20) -> dict:
        """직무·포지션 키워드로 채용공고를 검색한다 (특정 회사에 한정하지 않음).

        query: 검색어 (예: '백엔드 개발자', '데이터 분석').
        limit: 최대 반환 건수 (최대 100).
        """
        key = f"wanted:pos:{query}:{limit}"
        try:
            return await cached_call(key, lambda: wanted_client.search_positions(query, limit))
        except MissingApiKeyError as e:
            return {"error": str(e)}
        except Exception as e:  # noqa: BLE001 - 실호출로 검증되지 않은 소스라 방어적으로 감싼다.
            return {"error": f"원티드 호출 중 예기치 못한 오류: {e}"}
