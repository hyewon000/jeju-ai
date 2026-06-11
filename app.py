"""
app.py — 정책사업 사전검토 보고서 자동 생성 시스템 (Flask)
"""

import os
import re

import json

from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from dotenv import load_dotenv

import html as html_lib

import agents
import db
import word_export

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24))
app.config["TEMPLATES_AUTO_RELOAD"] = True

ALLOWED_TYPES = ["복지", "인프라", "문화관광", "경제창업", "환경", "행정서비스", "기타"]
FORBIDDEN_CHARS = re.compile(r"[<>|;'\"&\\]")
PER_PAGE = 20

PRECHECK_ITEMS = [
    ("보안성 검토",      "개인정보 처리 포함 시"),
    ("개인정보 영향평가", "5만명 이상 처리 시"),
    ("지방재정투자심사",  "총사업비 10억 이상 시"),
    ("의회 의결",        "공유재산 취득·처분 시"),
    ("법령 저촉 여부",   "모든 사업 확인 필요"),
    ("타 부서 협의",     "관련 부서 협의 필요"),
    ("환경영향평가",     "개발·시설 사업 해당 시"),
    ("안전영향평가",     "다중이용시설 포함 시"),
]

CHECKLIST_GROUPS = [
    ("예산·재정", [
        ("budget_large",    "총 예산이 5억 원 이상"),
        ("budget_local",    "국비 지원 없이 전액 시비"),
        ("budget_increase", "전년도 대비 50% 이상 증액"),
    ]),
    ("사업 성격", [
        ("new_project",     "신규 사업 (전년도 미추진)"),
        ("no_legal_basis",  "법령·조례 근거 미확보 상태"),
        ("duplicate",       "타 부서·기관 유사 사업 존재"),
    ]),
    ("추진 역량", [
        ("no_staff",        "전담 인력 미확보"),
        ("high_outsource",  "외부 위탁 비율 70% 이상"),
        ("no_post_mgmt",    "사후관리 계획 미수립"),
    ]),
    ("의회 리스크", [
        ("bias_risk",       "특정 지역·계층 편중 가능성"),
        ("no_kpi",          "구체적 성과지표 미설정"),
        ("low_execution",   "전년도 유사사업 집행률 70% 미만"),
    ]),
]

SECTION_LABELS = [
    ("section_01",  "1. 사업 개요"),
    ("section_02",  "2. 위험성 분석"),
    ("section_law", "3. 관련 법령 검토"),
    ("section_04",  "4. 타 지자체 유사 사례"),
    ("section_08",  "5. 의회 예상 질의·대응논리"),
    ("section_09",  "6. 종합 검토의견"),
]


# ─── 템플릿 필터 ─────────────────────────────────────────────────────────────

@app.template_filter("table_html")
def table_html_filter(text: str) -> str:
    """파이프(|) 구분 텍스트를 HTML 표로 변환. 빈 줄로 구분된 복수 블록 지원."""
    if not text:
        return '<p class="text-muted">(미생성)</p>'
    if "[생성 오류]" in text:
        return f'<p class="text-danger">{html_lib.escape(text)}</p>'

    # 빈 줄로 블록 분리
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        s = raw_line.strip()
        if not s:
            if current:
                blocks.append(current)
                current = []
        else:
            if re.match(r'^[\s|:\-]+$', s):  # 마크다운 구분선 제거
                continue
            current.append(s)
    if current:
        blocks.append(current)

    if not blocks:
        return '<p class="text-muted">(미생성)</p>'

    parts: list[str] = []
    for block in blocks:
        parts.append(_render_block(block))

    return "".join(parts)


def _render_block(lines: list[str]) -> str:
    """단일 블록(연속 줄) → HTML. 캡션 줄([...]) 처리 포함."""
    caption = ""
    table_lines = []

    for line in lines:
        if line.startswith("[") and line.endswith("]") and "|" not in line:
            caption = line[1:-1]  # 대괄호 제거
        else:
            table_lines.append(line)

    # 표 형식 아닌 블록 → pre
    if not table_lines or "|" not in table_lines[0]:
        pre = f'<pre class="section-pre">{html_lib.escape(chr(10).join(lines))}</pre>'
        return pre

    rows_html: list[str] = []
    for i, line in enumerate(table_lines):
        line = line.strip("|").strip()
        raw_cols = [c.strip() for c in line.split("|")]
        raw_cols = [c for c in raw_cols if c != ""]
        if not raw_cols:
            continue
        if i == 0:
            cells = "".join(f"<th>{html_lib.escape(c)}</th>" for c in raw_cols)
            rows_html.append(f"<tr>{cells}</tr>")
        else:
            cell_parts = []
            for c in raw_cols:
                if c.startswith("https://") or c.startswith("http://"):
                    safe_url = html_lib.escape(c)
                    cell_parts.append(
                        f'<td><a href="{safe_url}" target="_blank" '
                        f'rel="noopener noreferrer">바로가기</a></td>'
                    )
                else:
                    cell_parts.append(f"<td>{html_lib.escape(c)}</td>")
            rows_html.append(f"<tr>{''.join(cell_parts)}</tr>")

    if not rows_html:
        return f'<pre class="section-pre">{html_lib.escape(chr(10).join(lines))}</pre>'

    cap_html = (
        f'<p class="table-caption">{html_lib.escape(caption)}</p>' if caption else ""
    )
    thead = f"<thead>{rows_html[0]}</thead>"
    tbody = f"<tbody>{''.join(rows_html[1:])}</tbody>" if len(rows_html) > 1 else ""
    return (
        f'<div class="table-wrap">'
        f'{cap_html}'
        f'<table class="report-table">{thead}{tbody}</table>'
        f'</div>'
    )


# ─── DB 초기화 ────────────────────────────────────────────────────────────────

@app.before_request
def _ensure_db():
    db.init_db()


# ─── 입력 검증 ────────────────────────────────────────────────────────────────

def validate_inputs(form) -> tuple[dict, list[str]]:
    errors: list[str] = []

    project_name = form.get("project_name", "").strip()
    if len(project_name) < 2:
        errors.append("사업명은 2자 이상 입력하세요.")
    elif len(project_name) > 100:
        errors.append("사업명은 100자 이내로 입력하세요.")
    elif FORBIDDEN_CHARS.search(project_name):
        errors.append("사업명에 특수문자(<>\"|;&\\')는 사용할 수 없습니다.")

    project_type = form.get("project_type", "").strip()
    if project_type not in ALLOWED_TYPES:
        errors.append("올바른 사업 유형을 선택하세요.")

    description = form.get("description", "").strip()
    if len(description) < 5:
        errors.append("사업 내용은 5자 이상 입력하세요.")
    elif len(description) > 5000:
        errors.append("사업 내용은 5,000자 이내로 입력하세요.")

    budget: int | None = None
    budget_str = form.get("budget", "").strip()
    if budget_str:
        try:
            budget = int(budget_str)
            if budget < 0:
                errors.append("예산은 0 이상의 정수를 입력하세요.")
        except ValueError:
            errors.append("예산은 숫자로만 입력하세요.")

    period = form.get("period", "").strip()[:100]
    target = form.get("target", "").strip()[:100]

    inputs = {
        "project_name": project_name,
        "project_type": project_type,
        "target": target,
        "budget": budget,
        "period": period,
        "description": description,
    }
    return inputs, errors


# ─── 라우팅 ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    total = db.get_total_count()
    return render_template("index.html", allowed_types=ALLOWED_TYPES, total_reports=total)


@app.route("/generate", methods=["POST"])
def generate():
    inputs, errors = validate_inputs(request.form)
    if errors:
        for err in errors:
            flash(err, "error")
        return redirect(url_for("index"))

    try:
        sections = agents.generate_full_report(inputs)
    except Exception as exc:
        app.logger.error("보고서 생성 오류: %s", exc)
        flash(
            "보고서 생성 중 오류가 발생했습니다. "
            "API Key를 확인하거나 잠시 후 다시 시도하세요.",
            "error",
        )
        return redirect(url_for("index"))

    risk_level = agents.extract_risk_level(sections.get("section_09", ""))

    try:
        report_id = db.save_report(inputs, sections, risk_level)
    except Exception as exc:
        app.logger.error("DB 저장 오류: %s", exc)
        flash("보고서는 생성되었으나 저장에 실패했습니다.", "warning")
        report = {**inputs, **sections, "risk_level": risk_level, "id": None}
        return render_template(
            "result.html",
            report=report,
            section_labels=SECTION_LABELS,
        )

    return redirect(url_for("detail", report_id=report_id))


@app.route("/history")
def history():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    reports = db.get_report_list(page=page, per_page=PER_PAGE)
    total = db.get_total_count()
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

    return render_template(
        "history.html",
        reports=reports,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@app.route("/detail/<int:report_id>")
def detail(report_id: int):
    report = db.get_report_by_id(report_id)
    if report is None:
        abort(404)
    checklist_state = {}
    if report.get("checklist_data"):
        try:
            checklist_state = json.loads(report["checklist_data"])
        except (ValueError, TypeError):
            pass
    ai_judgment = _extract_judgment(report.get("section_09", ""))
    precheck_items = _parse_precheck(report.get("section_03", ""))
    return render_template(
        "result.html",
        report=report,
        section_labels=SECTION_LABELS,
        checklist_groups=CHECKLIST_GROUPS,
        checklist_state=checklist_state,
        ai_judgment=ai_judgment,
        precheck_items=precheck_items,
    )


def _parse_precheck(section_03_text: str) -> list[dict]:
    """section_03 텍스트에서 AI 판단/근거를 추출, 항목명은 PRECHECK_ITEMS 고정값 사용."""
    VALID_JUDGMENTS = {"해당", "확인 필요", "해당 없음"}
    fallback = [
        {"item": name, "condition": cond, "ai_judgment": "확인 필요", "ai_reason": ""}
        for name, cond in PRECHECK_ITEMS
    ]
    if not section_03_text:
        return fallback

    # 마크다운 구분선·헤더 제거 후 실제 데이터 행만 추출
    lines = []
    for l in section_03_text.strip().splitlines():
        stripped = l.strip()
        if not stripped:
            continue
        if re.match(r'^[\s|:\-]+$', stripped):  # |---|---| 형태 제거
            continue
        lines.append(stripped)

    results = []
    ai_idx = 0  # AI 출력 행 인덱스
    for name, cond in PRECHECK_ITEMS:
        # 현재 행이 헤더처럼 보이면 건너뜀
        while ai_idx < len(lines):
            parts = [p.strip().strip("|").strip() for p in lines[ai_idx].split("|")]
            parts = [p for p in parts if p]  # 빈 셀 제거
            ai_idx += 1
            if not parts:
                continue
            judgment = parts[0] if parts[0] in VALID_JUDGMENTS else "확인 필요"
            reason = parts[1] if len(parts) > 1 else ""
            results.append({"item": name, "condition": cond,
                            "ai_judgment": judgment, "ai_reason": reason})
            break
        else:
            results.append({"item": name, "condition": cond,
                            "ai_judgment": "확인 필요", "ai_reason": ""})
    return results


def _extract_judgment(section_09_text: str) -> str:
    """section_09 파이프 텍스트에서 '종합 판단' 값을 추출."""
    if not section_09_text:
        return ""
    for line in section_09_text.splitlines():
        if "종합 판단" in line and "|" in line:
            parts = line.split("|")
            if len(parts) >= 2:
                return parts[1].strip()
    return ""


@app.route("/download/<int:report_id>")
def download(report_id: int):
    text = db.get_report_text(report_id)
    if text is None:
        abort(404)
    filename = f"policy_report_{report_id}.txt"
    response = Response(
        text.encode("utf-8"),
        mimetype="text/plain; charset=utf-8",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@app.route("/checklist/<int:report_id>", methods=["POST"])
def save_checklist(report_id: int):
    if db.get_report_by_id(report_id) is None:
        return jsonify({"error": "not found"}), 404
    data = request.get_json(silent=True) or {}
    db.update_checklist(
        report_id,
        data.get("checklist", {}),
        data.get("risk_level", "중"),
    )
    return jsonify({"ok": True})


@app.route("/delete/<int:report_id>", methods=["POST"])
def delete(report_id: int):
    db.delete_report(report_id)
    flash("보고서가 삭제되었습니다.", "info")
    return redirect(url_for("history"))


@app.route("/download-word/<int:report_id>")
def download_word(report_id: int):
    report = db.get_report_by_id(report_id)
    if report is None:
        abort(404)
    try:
        docx_bytes = word_export.generate_word_bytes(report)
    except Exception as exc:
        app.logger.error("Word 생성 오류: %s", exc)
        flash("Word 문서 생성 중 오류가 발생했습니다.", "error")
        return redirect(url_for("detail", report_id=report_id))
    filename = f"policy_report_{report_id}.docx"
    response = Response(
        docx_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ─── 오류 핸들러 ──────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(exc):
    return render_template("error.html", message="페이지를 찾을 수 없습니다."), 404


@app.errorhandler(500)
def server_error(exc):
    return (
        render_template("error.html", message="서버 오류가 발생했습니다. 잠시 후 다시 시도하세요."),
        500,
    )


# ─── 보안 헤더 ────────────────────────────────────────────────────────────────

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# ─── 실행 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)
