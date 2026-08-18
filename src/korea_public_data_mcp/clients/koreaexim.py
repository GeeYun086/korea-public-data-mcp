"""한국수출입은행(koreaexim) Open API 클라이언트.

3종 서비스를 제공한다. 사이트에서 환율/대출금리/국제금리가 각각 별도 "API 상품"
페이지(apino=2/3/4)로 분리돼 있어 **서비스별로 별도 인증키**가 발급된다(공용 키 아님):
- 현재환율 (exchangeJSON, data=AP01) -> KOREAEXIM_EXCHANGE_API_KEY
- 대출금리 (interestJSON, data=AP02) -> KOREAEXIM_LOAN_API_KEY
- 국제금리 (internationalJSON, data=AP03) -> KOREAEXIM_INTERNATIONAL_API_KEY

날짜 지정 없이 호출하면 당일 영업일 데이터를 반환한다. 영업일 11시 이전이거나
비영업일(주말/공휴일)에 조회하면 데이터가 비어 있을 수 있다 (은행 측 사양).

2025-06-25부로 요청 도메인이 www.koreaexim.go.kr -> oapi.koreaexim.go.kr 로 변경되었고,
기존 도메인은 2026-04-30 이후 종료 예정이라 신규 도메인만 사용한다.
"""
from __future__ import annotations

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.http_client import get_json

_BASE = "https://oapi.koreaexim.go.kr/site/program/financial"

_RESULT_MESSAGES = {
    "1": "성공",
    "2": "DATA코드 오류",
    "3": "인증키 오류",
    "4": "일일 제한횟수(1,000회) 초과",
}


def _normalize_date(search_date: str) -> str:
    return search_date.replace("-", "") if search_date else ""


async def _call(endpoint: str, data_type: str, search_date: str, key_name: str) -> list[dict]:
    params = {"authkey": get_api_key(key_name), "data": data_type}
    normalized = _normalize_date(search_date)
    if normalized:
        params["searchdate"] = normalized
    result = await get_json("koreaexim", f"{_BASE}/{endpoint}", params=params)
    if isinstance(result, dict):
        result = [result]
    return result if isinstance(result, list) else []


def _check_error(rows: list[dict]) -> str | None:
    if not rows:
        return None
    code = str(rows[0].get("result", rows[0].get("RESULT", "1")))
    if code != "1":
        return _RESULT_MESSAGES.get(code, f"알 수 없는 오류 코드({code})")
    return None


async def get_exchange_rates(search_date: str = "") -> dict:
    """현재환율(매매기준율/전신환매매율) 조회. search_date 형식: YYYYMMDD 또는 YYYY-MM-DD, 생략 시 당일."""
    rows = await _call("exchangeJSON", "AP01", search_date, "koreaexim_exchange")
    error = _check_error(rows)
    if error:
        return {"error": error}
    if not rows:
        return {
            "error": "조회된 환율 데이터가 없습니다. 비영업일이거나 영업일 11시 이전일 수 있습니다.",
        }
    return {
        "search_date": search_date or "당일(영업일 기준)",
        "rates": [
            {
                "currency_unit": r.get("cur_unit"),
                "currency_name": r.get("cur_nm"),
                "ttb": r.get("ttb"),  # 전신환매입율
                "tts": r.get("tts"),  # 전신환매도율
                "deal_base_rate": r.get("deal_bas_r"),  # 매매기준율
                "book_price": r.get("bkpr"),
            }
            for r in rows
            if str(r.get("result", r.get("RESULT", "1"))) == "1"
        ],
    }


async def get_loan_rates(search_date: str = "") -> dict:
    """대출금리(수은채 유통수익률 기준) 조회. search_date 형식: YYYYMMDD 또는 YYYY-MM-DD, 생략 시 당일.

    주의: 공식 API 문서에는 응답 필드가 대문자(SFLN_INTRC_NM, INT_R)로 안내돼 있지만,
    실제 응답은 전부 소문자(sfln_intrc_nm, int_r)로 내려온다 (실제 키로 검증 완료).
    """
    rows = await _call("interestJSON", "AP02", search_date, "koreaexim_loan")
    error = _check_error(rows)
    if error:
        return {"error": error}
    if not rows:
        return {"error": "조회된 대출금리 데이터가 없습니다. 비영업일이거나 영업일 11시 이전일 수 있습니다."}
    return {
        "search_date": search_date or "당일(영업일 기준)",
        "rates": [
            {
                "loan_period": r.get("sfln_intrc_nm"),  # 대출기간
                "rate": r.get("int_r"),  # 고정기준금리
            }
            for r in rows
            if str(r.get("result", "1")) == "1"
        ],
    }


_INTL_RATE_TYPE_LABELS = {
    "sofr_list": "SOFR",
    "estr_list": "ESTR",
    "euribor_list": "EURIBOR",
    "tona_list": "TONA",
    "tibor_list": "TIBOR",
    "swapRfr_list": "SWAP(RFR)",
    "libor_list": "LIBOR",
    "swap_list": "SWAP",
    "cirr_list": "CIRR",
    "new_cirr_list": "신CIRR",
}


async def get_international_rates(search_date: str = "") -> dict:
    """국제금리(SOFR/ESTR/EURIBOR/TONA/TIBOR/SWAP/CIRR 등) 조회.
    search_date 형식: YYYYMMDD 또는 YYYY-MM-DD, 생략 시 당일.

    주의: 공식 문서상 응답 스키마(RESULT/CUR_FUND/SFLN_INTRC_NM/INT_R 평면 리스트)와 달리,
    실제 응답은 최상위 객체 하나에 금리 종류별 리스트(sofr_list/estr_list/...)가 중첩된
    형태로 내려온다 (LIBOR 폐지 이후 SOFR/ESTR/TONA 등 무위험지표금리 체계로 개편된 결과로
    보임 — 실제 키로 검증 완료). 이 함수가 그 중첩 구조를 평평하게 펼쳐서 반환한다.
    """
    rows = await _call("internationalJSON", "AP03", search_date, "koreaexim_international")
    error = _check_error(rows)
    if error:
        return {"error": error}
    if not rows:
        return {"error": "조회된 국제금리 데이터가 없습니다. 비영업일이거나 영업일 11시 이전일 수 있습니다."}
    top = rows[0]
    rates = []
    for key, label in _INTL_RATE_TYPE_LABELS.items():
        for entry in top.get(key) or []:
            rates.append(
                {
                    "rate_type": label,
                    "currency_fund": entry.get("cur_fund"),
                    "period": entry.get("sfln_intrc_nm"),
                    "rate": entry.get("int_r"),
                }
            )
    return {"search_date": search_date or "당일(영업일 기준)", "rates": rates}
