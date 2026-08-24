"""KCI(한국학술지인용색인, kci.go.kr — NRF 한국연구재단 운영) Open API 클라이언트.

스펙은 KCI 포털의 '논문 기본 정보 제공' 명세 페이지에서 확인했다 (2026-08,
kciportal/po/openapi/openDataView.kci?datasetBean.dtstSeqNo=1):
  - Base: https://open.kci.go.kr/po/openapi/openApiSearch.kci
  - apiCode=articleSearch
  - 파라미터: key(필수, 인증키), apiCode(필수), title(필수), author/journal/doi/
    institution/affiliation/keyword/abstract(전부 선택, UTF-8), dateFrom/dateTo
    (선택, 발행년월 YYYYMM 6자리 범위), regDateFrom/regDateTo, modDateFrom/modDateTo
    (선택, 등록일/수정일 YYYYMMDD), page, displayCount(기본 10, 최대 100).
    ※ title이 필수라서 검색어 없이는 호출할 수 없다.
  - 응답(XML) 구조: result > total, record(반복) > journalInfo(journal-name,
    publisher-name, foreign-listed/name, pub-year, pub-mon, volume, issue),
    articleInfo(article-categories, article-regularity, title-group/article-title,
    author-group/author, abstract-group/abstract, fpage, lpage, orte-open-yn, doi,
    uci, citation-count, url, verified).

★ 미검증 상태: 위 스펙은 공식 명세 페이지 기준이라 파라미터명은 신뢰도가 높지만,
키 발급에 사업자등록증 심사가 필요해(퇴사 시점 기준 미발급) 실제 호출로 응답을 받아본
적은 없다. 인증 실패·요청 오류 시 에러가 어떤 형태로 오는지(명세 페이지에 미기재)는
확인 불가라, NTIS/KIPRIS처럼 명시적인 에러 태그가 있을 때만 에러로 판정하고, 레코드
파싱도 태그 후보를 여러 개 두는 방어적 방식을 유지한다. 첫 실호출 후 다르면
_text()/_find_records() 호출부의 후보 목록만 조정하면 된다.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.rate_limiter import throttle

_BASE = "https://open.kci.go.kr/po/openapi/openApiSearch.kci"

_RECORD_TAGS = ("record", "Record", "RECORD", "item", "Item", "ITEM")


def _text(node: ET.Element, *paths: str) -> str:
    for path in paths:
        found = node.findtext(path)
        if found and found.strip():
            return found.strip()
    return ""


def _find_records(root: ET.Element) -> list[ET.Element]:
    for tag in _RECORD_TAGS:
        found = root.findall(f".//{tag}")
        if found:
            return found
    return []


def _find_error(root: ET.Element) -> str:
    """명시적인 에러 표시가 있을 때만 에러 메시지를 뽑는다.

    KCI 명세 페이지에는 에러 응답 형식이 기재돼 있지 않다. NTIS가 인증키 오류 등을
    HTTP 200 + 정상형 XML로 감춰서 준 전례가 있어 대비는 해두되, '결과 0건'을 에러로
    오판하지 않도록 정말 명시적인 태그(error/resultCode+resultMsg 조합)가 있을 때만
    에러로 취급한다.
    """
    for tag in ("error", "ERROR", "Error", "errMsg", "ERR_MSG"):
        found = root.find(f".//{tag}")
        if found is not None and (found.text or "").strip():
            return (found.text or "").strip()

    code = _text(root, ".//resultCode", ".//RESULT_CODE", ".//resultCd")
    msg = _text(root, ".//resultMsg", ".//RESULT_MSG", ".//resultMessage")
    if code and msg and code not in ("00", "0000", "0", "1", "success", "SUCCESS"):
        return f"{code}: {msg}"
    return ""


def _slim_article(node: ET.Element) -> dict:
    fpage = _text(node, "articleInfo/fpage", "fpage")
    lpage = _text(node, "articleInfo/lpage", "lpage")
    return {
        "논문명": _text(
            node, "articleInfo/title-group/article-title", "title-group/article-title",
            "articleInfo/title", "title",
        ),
        "저자": _text(node, "articleInfo/author-group/author", "author-group/author", "author"),
        "저널명": _text(node, "journalInfo/journal-name", "journal-name", "journalName"),
        "발행기관": _text(node, "journalInfo/publisher-name", "publisher-name"),
        "발행연도": _text(node, "journalInfo/pub-year", "pub-year", "pubYear"),
        "발행월": _text(node, "journalInfo/pub-mon", "pub-mon"),
        "권": _text(node, "journalInfo/volume", "volume"),
        "호": _text(node, "journalInfo/issue", "issue"),
        "페이지": f"{fpage}-{lpage}" if fpage or lpage else "",
        "DOI": _text(node, "articleInfo/doi", "doi"),
        "초록": _text(node, "articleInfo/abstract-group/abstract", "abstract-group/abstract", "abstract"),
        "인용횟수": _text(node, "articleInfo/citation-count", "citation-count"),
        "오픈액세스여부": _text(node, "articleInfo/orte-open-yn", "orte-open-yn"),
        "원문URL": _text(node, "articleInfo/url", "url"),
        "UCI": _text(node, "articleInfo/uci", "uci"),
    }


async def search_articles(
    query: str, author: str = "", year: str = "", limit: int = 20, page: int = 1
) -> dict:
    """KCI 등재 학술논문을 제목 키워드로 검색한다 (apiCode=articleSearch).

    query: 논문 제목에 포함될 검색어 (title 파라미터, KCI 스펙상 필수값).
    author: 저자명으로 좁히고 싶을 때 (선택).
    year: 발행연도(YYYY)로 좁히고 싶을 때 — dateFrom/dateTo(YYYYMM) 범위로 변환해 보낸다.
    """
    await throttle("kci")
    params = {
        "apiCode": "articleSearch",
        "key": get_api_key("kci"),
        "title": query,
        "displayCount": max(1, min(limit, 100)),
        "page": max(page, 1),
    }
    if author:
        params["author"] = author
    if year:
        params["dateFrom"] = f"{year}01"
        params["dateTo"] = f"{year}12"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_BASE, params=params)
    if resp.status_code >= 400:
        return {"error": f"KCI HTTP {resp.status_code}: {resp.text[:200]}"}

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        return {"error": f"KCI 응답 파싱 실패(XML 아님): {e}. raw={resp.text[:300]}"}

    err = _find_error(root)
    if err:
        return {"error": f"KCI 오류: {err}"}

    records = _find_records(root)
    articles = [_slim_article(r) for r in records]
    total = _text(root, ".//total", ".//totalCount", ".//TOTAL_COUNT") or str(len(articles))
    return {"query": query, "total": total, "count": len(articles), "articles": articles}
