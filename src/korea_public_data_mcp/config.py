"""환경변수 기반 설정 로더.

키가 아직 없어도 서버 자체는 문제없이 뜨도록, 키 검증은 '도구가 실제로 호출되는 시점'에만 수행한다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = Path(os.environ.get("MCP_CACHE_DIR", ".cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
RATE_LIMIT_PER_SECOND = float(os.environ.get("RATE_LIMIT_PER_SECOND", "3"))


class MissingApiKeyError(RuntimeError):
    """필요한 API 키가 .env 에 설정되지 않았을 때 발생시키는 예외.

    MCP 도구 함수 안에서 잡아서, Claude/사용자에게 친절한 안내 메시지로 변환해 돌려준다.
    """


@dataclass(frozen=True)
class ApiKeySpec:
    env_var: str
    issue_url: str
    display_name: str


API_KEYS = {
    "dart": ApiKeySpec(
        env_var="DART_API_KEY",
        issue_url="https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do (회원가입 후 [인증키 신청/관리])",
        display_name="금융감독원 OpenDART",
    ),
    "ecos": ApiKeySpec(
        env_var="ECOS_API_KEY",
        issue_url="https://ecos.bok.or.kr/api/#/ (Open API 인증키 신청)",
        display_name="한국은행 ECOS",
    ),
    "kosis": ApiKeySpec(
        env_var="KOSIS_API_KEY",
        issue_url="https://kosis.kr/openapi/index/index.jsp (OpenAPI 활용신청)",
        display_name="통계청 KOSIS",
    ),
    "data_go_kr": ApiKeySpec(
        env_var="DATA_GO_KR_API_KEY",
        issue_url="https://www.data.go.kr (원하는 서비스 상세페이지에서 [활용신청])",
        display_name="공공데이터포털",
    ),
}


def get_api_key(name: str) -> str:
    """name(dart/ecos/kosis/data_go_kr)에 해당하는 키를 반환. 없으면 발급 안내와 함께 에러."""
    spec = API_KEYS[name]
    value = os.environ.get(spec.env_var, "").strip()
    if not value:
        raise MissingApiKeyError(
            f"[{spec.display_name}] API 키가 설정되지 않았습니다. "
            f"{spec.issue_url} 에서 키를 발급받은 뒤 .env 의 {spec.env_var} 에 넣어주세요."
        )
    return value
