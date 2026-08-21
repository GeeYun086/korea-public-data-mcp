"""국민연금공단 사업장 가입자 내역 클라이언트.

data.go.kr REST 서비스 (Swagger로 확인, 2026-08).
  Base: https://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2
    1. getBassInfoSearchV2        — wkplNm(사업장명, 필수)으로 사업장 목록 조회. seq(식별번호)를 얻는 용도.
    2. getDetailInfoSearchV2      — seq(필수)로 상세조회. jnngpCnt(가입자수), crrmmNtcAmt(당월고지금액) 등.
    3. getPdAcctoSttusInfoSearchV2 — seq(필수) + dataCrtYm(옵션)으로 신규취득자수/상실가입자수(입퇴사 흐름).

가입자수는 국민연금 가입자 기준이라 실제 임직원수와 정확히 일치하지 않을 수 있다
(무보수 임원 제외, 사업장 분리 등의 이유로 차이가 날 수 있음).
"""
from __future__ import annotations

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.http_client import get_json

_BASE = "https://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2"


async def _call(operation: str, params: dict) -> dict:
    data = await get_json(
        "nps",
        f"{_BASE}/{operation}",
        params={"serviceKey": get_api_key("data_go_kr"), "dataType": "json", **params},
    )
    # 응답이 {"response": {"header":..., "body":...}} 한 겹 더 감싸져 있다 (실호출로 확인).
    envelope = data.get("response") or data
    header = envelope.get("header") or {}
    code = header.get("resultCode")
    if code not in ("00", "0", None):
        return {"error": header.get("resultMsg") or f"조회 실패 (코드 {code})"}
    body = envelope.get("body") or {}
    items = (body.get("items") or {}).get("item") or []
    if isinstance(items, dict):
        items = [items]
    return {"total": body.get("totalCount", 0), "items": items}


async def search_workplace(name: str, limit: int = 10) -> list[dict]:
    """사업장명으로 검색해 seq(식별번호)를 얻는다. 상세조회는 이 seq가 있어야 가능하다.

    부분일치라 대기업명을 넣으면 "OO건설/일용/[삼성전자] ..." 처럼 그 회사 현장에서
    일하는 협력업체명까지 잔뜩 잡힌다. 그래서 API가 주는 순서를 그대로 믿지 않고,
    더 넉넉히 받아온 뒤 회사명과 정확히 일치하거나 이름이 짧은(=협력업체 수식어가
    안 붙은) 사업장을 앞으로 정렬해서 실제 그 회사 본사/사업장을 찾기 쉽게 한다.
    """
    fetch_n = max(limit, min(100, limit * 5))
    result = await _call(
        "getBassInfoSearchV2",
        {"wkplNm": name, "numOfRows": fetch_n, "pageNo": 1},
    )
    if "error" in result:
        return []

    q = name.strip()
    items = result.get("items", [])
    items.sort(key=lambda it: (
        (it.get("wkplNm") or "").strip() != q,
        len(it.get("wkplNm") or ""),
    ))
    return [
        {
            "사업장명": it.get("wkplNm"),
            "사업장코드": it.get("seq"),
            "사업장구분": it.get("wkplStylDvcd"),
            "사업장상태": it.get("wkplJnngStcd"),
            "주소": it.get("wkplRoadNmDtlAddr"),
            "사업자등록번호": it.get("bzowrRgstNo"),
            "자료기준월": it.get("dataCrtYm"),
        }
        for it in items[:limit]
    ]


async def get_employee_count(seq: str) -> dict:
    """사업장코드(seq)로 가입자수(재직자수 근사치)·당월고지금액 등 상세를 조회한다."""
    result = await _call("getDetailInfoSearchV2", {"seq": seq})
    if "error" in result:
        return result
    items = result.get("items", [])
    if not items:
        return {"error": f"사업장코드 '{seq}' 의 상세정보가 없습니다."}
    it = items[0]
    return {
        "사업장코드": seq,
        "가입자수": it.get("jnngpCnt"),
        "당월고지금액": it.get("crrmmNtcAmt"),
        "자료기준월": it.get("dataCrtYm"),
    }


async def get_employee_trend(seq: str, year_month: str = "") -> dict:
    """사업장코드(seq)로 신규취득자수·상실가입자수(해당월 입퇴사 흐름)를 조회한다.
    year_month 를 비우면 최신 기준월로 조회한다."""
    params = {"seq": seq}
    if year_month:
        params["dataCrtYm"] = year_month
    result = await _call("getPdAcctoSttusInfoSearchV2", params)
    if "error" in result:
        return result
    items = result.get("items", [])
    if not items:
        return {"error": f"사업장코드 '{seq}' 의 해당 기간 자료가 없습니다."}
    it = items[0]
    return {
        "사업장코드": seq,
        "신규취득자수": it.get("nwAcqzrCnt"),
        "상실가입자수": it.get("lssJnngpCnt"),
        "자료기준월": it.get("dataCrtYm") or year_month,
    }
