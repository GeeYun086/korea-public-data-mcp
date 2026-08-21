"""KIPRIS Plus 특허정보 클라이언트.

주의할 점 두 가지 (예전 구현에서 실호출로 확인됨):
  1. 인증 파라미터명이 ServiceKey 다. 대문자 S 여야 하고, 일부 문서에 적힌
     accessKey / serviceKey 로는 INVALID_REQUEST_PARAMETER_ERROR 가 떨어진다.
  2. 응답이 XML 뿐이다. JSON 옵션이 없다.

무료 한도가 '월 1,000회'로 다른 소스(일 단위)보다 훨씬 빠듯하다.
한 번 검색에 여러 건을 받아오도록 하고, 캐시를 반드시 태운다.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.rate_limiter import throttle

_BASE = "https://plus.kipris.or.kr/kipo-api/kipi"
_SEARCH = "/patUtiModInfoSearchSevice/getWordSearch"


def _text(node: ET.Element, tag: str) -> str:
    found = node.findtext(tag)
    return found.strip() if found else ""


async def search_patents(word: str, limit: int = 20, page: int = 1) -> dict:
    """특허·실용신안을 키워드로 검색한다. 발명명칭·초록·출원인 등이 대상."""
    await throttle("kipris")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            _BASE + _SEARCH,
            params={
                "ServiceKey": get_api_key("kipris"),
                "word": word,
                "numOfRows": max(1, min(limit, 100)),
                "pageNo": max(page, 1),
            },
        )
    if resp.status_code >= 400:
        return {"error": f"KIPRIS HTTP {resp.status_code}: {resp.text[:200]}"}

    root = ET.fromstring(resp.text)
    code = _text(root, ".//resultCode")
    if code not in ("", "00"):
        msg = _text(root, ".//resultMsg")
        return {"error": f"KIPRIS 오류 {code}: {msg}"}

    items = root.findall(".//item")
    patents = [
        {
            "발명명칭": _text(it, "inventionTitle"),
            "출원번호": _text(it, "applicationNumber"),
            "출원일": _text(it, "applicationDate"),
            "출원인": _text(it, "applicantName"),
            "등록상태": _text(it, "registerStatus"),
            "등록번호": _text(it, "registerNumber"),
            "등록일": _text(it, "registerDate"),
            "IPC": _text(it, "ipcNumber"),
            "초록": _text(it, "astrtCont"),
            "대표도면": _text(it, "drawing"),
        }
        for it in items
    ]
    return {
        "query": word,
        "total": _text(root, ".//totalCount"),
        "count": len(patents),
        "patents": patents,
    }
