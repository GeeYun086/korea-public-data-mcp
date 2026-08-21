"""정부사업·조달 공고 통합 검색 MCP 도구."""
from __future__ import annotations

import asyncio
from datetime import date

from mcp.server.mcpserver import MCPServer

from korea_public_data_mcp.clients.gov_sources import FETCHERS
from korea_public_data_mcp.config import MissingApiKeyError
from korea_public_data_mcp.core.cache import cached_call
from korea_public_data_mcp import registry

# 소스를 지정하지 않은 검색에서 한 소스가 결과를 독식하지 못하게 막는 상한.
# 나라장터는 2주에 1.6만 건 규모라, 상한이 없으면 나머지 소스가 전부 묻힌다.
_DEFAULT_PER_SOURCE = 10
_MAX_PER_SOURCE = 50

_SEARCH_FIELDS = ("title", "summary", "target", "category", "org")


def _matches(record: dict, terms: list[str]) -> bool:
    if not terms:
        return True
    hay = " ".join(str(record.get(f) or "") for f in _SEARCH_FIELDS).lower()
    hay += " " + " ".join(str(v) for v in (record.get("extra") or {}).values()).lower()
    return all(t in hay for t in terms)


def _is_open(record: dict, today: str) -> bool:
    """마감일이 있고 이미 지났으면 제외. 마감일 정보가 없으면 판단하지 않고 남긴다."""
    end = record.get("apply_end") or ""
    return not end or end >= today


async def _collect(source_id: str) -> list[dict]:
    return await cached_call(f"gov:{source_id}", FETCHERS[source_id])


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def gov_search(
        query: str = "",
        sources: list[str] | None = None,
        domain: str = "",
        target: str = "",
        open_only: bool = True,
        limit_per_source: int = _DEFAULT_PER_SOURCE,
    ) -> dict:
        """정부 지원사업 공고와 공공 입찰공고를 여러 기관에서 한 번에 검색한다.

        검색 대상: 기업마당(중소기업 지원사업), K-Startup(창업 지원사업),
        과기정통부 사업공고, 나라장터(공공기관 입찰공고).

        query: 공고명·요약·지원대상·분야·기관명에서 찾을 키워드. 공백으로 나눈 여러 단어는 AND 조건.
               비워두면 최근 공고를 그대로 돌려준다.
        sources: 특정 기관만 볼 때 지정한다. 기관명으로 적으면 된다
                 (예: ['조달청'], ['기업마당','K-Startup']). 질문에 기관이 언급되면 반드시 채울 것.
        domain: 'gov_program'(지원사업) 또는 'procurement'(조달·입찰)로 종류를 좁힌다.
        target: 지원대상 필터 (예: '중소기업', '소상공인', '창업').
        open_only: True면 접수 마감일이 지난 공고를 제외한다.
        limit_per_source: 기관별 최대 반환 건수(기본 10). 나라장터는 건수가 압도적이라
                          이 상한이 없으면 다른 기관 공고가 전부 묻힌다.

        어느 기관을 조회할지 먼저 보려면 gov_list_sources 를 호출한다.
        """
        picked = registry.resolve(sources, domain=domain or None)
        if not picked:
            return {
                "error": f"조건에 맞는 소스가 없습니다. sources={sources}, domain={domain}",
                "available": registry.catalog(),
            }

        cap = max(1, min(int(limit_per_source or _DEFAULT_PER_SOURCE), _MAX_PER_SOURCE))
        terms = [t for t in query.lower().split() if t]
        today = date.today().isoformat()

        results = await asyncio.gather(
            *(_collect(s.id) for s in picked), return_exceptions=True
        )

        records: list[dict] = []
        status: list[dict] = []
        for src, res in zip(picked, results):
            if isinstance(res, MissingApiKeyError):
                status.append({"source": src.name, "state": "키 미설정", "detail": str(res)})
                continue
            if isinstance(res, BaseException):
                status.append({"source": src.name, "state": "조회 실패",
                               "detail": f"{type(res).__name__}: {res}"[:200]})
                continue

            hits = [r for r in res if _matches(r, terms)]
            if target:
                t = target.lower()
                hits = [r for r in hits if t in (r.get("target") or "").lower()]
            if open_only:
                hits = [r for r in hits if _is_open(r, today)]

            hits.sort(key=lambda r: (r.get("apply_end") or "9999", r.get("apply_start") or ""))
            status.append({
                "source": src.name, "state": "정상",
                "조회": len(res), "조건일치": len(hits), "반환": min(len(hits), cap),
            })
            records.extend(hits[:cap])

        ok = [s for s in status if s["state"] == "정상"]
        return {
            "query": query,
            "sources": [s.name for s in picked],
            "요약": f"{len(ok)}/{len(picked)}개 기관 조회 성공, 총 {len(records)}건 반환"
                    + (f" (기관별 최대 {cap}건)" if len(records) else ""),
            "기관별_상태": status,
            "results": records,
        }

    @mcp.tool()
    async def gov_list_sources(domain: str = "") -> dict:
        """검색 가능한 정부사업·조달 기관 목록과 각 기관이 무엇을 담고 있는지 반환한다.
        어느 기관을 조회해야 할지 판단이 서지 않을 때 gov_search 보다 먼저 호출한다.

        gov_search 로 검색되는 소스 외에, 통계·단가·코드사전처럼 공고가 아니라
        gov_search 에 넣지 않은 서비스도 함께 반환한다. 그쪽은 base_url/operations 를
        data_go_kr_generic_get 에 그대로 넣어 호출하면 된다."""
        return {
            "sources": registry.catalog(domain or None),
            "generic_get으로_호출_가능한_서비스": registry.EXTRA_ENDPOINTS,
        }
