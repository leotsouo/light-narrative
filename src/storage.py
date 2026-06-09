"""SQLite 本地儲存。"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from src.config import DB_PATH, DATA_DIR, EXPORTS_DIR, PROJECTS_DIR
from src.schemas import (
    AnalysisReport,
    Chunk,
    Document,
    ExtractionResult,
    Project,
)


def ensure_dirs() -> None:
    for d in (DATA_DIR, PROJECTS_DIR, EXPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                filename TEXT,
                raw_text TEXT,
                uploaded_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                project_id TEXT,
                idx INTEGER,
                title TEXT,
                text TEXT,
                kind TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS extractions (
                project_id TEXT PRIMARY KEY,
                payload TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reports (
                project_id TEXT PRIMARY KEY,
                payload TEXT,
                generated_at TEXT
            );
            """
        )

        # 輕量 migration：新增 chunk metadata 欄位（若缺少）
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
        if "chapter_index" not in cols:
            conn.execute("ALTER TABLE chunks ADD COLUMN chapter_index INTEGER DEFAULT 0")
        if "start_char" not in cols:
            conn.execute("ALTER TABLE chunks ADD COLUMN start_char INTEGER DEFAULT 0")
        if "end_char" not in cols:
            conn.execute("ALTER TABLE chunks ADD COLUMN end_char INTEGER DEFAULT 0")


# --- Projects ---


def create_project(name: str, description: str = "") -> Project:
    project = Project(name=name, description=description)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (project.id, project.name, project.description, project.created_at.isoformat()),
        )
    return project


def list_projects() -> list[Project]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [
        Project(
            id=r["id"],
            name=r["name"],
            description=r["description"] or "",
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in rows
    ]


def get_project(project_id: str) -> Project | None:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not r:
        return None
    return Project(
        id=r["id"],
        name=r["name"],
        description=r["description"] or "",
        created_at=datetime.fromisoformat(r["created_at"]),
    )


# --- Documents ---


def save_document(doc: Document) -> Document:
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO documents
               (id, project_id, filename, raw_text, uploaded_at)
               VALUES (?, ?, ?, ?, ?)""",
            (doc.id, doc.project_id, doc.filename, doc.raw_text, doc.uploaded_at.isoformat()),
        )
    return doc


def get_latest_document(project_id: str) -> Document | None:
    with get_db() as conn:
        r = conn.execute(
            "SELECT * FROM documents WHERE project_id = ? ORDER BY uploaded_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
    if not r:
        return None
    return Document(
        id=r["id"],
        project_id=r["project_id"],
        filename=r["filename"],
        raw_text=r["raw_text"] or "",
        uploaded_at=datetime.fromisoformat(r["uploaded_at"]),
    )


# --- Chunks ---


def save_chunks(chunks: list[Chunk]) -> None:
    if not chunks:
        return
    project_id = chunks[0].project_id
    with get_db() as conn:
        conn.execute("DELETE FROM chunks WHERE project_id = ?", (project_id,))
        conn.executemany(
            """INSERT INTO chunks (id, document_id, project_id, idx, title, text, kind, chapter_index, start_char, end_char)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    c.id,
                    c.document_id,
                    c.project_id,
                    c.index,
                    c.chapter_title,
                    c.text,
                    c.kind,
                    c.chapter_index,
                    c.start_char,
                    c.end_char,
                )
                for c in chunks
            ],
        )


def load_chunks(project_id: str) -> list[Chunk]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE project_id = ? ORDER BY idx",
            (project_id,),
        ).fetchall()
    return [
        Chunk(
            id=r["id"],
            document_id=r["document_id"],
            project_id=r["project_id"],
            index=r["idx"],
            chapter_title=r["title"] or "",
            text=r["text"] or "",
            kind=r["kind"] or "chunk",
            chapter_index=int(r["chapter_index"]) if "chapter_index" in r.keys() else 0,
            start_char=int(r["start_char"]) if "start_char" in r.keys() else 0,
            end_char=int(r["end_char"]) if "end_char" in r.keys() else 0,
        )
        for r in rows
    ]


def clear_project_text(project_id: str, *, clear_analysis: bool = True) -> None:
    """清除專案的上傳文件、文本區塊，並可選清除分析結果。"""
    with get_db() as conn:
        conn.execute("DELETE FROM chunks WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))
        if clear_analysis:
            conn.execute("DELETE FROM extractions WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM reports WHERE project_id = ?", (project_id,))


def delete_project(project_id: str) -> bool:
    """永久刪除專案及其所有資料（文本、分析、報告）。"""
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not exists:
            return False
    clear_project_text(project_id, clear_analysis=True)
    with get_db() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return True


def delete_chunk(project_id: str, chunk_id: str) -> bool:
    """刪除單一文本區塊並重新編號其餘區塊。"""
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM chunks WHERE project_id = ? AND id = ?",
            (project_id, chunk_id),
        )
        if cur.rowcount == 0:
            return False

    remaining = load_chunks(project_id)
    if not remaining:
        return True

    for i, chunk in enumerate(remaining):
        chunk.index = i
    save_chunks(remaining)
    return True


# --- Extractions ---


def save_extraction(project_id: str, result: ExtractionResult) -> None:
    payload = result.model_dump(mode="json")
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO extractions (project_id, payload, updated_at)
               VALUES (?, ?, ?)""",
            (project_id, json.dumps(payload, ensure_ascii=False), datetime.utcnow().isoformat()),
        )


def load_extraction(project_id: str) -> ExtractionResult | None:
    with get_db() as conn:
        r = conn.execute(
            "SELECT payload FROM extractions WHERE project_id = ?", (project_id,)
        ).fetchone()
    if not r:
        return None
    data = json.loads(r["payload"])
    return ExtractionResult.model_validate(data)


# --- Reports ---


def save_report(report: AnalysisReport) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO reports (project_id, payload, generated_at)
               VALUES (?, ?, ?)""",
            (
                report.project_id,
                report.model_dump_json(),
                report.generated_at.isoformat(),
            ),
        )


def load_report(project_id: str) -> AnalysisReport | None:
    with get_db() as conn:
        r = conn.execute(
            "SELECT payload FROM reports WHERE project_id = ?", (project_id,)
        ).fetchone()
    if not r:
        return None
    return AnalysisReport.model_validate_json(r["payload"])


def export_report_json(report: AnalysisReport, path: Path | None = None) -> Path:
    ensure_dirs()
    if path is None:
        path = EXPORTS_DIR / f"report_{report.project_id[:8]}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path
