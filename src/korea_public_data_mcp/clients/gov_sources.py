"""정부사업·조달 공고 소스별 어댑터.

기관마다 응답 형식이 전부 달라서(JSON/XML, 필드명, 날짜 표기), 여기서 공통 스키마로 맞춘다.
공통 스키마는 아래 normalize()가 만드는 dict 한 벌이다.

키워드 검색에 대해:
  대부분의 기관 API가 '제목 키워드 검색'을 지원하지 않는다(기간·분야·코드로만 조회 가능).
  그래서 각 어댑터는 최근 구간을 한 번 받아오고, 키워드 매칭은 이쪽에서 수행한다.
  fetch 크기를 무작정 키우면 일일 호출 한도를 깎아먹으므로 소스별 상한을 둔다.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import httpx

from korea_public_data_mcp.config import get_api_key
from korea_public_data_mcp.core.http_client import get_json
from korea_public_data_mcp.core.rate_limiter import throttle
from korea_public_data_mcp.registry import SOURCES

# 소스별로 한 번에 받아올 최대 건수. 키워드 필터는 이 안에서 수행한다.
_FETCH_LIMIT = 500
_G2B_FETCH_LIMIT = 300  # 나라장터는 건수가 압도적이라 더 좁게 받는다


def _ymd(value: str | None) -> str:
    """'20260818' / '2026-08-18 14:00:00' / '2026.08.18' -> '2026-08-18'."""
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return str(value).strip()


def _split_period(value: str | None) -> tuple[str, str]:
    """'2026-08-18 ~ 2026-08-28' 처럼 한 칸에 들어온 기간을 시작/종료로 나눈다."""
    if not value:
        return "", ""
    parts = re.split(r"~|∼|-\s*(?=\d{4})", str(value), maxsplit=1)
    if len(parts) == 2:
        return _ymd(parts[0]), _ymd(parts[1])
    return _ymd(value), ""


def normalize(source_id: str, **kw) -> dict:
    src = SOURCES[source_id]
    return {
        "source": src.id,
        "source_name": src.name,
        "domain": src.domain,
        "title": (kw.get("title") or "").strip(),
        "summary": (kw.get("summary") or "").strip()[:400],
        "target": (kw.get("target") or "").strip(),
        "category": (kw.get("category") or "").strip(),
        "org": (kw.get("org") or "").strip(),
        "apply_start": kw.get("apply_start") or "",
        "apply_end": kw.get("apply_end") or "",
        "url": kw.get("url") or "",
        "extra": {k: v for k, v in (kw.get("extra") or {}).items() if v},
    }


# ─────────────────────────────── 기업마당 ───────────────────────────────
async def fetch_bizinfo() -> list[dict]:
    """기업마당은 인증 파라미터가 serviceKey 가 아니라 crtfcKey 다."""
    await throttle("bizinfo")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do",
            params={"crtfcKey": get_api_key("bizinfo"), "dataType": "json", "searchCnt": _FETCH_LIMIT},
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"기업마당 HTTP {resp.status_code}: {resp.text[:200]}")
    rows = resp.json().get("jsonArray") or []
    out = []
    for r in rows:
        start, end = _split_period(r.get("reqstBeginEndDe"))
        out.append(
            normalize(
                "bizinfo",
                title=r.get("pblancNm"),
                summary=r.get("bsnsSumryCn"),
                target=r.get("trgetNm"),
                category=r.get("pldirSportRealmLclasCodeNm"),
                org=r.get("jrsdInsttNm"),
                apply_start=start,
                apply_end=end,
                url=r.get("pblancUrl"),
                extra={"수행기관": r.get("excInsttNm"), "신청방법": r.get("reqstMthPapersCn"),
                       "태그": r.get("hashtags"), "문의": r.get("refrncNm")},
            )
        )
    return out


# ─────────────────────────────── K-Startup ───────────────────────────────
async def fetch_kstartup(only_open: bool = True) -> list[dict]:
    params = {"page": 1, "perPage": _FETCH_LIMIT, "returnType": "json"}
    if only_open:
        params["cond[rcrt_prgs_yn::EQ]"] = "Y"
    data = await get_json(
        "data_go_kr",
        "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01",
        params={"serviceKey": get_api_key("data_go_kr"), **params},
    )
    out = []
    for r in data.get("data") or []:
        target = " / ".join(x for x in (r.get("aply_trgt"), r.get("biz_enyy")) if x)
        out.append(
            normalize(
                "kstartup",
                title=r.get("biz_pbanc_nm"),
                summary=r.get("pbanc_ctnt") or r.get("aply_trgt_ctnt"),
                target=target,
                category=r.get("supt_biz_clsfc"),
                org=r.get("sprv_inst") or r.get("pbanc_ntrp_nm"),
                apply_start=_ymd(r.get("pbanc_rcpt_bgng_dt")),
                apply_end=_ymd(r.get("pbanc_rcpt_end_dt")),
                url=r.get("detl_pg_url") or r.get("biz_gdnc_url"),
                extra={"지역": r.get("supt_regin"), "모집중": r.get("rcrt_prgs_yn"),
                       "담당부서": r.get("biz_prch_dprt_nm"), "문의": r.get("prch_cnpl_no")},
            )
        )
    return out


# ─────────────────────────────── 보조금24 ───────────────────────────────
async def fetch_bojo24(user_type: str | None = None) -> list[dict]:
    params: dict = {"page": 1, "perPage": _FETCH_LIMIT}
    if user_type:
        params["cond[사용자구분::EQ]"] = user_type
    data = await get_json(
        "data_go_kr",
        "https://api.odcloud.kr/api/gov24/v3/serviceList",
        params={"serviceKey": get_api_key("data_go_kr"), **params},
    )
    out = []
    for r in data.get("data") or []:
        out.append(
            normalize(
                "bojo24",
                title=r.get("서비스명"),
                summary=r.get("서비스목적요약"),
                target=" / ".join(x for x in (r.get("사용자구분"), r.get("지원대상")) if x),
                category=r.get("서비스분야"),
                org=r.get("소관기관명"),
                apply_start="",
                apply_end="",
                url=r.get("상세조회URL"),
                extra={"신청기한": r.get("신청기한"), "신청방법": r.get("신청방법"),
                       "지원유형": r.get("지원유형"), "접수기관": r.get("접수기관")},
            )
        )
    return out


# ─────────────────────────── 과기정통부 사업공고 ───────────────────────────
async def fetch_msit(pages: int = 5) -> list[dict]:
    """이 API는 numOfRows 를 무시하고 페이지당 10건만 준다. 응답도 XML 뿐이다."""
    out: list[dict] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, pages + 1):
            await throttle("data_go_kr")
            resp = await client.get(
                "https://apis.data.go.kr/1721000/msitannouncementinfo/businessAnnouncMentList",
                params={"serviceKey": get_api_key("data_go_kr"), "pageNo": page, "numOfRows": 10},
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"과기정통부 HTTP {resp.status_code}: {resp.text[:200]}")
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            if not items:
                break
            for it in items:
                get = lambda tag: (it.findtext(tag) or "").strip()  # noqa: E731
                out.append(
                    normalize(
                        "msit",
                        title=get("subject"),
                        summary="",
                        target="",
                        category="",
                        org=f"과학기술정보통신부 {get('deptName')}".strip(),
                        apply_start=_ymd(get("pressDt")),
                        apply_end="",
                        url=get("viewUrl"),
                        extra={"담당자": get("managerName"), "연락처": get("managerTel")},
                    )
                )
    return out


# ─────────────────────────── 나라장터 입찰공고 ───────────────────────────
async def fetch_g2b_bid(days: int = 14) -> list[dict]:
    """개방표준 서비스. 조회 기간이 필수라 최근 days 일로 범위를 잡는다."""
    end = date.today()
    start = end - timedelta(days=max(days, 1))
    data = await get_json(
        "data_go_kr",
        "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdBidPblancInfo",
        params={
            "serviceKey": get_api_key("data_go_kr"),
            "type": "json",
            "pageNo": 1,
            "numOfRows": _G2B_FETCH_LIMIT,
            "bidNtceBgnDt": start.strftime("%Y%m%d") + "0000",
            "bidNtceEndDt": end.strftime("%Y%m%d") + "2359",
        },
    )
    body = (data.get("response") or {}).get("body") or {}
    out = []
    for r in body.get("items") or []:
        out.append(
            normalize(
                "g2b_bid",
                title=r.get("bidNtceNm"),
                summary="",
                target=r.get("bidprcPsblIndstrytyNm") or r.get("prtcptPsblRgnNm"),
                category=r.get("bsnsDivNm"),
                org=r.get("ntceInsttNm"),
                apply_start=_ymd(r.get("bidNtceDate")),
                apply_end=_ymd(r.get("bidClseDate")),
                url=r.get("bidNtceUrl"),
                extra={"수요기관": r.get("dmndInsttNm"), "배정예산": r.get("asignBdgtAmt"),
                       "추정가격": r.get("presmptPrce"), "계약방법": r.get("cntrctCnclsMthdNm"),
                       "개찰일": _ymd(r.get("opengDate")), "공고번호": r.get("bidNtceNo")},
            )
        )
    return out


FETCHERS = {
    "bizinfo": fetch_bizinfo,
    "kstartup": fetch_kstartup,
    "bojo24": fetch_bojo24,
    "msit": fetch_msit,
    "g2b_bid": fetch_g2b_bid,
}
