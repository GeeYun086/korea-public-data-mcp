"""Korea Public Data MCP 서버 엔트리포인트.

Claude Desktop/Code 등 MCP 클라이언트가 stdio로 이 프로세스를 띄우고 통신한다.
API 키가 하나도 없어도 서버는 정상적으로 시작되고 도구 목록도 노출된다 —
실제 키가 필요한 시점은 각 도구가 '호출'될 때 뿐이다 (config.get_api_key 참고).
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.tools import (
    dart_tools,
    data_go_kr_tools,
    ecos_tools,
    education_ip_tools,
    gov_tools,
    kci_tools,
    koreaexim_tools,
    kosis_tools,
    nps_tools,
    ntis_tools,
    seoul_institute_tools,
    wanted_tools,
    work24_tools,
)

mcp = MCPServer(
    "korea-public-data",
    instructions=(
        "대한민국 공공데이터(금융감독원 OpenDART 재무제표/공시, 한국은행 ECOS 거시경제지표, "
        "통계청 KOSIS 국가통계, 공공데이터포털 data.go.kr, 한국수출입은행 환율/금리)와 "
        "정부 지원사업·공공 입찰공고(기업마당, K-Startup, 과기정통부, 나라장터), "
        "전국 학교 정보(나이스), 국내 특허·실용신안(KIPRIS Plus), 국가 R&D 과제정보(NTIS), "
        "서울연구원 연구보고서, KCI 학술논문(한국학술지인용색인), "
        "국민연금 사업장 가입자수(임직원수 추정), "
        "원티드 채용정보, 고용24 K-디지털 트레이닝(KDT) 훈련과정을 "
        "조회하는 도구 모음입니다. "
        "수치나 통계를 답할 때는 반드시 이 도구들로 조회한 실제 값을 근거로 답하고, "
        "임의로 추정하지 마세요. 회사 재무 정보는 dart_search_company로 corp_code를 먼저 "
        "확인한 뒤 dart_get_financial_statements를 호출하세요. "
        "정부 지원사업이나 입찰공고를 찾을 때는 gov_search를 쓰고, 질문에 기관명이 "
        "언급되면 sources에 그 기관을 지정하세요. "
        "\n\n[특정 업체의 수주·낙찰 이력 조회 시 필수 확인] '이 회사가 수주/낙찰한 사업을 "
        "찾아줘'처럼 업체 하나를 특정해 나라장터·조달 정보를 조회하는 요청을 받으면, "
        "gov_search를 바로 호출하지 말고 먼저 아래를 확인하세요(사용자가 이미 준 정보는 "
        "다시 묻지 말 것):\n"
        "  1) 정확한 상호명 — 사업자등록증 기준 정식 명칭(주식회사/(주) 표기, 지점 여부 포함)\n"
        "  2) 사업자등록번호 — API가 이 값으로 직접 필터링하진 못하지만, 결과에 동명이인·"
        "유사상호가 섞여 나올 경우 최종 확인용 대조 기준으로 필요\n"
        "  3) 조회 목적과 기간 — 진행 중 입찰인지/낙찰 이력인지/체결된 계약인지, 그리고 "
        "원하는 기간(나라장터 낙찰정보는 최근 14일, 계약정보는 최대 7일 단위로만 한 번에 "
        "조회되므로 장기간이면 나눠서 여러 번 호출해야 함을 미리 안내)\n"
        "이 정보를 확인한 뒤 gov_search 호출 시 sources=['나라장터']를 지정하고, query가 "
        "아니라 company 파라미터에 정확한 상호를 넣으세요 — query는 부분일치라 계열사·"
        "유사상호까지 함께 걸리지만, company는 정규화 후 완전히 같은 업체명만 통과시킵니다. "
        "그래도 후보가 여러 건이면 사업자등록번호로 사용자에게 최종 확인을 요청하고, 확정 "
        "전에는 결과를 '후보'로 표시하세요."
    ),
)

dart_tools.register(mcp)
ecos_tools.register(mcp)
kosis_tools.register(mcp)
data_go_kr_tools.register(mcp)
koreaexim_tools.register(mcp)
gov_tools.register(mcp)
education_ip_tools.register(mcp)
ntis_tools.register(mcp)
seoul_institute_tools.register(mcp)
kci_tools.register(mcp)
nps_tools.register(mcp)
wanted_tools.register(mcp)
work24_tools.register(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
