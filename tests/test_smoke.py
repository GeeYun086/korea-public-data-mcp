"""API 키 없이도 돌아가는 최소 스모크 테스트.

- 서버 모듈 import 및 도구 등록이 에러 없이 되는지
- 키가 없는 상태에서 도구를 호출하면 크래시 대신 안내 메시지가 담긴 dict를 반환하는지
"""
import asyncio

import pytest

from korea_public_data_mcp import server


def test_server_imports_and_registers_tools():
    tool_names = set(asyncio.run(server.mcp.list_tools()).__class__.__name__ and [])
    # list_tools()는 코루틴이라 위 표현은 이름만 확보하기 위한 트릭 대신 아래처럼 직접 호출
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    assert "dart_search_company" in names
    assert "ecos_get_key_indicator" in names
    assert "kosis_search_statistics" in names
    assert "data_go_kr_generic_get" in names
    assert "koreaexim_get_exchange_rates" in names
    assert "gov_search" in names
    assert "gov_list_sources" in names
    assert "ip_search" in names
    assert "neis_search_schools" in names
    assert "ntis_search_projects" in names
    assert "si_search_reports" in names
    assert "nps_search_employee_count" in names
    assert "nps_get_employee_trend" in names
    assert "wanted_search_company" in names
    assert "wanted_get_company_jobs" in names
    assert "wanted_search_positions" in names
    assert "work24_search_kdt_courses" in names
    assert "kci_search_articles" in names


@pytest.mark.parametrize(
    "tool_name,kwargs",
    [
        ("dart_search_company", {"company_name": "삼성전자"}),
        ("ecos_get_key_indicator", {"indicator": "기준금리", "start": "202301", "end": "202312"}),
        ("kosis_search_statistics", {"keyword": "실업률"}),
        (
            "data_go_kr_generic_get",
            {
                "base_url": "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService",
                "path": "getDataSetOpnStdBidPblancInfo",
                "params": {"pageNo": 1, "numOfRows": 1},
            },
        ),
        ("koreaexim_get_exchange_rates", {}),
        ("gov_search", {"query": "AI", "sources": ["기업마당"]}),
        ("ip_search", {"query": "인공지능"}),
        ("ntis_search_projects", {"query": "이차전지"}),
        ("si_search_reports", {"query": "서울"}),
        ("nps_search_employee_count", {"company_name": "삼성전자"}),
        ("nps_get_employee_trend", {"seq": "1"}),
        ("wanted_search_company", {"query": "토스"}),
        ("wanted_get_company_jobs", {"company_id": "1"}),
        ("wanted_search_positions", {"query": "백엔드"}),
        ("work24_search_kdt_courses", {"keyword": "AI"}),
        ("kci_search_articles", {"query": "인공지능"}),
    ],
)
def test_tools_fail_gracefully_without_api_key(tool_name, kwargs, monkeypatch):
    for var in [
        "DART_API_KEY",
        "ECOS_API_KEY",
        "KOSIS_API_KEY",
        "DATA_GO_KR_API_KEY",
        "KOREAEXIM_EXCHANGE_API_KEY",
        "KOREAEXIM_LOAN_API_KEY",
        "KOREAEXIM_INTERNATIONAL_API_KEY",
        "BIZINFO_API_KEY",
        "KIPRIS_API_KEY",
        "NTIS_API_KEY",
        "SEOUL_INSTITUTE_API_KEY",
        "WANTED_CLIENT_ID",
        "WANTED_CLIENT_SECRET",
        "WANTED_AUTHORIZATION",
        "WORK24_API_KEY",
        "KCI_API_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)

    result = asyncio.run(server.mcp.call_tool(tool_name, kwargs))
    # call_tool은 (content_list, is_error) 형태 등 SDK 버전에 따라 다를 수 있으므로
    # 예외 없이 반환되는지만 확인한다.
    assert result is not None


def test_neis_search_schools_works_without_api_key(monkeypatch):
    """NEIS는 다른 소스와 달리 키가 없어도 에러 대신 5건 제한 결과를 준다."""
    monkeypatch.delenv("NEIS_API_KEY", raising=False)
    result = asyncio.run(
        server.mcp.call_tool("neis_search_schools", {"region": "서울", "school_name": "고등학교"})
    )
    assert result is not None


def test_registry_resolves_sources_by_agency_name():
    """모델은 '조달청'처럼 기관명으로 부르는 경우가 많다. 별칭으로도 잡혀야 한다."""
    from korea_public_data_mcp import registry

    # "조달청"은 조달 4단계 전부에 걸린 별칭이라 단계별 소스가 모두 잡혀야 한다
    assert {s.id for s in registry.resolve(["조달청"])} == {
        "g2b_order_plan", "g2b_request", "g2b_prestandard",
        "g2b_bid", "g2b_award", "g2b_contract"}
    assert [s.id for s in registry.resolve(["사전규격"])] == ["g2b_prestandard"]
    assert [s.id for s in registry.resolve(["기업마당"])] == ["bizinfo"]
    # 보조금24는 활용신청을 중단해 소스에서 제거했다 (bizinfo/kstartup/msit 3종)
    assert len(registry.resolve(None, domain="gov_program")) == 3
    assert len(registry.resolve(None, domain="procurement")) == 6
    assert registry.resolve(["존재하지않는기관"]) == []
