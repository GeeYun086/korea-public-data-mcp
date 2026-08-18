"""금융감독원 OpenDART 클라이언트.

- corpCode.xml 전체 목록을 한 번만 내려받아 로컬에 캐싱 (회사명 -> corp_code 매핑)
  -> 회사 검색을 위해 API를 반복 호출하지 않는다.
- 재무제표는 '단일회사 전체 재무제표(fnlttSinglAcntAll)' API로 계정과목을 한 번에 통째로 받는다
  -> 계정과목 하나하나 개별 호출하지 않는다 (호출 횟수/차단 위험 최소화).
"""
from __future__ import annotations

import io
import time
import zipfile
import xml.etree.ElementTree as ET

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.cache import (
    disk_file_is_fresh,
    read_disk_json,
    write_disk_json,
)
from korea_public_data_mcp.core.http_client import get_bytes, get_json

_BASE = "https://opendart.fss.or.kr/api"
_CORP_CODE_CACHE_NAME = "dart_corp_codes.json"
_CORP_CODE_MAX_AGE = 7 * 24 * 3600  # 회사 목록은 자주 안 바뀌므로 1주일 캐시


async def _download_corp_codes() -> list[dict]:
    raw = await get_bytes(
        "dart", f"{_BASE}/corpCode.xml", params={"crtfc_key": get_api_key("dart")}
    )
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        xml_bytes = zf.read(zf.namelist()[0])
    root = ET.fromstring(xml_bytes)
    companies = []
    for node in root.findall("list"):
        companies.append(
            {
                "corp_code": (node.findtext("corp_code") or "").strip(),
                "corp_name": (node.findtext("corp_name") or "").strip(),
                "stock_code": (node.findtext("stock_code") or "").strip(),
            }
        )
    return companies


async def _load_corp_codes() -> list[dict]:
    if disk_file_is_fresh(_CORP_CODE_CACHE_NAME, _CORP_CODE_MAX_AGE):
        cached = read_disk_json(_CORP_CODE_CACHE_NAME)
        if cached:
            return cached
    companies = await _download_corp_codes()
    write_disk_json(_CORP_CODE_CACHE_NAME, companies)
    return companies


async def search_company(name: str, limit: int = 10) -> list[dict]:
    """회사명(부분일치)으로 corp_code를 찾는다. 상장사는 stock_code도 함께 반환."""
    companies = await _load_corp_codes()
    name_lower = name.strip().lower()
    matches = [c for c in companies if name_lower in c["corp_name"].lower()]
    # 정확히 일치하는 것을 우선 정렬
    matches.sort(key=lambda c: (c["corp_name"].lower() != name_lower, c["corp_name"]))
    return matches[:limit]


_REPORT_CODE_MAP = {
    "1분기": "11013",
    "반기": "11012",
    "3분기": "11014",
    "사업보고서": "11011",
    "연간": "11011",
}


async def get_financial_statements(
    corp_code: str, year: int, report: str = "사업보고서", fs_div: str = "CFS"
) -> dict:
    """단일회사 전체 재무제표 조회 (fs_div: CFS=연결, OFS=별도)."""
    report_code = _REPORT_CODE_MAP.get(report, report if report in _REPORT_CODE_MAP.values() else "11011")
    data = await get_json(
        "dart",
        f"{_BASE}/fnlttSinglAcntAll.json",
        params={
            "crtfc_key": get_api_key("dart"),
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": report_code,
            "fs_div": fs_div,
        },
    )
    if data.get("status") != "000":
        return {"error": data.get("message", "조회 실패"), "status": data.get("status")}
    items = data.get("list", [])
    # 토큰 절약을 위해 핵심 필드만 추려서 반환
    slim = [
        {
            "account_nm": it.get("account_nm"),
            "fs_nm": it.get("fs_nm"),
            "sj_nm": it.get("sj_nm"),
            "thstrm_amount": it.get("thstrm_amount"),
            "frmtrm_amount": it.get("frmtrm_amount"),
            "bfefrmtrm_amount": it.get("bfefrmtrm_amount"),
            "currency": it.get("currency"),
        }
        for it in items
    ]
    return {"corp_code": corp_code, "year": year, "report": report, "fs_div": fs_div, "items": slim}


async def get_company_disclosures(corp_code: str, start_date: str, end_date: str, page_count: int = 20) -> dict:
    """기간 내 공시 목록 (예: 20240101~20241231)."""
    data = await get_json(
        "dart",
        f"{_BASE}/list.json",
        params={
            "crtfc_key": get_api_key("dart"),
            "corp_code": corp_code,
            "bgn_de": start_date,
            "end_de": end_date,
            "page_count": page_count,
        },
    )
    if data.get("status") != "000":
        return {"error": data.get("message", "조회 실패"), "status": data.get("status")}
    return {
        "total_count": data.get("total_count"),
        "list": [
            {
                "report_nm": it.get("report_nm"),
                "rcept_no": it.get("rcept_no"),
                "flr_nm": it.get("flr_nm"),
                "rcept_dt": it.get("rcept_dt"),
            }
            for it in data.get("list", [])
        ],
    }
