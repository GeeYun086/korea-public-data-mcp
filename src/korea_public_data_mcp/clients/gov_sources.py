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
    rows = await _g2b(
        "PubDataOpnStdService/getDataSetOpnStdBidPblancInfo",
        {"bidNtceBgnDt": start.strftime("%Y%m%d") + "0000",
         "bidNtceEndDt": end.strftime("%Y%m%d") + "2359"},
    )
    out = []
    for r in rows:
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


async def _g2b(path: str, params: dict, limit: int = _G2B_FETCH_LIMIT) -> list[dict]:
    """나라장터 계열 API는 페이지 1이 '가장 오래된' 건이다.

    사전규격만 봐도 30일 조회 시 page 1은 7/20, 마지막 페이지가 8/19다.
    그냥 page 1을 받으면 이미 마감된 옛날 건만 손에 들어오므로,
    총 건수를 먼저 확인한 뒤 마지막 페이지(=최신)를 가져온다.
    """
    # 조달청 API는 서비스별로 ao/ad/as/at 하위 경로가 다르다. path 에 접두어가 이미
    # 붙어 있으면 그대로 쓰고, 없으면 가장 흔한 ao/ 를 붙인다.
    prefix = "" if path.startswith(("ao/", "ad/", "as/", "at/")) else "ao/"
    url = f"https://apis.data.go.kr/1230000/{prefix}{path}"
    key = get_api_key("data_go_kr")
    base = {"serviceKey": key, "type": "json", **params}

    head = await get_json("data_go_kr", url, params={**base, "pageNo": 1, "numOfRows": 1})
    body = ((head.get("response") or {}).get("body") or {})
    total = int(body.get("totalCount") or 0)
    if total <= 0:
        return []

    last_page = max(1, -(-total // limit))  # 올림 나눗셈

    async def page(no: int) -> list[dict]:
        data = await get_json("data_go_kr", url, params={**base, "pageNo": no, "numOfRows": limit})
        return ((data.get("response") or {}).get("body") or {}).get("items") or []

    rows = await page(last_page)
    # 마지막 페이지는 나머지만 담겨 몇 건 안 되는 경우가 많다(예: 5,526건/300 -> 126건).
    # 표본이 너무 얇으면 키워드 검색이 헛돌므로 바로 앞 페이지까지 붙인다.
    if len(rows) < limit and last_page > 1:
        rows = await page(last_page - 1) + rows
    return rows


# ─────────────────────────── 나라장터 발주계획 ───────────────────────────
async def fetch_g2b_order_plan(year: str = "") -> list[dict]:
    """발주계획은 기간 파라미터가 inqryBgnDate/inqryEndDate(8자리)다.
    입찰공고 쪽의 inqryBgnDt(12자리)와 이름이 달라 혼동하기 쉽다."""
    end = date.today()
    start = date(end.year, 1, 1) if not year else date(int(year), 1, 1)
    rows = await _g2b(
        "OrderPlanSttusService/getOrderPlanSttusListThng",
        {"inqryDiv": "1",
         "inqryBgnDate": start.strftime("%Y%m%d"),
         "inqryEndDate": end.strftime("%Y%m%d")},
    )
    out = []
    for r in rows:
        month = str(r.get("orderMnth") or "").zfill(2)
        out.append(
            normalize(
                "g2b_order_plan",
                title=(r.get("bizNm") or "").strip(),
                summary=r.get("usgCntnts") or r.get("specCntnts"),
                target=r.get("prdctClsfcNoNm"),
                category=r.get("bsnsDivNm"),
                org=r.get("orderInsttNm") or r.get("totlmngInsttNm"),
                apply_start=f"{r.get('orderYear')}-{month}-01" if month.isdigit() else "",
                apply_end="",
                url=r.get("orderPlanDtlUrl"),
                extra={"발주예정월": f"{r.get('orderYear')}-{month}", "발주금액": r.get("sumOrderAmt"),
                       "계약방법": r.get("cntrctMthdNm"), "조달방식": r.get("prcrmntMethd"),
                       "담당": r.get("ofclNm"), "연락처": r.get("telNo")},
            )
        )
    return out


# ─────────────────────────── 나라장터 조달요청 ───────────────────────────
async def fetch_g2b_request(days: int = 30) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=max(days, 1))
    rows = await _g2b(
        "PrcrmntReqInfoService/getPrcrmntReqInfoListThng",
        {"inqryDiv": "1",
         "inqryBgnDt": start.strftime("%Y%m%d") + "0000",
         "inqryEndDt": end.strftime("%Y%m%d") + "2359"},
    )
    out = []
    for r in rows:
        out.append(
            normalize(
                "g2b_request",
                title=r.get("prcrmntReqNm"),
                summary=r.get("rprsntSpecDtlsCntnts"),
                target=r.get("rprsntPrdctClsfcNoNm"),
                category=r.get("bsnsDivNm"),
                org=r.get("orderInsttNm"),
                apply_start=_ymd(r.get("rcptDt")),
                apply_end="",
                url=r.get("prcrmntReqInfoUrl"),
                extra={"요청번호": r.get("prcrmntReqNo"), "예산액": r.get("bdgtAmt"),
                       "대표품목": r.get("rprsntPrdctClsfcNoNm"), "계약형태": r.get("cntrctCnclsStleNm"),
                       "납품장소": r.get("rprsntDlvrPlce"), "담당": r.get("prcrmntReqOfclNm")},
            )
        )
    return out


# ─────────────────────────── 나라장터 사전규격 ───────────────────────────
async def fetch_g2b_prestandard(days: int = 30) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=max(days, 1))
    rows = await _g2b(
        "HrcspSsstndrdInfoService/getPublicPrcureThngInfoThng",
        {"inqryDiv": "1",
         "inqryBgnDt": start.strftime("%Y%m%d") + "0000",
         "inqryEndDt": end.strftime("%Y%m%d") + "2359"},
    )
    out = []
    for r in rows:
        out.append(
            normalize(
                "g2b_prestandard",
                title=r.get("prdctClsfcNoNm"),
                summary=r.get("prdctDtlList"),
                target="",
                category=r.get("bsnsDivNm"),
                org=r.get("rlDminsttNm") or r.get("orderInsttNm"),
                apply_start=_ymd(r.get("rcptDt")),
                apply_end=_ymd(r.get("opninRgstClseDt")),  # 의견등록 마감
                url=r.get("specDocFileUrl1"),
                extra={"배정예산": r.get("asignBdgtAmt"), "의견마감": r.get("opninRgstClseDt"),
                       "납품기한": _ymd(r.get("dlvrTmlmtDt")), "SW사업여부": r.get("swBizObjYn"),
                       "담당": r.get("ofclNm"), "규격번호": r.get("bfSpecRgstNo")},
            )
        )
    return out


# ─────────────────────────── 나라장터 계약정보 ───────────────────────────
async def fetch_g2b_contract(days: int = 7) -> list[dict]:
    """계약정보는 조회 기간 상한이 7일(양끝 포함)이다.
    8일치를 요청하면 resultCode 07 '입력범위값 초과 에러'가 떨어지므로 간격은 6일까지만 준다."""
    end = date.today()
    start = end - timedelta(days=min(max(days, 1), 7) - 1)
    rows = await _g2b(
        "PubDataOpnStdService/getDataSetOpnStdCntrctInfo",
        {"cntrctCnclsBgnDate": start.strftime("%Y%m%d"),
         "cntrctCnclsEndDate": end.strftime("%Y%m%d")},
    )
    out = []
    for r in rows:
        out.append(
            normalize(
                "g2b_contract",
                title=r.get("cntrctNm"),
                summary="",
                target="",
                category=r.get("bsnsDivNm"),
                org=r.get("dmndInsttNm") or r.get("cntrctInsttNm"),
                apply_start=_ymd(r.get("cntrctCnclsDate")),
                apply_end="",
                url=r.get("cntrctDtlUrl") or "",
                extra={"계약금액": r.get("thtmCntrctAmt") or r.get("totCntrctAmt"),
                       "계약형태": r.get("cntrctCnclsSttusNm"), "계약번호": r.get("cntrctNo")},
            )
        )
    return out


# ─────────────────────────── 나라장터 낙찰정보 ───────────────────────────
async def fetch_g2b_award(days: int = 14) -> list[dict]:
    """낙찰은 개방표준(getDataSetOpnStdScsbidInfo)이 아니라 별도 서비스인
    ScsbidInfoService 를 쓴다. 개방표준 쪽은 필수 파라미터명이 확인되지 않았다."""
    end = date.today()
    start = end - timedelta(days=max(days, 1))
    rows = await _g2b(
        "as/ScsbidInfoService/getScsbidListSttusThng",
        {"inqryDiv": "1",
         "inqryBgnDt": start.strftime("%Y%m%d") + "0000",
         "inqryEndDt": end.strftime("%Y%m%d") + "2359"},
    )
    out = []
    for r in rows:
        out.append(
            normalize(
                "g2b_award",
                title=r.get("bidNtceNm"),
                summary="",
                target="",
                category="",
                org=r.get("dminsttNm"),
                apply_start=_ymd(r.get("rlOpengDt")),
                apply_end="",
                url="",
                extra={"낙찰업체": r.get("bidwinnrNm"), "낙찰금액": r.get("sucsfbidAmt"),
                       "낙찰률": r.get("sucsfbidRate"), "참여업체수": r.get("prtcptCnum"),
                       "개찰일시": r.get("rlOpengDt"), "공고번호": r.get("bidNtceNo")},
            )
        )
    return out


FETCHERS = {
    "bizinfo": fetch_bizinfo,
    "kstartup": fetch_kstartup,
    "bojo24": fetch_bojo24,
    "msit": fetch_msit,
    "g2b_order_plan": fetch_g2b_order_plan,
    "g2b_request": fetch_g2b_request,
    "g2b_prestandard": fetch_g2b_prestandard,
    "g2b_bid": fetch_g2b_bid,
    "g2b_award": fetch_g2b_award,
    "g2b_contract": fetch_g2b_contract,
}
