# 정책사업 사전검토 보고서 자동 생성 시스템

고양특례시 정책사업의 의회 심의 사전검토를 자동화하는 웹 애플리케이션.  
담당자가 사업 기본 정보를 입력하면 Claude AI Multi-Agent가 6개 섹션으로 구성된 정책 원페이퍼 보고서를 자동 생성합니다.

---

## 주요 기능

- 사업명·유형·예산·기간·내용 입력 폼
- Claude API 기반 6개 섹션 보고서 자동 생성 (병렬 처리)
- Tavily 실시간 검색으로 타 지자체 유사 사례 수집
- 국가법령정보센터 API 연동 관련 법령 자동 검색
- 생성 이력 SQLite 저장 및 조회
- Word(.docx) 다운로드 / 인쇄(PDF) 저장
- 담당자 위험도 체크리스트 AJAX 저장

---

## 보고서 구성

| # | 섹션 |
|---|------|
| ① | 사전 검토 체크리스트 |
| 1 | 사업 개요 |
| 2 | 위험성 분석 |
| 3 | 관련 법령 검토 |
| 4 | 타 지자체 유사 사례 + 예산 비교표 |
| 5 | 의회 예상 질의·대응논리 |
| 6 | 종합 검토의견 |

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | Python 3.11+, Flask 3.x |
| AI | Anthropic Claude API (`claude-sonnet-4-6`) |
| 검색 | Tavily API |
| 법령 | 국가법령정보센터 DRF API |
| DB | SQLite3 |
| 프론트 | Jinja2, HTML5, CSS3 |

---

## 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/<your-username>/jeju-ai.git
cd jeju-ai
```

### 2. 가상환경 생성 및 의존성 설치

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

`.env` 파일을 열어 아래 값을 입력합니다 (필수/선택 구분 참고).

### 4. 앱 실행

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 접속

---

## 환경변수 목록

| 변수명 | 필수 | 설명 | 발급처 |
|--------|------|------|--------|
| `ANTHROPIC_API_KEY` | **필수** | Claude API 인증키 | [console.anthropic.com](https://console.anthropic.com) |
| `SECRET_KEY` | **필수** | Flask 세션 암호화 키 (32자 이상 랜덤 문자열) | 직접 생성 |
| `CLAUDE_MODEL` | 선택 | 사용할 Claude 모델 ID | 기본값: `claude-sonnet-4-6` |
| `FLASK_DEBUG` | 선택 | 디버그 모드 (`true`/`false`) | 기본값: `false` |
| `TAVILY_API_KEY` | 선택 | 타 지자체 사례 실시간 검색 | [app.tavily.com](https://app.tavily.com) |
| `LAW_API_KEY` | 선택 | 국가법령정보센터 법령 검색 | [open.law.go.kr](https://open.law.go.kr) — 회원 ID가 키 |

> 선택 항목은 미설정 시 해당 기능이 생략되거나 "확인 필요"로 표시됩니다. 앱 자체는 정상 동작합니다.

---

## SECRET_KEY 생성 방법

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 보안 주의사항

- `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 업로드되지 않습니다.
- API 키를 코드에 직접 작성하지 마세요.
- 운영 환경에서는 `FLASK_DEBUG=false`로 설정하세요.
- `reports.db`(생성된 보고서 DB)는 Git에 포함되지 않습니다.

---

## 테스트

```bash
# 문법 검사
python -m py_compile app.py agents.py db.py

# 의존성 충돌 확인
pip check

# 임포트 테스트
python -c "import app; print('OK')"
```

---

## 라이선스

내부 업무용 소프트웨어입니다.
