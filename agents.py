"""
agents.py — Claude API Multi-Agent 보고서 생성 모듈 (5개 섹션, 표 형식)
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

COMMON_SYSTEM_PROMPT = """당신은 경기도 고양특례시 정책사업의 내부 검토를 수행하는 전문 행정 분석가입니다.

[고양특례시 행정 기본 정보]
- 인구: 약 107만 명 / 행정구: 덕양구·일산동구·일산서구
- 특성: 수도권 서북부 거점 도시, GTX-A 개통, 방송영상밸리
- 의회: 고양시의회(시의원 35명), 경기도의회 고양 선거구

[출력 규칙 — 반드시 준수]
1. 지정된 파이프(|) 구분 표 형식으로만 출력한다. 표 외 설명 문장 금지.
2. 셀 내에 | 문자 절대 사용 금지 — 대신 / 사용.
3. 미확인 타 지자체 사례(시·군명·예산액·수치)를 단정하지 않는다.
4. 법령 조문 번호(제X조 제X항) 임의 생성 금지. 법률명만 언급.
5. 단정 표현 대신 "~로 판단됨", "~가능성 있음", "~검토 필요" 사용."""


def _format_budget(budget) -> str:
    if budget is None:
        return "미기재"
    try:
        return f"{int(budget):,}원"
    except (ValueError, TypeError):
        return str(budget)


def _build_context(inputs: dict) -> str:
    return (
        f"사업명: {inputs.get('project_name', '(미기재)')}\n"
        f"사업 유형: {inputs.get('project_type', '(미기재)')}\n"
        f"주요 대상: {inputs.get('target') or '(미기재)'}\n"
        f"총 예산: {_format_budget(inputs.get('budget'))}\n"
        f"사업 기간: {inputs.get('period') or '(미기재)'}\n"
        f"사업 내용:\n{inputs.get('description', '')}"
    )


def call_claude(prompt: str, system_prompt: str = COMMON_SYSTEM_PROMPT) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def call_claude_with_retry(
    prompt: str,
    system_prompt: str = COMMON_SYSTEM_PROMPT,
    max_retries: int = 2,
) -> str:
    for attempt in range(max_retries + 1):
        try:
            return call_claude(prompt, system_prompt)
        except anthropic.RateLimitError:
            if attempt < max_retries:
                time.sleep(2 ** (attempt + 1))
            else:
                raise
        except (anthropic.APIStatusError, anthropic.APIConnectionError):
            raise


# ─── 섹션별 생성 함수 ────────────────────────────────────────────────────────


def generate_section_01_overview(inputs: dict) -> str:
    ctx = _build_context(inputs)
    prompt = f"""[1. 사업 개요] 섹션을 아래 표 형식으로만 출력하라. 헤더 포함, 셀 내 | 금지.

{ctx}

항목|내용
사업 목적|(핵심 1줄)
주요 대상|(대상 그룹)
사업 기간|(기간)
총 예산|(예산)
주요 내용|(핵심 항목 3-5개, /로 구분)
기대효과|(핵심 1-2줄)"""
    return call_claude_with_retry(prompt)


def generate_section_02_risk(inputs: dict, law_context: str = "") -> str:
    ctx = _build_context(inputs)
    law_block = f"\n{law_context}\n" if law_context else ""
    prompt = f"""[2. 위험성 분석] 섹션을 아래 표 형식으로만 출력하라. 헤더 포함, 셀 내 | 금지.
법적 위험 행에는 아래 검색된 법령명을 근거로 작성하되, 조문 번호(제X조 제X항) 임의 생성 금지.
{law_block}
{ctx}

위험 유형|수준|위험 내용|대응 방안
예산 집행|(상/중/하)|(1줄)|(1줄)
운영|(상/중/하)|(1줄)|(1줄)
민원·이해관계|(상/중/하)|(1줄)|(1줄)
법적|(상/중/하)|(관련 법령명 명시, 조문번호 금지)|(관련 조문 확인 필요 명시)
효과성|(상/중/하)|(1줄)|(1줄)"""
    return call_claude_with_retry(prompt)


def generate_precheck(inputs: dict, law_context: str = "") -> str:
    ctx = _build_context(inputs)
    law_block = f"\n{law_context}\n" if law_context else ""
    prompt = f"""아래 8개 사전 검토 항목에 대해 이 사업의 해당 여부를 순서대로 판단하라.
반드시 8줄만 출력. 헤더·번호·항목명 없이. | 구분. 셀 내 | 사용 금지.
판단값: "해당" / "확인 필요" / "해당 없음" 중 하나만.
출력 형식: [판단]|[이 사업 기준 판단 근거 1줄]
5번 법령 저촉 여부: 아래 검색된 법령명이 있으면 법령명 명시. 조문 번호 임의 생성 금지.
{law_block}
{ctx}

판단 순서:
1. 보안성 검토 — 개인정보(이름·주소·생체 등) 처리 포함 여부
2. 개인정보 영향평가 — 5만명 이상 처리 여부
3. 지방재정투자심사 — 총사업비 10억 원 이상 여부
4. 의회 의결 — 공유재산 취득·처분 포함 여부
5. 법령 저촉 여부 — 검색된 관련 법령명 명시(조문번호 금지), 없으면 확인 필요
6. 타 부서 협의 — 협의 필요 부서 언급
7. 환경영향평가 — 개발·시설 사업 해당 여부
8. 안전영향평가 — 다중이용시설 포함 여부"""
    return call_claude_with_retry(prompt)


def _inject_url_column(table_text: str, url_map: dict) -> str:
    """Claude 출력 파이프 표에 '법령 링크' 열을 마지막에 추가."""
    import re as _re
    lines_out = []
    header_done = False
    for line in table_text.strip().splitlines():
        s = line.strip()
        if not s or _re.match(r'^[\s|:\-]+$', s):
            continue
        if not header_done:
            lines_out.append(s.rstrip("|") + "|법령 링크")
            header_done = True
        else:
            parts = s.strip("|").split("|")
            law_name = parts[0].strip() if parts else ""
            url = url_map.get(law_name, "")
            lines_out.append(s.rstrip("|") + f"|{url}")
    return "\n".join(lines_out)


def generate_section_law(inputs: dict, law_context: str = "", laws: list = None) -> str:
    url_map = {}
    if laws:
        from law_search import make_url_map
        url_map = make_url_map(laws)

    # API 결과 없으면 고정 안내 행 반환 (AI 생성 없음)
    if not law_context:
        return (
            "법령명|관련 조문|주요 내용 요약|적용 여부|법령 링크\n"
            "검색 결과 없음|담당자 직접 확인 필요"
            "|사업 관련 법령 전체를 담당자가 직접 검토 필요|확인 필요|"
        )

    ctx = _build_context(inputs)
    prompt = f"""[3. 관련 법령 검토] 섹션을 아래 4열 표 형식으로만 출력하라. 헤더 포함. 셀 내 | 금지.

[절대 준수 규칙]
- "법령명" 열: 아래 "API 검색 법령 목록"에 있는 법령명만 사용. 목록에 없는 법령 추가 금지.
- "관련 조문" 열: 반드시 "담당자 직접 확인 필요" 고정 출력. 제X조·제X항 등 조문 번호 임의 생성 절대 금지.
- "주요 내용 요약" 열: 해당 법령의 일반적 목적과 이 사업과의 관련성을 1줄로 서술.
- "적용 여부" 열: "해당 가능성 있음" / "검토 필요" / "해당 없음" 중 하나만 출력.
- URL 열은 출력하지 않는다 (시스템이 자동 추가).

{law_context}

{ctx}

법령명|관련 조문|주요 내용 요약|적용 여부
(API 목록 내 법령명 그대로)|담당자 직접 확인 필요|(법령 목적 + 이 사업 관련성 1줄)|(판단)"""
    result = call_claude_with_retry(prompt)
    return _inject_url_column(result, url_map)


def generate_section_04_cases(inputs: dict) -> str:
    ctx = _build_context(inputs)

    # Tavily 실시간 검색 (실패/미설정 시 빈 문자열)
    from tavily_search import search_cases
    search_ctx = search_cases(
        inputs.get("project_name", ""),
        inputs.get("project_type", ""),
    )

    if search_ctx:
        search_block = (
            "\n[실시간 검색 결과 — 아래 내용을 우선 반영하여 표 작성. "
            "검색에 없는 수치·사례는 단정 금지]\n"
            + search_ctx
            + "\n"
        )
        source_note = "검색 결과 기반 (Tavily). 수치·출처는 담당자 확인 권고."
    else:
        search_block = ""
        source_note = "AI 훈련 데이터 기반. 담당자 직접 확인 권고."

    prompt = f"""[3. 타 지자체 유사 사례] 섹션을 아래 표 형식으로만 출력하라. 헤더 포함, 셀 내 | 금지.
시·군명을 명시하되 확인되지 않은 수치는 "~로 알려져 있음" 표현 사용.
{search_block}
{ctx}

지자체|사업명(유사사업)|주요 내용|성과 및 시사점
(지자체명)|(유사 사업명)|(핵심 추진 방식 1줄)|(성과 또는 교훈 1줄)
(지자체명)|(유사 사업명)|(핵심 추진 방식 1줄)|(성과 또는 교훈 1줄)
(지자체명)|(유사 사업명)|(핵심 추진 방식 1줄)|(성과 또는 교훈 1줄)
고양특례시 시사점|(-)|(인구 107만/3개구 특성 반영 적용 방향 1줄)|({source_note})"""
    return call_claude_with_retry(prompt)


def generate_section_08_qa(inputs: dict) -> str:
    ctx = _build_context(inputs)
    prompt = f"""[4. 의회 예상 질의·대응논리] 섹션을 아래 표 형식으로만 출력하라. 헤더 포함, 셀 내 | 금지.
미확인 수치·사례 단정 금지.

{ctx}

질의|대응 논리|보완 필요
(예산 타당성 질의 1줄)|(대응 1-2줄)|(준비 사항 1줄)
(사업 필요성 질의 1줄)|(대응 1-2줄)|(준비 사항 1줄)
(중복성 질의 1줄)|(대응 1-2줄)|(준비 사항 1줄)
(성과 측정 질의 1줄)|(대응 1-2줄)|(준비 사항 1줄)
(사후 관리 질의 1줄)|(대응 1-2줄)|(준비 사항 1줄)"""
    return call_claude_with_retry(prompt)


def generate_section_09_summary(inputs: dict) -> str:
    ctx = _build_context(inputs)
    prompt = f"""[5. 종합 검토의견] 섹션을 아래 표 형식으로만 출력하라. 헤더 포함, 셀 내 | 금지.

{ctx}

항목|내용
종합 판단|(적정 / 조건부 적정 / 재검토 필요 / 부적정 중 하나)
판단 근거|(3-5개 핵심, /로 구분)
핵심 관리 포인트|(3개 이내, /로 구분)
검토자 의견|본 보고서는 Claude AI 자동 생성 초안. 법령·사례 담당자 직접 확인 필요."""
    return call_claude_with_retry(prompt)


# ─── 위험도 추출 ─────────────────────────────────────────────────────────────


def extract_risk_level(summary_text: str) -> str:
    if not summary_text:
        return "중"
    if "부적정" in summary_text:
        return "고"
    if "재검토 필요" in summary_text:
        return "고"
    if "조건부 적정" in summary_text:
        return "중"
    if "적정" in summary_text:
        return "저"
    return "중"


# ─── Multi-Agent 실행 ────────────────────────────────────────────────────────


def generate_full_report(inputs: dict) -> dict:
    # 법령 검색 사전 실행 (병렬 섹션 생성 전, 약 2-3초)
    law_context = ""
    try:
        from law_search import search_laws, format_for_context
        laws = search_laws(
            inputs.get("project_name", ""),
            inputs.get("project_type", ""),
        )
        law_context = format_for_context(laws)
    except Exception as exc:
        logger.warning("법령 검색 사전 실행 실패: %s", exc)

    section_funcs = [
        ("section_01",  "사업 개요",             generate_section_01_overview),
        ("section_02",  "위험성 분석",            lambda i: generate_section_02_risk(i, law_context)),
        ("section_03",  "사전 검토 체크리스트",    lambda i: generate_precheck(i, law_context)),
        ("section_law", "관련 법령 검토",          lambda i: generate_section_law(i, law_context, laws)),
        ("section_04",  "타 지자체 유사 사례",     generate_section_04_cases),
        ("section_08",  "의회 예상 질의·대응논리", generate_section_08_qa),
        ("section_09",  "종합 검토의견",           generate_section_09_summary),
    ]

    sections: dict = {}
    with ThreadPoolExecutor(max_workers=len(section_funcs)) as executor:
        future_to_meta = {
            executor.submit(func, inputs): (key, label)
            for key, label, func in section_funcs
        }
        for future in as_completed(future_to_meta):
            key, label = future_to_meta[future]
            try:
                sections[key] = future.result()
            except Exception as exc:
                sections[key] = f"[{label} 생성 오류]\n{type(exc).__name__}: {exc}"

    return sections
