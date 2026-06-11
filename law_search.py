"""
law_search.py — 국가법령정보센터 DRF API 연동 (법령명 검색)
조문 번호는 API가 제공하지 않으므로 법령명만 반환. 조문 단정 금지 원칙 준수.
"""

import os
import logging
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

logger = logging.getLogger(__name__)

LAW_SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"

# 사업 유형별 추가 검색 키워드 (법령 관련 용어)
TYPE_KEYWORDS: dict[str, list[str]] = {
    "복지":       ["사회보장", "복지서비스"],
    "인프라":     ["건설기술", "공유재산"],
    "문화관광":   ["문화예술", "관광진흥"],
    "경제창업":   ["중소기업", "창업지원"],
    "환경":       ["환경영향평가", "자연환경보전"],
    "행정서비스": ["개인정보보호", "전자정부"],
    "기타":       [],
}


def search_laws(project_name: str, project_type: str = "") -> list[dict]:
    """
    프로젝트명·유형으로 관련 법령 검색.
    반환: [{"name": "법령명", "type": "법률|시행령 등", "dept": "소관부처"}, ...]
    LAW_API_KEY 미설정 또는 오류 시 빈 리스트.
    """
    api_key = os.getenv("LAW_API_KEY", "").strip()
    if not api_key:
        logger.debug("LAW_API_KEY 미설정 — 법령 검색 스킵")
        return []

    queries = [project_name] + TYPE_KEYWORDS.get(project_type, [])[:2]

    found: dict[str, dict] = {}
    for query in queries[:3]:
        if not query.strip():
            continue
        try:
            results = _call_api(api_key, query, display=15)
            for r in results:
                name = r.get("name", "")
                if name and name not in found:
                    found[name] = r
            if len(found) >= 10:
                break
        except Exception as exc:
            logger.warning("법령 검색 실패 (query=%s): %s", query, exc)

    return list(found.values())[:10]


# 시행령·시행규칙 등 하위 법규 제외 — 법률만 사용
_LAW_ONLY = {"법률"}


def _call_api(api_key: str, query: str, display: int = 15) -> list[dict]:
    params = {
        "OC":      api_key,
        "target":  "law",
        "type":    "XML",
        "query":   query,
        "display": display,
        "page":    1,
    }
    resp = requests.get(LAW_SEARCH_URL, params=params, timeout=8)
    resp.raise_for_status()
    return _parse_xml(resp.content)


def _parse_xml(content: bytes) -> list[dict]:
    """XML 응답에서 법률만 추출 (시행령·시행규칙 제외)."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []

    results: list[dict] = []
    seen: set[str] = set()

    for parent in root.iter():
        name_elem = parent.find("법령명한글")
        if name_elem is None or not name_elem.text:
            continue
        name = name_elem.text.strip()
        if name in seen:
            continue

        type_elem = parent.find("법령구분명")
        law_type = (type_elem.text or "").strip() if type_elem is not None else ""

        # 법률만 포함, 시행령·시행규칙·규정·고시 등 제외
        if law_type not in _LAW_ONLY:
            continue

        seen.add(name)
        dept_elem = parent.find("소관부처명")
        results.append({
            "name": name,
            "type": law_type,
            "dept": (dept_elem.text or "").strip() if dept_elem is not None else "",
            "url":  f"https://www.law.go.kr/법령/{quote(name, safe='')}",
        })

    return results


def format_for_context(laws: list[dict]) -> str:
    """Claude 프롬프트용 법령 컨텍스트 텍스트."""
    if not laws:
        return ""
    lines = [
        "[국가법령정보센터 검색 결과 — 법령명만 제공됨]",
        "[조문 번호(제X조 제X항)는 담당자가 직접 확인해야 함. 단정 금지]",
    ]
    for law in laws:
        parts = [f"· {law['name']}"]
        if law.get("type"):
            parts.append(f"({law['type']})")
        if law.get("dept"):
            parts.append(f"/ 소관: {law['dept']}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def make_url_map(laws: list[dict]) -> dict[str, str]:
    """법령명 → URL 매핑 딕셔너리."""
    return {law["name"]: law["url"] for law in laws if law.get("url")}
