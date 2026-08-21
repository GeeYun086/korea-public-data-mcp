"""고용24(work24.go.kr) 국민내일배움카드 훈련과정 클라이언트 — KDT 포함.

work24.go.kr Open API 소개 페이지의 실제 아코디언 명세로 확인한 스펙 (2026-08):
  목록조회: https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L01.do
  인증: authKey (쿼리파라미터). "OPEN-API는 고용24 기업회원 전용 서비스"라고 명시되어
        있어 신청 시 사업자등록번호가 필요하다.
  필수 파라미터: returnType(XML/JSON), outType='1'(리스트), pageNum, pageSize,
                srchTraStDt/srchTraEndDt(훈련시작일 조회기간), sort, sortCol
  훈련유형(crseTracseSe): 'C0104'=K-디지털 트레이닝, 'C0105'=K-디지털 기초역량훈련

주의: JSON 응답의 최상위 배열 키 이름은 실제 호출로 확인하지 못했다(XML 태그명
"scn_list"만 확인됨). 흔한 변환 패턴 두 가지를 모두 시도하도록 방어적으로 짜뒀으니,
실제 키로 첫 호출을 해보고 다르면 _ROW_KEYS 후보를 조정할 것.
"""
from __future__ import annotations

from datetime import date, timedelta

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.rate_limiter import throttle

_URL = "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L01.do"

COURSE_TYPES = {
    "kdt": "C0104",  # K-디지털 트레이닝
    "kdt_basic": "C0105",  # K-디지털 기초역량훈련
}

_ROW_KEYS = ("srchList", "scn_list", "list")


async def search_courses(
    course_type: str = "kdt",
    keyword: str = "",
    days_ahead: int = 180,
    limit: int = 20,
    page: int = 1,
) -> dict:
    """국민내일배움카드 훈련과정을 검색한다 (기본값은 K-디지털 트레이닝).

    course_type: 'kdt'(K-디지털 트레이닝, 기본값) | 'kdt_basic'(K-디지털 기초역량훈련).
    keyword: 훈련과정명 부분검색. 비우면 필터 없이 조회한다.
    days_ahead: 오늘부터 며칠 뒤까지 시작하는 과정을 볼지 (기본 180일).
    """
    crse = COURSE_TYPES.get(course_type, course_type)
    start = date.today()
    end = start + timedelta(days=max(days_ahead, 1))

    params = {
        "authKey": get_api_key("work24"),
        "returnType": "JSON",
        "outType": "1",
        "pageNum": max(page, 1),
        "pageSize": max(1, min(limit, 100)),
        "srchTraStDt": start.strftime("%Y%m%d"),
        "srchTraEndDt": end.strftime("%Y%m%d"),
        "sort": "ASC",
        "sortCol": "2",
        "crseTracseSe": crse,
    }
    if keyword:
        params["srchTraProcessNm"] = keyword

    await throttle("work24")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_URL, params=params)
    if resp.status_code >= 400:
        return {"error": f"고용24 HTTP {resp.status_code}: {resp.text[:200]}"}

    try:
        data = resp.json()
    except ValueError:
        return {"error": f"응답 파싱 실패(JSON 아님): {resp.text[:300]}"}

    rows = []
    for key in _ROW_KEYS:
        if key in data:
            rows = data[key]
            break
    if isinstance(rows, dict):
        rows = [rows]

    courses = [
        {
            "과정명": r.get("title"),
            "훈련기관": r.get("subTitle") or r.get("trainstCstId"),
            "주소": r.get("address"),
            "전화": r.get("telNo"),
            "훈련기간_시작": r.get("traStartDate"),
            "훈련기간_종료": r.get("traEndDate"),
            "수강비": r.get("courseMan"),
            "정원": r.get("yardMan"),
            "취업률_3개월": r.get("eiEmplRate3"),
            "취업률_6개월": r.get("eiEmplRate6"),
            "만족도": r.get("stdgScor"),
            "과정ID": r.get("trprId"),
        }
        for r in rows
    ]
    return {"course_type": course_type, "count": len(courses), "courses": courses}
