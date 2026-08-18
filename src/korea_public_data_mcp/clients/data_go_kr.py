"""공공데이터포털(data.go.kr) 클라이언트.

공공데이터포털은 사실상 '허브'라서 서비스마다 엔드포인트가 전부 다르다.
그래서 여기서는 두 가지를 제공한다.

1) 가장 많이 쓰이는 구체 서비스 하나를 완성도 있게 구현: 국세청 사업자등록정보 진위확인/상태조회
   - 최대 100건을 한 번의 POST로 배치 조회 (건별 호출 반복 금지 -> 차단 위험/호출량 대폭 절감)
2) 새로운 서비스를 추가하기 쉽도록 만든 범용 GET 프록시(generic_get)
   - README의 '확장 가이드'에 따라 새 서비스 추가 시 이 함수를 그대로 재사용 가능
"""
from __future__ import annotations

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.http_client import get_json
from korea_public_data_mcp.core.rate_limiter import throttle

_BIZ_STATUS_URL = (
    "https://api.odcloud.kr/api/nts-businessman/v1/status"
)


async def check_business_status(business_numbers: list[str]) -> dict:
    """사업자등록번호(하이픈 없이 10자리) 최대 100개를 한 번에 배치 조회한다."""
    if len(business_numbers) > 100:
        return {"error": "한 번에 최대 100건까지 조회할 수 있습니다. 목록을 나눠서 호출하세요."}

    await throttle("data_go_kr")
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            _BIZ_STATUS_URL,
            params={"serviceKey": get_api_key("data_go_kr")},
            json={"b_no": business_numbers},
            headers={"Content-Type": "application/json"},
        )
    if resp.status_code >= 400:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    data = resp.json()
    rows = data.get("data", [])
    return {
        "count": len(rows),
        "results": [
            {
                "b_no": r.get("b_no"),
                "status": r.get("b_stt"),  # 계속사업자/휴업자/폐업자
                "tax_type": r.get("tax_type"),
                "end_date": r.get("end_dt"),
            }
            for r in rows
        ],
    }


async def generic_get(base_url: str, path: str, params: dict) -> dict:
    """새로운 data.go.kr 서비스를 추가할 때 쓰는 범용 GET 헬퍼.
    호출부에서 serviceKey는 자동으로 채워준다."""
    full_params = {"serviceKey": get_api_key("data_go_kr"), **params}
    return await get_json("data_go_kr", f"{base_url.rstrip('/')}/{path.lstrip('/')}", params=full_params)
