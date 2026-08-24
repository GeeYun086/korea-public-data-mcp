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
        "언급되면 sources에 그 기관을 지정하세요."
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
