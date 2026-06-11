"""
tavily_search.py — Tavily API를 통한 타 지자체 유사 사례 검색
"""

import os
import logging

logger = logging.getLogger(__name__)


def _format_results(response: dict) -> str:
    """Tavily 응답 → Claude 컨텍스트용 텍스트 변환."""
    parts: list[str] = []

    answer = response.get("answer", "").strip()
    if answer:
        parts.append(f"[검색 요약]\n{answer}")

    results = response.get("results", [])
    if results:
        parts.append("[관련 검색 결과]")
        for r in results:
            title = r.get("title", "").strip()
            content = r.get("content", "").strip()[:400]
            if title or content:
                parts.append(f"· {title}\n  {content}")

    return "\n\n".join(parts)


def search_cases(project_name: str, project_type: str = "") -> str:
    """
    '{project_name} 타 지자체 사례' Tavily 검색.
    결과 있으면 정제된 텍스트, 없거나 오류면 빈 문자열 반환.
    """
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        logger.debug("TAVILY_API_KEY 미설정 — 검색 스킵")
        return ""

    try:
        from tavily import TavilyClient  # 설치 여부 런타임 확인
    except ImportError:
        logger.warning("tavily-python 미설치 — 검색 스킵 (pip install tavily-python)")
        return ""

    queries = [
        f"{project_name} 지자체 추진 사례 결과",
        f"{project_name} {project_type} 지방자치단체 사례" if project_type else "",
    ]

    try:
        client = TavilyClient(api_key=api_key)
        all_parts: list[str] = []

        for query in queries:
            if not query.strip():
                continue
            resp = client.search(
                query=query,
                search_depth="basic",
                max_results=4,
                include_answer=True,
            )
            chunk = _format_results(resp)
            if chunk:
                all_parts.append(chunk)

        if not all_parts:
            return ""

        return "\n\n---\n\n".join(all_parts)

    except Exception as exc:
        logger.warning("Tavily 검색 실패 (%s) — fallback AI 생성으로 전환", exc)
        return ""
