"""통계청 KOSIS(국가통계포털) 클라이언트.

- 통합검색으로 원하는 통계표(orgId/tblId)를 찾고
- 통계자료 조회는 '표 단위'로 한 번에 여러 시점 데이터를 받아온다(newEstprmtPeriod 등 범위 파라미터 사용)
  -> 항목 하나씩 반복 조회하지 않는다.
"""
from __future__ import annotations

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.http_client import get_json

_BASE = "https://kosis.kr/openapi"


async def search_statistics(keyword: str, limit: int = 20) -> list[dict]:
    """통합검색: 키워드로 통계표(orgId/tblId) 목록을 찾는다."""
    data = await get_json(
        "kosis",
        f"{_BASE}/statisticsList.do",
        params={
            "method": "getList",
            "apiKey": get_api_key("kosis"),
            "vwCd": "MT_ZTITLE",
            "parentListId": "",
            "format": "json",
            "jsonVD": "Y",
            "searchNm": keyword,
        },
    )
    if isinstance(data, dict) and data.get("err"):
        return [{"error": data.get("errMsg", "검색 실패")}]
    if not isinstance(data, list):
        return []
    return [
        {
            "org_id": row.get("ORG_ID"),
            "tbl_id": row.get("TBL_ID"),
            "tbl_nm": row.get("TBL_NM"),
        }
        for row in data[:limit]
    ]


async def get_statistics_data(
    org_id: str,
    tbl_id: str,
    prd_se: str = "Y",
    start_prd: str = "",
    end_prd: str = "",
    item_ids: str = "",
    obj_l1: str = "",
) -> dict:
    """표 단위 통계자료 일괄 조회.
    prd_se: 'Y'(연) | 'Q'(분기) | 'M'(월).
    start_prd/end_prd: 기간(예: 연간이면 '2019'~'2023')로 범위 지정 -> 한 번에 여러 연도 수치를 받는다.
    """
    params = {
        "method": "getList",
        "apiKey": get_api_key("kosis"),
        "orgId": org_id,
        "tblId": tbl_id,
        "format": "json",
        "jsonVD": "Y",
        "prdSe": prd_se,
    }
    if start_prd:
        params["startPrdDe"] = start_prd
    if end_prd:
        params["endPrdDe"] = end_prd
    if item_ids:
        params["itmId"] = item_ids
    if obj_l1:
        params["objL1"] = obj_l1

    data = await get_json("kosis", f"{_BASE}/Param/statisticsParameterData.do", params=params)
    if isinstance(data, dict) and data.get("err"):
        return {"error": data.get("errMsg", "조회 실패")}
    if not isinstance(data, list):
        return {"error": "예상치 못한 응답 형식", "raw": data}
    return {
        "org_id": org_id,
        "tbl_id": tbl_id,
        "count": len(data),
        "data": [
            {
                "period": row.get("PRD_DE"),
                "item": row.get("ITM_NM"),
                "category": row.get("C1_NM"),
                "value": row.get("DT"),
                "unit": row.get("UNIT_NM"),
            }
            for row in data
        ],
    }
