"""
finance_search.py — 열린데이터포털 지방재정 API 연동
지자체별 예산 정보 조회 및 비교표 생성
"""

import os
import logging
import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote

logger = logging.getLogger(__name__)

FINANCE_API_BASE = "https://apis.data.go.kr/1741000/GovernmentsIndependence"
OPERATION_PATHS = [
    "GovernmentsIndependenceService/getGovernmentsIndependenceInfoList",
    "GovernmentsIndependenceService/getIndependenceInfoList",
    "getGovernmentsIndependenceInfoList",
]

# 지자체명 추출 패턴 (Tavily 텍스트에서)
_MUNI_RE = re.compile(
    r"[가-힣]{2,6}(?:특별시|광역시|특별자치시|특례시|특별자치도|자치시|시|군)(?!\w)"
)
_SKIP_WORDS = {"고양특례시", "고양시", "확인 필요", "지자체"}


def extract_municipality_names(text: str) -> list[str]:
    """Tavily 검색 텍스트에서 지자체명 추출. 고양시 및 중복 제외."""
    if not text:
        return []
    found: dict[str, int] = {}
    for m in _MUNI_RE.finditer(text):
        name = m.group()
        if name not in _SKIP_WORDS:
            found[name] = found.get(name, 0) + 1
    # 빈도 순 정렬, 최대 4개
    return [n for n, _ in sorted(found.items(), key=lambda x: -x[1])][:4]


def _call_api(api_key: str, muni_name: str) -> dict:
    """단일 지자체 예산 조회. 성공 시 dict, 실패 시 None."""
    # data.go.kr 키는 인코딩 상태로 올 수 있으므로 디코딩 후 URL에 직접 삽입
    decoded_key = unquote(api_key)

    for op in OPERATION_PATHS:
        url = f"{FINANCE_API_BASE}/{op}"
        try:
            resp = requests.get(
                url,
                params={
                    "serviceKey": decoded_key,
                    "pageNo":     1,
                    "numOfRows":  5,
                    "type":       "xml",
                    "laName":     muni_name,
                },
                timeout=6,
            )
            if resp.status_code != 200:
                continue
            result = _parse_xml(resp.content, muni_name)
            if result:
                return result
        except Exception as exc:
            logger.debug("재정 API 호출 실패 (%s, %s): %s", op, muni_name, exc)
            continue
    return {}


def _parse_xml(content: bytes, muni_name: str) -> dict:
    """XML 응답에서 재정자립도/예산 관련 필드 추출.
    GovernmentsIndependence API: 재정자립도(%) + 자주재원 제공.
    필드명은 API 응답 확인 후 확정 필요.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return {}

    # 오류 응답 확인
    result_code = root.findtext(".//resultCode") or root.findtext(".//errCode") or ""
    if result_code and result_code not in ("00", "0000", "OK", ""):
        return {}

    NAME_TAGS   = ["자치단체명", "지방자치단체명", "laName", "localName", "siDoNm", "sggNm"]
    YEAR_TAGS   = ["기준연도", "회계연도", "accntYear", "year", "fiscalYear", "연도"]
    BUDGET_TAGS = ["예산현액", "예산액", "budgetAmt", "totalBudget", "총예산",
                   "자주재원", "자주재원합계", "세출예산"]

    for item in root.iter():
        if item.tag.lower() in ("item", "row", "data", "info"):
            name = _find_text(item, NAME_TAGS) or muni_name
            year = _find_text(item, YEAR_TAGS) or ""
            budget_raw = _find_text(item, BUDGET_TAGS)

            if budget_raw:
                try:
                    budget_int = int(re.sub(r"[^0-9]", "", budget_raw))
                    budget_str = _format_budget(budget_int)
                except ValueError:
                    budget_str = budget_raw
                return {"name": name, "budget": budget_str, "year": year}

    logger.debug("재정 API 응답 태그 목록: %s", [c.tag for c in root][:10])
    return {}


def _find_text(elem, tag_list: list[str]) -> str:
    for tag in tag_list:
        val = elem.findtext(tag)
        if val and val.strip():
            return val.strip()
    return ""


def _format_budget(won: int) -> str:
    """원 단위 → 억원/천만원 표시."""
    if won >= 100_000_000:
        return f"{won // 100_000_000:,}억원"
    if won >= 10_000_000:
        return f"{won // 10_000_000:,}천만원"
    return f"{won:,}원"


def get_budget_comparison(
    muni_names: list[str],
    project_name: str,
    own_budget: int | None,
    own_period: str,
) -> list[dict]:
    """
    지자체 목록에 대해 지방재정 API 조회.
    반환: [{"name", "project", "budget", "period", "note"}, ...]
    첫 행은 항상 고양특례시(입력값 기준).
    """
    api_key = os.getenv("DATA_GO_KR_API_KEY", "").strip()

    rows: list[dict] = []

    # 첫 행: 고양특례시 (사용자 입력 예산)
    rows.append({
        "name":    "고양특례시",
        "project": project_name,
        "budget":  _format_budget(own_budget) if own_budget else "입력값 없음",
        "period":  own_period or "-",
        "note":    "비교 기준 (입력 예산)",
    })

    if not api_key:
        logger.debug("DATA_GO_KR_API_KEY 미설정 — 재정 API 스킵")
        for name in muni_names:
            rows.append({
                "name": name, "project": "확인 필요",
                "budget": "확인 필요", "period": "확인 필요",
                "note": "API 키 미설정",
            })
        return rows

    for name in muni_names:
        try:
            result = _call_api(api_key, name)
            if result and result.get("budget"):
                rows.append({
                    "name":    result["name"],
                    "project": "유사 사업 확인 필요",
                    "budget":  result["budget"],
                    "period":  result.get("year") or "확인 필요",
                    "note":    "지방재정 API 조회값",
                })
            else:
                rows.append({
                    "name": name, "project": "확인 필요",
                    "budget": "확인 필요", "period": "확인 필요",
                    "note": "API 조회 결과 없음",
                })
        except Exception as exc:
            logger.warning("재정 조회 실패 (%s): %s", name, exc)
            rows.append({
                "name": name, "project": "확인 필요",
                "budget": "확인 필요", "period": "확인 필요",
                "note": "조회 오류",
            })

    return rows


def format_budget_table(rows: list[dict]) -> str:
    """예산 비교 데이터 → 파이프 구분 표 문자열."""
    if not rows:
        return ""
    lines = [
        "[예산 비교표 (지방재정 API 기반)]",
        "지자체명|유사 사업명|예산 규모|사업 기간|비고",
    ]
    for r in rows:
        lines.append(
            f"{r['name']}|{r['project']}|{r['budget']}|{r['period']}|{r['note']}"
        )
    return "\n".join(lines)
