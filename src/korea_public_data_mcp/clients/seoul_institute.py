"""서울연구원(si.re.kr) Open API 클라이언트.

실제 호출로 확인한 스펙 (공식 안내 페이지의 예시 RDF/dc: 구조와는 다름 — 실제 응답에는
네임스페이스가 없다):
  - POST https://www.si.re.kr/api, Content-Type: application/x-www-form-urlencoded
  - 파라미터: key(인증키) / command(현재 'extract'만 지원) / type(콘텐츠 종류, 필수) /
              page(0부터 시작, 기본 0) / npp(페이지당 건수, 기본 10)
  - type 은 검색어가 아니라 '콘텐츠 카테고리' 다. 자유 키워드 검색 파라미터는 없어서,
    카테고리 전체(또는 지정된 카테고리)를 받아온 뒤 제목/설명에서 키워드로 걸러낸다.
  - 응답은 XML: <TheSeoulInstituteList><total_nodes>N</total_nodes>
    <row><title><![CDATA[...]]></title><date>...</date><description><![CDATA[...]]></description>
    <identifier><![CDATA[...]]></identifier><creator>...</creator><type>...</type>
    <rights>...</rights><language>ko</language>...</row>...</TheSeoulInstituteList>
    (Dublin Core 필드셋이지만 dc: 네임스페이스 접두어 없이 평평하게 온다)
  - 에러 응답 형식은 공식 문서에 명시가 없어 확인 안 됨 — HTTP 상태코드로만 판단한다.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.rate_limiter import throttle

_URL = "https://www.si.re.kr/api"

CONTENT_TYPES = {
    "research_report": "연구보고서",
    "si_competition": "서울연구논문 공모전",
    "other": "단행본",
    "world_trends": "세계도시동향",
    "policy_report": "정책리포트",
    "infographics": "서울인포그래픽스",
    "studies": "서울도시연구",
    "cardnews": "카드뉴스",
    "small_report": "작은연구 좋은서울",
    "pr_video": "영상이야기",
    "collection": "학술행사자료집",
}

_FIELD_LABELS = {
    "title": "제목",
    "date": "날짜",
    "description": "설명",
    "identifier": "원문링크",
    "creator": "저자",
    "publisher": "발행처",
    "rights": "이용조건",
    "language": "언어",
    "subject": "주제",
}


async def _fetch_type(content_type: str, page: int, npp: int) -> tuple[int, list[dict]]:
    await throttle("seoul_institute")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _URL,
            data={
                "key": get_api_key("seoul_institute"),
                "command": "extract",
                "type": content_type,
                "page": max(page, 0),
                "npp": max(1, min(npp, 100)),
            },
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"서울연구원 HTTP {resp.status_code}: {resp.text[:200]}")

    root = ET.fromstring(resp.text)
    total_text = root.findtext("total_nodes") or "0"
    total = int(total_text) if total_text.strip().isdigit() else 0

    docs = []
    for row in root.findall("row"):
        rec = {"콘텐츠유형": CONTENT_TYPES.get(content_type, content_type)}
        for child in row:
            if child.text and child.text.strip():
                label = _FIELD_LABELS.get(child.tag, child.tag)
                rec[label] = child.text.strip()
        docs.append(rec)
    return total, docs


async def search_reports(
    query: str = "", content_type: str = "research_report", limit: int = 20, page: int = 0
) -> dict:
    """서울연구원 연구보고서·정책연구자료 메타데이터를 조회한다.

    content_type 은 자유 검색어가 아니라 콘텐츠 카테고리다 (예: 'research_report').
    자유 키워드 검색 파라미터가 공식 문서에 없어, 지정된 카테고리를 받아온 뒤
    제목(title)/설명(description)에서 키워드로 걸러낸다.
    """
    if content_type not in CONTENT_TYPES:
        return {
            "error": f"content_type='{content_type}' 은 유효하지 않다.",
            "content_types": CONTENT_TYPES,
        }

    total, docs = await _fetch_type(content_type, page, limit)

    if query:
        terms = query.lower().split()
        docs = [
            d for d in docs
            if all(t in " ".join(str(v) for v in d.values()).lower() for t in terms)
        ]

    return {
        "query": query,
        "content_type": content_type,
        "total": total,
        "count": len(docs),
        "reports": docs,
    }
