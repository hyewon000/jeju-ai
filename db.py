"""
db.py — SQLite 보고서 이력 관리 모듈
"""

import json
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "reports.db"))

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT    NOT NULL,
    project_type TEXT,
    target       TEXT,
    budget       INTEGER,
    period       TEXT,
    description  TEXT,
    section_01   TEXT,
    section_02   TEXT,
    section_03   TEXT,
    section_04   TEXT,
    section_05   TEXT,
    section_06   TEXT,
    section_07   TEXT,
    section_08   TEXT,
    section_09   TEXT,
    risk_level   TEXT    NOT NULL DEFAULT '중',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
)
"""

SECTION_LABELS = [
    ("section_01",  "1. 사업 개요"),
    ("section_02",  "2. 위험성 분석"),
    ("section_law", "3. 관련 법령 검토"),
    ("section_04",  "4. 타 지자체 유사 사례"),
    ("section_08",  "5. 의회 예상 질의·대응논리"),
    ("section_09",  "6. 종합 검토의견"),
]


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(CREATE_TABLE_SQL)
        for col_sql in [
            "ALTER TABLE reports ADD COLUMN checklist_data TEXT",
            "ALTER TABLE reports ADD COLUMN checklist_risk TEXT",
            "ALTER TABLE reports ADD COLUMN section_law TEXT",
        ]:
            try:
                conn.execute(col_sql)
            except sqlite3.OperationalError:
                pass
        conn.commit()


def save_report(inputs: dict, sections: dict, risk_level: str = "중") -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """INSERT INTO reports
               (project_name, project_type, target, budget, period, description,
                section_01, section_02, section_03, section_04, section_05,
                section_06, section_07, section_08, section_09,
                section_law, risk_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                inputs.get("project_name"),
                inputs.get("project_type"),
                inputs.get("target"),
                inputs.get("budget"),
                inputs.get("period"),
                inputs.get("description"),
                sections.get("section_01"),
                sections.get("section_02"),
                sections.get("section_03"),
                sections.get("section_04"),
                sections.get("section_05"),
                sections.get("section_06"),
                sections.get("section_07"),
                sections.get("section_08"),
                sections.get("section_09"),
                sections.get("section_law"),
                risk_level,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_report_list(page: int = 1, per_page: int = 20) -> list[dict]:
    offset = (page - 1) * per_page
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT id, project_name, project_type, risk_level, created_at
               FROM reports ORDER BY id DESC LIMIT ? OFFSET ?""",
            (per_page, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def get_total_count() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) FROM reports").fetchone()
    return row[0] if row else 0


def get_report_by_id(report_id: int) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    return dict(row) if row else None


def update_checklist(report_id: int, checklist_data: dict, checklist_risk: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE reports SET checklist_data = ?, checklist_risk = ? WHERE id = ?",
            (json.dumps(checklist_data, ensure_ascii=False), checklist_risk, report_id),
        )
        conn.commit()


def delete_report(report_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()


def get_report_text(report_id: int) -> str | None:
    report = get_report_by_id(report_id)
    if not report:
        return None

    sep = "=" * 60
    budget = report.get("budget")
    budget_str = f"{int(budget):,}원" if budget else "미기재"

    lines = [
        "정책사업 사전검토 보고서",
        sep,
        f"사업명    : {report['project_name']}",
        f"사업 유형 : {report.get('project_type') or '-'}",
        f"주요 대상 : {report.get('target') or '-'}",
        f"총 예산   : {budget_str}",
        f"사업 기간 : {report.get('period') or '-'}",
        f"위험도    : {report.get('risk_level') or '-'}",
        f"생성일시  : {report.get('created_at') or '-'}",
        sep,
    ]

    for key, label in SECTION_LABELS:
        content = report.get(key) or "(미생성)"
        lines.append(f"\n[{label}]\n{content}")

    lines.append(f"\n{sep}")
    lines.append("※ 본 보고서는 Claude AI가 자동 생성한 내부 검토 초안입니다.")
    lines.append("  법령 조문 번호와 타 지자체 사례는 담당자가 직접 확인 후 활용하십시오.")
    lines.append("  최종 결정은 담당 부서 및 결재권자 권한입니다.")

    return "\n".join(lines)
