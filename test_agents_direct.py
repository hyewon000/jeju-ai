# -*- coding: utf-8 -*-
"""agents.py 직접 호출 테스트 — 고양시 사업 예시"""
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import agents
import db

inputs = {
    "project_name": "고양시 노인 AI 디지털 교육 지원 사업",
    "project_type": "복지",
    "target": "고양시 거주 만 65세 이상 노인",
    "budget": 180000000,
    "period": "2025년 4월 ~ 2025년 12월",
    "description": (
        "디지털 소외 계층인 고양시 노인을 대상으로 스마트폰·키오스크·AI 서비스 활용 능력을 "
        "향상시키기 위한 교육 지원 사업. 덕양구·일산동구·일산서구 3개 구별 복지관 및 노인복지센터를 "
        "거점으로 지정하여 집합 교육과 찾아가는 방문 교육을 병행 운영함. "
        "교육 내용: 스마트폰 기본 조작, 카카오톡·유튜브 활용, 공공 키오스크 사용법, "
        "AI 음성인식 서비스(챗GPT 등) 기초 활용. "
        "강사 인력은 지역 디지털 사회혁신 기관과 협약을 통해 조달할 계획이며, "
        "연간 교육 목표 인원은 3,000명, 수료율 80% 이상을 성과지표로 설정함. "
        "교육 수료자에게는 수료증 및 스마트기기 활용 지원금(1인 5만원) 지급 예정."
    ),
}

SECTION_NAMES = {
    "section_01": "1. 사업 개요",
    "section_02": "2. 위험성 분석",
    "section_03": "3. 의회 공격요소",
    "section_04": "4. 타 지자체 유사 사례",
    "section_05": "5. 법령/조례 검토",
    "section_06": "6. 예산 타당성 검토",
    "section_07": "7. 추진 체크리스트",
    "section_08": "8. 의회 예상 질의·대응논리",
    "section_09": "9. 종합 검토의견",
}

print("=" * 60)
print("보고서 생성 시작:", inputs["project_name"])
print("=" * 60)

start = time.time()
sections = agents.generate_full_report(inputs)
elapsed = time.time() - start

print(f"\n생성 완료: {elapsed:.1f}초\n")

errors = []
for key, label in SECTION_NAMES.items():
    content = sections.get(key, "")
    ok = bool(content) and "[생성 오류]" not in content
    status = "OK" if ok else "오류"
    length = len(content) if content else 0
    print(f"  [{status}] {label} — {length}자")
    if not ok:
        errors.append(label)

risk_level = agents.extract_risk_level(sections.get("section_09", ""))
print(f"\n위험도: {risk_level}")

db.init_db()
rid = db.save_report(inputs, sections, risk_level)
print(f"DB 저장: report_id = {rid}")

txt = db.get_report_text(rid)
out_file = "test_report_output.txt"
with open(out_file, "w", encoding="utf-8") as f:
    f.write(txt)
print(f"TXT 저장: {out_file} ({len(txt)}자)\n")

print("=" * 60)
if errors:
    print(f"경고: {len(errors)}개 섹션 오류 — {errors}")
else:
    print("모든 섹션 정상 생성 완료")
print("=" * 60)

print("\n[종합 검토의견 요약]")
summary = sections.get("section_09", "")
print(summary[:800] + ("..." if len(summary) > 800 else ""))
