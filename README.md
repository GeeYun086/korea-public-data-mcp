# korea-public-data-mcp

대한민국 공공데이터(금융감독원 OpenDART, 한국은행 ECOS, 통계청 KOSIS, 공공데이터포털)를
Claude가 직접 호출해서, 재무·경제·통계 수치를 **추측이 아니라 실제 API 응답 기반으로** 답하게
만들어주는 MCP 서버입니다.

DART 전자공시 데이터를 붙여 재무제표 질문에 답하는 MCP들과 동일한 방식으로,
"이 회사 작년 매출 얼마야?", "최근 기준금리 추이 알려줘", "우리나라 실업률 몇 %야?" 같은
질문에 Claude가 이 서버의 도구를 호출해 최신 수치를 근거로 답하게 됩니다.

> 이름은 임시로 `korea-public-data-mcp`로 잡았습니다. GitHub에 올릴 때 원하는 이름으로
> 자유롭게 바꾸셔도 코드 동작에는 영향이 없습니다.

## 왜 이렇게 만들었나 (설계 원칙)

담당자분이 요청하신 세 가지 제약을 지키는 방향으로 설계했습니다.

1. **LLM/외부 비용 없음** — 이 서버는 데이터를 "가져오기만" 합니다. 내부에서 어떤 LLM도
   호출하지 않고, 유료 API도 쓰지 않습니다. 실제 추론/요약은 이 MCP를 호출하는 Claude가
   하기 때문에, 서버 운영 비용은 사실상 0원(전기세/서버 자원 제외)입니다.
2. **API 차단(IP 밴) 방지** — 정부 공공 API들은 초당/일 호출 제한을 넘기면 일시 차단되는
   경우가 있습니다. 그래서:
   - 모든 API 호출 앞단에 **초당 호출수 제한(토큰버킷)** 을 걸어 스스로 속도를 늦춥니다.
   - 같은 질문을 반복하면 **메모리 캐시**로 재사용하고, DART 회사 목록처럼 큰 정적 파일은
     **디스크 캐시**(기본 7일)로 재다운로드를 막습니다.
   - 계정과목/기간을 하나씩 개별 호출하지 않고, **표 단위·기간 범위 단위로 한 번에** 받아옵니다
     (예: 재무제표는 회사당 1회 호출로 전체 계정과목을 받고, 통계는 시작~종료 기간을 한 번에 조회).
   - 사업자등록 상태조회처럼 배치가 지원되는 API는 **최대 100건을 한 번의 호출로 묶어서** 보냅니다.
   - 429/5xx 응답에는 지수 백오프로 최대 3회까지만 재시도합니다.
3. **각자 Docker로 실행** — 별도 서버를 띄우지 않고, 팀원 각자 로컬에서
   `docker build` + `docker run`으로 띄워 자기 Claude에 연결하는 구조입니다.

## 지금 포함된 API (1차 핵심 범위)

전체 요청 목록(40여 개)을 한 번에 다 구현하면 유지보수가 어려워지는 범위라, 담당자분이
가장 자주 찾을 핵심 4개 기관부터 먼저 완성도 있게 구현했습니다. 나머지는 [확장 가이드](#확장-가이드-새-api-추가하기)를 따라 같은 패턴으로 계속 추가하면 됩니다.

| 기관 | 제공 도구 | 비고 |
| --- | --- | --- |
| 금융감독원 OpenDART | `dart_search_company`, `dart_get_financial_statements`, `dart_get_company_disclosures` | 회사명 검색 → corp_code → 재무제표/공시 순서로 사용 |
| 한국은행 ECOS | `ecos_get_key_indicator`, `ecos_search_statistics`, `ecos_get_statistic_data` | 기준금리/환율/GDP/물가는 이름으로 바로 조회 가능 |
| 통계청 KOSIS | `kosis_search_statistics`, `kosis_get_statistics_data` | 키워드 검색 후 표 단위로 기간 범위 일괄 조회 |
| 공공데이터포털 (data.go.kr) | `data_go_kr_check_business_status`, `data_go_kr_generic_get` | 사업자등록 상태는 배치(최대 100건) 지원, 그 외 서비스는 범용 GET 도구로 임시 대응 |

## API 키 발급 안내

아직 발급받은 키가 없어도 서버는 정상적으로 뜨고 도구 목록도 보입니다. 다만 실제로 도구를
호출하면 아래 키가 없다는 안내 메시지가 반환되니, 필요한 것부터 순서대로 신청하시면 됩니다.

| 기관 | 발급처 | 참고 |
| --- | --- | --- |
| OpenDART | https://opendart.fss.or.kr → 회원가입 → [인증키 신청/관리] | 가입 즉시 발급, 가장 빠름 |
| ECOS | https://ecos.bok.or.kr/api/#/ | Open API 인증키 신청, 즉시~1일 이내 |
| KOSIS | https://kosis.kr/openapi/index/index.jsp | "OpenAPI 활용신청", 승인까지 시간이 걸릴 수 있음 |
| 공공데이터포털 | https://www.data.go.kr → 원하는 서비스 상세페이지 → [활용신청] | 서비스별로 별도 신청 필요. 우선 "국세청_사업자등록정보 진위확인 및 상태조회"부터 신청 추천 |

키를 받으면 `.env.example`을 `.env`로 복사해서 채워 넣으세요.

```bash
cp .env.example .env
# .env 파일을 열어 발급받은 키 입력
```

## 빠른 시작 (Docker)

```bash
git clone <이 레포 주소>
cd korea-public-data-mcp
cp .env.example .env   # 키 채워넣기 (없어도 일단 진행 가능)
docker build -t korea-public-data-mcp .
```

Claude Desktop / Claude Code의 MCP 설정(`claude_desktop_config.json` 등)에 아래처럼 등록합니다.

```json
{
  "mcpServers": {
    "korea-public-data": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "/절대경로/korea-public-data-mcp/.env",
        "korea-public-data-mcp"
      ]
    }
  }
}
```

Claude를 재시작하면 도구 목록에 `dart_*`, `ecos_*`, `kosis_*`, `data_go_kr_*` 도구들이
나타납니다. 이제 "삼성전자 2023년 매출액 알려줘" 같은 질문을 하면 Claude가 이 도구들을
호출해서 실제 수치로 답합니다.

### 로컬(Docker 없이) 개발/테스트

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install pytest
pytest -q                      # 키 없이도 통과하는 스모크 테스트
python -m korea_public_data_mcp.server   # stdio로 직접 실행해보기 (Ctrl+C로 종료)
```

## 확장 가이드 (새 API 추가하기)

담당자분이 주신 전체 목록(RISS, KIPRIS, 국가법령정보, 나라장터, 서울 열린데이터광장 등)은
아래 패턴을 그대로 반복하면 됩니다. 예시로 새 기관 `foo`를 추가한다면:

1. `src/korea_public_data_mcp/config.py`의 `API_KEYS`에 `foo` 항목 추가 (env var, 발급 URL)
2. `src/korea_public_data_mcp/clients/foo.py` 작성 — `core/http_client.get_json`을 사용해
   실제 엔드포인트 호출 로직만 작성 (재시도/속도제한은 공용 클라이언트가 자동 처리)
3. `src/korea_public_data_mcp/tools/foo_tools.py` 작성 — `@mcp.tool()` 데코레이터로
   client 함수를 감싸고, `MissingApiKeyError`를 잡아 안내 메시지로 반환, `cached_call`로 캐싱
4. `src/korea_public_data_mcp/server.py`에서 `foo_tools.register(mcp)` 한 줄 추가
5. `.env.example`, README 표에 항목 추가

이 구조 덕분에 새 API를 추가해도 차단 방지(속도 제한/캐시/배치) 로직을 매번 새로 짤 필요가
없습니다.

## 다음 확장 후보 (담당자 요청 목록 기준)

- 법률/행정: 국가법령정보 Open API, 열린국회정보 API
- 조달/사업: 나라장터(g2b), 조달데이터허브, NTIS 국가과학기술정보
- 학술: RISS, KISTI, 국립중앙도서관 OpenAPI
- 지식재산권: KIPRIS Plus (특허·상표)
- 지역: 서울 열린데이터광장, 경기데이터드림

우선순위나 다음에 붙일 API를 알려주시면 그 항목부터 이어서 구현해 드릴게요.

## 라이선스

내부용으로 자유롭게 사용/수정하세요.
