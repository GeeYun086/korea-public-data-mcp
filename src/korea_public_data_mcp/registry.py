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
