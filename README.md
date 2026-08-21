# korea-public-data-mcp

대한민국 공공데이터를 Claude가 **직접 조회해서 답하게** 해주는 MCP 서버입니다.

기업 재무제표, 환율·금리 같은 경제 지표, 정부 지원사업 공고, 공공 입찰공고,
특허·학교정보·국가 R&D 과제까지 물어보면 기관 API를 실제로 호출해 받아온 값으로 답합니다.
도구 이름을 외울 필요 없이 한국어로 물어보면 됩니다.

```
중소기업 수출 지원사업 뭐 있어?
조달청 사전규격에 시스템 관련 뭐 올라왔어?
삼성전자 2024년 재무제표 알려줘
작년부터 지금까지 기준금리 어떻게 변했어?
이차전지 관련 국가 R&D 과제 뭐 있어?
인공지능 관련 특허 좀 찾아줘
서울 강남구에 있는 고등학교 알려줘
```

---

## 분야별 진행 현황

| 분야 | 상태 | 소스 |
| --- | --- | --- |
| **금융** | ✅ 완료 | 4곳 |
| **정부사업 · 조달** | ✅ 완료 | 10곳 |
| **지식재산권 / 특허** | ✅ 완료 | KIPRIS Plus |
| **교육** | ✅ 완료 | NEIS |
| 학술 / 연구 | 🔶 일부 | NTIS(완료) · 서울연구원(완료) · KCI/KISTI(승인 대기) |
| 법률 / 행정 / 안전 | ⛔ 제외 | — |
| 공공통합포털 | ⛔ 제외 | — |

### 금융

| 기관 | 제공 데이터 | 출처 |
| --- | --- | --- |
| 금융감독원 OpenDART | 상장·외감법인 재무제표, 공시, 기업코드 | [opendart.fss.or.kr](https://opendart.fss.or.kr) |
| 한국은행 ECOS | 기준금리, 환율, GDP, 물가 등 거시경제 통계 | [ecos.bok.or.kr](https://ecos.bok.or.kr) |
| 통계청 KOSIS | 국가통계 13만종 | [kosis.kr](https://kosis.kr/openapi) |
| 한국수출입은행 | 현재환율, 대출금리, 국제금리 | [koreaexim.go.kr](https://www.koreaexim.go.kr/ir/HPHKIR019M01) |

### 정부사업 — 지원사업 4가지

| 소스 | 제공 데이터 | 출처 |
| --- | --- | --- |
| 기업마당 (중소벤처기업부) | 중소기업·소상공인 지원사업 공고. 금융·기술·인력·수출·내수·창업·경영 8개 분야. 중앙부처와 지자체 공고 포함 | [bizinfo.go.kr](https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi) |
| K-Startup (창업진흥원) | 창업 지원사업 공고. 예비창업자~창업 7년 이내 | [data.go.kr 15125364](https://www.data.go.kr/data/15125364/openapi.do) |
| 보조금24 (행정안전부) | 정부·지자체 공공서비스(혜택) 목록 | [data.go.kr 15113968](https://www.data.go.kr/data/15113968/openapi.do) |
| 과기정통부 사업공고 | R&D·국제협력·인프라 사업 공모 공고 | [data.go.kr 15074634](https://www.data.go.kr/data/15074634/openapi.do) |

### 정부사업 — 조달 6가지 (조달청 나라장터)

조달은 한 사업이 아래 6단계의 순서로 흘러갑니다. 앞 단계일수록 먼저 알 수 있습니다.

```
발주계획  →  조달요청  →  사전규격  →  입찰공고  →  낙찰  →  계약
수개월 전     구매요청    2주~1달 전     지금       결과     완료
```

| 단계 | 제공 데이터 | 출처 |
| --- | --- | --- |
| 발주계획 | 공공기관이 미리 공개하는 발주 예정 목록. 사업명·발주기관·발주월·발주금액 | [data.go.kr 15129462](https://www.data.go.kr/data/15129462/openapi.do) |
| 조달요청 | 수요기관이 조달청에 구매를 요청한 건. 요청명·수요기관·예산액 | [data.go.kr 15129468](https://www.data.go.kr/data/15129468/openapi.do) |
| 사전규격 | 입찰 전 의견수렴 단계의 규격안. 사업명·수요기관·배정예산·의견마감 | [data.go.kr 15129437](https://www.data.go.kr/data/15129437/openapi.do) |
| 입찰공고 | 공고명·공고기관·수요기관·배정예산·추정가격·입찰마감 | [data.go.kr 15058815](https://www.data.go.kr/data/15058815/openapi.do) |
| 낙찰 | 낙찰업체·낙찰금액·낙찰률·참여업체수 | [data.go.kr 15129397](https://www.data.go.kr/data/15129397/openapi.do) |
| 계약 | 계약명·수요기관·계약금액·계약방법 | [data.go.kr 15129427](https://www.data.go.kr/data/15129427/openapi.do) |

### 그 밖에 호출 가능한 서비스

아래는 공고가 아니라 통계·단가·코드사전 성격이라 `gov_search` 결과에 넣지 않았습니다.
인증키 권한은 확보되어 있고 엔드포인트도 확인되어, `data_go_kr_generic_get` 으로 바로 호출됩니다.
`gov_list_sources` 를 호출하면 주소와 오퍼레이션명이 함께 나옵니다.

| 서비스 | 쓰임 | 출처 |
| --- | --- | --- |
| 공공조달통계정보 | 기관별·기업별·계약방법별 조달 실적 집계 | [15129412](https://www.data.go.kr/data/15129412/openapi.do) |
| 나라장터 가격정보현황 | 시설공통자재·시장시공 단가. 입찰 가격 산정 참고 | [15129415](https://www.data.go.kr/data/15129415/openapi.do) |
| 나라장터 계약과정통합공개 | 계약 체결 과정 통합 공개 | [15129459](https://www.data.go.kr/data/15129459/openapi.do) |
| 나라장터 사용자정보 | 등록 조달업체·수요기관 정보 | [15129466](https://www.data.go.kr/data/15129466/openapi.do) |
| 나라장터 업종·근거법규 | 업종 코드와 근거 법령. 입찰 참가자격 해석용 | [15129467](https://www.data.go.kr/data/15129467/openapi.do) |
| 나라장터쇼핑몰 품목정보 | 종합쇼핑몰 물품 카탈로그 | [15129471](https://www.data.go.kr/data/15129471/openapi.do) |
| 조달청 물품목록정보 | 물품 분류번호 사전 | [15129417](https://www.data.go.kr/data/15129417/openapi.do) |
| 조달청 물품관리정보 | 물품 내용연수 고시 | [15129470](https://www.data.go.kr/data/15129470/openapi.do) |
| 창업진흥원 창업공간플랫폼 | 창업 보육센터·공간 정보 | [15125365](https://www.data.go.kr/data/15125365/openapi.do) |
| 한국연구재단 NRIC | 연구인력 채용정보 | [15088749](https://www.data.go.kr/data/15088749/openapi.do) |

### 지식재산권

| 기관 | 제공 데이터 | 출처 |
| --- | --- | --- |
| KIPRIS Plus (특허청) | 국내 특허·실용신안 서지정보. 발명명칭·초록으로 키워드 검색, 출원인·등록상태·IPC 분류 반환 | [plus.kipris.or.kr](https://plus.kipris.or.kr) |

### 교육

| 기관 | 제공 데이터 | 출처 |
| --- | --- | --- |
| NEIS (교육부) | 전국 초·중·고·특수학교 기본정보(주소·전화·홈페이지 등). 인증키 없이도 동작(5건 제한), 키가 있으면 최대 1,000건 | [open.neis.go.kr](https://open.neis.go.kr) |

### 학술 / 연구

| 기관 | 제공 데이터 | 상태 | 출처 |
| --- | --- | --- | --- |
| NTIS (과기정통부) | 국가 R&D 과제 키워드 검색 (과제명·연구책임자·주관기관·연구기간·연구비) | ✅ 완료 (실호출로 확인) | [ntis.go.kr](https://www.ntis.go.kr) |
| 서울연구원 | 연구보고서·정책리포트 등 11개 카테고리의 메타데이터(제목·날짜·저자·원문링크) | ✅ 완료 (실호출로 확인) | [si.re.kr/openapi](https://www.si.re.kr/openapi) |
| KCI 한국학술지인용색인 | 학술논문 검색 | ⏸ 활용신청 승인 대기 | [kci.go.kr](https://www.kci.go.kr) |
| KISTI | 국가R&D 연구보고서 검색 | ⏸ 활용신청 승인 대기 (승인되면 `data_go_kr_generic_get`으로 즉시 호출 가능) | [15102622](https://www.data.go.kr/data/15102622/openapi.do) |

---

## 인증키 현황

발급처는 11곳이며, **공공데이터포털 키 하나가 소스 7곳을 담당**합니다.

| 발급처 | 환경변수 | 상태 | 발급 방법 |
| --- | --- | --- | --- |
| 금융감독원 OpenDART | `DART_API_KEY` | ✅ | 회원가입 → 인증키 신청, 즉시 |
| 한국은행 ECOS | `ECOS_API_KEY` | ✅ | Open API 신청, 즉시~1일 |
| 통계청 KOSIS | `KOSIS_API_KEY` | ✅ | OpenAPI 활용신청 후 승인 |
| 공공데이터포털 | `DATA_GO_KR_API_KEY` | ✅ | 서비스 상세페이지에서 활용신청 |
| 한국수출입은행 | `KOREAEXIM_EXCHANGE_API_KEY`<br>`KOREAEXIM_LOAN_API_KEY`<br>`KOREAEXIM_INTERNATIONAL_API_KEY` | ✅ | 상품별로 각각 신청, 즉시 |
| 기업마당 | `BIZINFO_API_KEY` | ✅ | 신청서 작성 → 이메일 수신, 1일 |
| KIPRIS Plus | `KIPRIS_API_KEY` | ✅ | 회원가입 → Open API 인증키 신청, 즉시 |
| NEIS | `NEIS_API_KEY` | ✅ (선택) | 회원가입 → 인증키 신청, 즉시. 없어도 동작(5건 제한) |
| NTIS | `NTIS_API_KEY` | ✅ | 소속기관 등록 + 서버 IP 필요, 승인 수일 |
| 서울연구원 | `SEOUL_INSTITUTE_API_KEY` | ✅ | 신청 폼 제출 → 승인 후 이메일로 키·연동가이드 수신 |

### 공공데이터포털 인증키는 계정당 1개입니다

서비스마다 키가 발급되지 않습니다. **키 1개에 서비스별 사용 권한이 붙는 구조**입니다.
서비스를 몇 개 신청하든 `.env` 에 넣을 값은 하나뿐입니다.

포털이 인증키를 Encoding / Decoding 두 형태로 보여주는데, **Decoding 키**를 넣어야 합니다.

---

## 설치 및 실행

```bash
python -m venv .venv
.venv/Scripts/pip install -e .
cp .env.example .env      # 발급받은 키 입력
```

키가 하나도 없어도 서버는 정상적으로 뜹니다. 키가 필요한 도구를 호출할 때만 발급 안내가 나옵니다.

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json` 의 `mcpServers` 에 추가한 뒤 앱을 재시작합니다.

```json
"korea-public-data": {
  "command": "C:\\경로\\public-data-mcp\\.venv\\Scripts\\python.exe",
  "args": ["-m", "korea_public_data_mcp.server"]
}
```

### Claude Code

프로젝트 루트에 `.mcp.json` 을 만들거나 아래로 등록합니다.

```bash
claude mcp add korea-public-data -- C:\경로\public-data-mcp\.venv\Scripts\python.exe -m korea_public_data_mcp.server
```

### Docker

stdio 통신이라 포트를 열지 않습니다. 인증키는 반드시 실행 시점에 주입하세요.

```bash
docker build -t korea-public-data-mcp .
docker run -i --rm --env-file .env korea-public-data-mcp
```

---

## 제공 도구 (18개)

### 정부사업 · 조달

여러 기관이 같은 성격의 "공고"를 제공하므로 하나의 검색 도구로 묶었습니다.

| 도구 | 설명 |
| --- | --- |
| `gov_search` | 10개 소스를 한 번에 검색합니다. 기관을 지정하면 그쪽만 조회하고, 지정하지 않으면 전체를 훑되 기관별 상한(기본 10건)을 적용합니다 |
| `gov_list_sources` | 조회 가능한 소스 목록과 각 소스의 특성을 반환합니다. `generic_get` 으로 호출할 수 있는 서비스의 주소·오퍼레이션명도 함께 나옵니다 |

`gov_search` 인자

| 인자 | 설명 |
| --- | --- |
| `query` | 공고명·요약·지원대상·분야·기관명에서 찾을 키워드. 공백으로 나눈 여러 단어는 AND |
| `sources` | 기관 지정 (예: `["조달청"]`, `["기업마당","K-Startup"]`) |
| `domain` | `gov_program`(지원사업) 또는 `procurement`(조달) |
| `target` | 지원대상 (예: `중소기업`, `소상공인`, `창업`) |
| `open_only` | 접수 마감된 공고 제외 (기본 `true`) |
| `limit_per_source` | 기관별 최대 반환 건수 (기본 10) |

### 금융

기관마다 데이터 성격이 완전히 달라 개별 도구로 제공합니다.

| 도구 | 설명 |
| --- | --- |
| `dart_search_company` | 회사명으로 기업코드를 찾습니다. 다른 DART 도구보다 먼저 호출합니다 |
| `dart_get_financial_statements` | 재무제표 전체를 한 번에 조회합니다 (연결 `CFS` / 별도 `OFS`) |
| `dart_get_company_disclosures` | 기간별 공시 목록을 조회합니다 |
| `ecos_get_key_indicator` | 기준금리·원달러환율·GDP성장률·소비자물가지수를 이름으로 바로 조회합니다 |
| `ecos_search_statistics` | 그 밖의 한국은행 통계표를 검색합니다 |
| `ecos_get_statistic_data` | 통계표 코드로 실제 수치를 조회합니다 |
| `kosis_search_statistics` | 통계청 통계표를 검색합니다 |
| `kosis_get_statistics_data` | 통계표를 기간 범위 단위로 일괄 조회합니다 |
| `koreaexim_get_exchange_rates` | 환율 (매매기준율·전신환매매율) |
| `koreaexim_get_loan_rates` | 대출금리 |
| `koreaexim_get_international_rates` | 국제금리 (SOFR·ESTR 등) |

### 지식재산권 · 교육 · 학술연구

기관마다 데이터 성격이 완전히 달라 개별 도구로 제공합니다.

| 도구 | 설명 |
| --- | --- |
| `ip_search` | KIPRIS Plus로 국내 특허·실용신안을 키워드로 검색합니다 (발명명칭·초록·출원인 대상). 무료 한도가 월 1,000회로 빠듯합니다 |
| `neis_search_schools` | NEIS로 전국 초·중·고·특수학교 기본정보를 조회합니다. 인증키가 없어도 동작하지만 5건으로 제한됩니다 |
| `ntis_search_projects` | NTIS로 국가 R&D 과제를 키워드로 검색합니다 |
| `si_search_reports` | 서울연구원 연구보고서·정책리포트 등 11개 카테고리에서 자료를 검색합니다. 카테고리(`content_type`)를 먼저 지정해야 합니다 |

### 공통

| 도구 | 설명 |
| --- | --- |
| `data_go_kr_generic_get` | 공공데이터포털의 다른 서비스를 호출합니다. 포털에서 활용신청만 하면 코드 수정 없이 사용할 수 있습니다 |

---

## 라이선스

각 기관 API의 이용약관과 출처표시 의무를 따릅니다.
