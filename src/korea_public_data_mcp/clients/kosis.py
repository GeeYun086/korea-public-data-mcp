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
    """통합검색: 키워드로 통계표(orgId/tblId) 목록을 찾는다.

    주의: statisticsList.do(getList)는 vwCd/parentListId로 주제별 목록을 '순회'하는
    API라 searchNm을 줘도 무시된다. 실제 키워드 검색은 별도 엔드포인트인
    statisticsSearch.do 를 써야 한다 (실제 키로 검증 완료).
    """
    data = await get_json(
        "kosis",
        f"{_BASE}/statisticsSearch.do",
        params={
            "method": "getList",
            "apiKey": get_api_key("kosis"),
            "format": "json",
            "jsonVD": "Y",
            "searchNm": keyword,
            "sort": "RANK",
            "startCount": 1,
            "resultCount": limit,
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


_MAX_OBJ_LEVEL = 4  # KOSIS 통계표는 분류(objL) 단계가 표마다 0~4개로 제각각이다


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

    KOSIS는 표마다 분류코드(objL1, objL2, ...)를 정확히 표의 분류 단계 수만큼만 넘겨야
    하고(적으면 "필수요청변수값 누락", 많으면 "잘못된 요청 변수" 오류), 몇 단계인지는
    표마다 달라 미리 알 수 없다. 그래서 0단계부터 시작해 "objL 누락" 오류가 나오는 동안만
    한 단계씩 늘려가며 재시도한다(최대 4단계, 실제 API로 검증된 동작). 표 하나당 보통
    1~2회 안에 성사되고, 성공/최종 실패 시 더 이상 호출하지 않는다.
    """
    base_params = {
        "method": "getList",
        "apiKey": get_api_key("kosis"),
        "orgId": org_id,
        "tblId": tbl_id,
        "format": "json",
        "jsonVD": "Y",
        "prdSe": prd_se,
        "itmId": item_ids or "ALL",
    }
    if start_prd:
        base_params["startPrdDe"] = start_prd
    if end_prd:
        base_params["endPrdDe"] = end_prd

    data: object = None
    last_error: dict = {"error": "알 수 없는 오류"}
    for level in range(0, _MAX_OBJ_LEVEL + 1):
        params = dict(base_params)
        for i in range(1, level + 1):
            params[f"objL{i}"] = obj_l1 if (i == 1 and obj_l1) else "ALL"
        data = await get_json("kosis", f"{_BASE}/Param/statisticsParameterData.do", params=params)
        if isinstance(data, list):
            break
        if isinstance(data, dict) and data.get("err"):
            code = str(data.get("err"))
            msg = data.get("errMsg", "조회 실패")
            if code == "20" and "objL" in msg:
                last_error = {"error": msg}
                continue  # 분류 단계가 더 필요함 -> 다음 단계로 재시도
            return {"error": msg}  # 그 외 오류는 재시도해도 소용없음
        return {"error": "예상치 못한 응답 형식", "raw": data}
    else:
        return last_error

    def _slim(row: dict) -> dict:
        slim = {
            "period": row.get("PRD_DE"),
            "item": row.get("ITM_NM"),
            "category": row.get("C1_NM"),
            "value": row.get("DT"),
            "unit": row.get("UNIT_NM"),
        }
        if row.get("C2_NM") is not None:  # 분류가 2단계 이상인 표만 추가로 노출
            slim["category2"] = row.get("C2_NM")
        return slim

    return {
        "org_id": org_id,
        "tbl_id": tbl_id,
        "count": len(data),
        "data": [_slim(row) for row in data],
    }
