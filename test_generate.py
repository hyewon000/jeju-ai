"""보고서 생성 테스트 스크립트"""
import urllib.request
import urllib.parse
import urllib.error

data = urllib.parse.urlencode({
    "project_name": "고양시 청년 창업 지원 사업",
    "project_type": "경제창업",
    "target": "만 39세 이하 고양시 거주 청년",
    "budget": "300000000",
    "period": "2025년 3월 ~ 2025년 12월",
    "description": (
        "청년 창업자를 대상으로 창업 준비부터 사업화까지 전 과정을 지원하는 사업. "
        "창업 교육 50시간 제공, 전문가 멘토링, 공유 오피스 입주 공간 제공(최대 6개월), "
        "초기 사업화 자금 최대 3천만원 지원 포함. 대상 선정은 서류 심사 및 발표 평가를 통해 "
        "20개 팀 내외를 선발하며, 선발 후 분기별 성과 보고를 통해 지원 지속 여부를 결정함."
    ),
}).encode("utf-8")


class NoRedir(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)
    http_error_301 = http_error_303 = http_error_302


print("POST /generate 요청 중... (약 1~2분 소요)")
opener = urllib.request.build_opener(NoRedir)
req = urllib.request.Request(
    "http://localhost:5000/generate",
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
try:
    resp = opener.open(req, timeout=200)
    print("OK status:", resp.status)
except urllib.error.HTTPError as e:
    location = e.headers.get("Location", "none")
    print(f"응답 코드: {e.code}  →  Location: {location}")

    if e.code == 302 and location and location.startswith("/detail/"):
        report_id = location.split("/")[-1]
        print(f"\n보고서 ID: {report_id}  →  /detail/{report_id} 조회 중...")

        req2 = urllib.request.Request(f"http://localhost:5000/detail/{report_id}")
        try:
            resp2 = urllib.request.urlopen(req2, timeout=30)
            html = resp2.read().decode("utf-8")
            # 섹션 헤더 추출
            import re
            sections = re.findall(r'class="section-header">([^<]+)<', html)
            print(f"\n생성된 섹션 ({len(sections)}개):")
            for s in sections:
                print(f"  ✓ {s.strip()}")

            # 위험도 뱃지 추출
            badge = re.search(r'class="badge badge-\w+">([^<]+)<', html)
            if badge:
                print(f"\n위험도: {badge.group(1).strip()}")

            # 다운로드 테스트
            req3 = urllib.request.Request(f"http://localhost:5000/download/{report_id}")
            resp3 = urllib.request.urlopen(req3, timeout=30)
            txt = resp3.read().decode("utf-8")
            print(f"\nTXT 다운로드: {len(txt)} 자")
            print("\n=== 보고서 앞 200자 미리보기 ===")
            print(txt[:200])
            print("...(이하 생략)...")

            with open("test_report_output.txt", "w", encoding="utf-8") as f:
                f.write(txt)
            print(f"\n전체 보고서 저장: test_report_output.txt")

        except Exception as ex:
            print(f"상세 조회 오류: {ex}")

    elif e.code == 302 and location == "/":
        print("⚠ 검증 실패로 홈으로 리다이렉트됨")
    else:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"응답 본문: {body}")
