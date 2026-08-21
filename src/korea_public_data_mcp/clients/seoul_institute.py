"""서울연구원(si.re.kr) Open API 클라이언트.

실제 호출로 확인한 스펙 (공식 안내 페이지의 예시 RDF/dc: 구조와는 다름 — 실제 응답에는
네임스페이스가 없다):
  - POST https://www.si.re.kr/api, Content-Type: application/x-www-form-urlencoded
  - 파라미터: key(인증키) / command(현재 'extract'만 지원) / type(콘텐츠 종류, 필수) /
              page(1부터 시작 — 공식 안내는 0부터라고 하지만 page=0 과 page=1 이
                   같은 결과를 준다. 실호출로 확인) / npp(페이지당 건수, 기본 10)
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

import html
import re
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


_MAX_NPP = 100  # API 가 페이지당 허용하는 최대 건수
_DEFAULT_MAX_PAGES = 30  # 현재 최대 카테고리(연구보고서)가 24페이지라 여유를 둔다.

_SEARCH_FIELDS = ("제목", "설명", "저자", "주제")
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_html(text: str) -> str:
    """설명 필드는 HTML 이 엔티티로 이스케이프된 채 CDATA 로 온다 (&lt;p&gt; 등).

    언이스케이프 후 태그를 걷어내지 않으면 두 가지 문제가 생긴다.
    1) 사용자에게 '&lt;blockquote&gt;' 같은 마크업이 그대로 보인다.
    2) 'blockquote', 'nbsp' 같은 태그·엔티티 이름이 검색어에 걸려 오탐이 된다.
    """
    out = html.unescape(text or "")
    out = _TAG_RE.sub(" ", out)
    return re.sub(r"\s+", " ", out).strip()


async def _fetch_type(content_type: str, page: int, npp: int) -> tuple[int, list[dict]]:
    await throttle("seoul_institute")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _URL,
            data={
                "key": get_api_key("seoul_institute"),
                "command": "extract",
                "type": content_type,
                "page": max(page, 1),  # 0 은 1 과 동일하게 취급된다
                "npp": max(1, min(npp, _MAX_NPP)),
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
                rec[label] = _clean_html(child.text) if label == "설명" else child.text.strip()
        docs.append(rec)
    return total, docs


def _matches(doc: dict, terms: list[str]) -> bool:
    """제목·설명·저자·주제에서만 찾는다.

    전체 필드를 합쳐서 검색하면 '언어'(항상 'ko'), '이용조건', '콘텐츠유형'(항상 '연구보고서')
    같은 상수 필드 때문에 아무 검색어나 전건 매칭되는 오탐이 난다.
    """
    hay = " ".join(str(doc.get(f, "")) for f in _SEARCH_FIELDS).lower()
    return all(t in hay for t in terms)


async def search_reports(
    query: str = "",
    content_type: str = "research_report",
    limit: int = 20,
    page: int = 1,
    max_pages: int = _DEFAULT_MAX_PAGES,
) -> dict:
    """서울연구원 연구보고서·정책연구자료 메타데이터를 조회한다.

    이 API 에는 자유 키워드 검색 파라미터가 없다 (type 은 검색어가 아니라 카테고리다).
    그래서 검색어가 주어지면 카테고리를 페이지 단위로 순회하며 이쪽에서 걸러낸다.
    limit 은 '반환할 매칭 건수'이고, 목표 건수를 채우면 남은 페이지는 받지 않는다.

    (과거에는 limit 만큼만 한 페이지 받아서 그 안에서 필터링했다. 그래서 limit=2 로 부르면
     전체 2,296건 중 2건만 훑고 '0건'을 반환해, 검색 결과가 없는 것처럼 보였다.)
    """
    if content_type not in CONTENT_TYPES:
        return {
            "error": f"content_type='{content_type}' 은 유효하지 않다.",
            "content_types": CONTENT_TYPES,
        }

    want = max(1, min(limit, _MAX_NPP))

    # 검색어가 없으면 순회할 이유가 없다 — 요청한 페이지 한 장만 돌려준다.
    if not query.strip():
        total, docs = await _fetch_type(content_type, page, want)
        return {
            "query": "",
            "content_type": content_type,
            "total": total,
            "scanned": len(docs),
            "count": len(docs),
            "reports": docs,
        }

    terms = query.lower().split()
    matched: list[dict] = []
    seen: set[str] = set()  # 같은 자료가 여러 페이지에 걸쳐 나오는 경우가 있다
    scanned = 0
    pages = 0
    total = 0
    cur = max(page, 1)

    exhausted = False
    while pages < max_pages:
        total, docs = await _fetch_type(content_type, cur, _MAX_NPP)
        pages += 1
        if not docs:
            exhausted = True
            break
        scanned += len(docs)
        for d in docs:
            if not _matches(d, terms):
                continue
            ident = str(d.get("원문링크") or d.get("제목") or "")
            if ident in seen:
                continue
            seen.add(ident)
            matched.append(d)
            if len(matched) >= want:
                break
        if len(matched) >= want:
            break
        # 끝 판정은 '받은 건수 < 요청 건수' 로만 한다.
        # total_nodes 를 믿고 scanned >= total 로 끊으면 뒤쪽 자료를 놓친다 —
        # 연구보고서 카테고리는 total_nodes 가 2,296 인데 실제로는 2,314건이 나온다 (실호출 확인).
        if len(docs) < _MAX_NPP:
            exhausted = True
            break
        cur += 1

    out = {
        "query": query,
        "content_type": content_type,
        "total_reported": total,  # API 가 알려주는 값. 실제보다 작을 수 있어 참고용이다.
        "scanned": scanned,
        "pages_fetched": pages,
        "exhausted": exhausted,
        "count": len(matched),
        "reports": matched,
    }
    if exhausted:
        out["note"] = f"카테고리 전체를 끝까지 확인했다 ({scanned}건 확인, {len(matched)}건 일치)."
    else:
        out["note"] = (
            f"{scanned}건까지 확인해 {len(matched)}건을 찾았다 (API 집계 {total}건). "
            "아직 안 본 자료가 남아 있다 — limit 을 늘리거나 page 로 이어서 조회할 것."
        )
    return out
