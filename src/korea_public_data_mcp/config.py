"""환경변수 기반 설정 로더.

키가 아직 없어도 서버 자체는 문제없이 뜨도록, 키 검증은 '도구가 실제로 호출되는 시점'에만 수행한다.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# MCP 클라이언트(Claude Desktop 등)가 이 프로세스를 실행할 때 작업 디렉터리(cwd)가
# 프로젝트 폴더가 아닐 수 있어, load_dotenv()의 기본 탐색(cwd 기준)만 믿으면 .env를
# 못 찾는 경우가 생긴다. 그래서 이 파일 위치를 기준으로 프로젝트 루트의 .env를 명시적으로 지정한다.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _resolve_cache_dir() -> Path:
    """캐시 디렉터리를 정하고 생성한다.

    .env 와 마찬가지로 '작업 디렉터리(cwd)'를 믿으면 안 된다. MCP 클라이언트가 서버를
    띄울 때 cwd가 프로젝트 폴더가 아니라 앱 설치 경로나 시스템 폴더인 경우가 있고,
    거기에 .cache 를 만들려다 PermissionError 로 서버가 통째로 죽는다.
    (Claude Code는 cwd가 프로젝트라 안 터지고, Claude Desktop에서만 터졌다.)

    그래서 기본값을 프로젝트 루트 기준 절대경로로 잡고, 그마저 쓸 수 없는 환경
    (읽기 전용 설치 등)이면 임시 폴더로 물러난다. 캐시는 없어도 동작에 지장이 없으므로
    캐시 문제로 서버가 못 뜨는 일은 없어야 한다.
    """
    for candidate in (
        Path(os.environ["MCP_CACHE_DIR"]) if os.environ.get("MCP_CACHE_DIR") else None,
        _PROJECT_ROOT / ".cache",
        Path(tempfile.gettempdir()) / "korea-public-data-mcp-cache",
    ):
        if candidate is None:
            continue
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue
    return Path(tempfile.gettempdir())


CACHE_DIR = _resolve_cache_dir()

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
    # 한국수출입은행은 환율/대출금리/국제금리가 각각 별도 "API 상품" 페이지로 분리돼 있어
    # 서비스별로 별도 인증키가 발급된다 (공용 키 하나가 아님).
    "koreaexim_exchange": ApiKeySpec(
        env_var="KOREAEXIM_EXCHANGE_API_KEY",
        issue_url="https://www.koreaexim.go.kr/ir/HPHKIR020M01?apino=2 (현재환율 API, 즉시 발급)",
        display_name="한국수출입은행(환율)",
    ),
    "koreaexim_loan": ApiKeySpec(
        env_var="KOREAEXIM_LOAN_API_KEY",
        issue_url="https://www.koreaexim.go.kr/ir/HPHKIR020M01?apino=3 (대출금리 API, 즉시 발급)",
        display_name="한국수출입은행(대출금리)",
    ),
    "koreaexim_international": ApiKeySpec(
        env_var="KOREAEXIM_INTERNATIONAL_API_KEY",
        issue_url="https://www.koreaexim.go.kr/ir/HPHKIR020M01?apino=4 (국제금리 API, 즉시 발급)",
        display_name="한국수출입은행(국제금리)",
    ),
    # 아래 3곳은 data.go.kr 경유가 아니라 기관 사이트에서 직접 발급받는 별도 키다.
    # NTIS는 '소속기관 등록'과 '호출 서버 공인 IP'가 신청서 선행 조건이라 즉시 발급이 안 되고
    # 승인까지 수일 걸린다 (.env.example 의 발급 절차 주석 참고).
    "ntis": ApiKeySpec(
        env_var="NTIS_API_KEY",
        issue_url=(
            "https://www.ntis.go.kr/rndopen/api/mng/apiMain.do "
            "(로그인 → 소속기관 등록 → API별 활용신청 → 승인 대기)"
        ),
        display_name="NTIS 국가과학기술지식정보서비스",
    ),
    # 기업마당은 인증키 파라미터명이 serviceKey 가 아니라 crtfcKey 이므로 호출부에서 주의.
    "bizinfo": ApiKeySpec(
        env_var="BIZINFO_API_KEY",
        issue_url="https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi (신청 폼 작성 → 이메일로 인증키 수신)",
        display_name="기업마당 Bizinfo",
    ),
    # KIPRIS Plus는 인증 파라미터명이 ServiceKey (대문자 S) 다. accessKey/serviceKey로
    # 넣으면 INVALID_REQUEST_PARAMETER_ERROR 가 떨어진다 (실호출로 확인).
    "kipris": ApiKeySpec(
        env_var="KIPRIS_API_KEY",
        issue_url="https://plus.kipris.or.kr (회원가입 → Open API 인증키 신청)",
        display_name="KIPRIS Plus 특허정보",
    ),
    # 서울연구원은 신청 폼 제출 후 승인되면 이메일로 키와 연동가이드를 함께 보내준다.
    "seoul_institute": ApiKeySpec(
        env_var="SEOUL_INSTITUTE_API_KEY",
        issue_url="https://www.si.re.kr/openapi (신청 폼 제출 → 승인 후 이메일로 인증키·연동가이드 수신)",
        display_name="서울연구원",
    ),
    # AI Hub 키는 사업공고용이 아니라 aihubshell 데이터셋 다운로드/메타데이터 조회용이다.
    "aihub": ApiKeySpec(
        env_var="AIHUB_API_KEY",
        issue_url="https://www.aihub.or.kr/devsport/apishell/list.do (회원가입 → [API key 발급] → 이메일 수신)",
        display_name="AI Hub",
    ),
}


def get_api_key(name: str) -> str:
    """name(API_KEYS 의 키)에 해당하는 값을 반환. 없으면 발급 안내와 함께 에러."""
    spec = API_KEYS[name]
    value = os.environ.get(spec.env_var, "").strip()
    if not value:
        raise MissingApiKeyError(
            f"[{spec.display_name}] API 키가 설정되지 않았습니다. "
            f"{spec.issue_url} 에서 키를 발급받은 뒤 .env 의 {spec.env_var} 에 넣어주세요."
        )
    return value
