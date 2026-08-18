"""한국은행 ECOS(경제통계시스템) 클라이언트.

- StatisticWord: 키워드로 통계용어/코드 검색
- StatisticTableList: 통계표 목록/구조 검색
- StatisticSearch: 실제 수치 데이터 조회 (기간 범위를 한 번에 조회 -> 다건 호출 방지)

자주 쓰이는 지표(기준금리, 원/달러 환율, GDP, 소비자물가지수)는 stat_code를 미리 매핑해
'ecos_get_key_indicator' 하나로 바로 조회할 수 있게 해둔다.
"""
from __future__ import annotations

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.cache import (
    disk_file_is_fresh,
    read_disk_json,
    write_disk_json,
)
from korea_public_data_mcp.core.http_client import get_json

_BASE = "https://ecos.bok.or.kr/api"
_TABLE_LIST_CACHE_NAME = "ecos_statistic_tables.json"
_TABLE_LIST_MAX_AGE = 7 * 24 * 3600  # 통계표 목록은 자주 안 바뀌므로 1주일 캐시
_TABLE_LIST_MAX_ROWS = 2000  # 현재 834건. 여유를 두고 한 번에 받는다.

# stat_code, cycle(D/M/Q/A), item_code1 조합. ECOS 통계코드 체계 기준 대표값.
KEY_INDICATORS = {
    "기준금리": {"stat_code": "722Y001", "cycle": "M", "item_code1": "0101000"},
    "원달러환율": {"stat_code": "731Y001", "cycle": "D", "item_code1": "0000001"},
    "GDP성장률": {"stat_code": "200Y001", "cycle": "Q", "item_code1": "10111"},
    "소비자물가지수": {"stat_code": "901Y009", "cycle": "M", "item_code1": "0"},
}


async def search_statistic_word(keyword: str) -> list[dict]:
    data = await get_json(
        "ecos",
        f"{_BASE}/StatisticWord/{get_api_key('ecos')}/json/kr/1/50/{keyword}",
    )
    rows = data.get("StatisticWord", {}).get("row", [])
    return [{"word": r.get("WORD"), "content": r.get("CONTENT")} for r in rows]


async def _load_statistic_tables() -> list[dict]:
    """ECOS 통계표 전체 목록을 받아 로컬에 캐싱한다.

    StatisticTableList의 마지막 경로 인자는 '키워드'가 아니라 '통계표코드'다.
    거기에 검색어를 넣으면 INFO-200(해당 데이터 없음)만 돌아오므로,
    전체 목록을 한 번 받아두고 키워드 필터링은 아래 search_statistic_tables에서 직접 한다.
    """
    if disk_file_is_fresh(_TABLE_LIST_CACHE_NAME, _TABLE_LIST_MAX_AGE):
        cached = read_disk_json(_TABLE_LIST_CACHE_NAME)
        if cached:
            return cached
    data = await get_json(
        "ecos",
        f"{_BASE}/StatisticTableList/{get_api_key('ecos')}/json/kr/1/{_TABLE_LIST_MAX_ROWS}",
    )
    rows = data.get("StatisticTableList", {}).get("row", [])
    tables = [
        {
            "stat_code": r.get("STAT_CODE"),
            "stat_name": r.get("STAT_NAME"),
            "cycle": r.get("CYCLE"),
            "srch_yn": r.get("SRCH_YN"),  # 'Y'인 것만 실제 데이터 조회가 가능하다
        }
        for r in rows
    ]
    write_disk_json(_TABLE_LIST_CACHE_NAME, tables)
    return tables


async def search_statistic_tables(keyword: str) -> list[dict]:
    """통계표명 부분일치로 stat_code를 찾는다. 공백으로 구분한 여러 단어는 AND 조건."""
    tables = await _load_statistic_tables()
    terms = [t for t in keyword.strip().lower().split() if t]
    if not terms:
        return tables
    return [t for t in tables if all(term in (t["stat_name"] or "").lower() for term in terms)]


async def get_statistic_search(
    stat_code: str,
    cycle: str,
    start: str,
    end: str,
    item_code1: str = "",
    item_code2: str = "",
) -> dict:
    """수치 데이터 조회. cycle: D(일)/M(월)/Q(분기)/A(연). start/end는 cycle에 맞는 형식
    (예: 월간이면 202301, 연간이면 2023, 일간이면 20230101)."""
    path_parts = [
        _BASE,
        "StatisticSearch",
        get_api_key("ecos"),
        "json",
        "kr",
        "1",
        "1000",
        stat_code,
        cycle,
        start,
        end,
        item_code1,
    ]
    if item_code2:
        path_parts.append(item_code2)
    url = "/".join(p for p in path_parts if p != "")
    data = await get_json("ecos", url)
    result = data.get("StatisticSearch")
    if not result:
        # RESULT 코드에 에러 메시지가 담기는 경우
        err = data.get("RESULT", {})
        return {"error": err.get("MESSAGE", "조회 실패"), "code": err.get("CODE")}
    rows = result.get("row", [])
    return {
        "stat_code": stat_code,
        "count": len(rows),
        "data": [
            {"time": r.get("TIME"), "value": r.get("DATA_VALUE"), "unit": r.get("UNIT_NAME")}
            for r in rows
        ],
    }


async def get_key_indicator(name: str, start: str, end: str) -> dict:
    if name not in KEY_INDICATORS:
        return {"error": f"'{name}'은 사전 등록된 지표가 아닙니다. ecos_search_statistics로 stat_code를 먼저 찾아 ecos_get_statistic_data를 사용하세요. 등록된 지표: {list(KEY_INDICATORS)}"}
    spec = KEY_INDICATORS[name]
    return await get_statistic_search(spec["stat_code"], spec["cycle"], start, end, spec["item_code1"])
