"""교육부 나이스(NEIS) 교육정보 개방 포털 클라이언트.

인증키 없이도 호출은 되지만 응답이 5건으로 고정된다. 키를 넣어야 1,000건까지 받는다.
시도교육청 코드(ATPT_OFCDC_SC_CODE)를 알아야 조회 범위를 좁힐 수 있어, 자주 쓰는
코드는 아래에 표로 두고 사용자가 '서울'처럼 말해도 찾아지게 한다.
"""
from __future__ import annotations

import os

from korea_public_data_mcp.core.http_client import get_json

_BASE = "https://open.neis.go.kr/hub"

OFFICE_CODES = {
    "서울": "B10", "부산": "C10", "대구": "D10", "인천": "E10", "광주": "F10",
    "대전": "G10", "울산": "H10", "세종": "I10", "경기": "J10", "강원": "K10",
    "충북": "M10", "충남": "N10", "전북": "P10", "전남": "Q10", "경북": "R10",
    "경남": "S10", "제주": "T10",
}

SCHOOL_KINDS = ("초등학교", "중학교", "고등학교", "특수학교", "각종학교")


def resolve_office(region: str | None) -> str | None:
    """'서울', '서울특별시', '서울시교육청' 같은 표기를 코드로 바꾼다."""
    if not region:
        return None
    q = region.strip()
    if not q:
        return None
    if q.upper() in OFFICE_CODES.values():
        return q.upper()
    for name, code in OFFICE_CODES.items():
        if name in q or q in name:
            return code
    return None


async def search_schools(
    region: str = "", school_name: str = "", school_kind: str = "", limit: int = 100
) -> dict:
    """전국 초·중·고·특수학교 기본정보를 조회한다."""
    params: dict = {"Type": "json", "pIndex": 1, "pSize": max(1, min(limit, 1000))}

    key = os.environ.get("NEIS_API_KEY", "").strip()
    if key:
        params["KEY"] = key

    office = resolve_office(region)
    if office:
        params["ATPT_OFCDC_SC_CODE"] = office
    if school_name:
        params["SCHUL_NM"] = school_name
    if school_kind:
        params["SCHUL_KND_SC_NM"] = school_kind

    data = await get_json("neis", f"{_BASE}/schoolInfo", params=params)

    top = data.get("schoolInfo")
    if not top:
        info = data.get("RESULT", {})
        return {
            "total": 0, "count": 0, "schools": [],
            "note": info.get("MESSAGE", "조회 결과가 없습니다."),
        }

    head_block = (top[0].get("head") or [{}])[0]
    total = head_block.get("list_total_count", 0)
    rows = top[1].get("row", []) if len(top) > 1 else []

    schools = [
        {
            "학교명": r.get("SCHUL_NM"),
            "학교급": r.get("SCHUL_KND_SC_NM"),
            "교육청": r.get("ATPT_OFCDC_SC_NM"),
            "지역": r.get("LCTN_SC_NM"),
            "설립구분": r.get("FOND_SC_NM"),
            "주소": r.get("ORG_RDNMA"),
            "전화": r.get("ORG_TELNO"),
            "홈페이지": r.get("HMPG_ADRES"),
            "학교코드": r.get("SD_SCHUL_CODE"),
        }
        for r in rows
    ]
    result = {"total": total, "count": len(schools), "schools": schools}
    if not key:
        result["note"] = "인증키가 없어 결과가 5건으로 제한됩니다. NEIS_API_KEY를 설정하면 최대 1,000건까지 조회됩니다."
    return result
