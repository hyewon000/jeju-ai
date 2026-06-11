# CLAUDE.md — AI 정책 사전검토 및 원페이퍼 보고서 자동 생성 시스템

## 프로젝트 개요

고양시 정책사업의 의회 심의 사전검토를 자동화하는 웹 애플리케이션.
담당자가 사업 기본 정보를 입력하면 Claude API 기반 Multi-Agent가 9개 섹션으로 구성된
정책 원페이퍼 보고서를 자동 생성한다.

## 핵심 기능

- 사업명·유형·예산·기간·내용 입력 폼
- Claude API Multi-Agent를 통한 9개 섹션 보고서 자동 생성
- 생성 이력 SQLite 저장 및 조회
- 보고서 TXT 파일 다운로드
- 의회 공격요소·예상 질의·대응논리 포함

## 보고서 9개 섹션

1. 사업 개요
2. 위험성 분석
3. 의회 공격요소
4. 타 지자체 유사 사례
5. 법령/조례 검토
6. 예산 타당성 검토
7. 추진 체크리스트
8. 의회 예상 질의·대응논리
9. 종합 검토의견

## 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | Python 3.11+, Flask 3.x |
| AI API | Anthropic Claude API (anthropic SDK) |
| DB | SQLite3 (내장 모듈) |
| 프론트엔드 | Jinja2, HTML5, CSS3 (바닐라) |
| 환경변수 | python-dotenv |
| 기본 모델 | claude-sonnet-4-6 |

## 디렉터리 구조

```
jeju-ai/
├── app.py              # Flask 메인 앱, 라우팅
├── agents.py           # Claude API 호출, Multi-Agent 실행
├── db.py               # SQLite 연동
├── templates/
│   ├── base.html       # 공통 레이아웃
│   ├── index.html      # 입력 폼
│   ├── result.html     # 보고서 결과
│   ├── history.html    # 이력 목록
│   └── error.html      # 오류 페이지
├── static/
│   └── style.css       # 스타일시트
├── requirements.txt
├── .env                # 환경변수 (Git 제외)
├── .env.example        # 환경변수 예시 (Git 포함)
├── .gitignore
├── CLAUDE.md           # 이 파일
└── .claude/
    ├── agents/         # Agent 정의
    └── skills/         # Skill 정의
```

## 실행 명령어

```bash
# 1. 가상환경 생성 (최초 1회)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정 (최초 1회)
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
# .env 파일에 ANTHROPIC_API_KEY 입력

# 4. 앱 실행
python app.py

# 5. 브라우저 접속
# http://localhost:5000
```

## 테스트 명령어

```bash
# 문법 검사
python -m py_compile app.py agents.py db.py

# 의존성 충돌 확인
pip check

# 단순 기동 테스트 (5초)
python -c "import app; print('Import OK')"

# 보안 패턴 검사 (API Key 하드코딩 여부)
grep -r "sk-ant-" . --include="*.py"
```

## 코딩 규칙

### 일반
- Python 3.11+ 문법 사용
- 타입 힌트 사용 권장 (함수 인자, 반환값)
- 함수당 최대 50줄, 파일당 최대 300줄 기준
- 주석은 WHY가 불명확한 경우에만 작성

### Flask
- 블루프린트는 기능이 5개 라우트 초과 시 도입 검토
- `abort()` 사용으로 오류 처리 일관성 유지
- 입력 검증은 라우트 함수 초입에서 수행

### SQLite
- SQL 쿼리는 항상 파라미터 바인딩 (`?`) 사용
- f-string SQL 쿼리 절대 금지
- `row_factory = sqlite3.Row` 사용으로 dict 변환

### HTML/CSS
- Jinja2 자동 이스케이프 비활성화 금지
- `| safe` 필터는 신뢰할 수 있는 내부 데이터에만 제한적 사용
- CSS 클래스 기반 스타일링, 인라인 스타일 최소화

## Claude API 사용 규칙

- API Key는 반드시 `os.getenv("ANTHROPIC_API_KEY")`로만 로딩
- 코드에 Key 값 직접 작성 절대 금지
- 사용 모델은 환경변수 `CLAUDE_MODEL`로 제어
- 기본 모델: `claude-sonnet-4-6`
- max_tokens: 섹션당 4096 (조정 필요 시 환경변수로)
- API 호출 실패 시 해당 섹션만 오류 표시, 앱 전체 중단 금지
- Rate Limit 오류 시 지수 백오프 재시도 (최대 2회)

## 보고서 생성 규칙

1. 실제 확인하지 않은 타 지자체 사례를 단정하지 않는다
   → "유사 사례 존재 가능성 있으나 추가 확인 필요"로 표현
2. 법령 조문 번호(제X조 제X항)를 임의로 생성하지 않는다
   → 법률 명칭만 언급하고 "관련 조문 검토 필요" 병기
3. 공문서형 문체를 유지한다 (간결, 객관적, 과장 없음)
4. 단정 표현 대신 "~로 판단됨", "~가능성 있음" 사용
5. 보고서는 내부 검토 초안이며, 최종본은 담당자가 검토 후 사용

## 보안 주의사항

### 필수 준수
- `.env` 파일을 Git에 절대 포함하지 않는다
- `ANTHROPIC_API_KEY` 하드코딩 금지
- `SECRET_KEY` 하드코딩 금지
- `debug=True` 운영 기본값 설정 금지 → `FLASK_DEBUG` 환경변수 사용
- 사용자 입력을 검증 없이 SQL, 파일명, HTML에 사용 금지
- 다운로드 파일명은 ID 기반으로 생성 (사업명 직접 사용 금지)

### 권고 사항
- 운영 환경에서 HTTPS 사용
- `SECRET_KEY`는 최소 32바이트 랜덤 값 사용
- 정기적 API Key 교체
- DB 파일 정기 백업

## 금지사항

| 항목 | 이유 |
|------|------|
| API Key 코드 하드코딩 | Key 노출 시 과금 및 데이터 유출 위험 |
| 미확인 지자체 사례 단정 | 허위 정보로 행정 판단 왜곡 가능 |
| 미확인 법령 조문 번호 생성 | 법적 근거 오인으로 행정 오류 발생 가능 |
| Flask debug=True 운영 기본값 | Werkzeug 디버거로 서버 코드 노출 위험 |
| .env 파일 Git 포함 | API Key, Secret Key 전체 공개 위험 |
| 사업명을 파일명에 직접 사용 | Path Traversal 및 파일명 인젝션 위험 |
| f-string SQL 쿼리 | SQL Injection 취약점 |
| `{{ variable \| safe }}` 무분별 사용 | XSS 취약점 |

## Agent 팀 역할 요약

| Agent | 역할 | 주요 파일 |
|-------|------|----------|
| policy-domain-analyst | 도메인 분석, 위험도 분류 | (분석 결과 → 컨텍스트) |
| flask-backend-engineer | 백엔드 구현 | app.py |
| claude-api-engineer | API 연동, Multi-Agent 실행 | agents.py |
| report-prompt-engineer | 9개 섹션 프롬프트 설계 | agents.py 내 프롬프트 |
| frontend-ui-engineer | HTML/CSS 구현 | templates/, static/ |
| sqlite-data-engineer | DB 설계 및 구현 | db.py |
| qa-reviewer | 전체 품질 검토 | 전체 |
| security-reviewer | 보안 취약점 검토 | 전체 |

## Skill 목록

| Skill | 사용 시점 |
|-------|----------|
| policy-report-generation | 보고서 생성 전체 절차 |
| council-risk-analysis | 섹션 03, 08 생성 시 |
| public-sector-writing-style | 모든 섹션 문체 기준 |
| flask-project-scaffold | 프로젝트 초기 생성 시 |
| report-quality-check | 보고서 완성 후 검증 |
| safe-env-management | 환경변수 및 Key 관리 |
