"""공공데이터포털(data.go.kr) 클라이언트.

공공데이터포털은 사실상 '허브'라서 서비스마다 엔드포인트가 전부 다르다.
그래서 개별 서비스를 하나씩 구현하는 대신, 새로운 서비스를 바로 붙일 수 있는
범용 GET 프록시(generic_get)를 제공한다.

인증키는 계정당 1개이고 서비스별 '활용신청'으로 권한만 붙는 구조라, 포털에서 활용신청만
해두면 코드 수정 없이 이 함수로 곧바로 호출할 수 있다.
자주 쓰게 되는 서비스는 README의 '확장 가이드'에 따라 전용 client/tool로 승격한다.
"""
from __future__ import annotations

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.http_client import get_json


async def generic_get(base_url: str, path: str, params: dict) -> dict:
    """data.go.kr 서비스를 호출하는 범용 GET 헬퍼.
    호출부에서 serviceKey는 자동으로 채워준다."""
    full_params = {"serviceKey": get_api_key("data_go_kr"), **params}
    return await get_json("data_go_kr", f"{base_url.rstrip('/')}/{path.lstrip('/')}", params=full_params)
