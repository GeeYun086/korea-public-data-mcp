"""수집 소스 레지스트리.

소스를 '코드'가 아니라 '데이터'로 관리한다. 새 소스를 붙일 때 도구 코드를 고치지 않고
여기에 항목 하나를 추가하고 clients/gov_sources.py 에 어댑터 함수만 붙이면 된다.

domain 태그는 지금은 검색 필터로만 쓰지만, 나중에 서버를 도메인별로 쪼개거나
도메인 단위 도구를 나눌 때 그대로 재사용한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    id: str
    name: str  # 사용자/모델이 부르는 이름
    domain: str  # gov_program | procurement
    api_key: str  # config.API_KEYS 의 키 이름
    description: str
    aliases: tuple[str, ...] = ()  # "조달청", "나라장터" 처럼 질문에 등장할 수 있는 표기
    stage: str = ""  # 조달 단계 (발주계획/사전규격/입찰공고 ...). 지원사업은 빈 값
    note: str = ""


SOURCES: dict[str, Source] = {
    "bizinfo": Source(
        id="bizinfo",
        name="기업마당",
        domain="gov_program",
        api_key="bizinfo",
        description="중소기업·소상공인 지원사업 공고 (금융/기술/인력/수출/내수/창업/경영). 중앙부처와 지자체 공고를 함께 제공",
        aliases=("기업마당", "bizinfo", "중소기업 지원사업", "중소벤처기업부"),
        note="지원대상의 약 80%가 '중소기업'. 다른 소스가 못 잡는 일반 중소기업 층을 담당한다.",
    ),
    "kstartup": Source(
        id="kstartup",
        name="K-Startup",
        domain="gov_program",
        api_key="data_go_kr",
        description="창업 지원사업 공고. 예비창업자~창업 7년 이내 대상이 중심",
        aliases=("K-Startup", "케이스타트업", "창업진흥원", "창업지원"),
        note="창업업력(예비창업자/1년미만/…)으로 대상을 좁힐 수 있다.",
    ),
    "bojo24": Source(
        id="bojo24",
        name="보조금24",
        domain="gov_program",
        api_key="data_go_kr",
        description="정부·지자체가 제공하는 공공서비스(혜택) 목록. 개인 대상 복지·혜택이 대부분이고 소상공인 항목이 일부 포함",
        aliases=("보조금24", "보조금", "공공서비스", "행정안전부", "정부혜택"),
        note="사용자구분 기준 개인 82%. 기업 지원사업을 찾을 때는 기대치를 낮게 잡을 것.",
    ),
    "msit": Source(
        id="msit",
        name="과기정통부 사업공고",
        domain="gov_program",
        api_key="data_go_kr",
        description="과학기술정보통신부가 게시하는 R&D·국제협력·인프라 사업 공모 공고",
        aliases=("과기정통부", "과학기술정보통신부", "msit"),
        note="부처 본부 게시판 공고만 제공한다. IITP·한국연구재단 등 산하 전문기관 공고는 포함되지 않는다(실호출 확인).",
    ),
    # ── 조달은 한 사업이 아래 순서로 흘러간다. 앞 단계일수록 먼저 알 수 있다. ──
    #    발주계획(수개월 전) → 사전규격(2주~1달 전) → 입찰공고 → 계약
    "g2b_order_plan": Source(
        id="g2b_order_plan",
        name="나라장터 발주계획",
        domain="procurement",
        api_key="data_go_kr",
        description="공공기관이 연간·분기 단위로 미리 공개하는 발주 예정 목록. 사업명·발주기관·발주월·계약방법·발주금액 제공",
        aliases=("발주계획", "발주", "나라장터", "조달청", "조달", "g2b"),
        stage="발주계획",
        note="입찰공고보다 수개월 앞선 신호다. 아직 공고가 안 뜬 사업을 미리 파악할 때 쓴다.",
    ),
    "g2b_request": Source(
        id="g2b_request",
        name="나라장터 조달요청",
        domain="procurement",
        api_key="data_go_kr",
        description="수요기관이 조달청에 구매를 요청한 건. 요청명·수요기관·요청금액 제공",
        aliases=("조달요청", "구매요청", "나라장터", "조달청", "조달", "g2b"),
        stage="조달요청",
        note="발주계획과 입찰공고 사이 단계다. 조달청을 거치는 건만 올라온다.",
    ),
    "g2b_prestandard": Source(
        id="g2b_prestandard",
        name="나라장터 사전규격",
        domain="procurement",
        api_key="data_go_kr",
        description="입찰공고 전 의견수렴 단계에 공개되는 규격안. 사업명·수요기관·배정예산·의견등록 마감일시 제공",
        aliases=("사전규격", "규격", "사전공개", "나라장터", "조달청", "조달", "g2b"),
        stage="사전규격",
        note="입찰공고보다 2주~1달 앞선 신호다. 의견등록 마감 전이면 규격에 의견을 낼 수 있다.",
    ),
    "g2b_bid": Source(
        id="g2b_bid",
        name="나라장터 입찰공고",
        domain="procurement",
        api_key="data_go_kr",
        description="공공기관 입찰공고. 공고명·공고기관·수요기관·배정예산·추정가격·입찰마감일 제공",
        aliases=("나라장터", "조달청", "입찰", "입찰공고", "g2b", "조달"),
        stage="입찰공고",
        note="건수가 매우 많다(2주 약 1.6만 건). 조회 기간을 반드시 좁혀서 호출한다.",
    ),
    "g2b_award": Source(
        id="g2b_award",
        name="나라장터 낙찰정보",
        domain="procurement",
        api_key="data_go_kr",
        description="개찰이 끝난 건의 낙찰 결과. 낙찰업체명·사업자번호·낙찰금액·낙찰률·참여업체수 제공",
        aliases=("낙찰", "낙찰정보", "개찰", "나라장터", "조달청", "조달", "g2b"),
        stage="낙찰",
        note="낙찰률과 참여업체수가 있어 경쟁 강도와 가격 수준을 가늠할 때 쓴다.",
    ),
    "g2b_contract": Source(
        id="g2b_contract",
        name="나라장터 계약정보",
        domain="procurement",
        api_key="data_go_kr",
        description="체결이 끝난 계약 내역. 계약명·수요기관·계약금액·계약방법 제공",
        aliases=("계약", "계약정보", "나라장터", "조달청", "조달", "g2b"),
        stage="계약",
        note="이미 끝난 건이라 사업 발굴용이 아니라 실적·경쟁사 분석용이다.",
    ),
}


def resolve(names: list[str] | None, domain: str | None = None) -> list[Source]:
    """소스 이름/별칭 목록을 Source 목록으로 바꾼다.

    names 가 비어 있으면 domain 에 해당하는(또는 전체) 소스를 반환한다.
    매칭은 id/name/alias 부분일치로 관대하게 처리한다 — 모델이 '조달청'처럼
    기관명으로 부르는 경우가 많기 때문이다.
    """
    pool = [s for s in SOURCES.values() if domain is None or s.domain == domain]
    if not names:
        return pool

    picked: list[Source] = []
    for raw in names:
        q = raw.strip().lower()
        if not q:
            continue
        for s in pool:
            if s in picked:
                continue
            hay = [s.id, s.name, *s.aliases]
            if any(q in h.lower() or h.lower() in q for h in hay):
                picked.append(s)
    return picked


def catalog(domain: str | None = None) -> list[dict]:
    """등록된 소스 목록을 사람이 읽을 수 있는 형태로 반환한다."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "domain": s.domain,
            "stage": s.stage,
            "description": s.description,
            "note": s.note,
        }
        for s in SOURCES.values()
        if domain is None or s.domain == domain
    ]


# 전용 어댑터를 두지 않은 서비스들.
#
# 공고가 아니라 통계·단가·코드사전 성격이라 gov_search 결과에 섞으면 오히려 방해가 된다.
# 다만 활용신청은 완료돼 있고 엔드포인트도 확인했으므로, data_go_kr_generic_get 으로
# 바로 호출할 수 있다. 모델이 주소를 추측할 수는 없으니 여기에 적어두고 목록으로 노출한다.
# (엔드포인트는 data.go.kr 상세페이지에 포함된 Swagger 명세에서 확인 — 2026-08 기준)
EXTRA_ENDPOINTS = [
    {
        "id": "15129412", "name": "공공조달통계정보",
        "base_url": "https://apis.data.go.kr/1230000/at/PubPrcrmntStatInfoService",
        "operations": ["getTotlPubPrcrmntSttus", "getDminsttAccotBsnsObjAccotArslt",
                       "getPrcrmntEntrprsAccotCntrctMthdAccotArslt"],
        "note": "24개 전자조달시스템의 계약 집계. 기관별·기업별·계약방법별 실적. 개별 공고가 아니라 시장 규모 분석용",
    },
    {
        "id": "15129415", "name": "나라장터 가격정보현황",
        "base_url": "https://apis.data.go.kr/1230000/ao/PriceInfoService",
        "operations": ["getPriceInfoListFcltyCmmnMtrilEngrk", "getPriceInfoListMrktCnstrctPcEngrk"],
        "note": "시설공통자재·시장시공 단가. 입찰 가격 산정 참고용",
    },
    {
        "id": "15129459", "name": "나라장터 계약과정통합공개",
        "base_url": "https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService",
        "operations": ["getCntrctProcssIntgOpenThng", "getCntrctProcssIntgOpenServc",
                       "getCntrctProcssIntgOpenCnstwk"],
        "note": "계약 체결 과정 통합 공개. 업무구분별로 오퍼레이션이 나뉜다",
    },
    {
        "id": "15129417", "name": "조달청 물품목록정보",
        "base_url": "https://apis.data.go.kr/1230000/ao/ThngListInfoService02",
        "operations": ["getThngGuidanceMapInfo02", "getThngPrdnmLocplcAccotListInfoInfoPrdlstSearch02"],
        "note": "물품 분류번호 사전. 다른 조달 API의 품목 코드를 해석할 때 쓴다",
    },
    {
        "id": "15129470", "name": "조달청 물품관리정보",
        "base_url": "https://apis.data.go.kr/1230000/ao/PrdctMngInfoService",
        "operations": ["getPrdctClsfcNoUslfsvc"],
        "note": "물품 내용연수 고시 정보",
    },
    {
        "id": "15129466", "name": "나라장터 사용자정보",
        "base_url": "https://apis.data.go.kr/1230000/ao/UsrInfoService02",
        "operations": ["getPrcrmntCorpBasicInfo02", "getDminsttInfo02", "getUnptRsttCorpInfo02"],
        "note": "나라장터 등록 조달업체·수요기관 정보. inqryDiv 필수",
    },
    {
        "id": "15129467", "name": "나라장터 업종·근거법규",
        "base_url": "https://apis.data.go.kr/1230000/ao/IndstrytyBaseLawrgltInfoService",
        "operations": ["getIndstrytyBaseLawrgltInfoList"],
        "note": "업종 코드와 근거 법령 사전. 입찰 참가자격(면허) 해석용",
    },
    {
        "id": "15129471", "name": "나라장터쇼핑몰 품목정보",
        "base_url": "https://apis.data.go.kr/1230000/at/ShoppingMallPrdctInfoService",
        "operations": ["getMASCntrctPrdctInfoList"],
        "note": "종합쇼핑몰 물품 카탈로그. 공고가 아니라 이미 계약된 상품 목록",
    },
    {
        "id": "15125365", "name": "창업진흥원 창업공간플랫폼",
        "base_url": "https://apis.data.go.kr/B552735/kisedSlpService",
        "operations": ["getCenterList", "getCenterSpaceList"],
        "note": "창업 보육센터·공간 정보. 공고가 아니라 시설 목록",
    },
]
