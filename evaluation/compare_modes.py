"""Compare heuristic vs Ollama extraction on the same chunks (期末展示用)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.conflict_agent import run_conflict_detection
from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.config import OLLAMA_DEFAULT_MODEL
from src.llm_client import get_llm
from src.report_writer import build_report
from src.schemas import Chunk, ConflictReport, ExtractionResult

NOTES = [
    "Extraction may differ between modes; conflict detection always uses the same deterministic rules.",
    "Ollama 未連線時，ollama 欄位為空並標記 skipped.",
    "This comparison is for demonstration, not a formal benchmark.",
]


def entity_counts(extraction: ExtractionResult) -> dict[str, int]:
    return {
        "characters": len(extraction.characters),
        "locations": len(extraction.locations),
        "objects": len(extraction.objects),
        "events": len(extraction.events),
        "world_rules": len(extraction.world_rules),
    }


def conflict_counts(conflicts: list[ConflictReport]) -> dict[str, int]:
    counts: dict[str, int] = {
        "world_rule_violation": 0,
        "character_state_conflict": 0,
        "unique_item_conflict": 0,
        "item_location_conflict": 0,
        "character_consistency_drift": 0,
        "world_setting_conflict": 0,
    }
    for c in conflicts:
        counts[c.conflict_type] = counts.get(c.conflict_type, 0) + 1
    return counts


def conflict_key(conflict: ConflictReport) -> tuple[str, str, tuple[str, ...]]:
    entities = tuple(sorted(conflict.related_entities))
    return (conflict.conflict_type, conflict.title.strip(), entities)


def summarize_conflicts(conflicts: list[ConflictReport]) -> list[dict[str, Any]]:
    return [
        {
            "conflict_type": c.conflict_type,
            "severity": c.severity,
            "title": c.title,
            "related_entities": c.related_entities,
        }
        for c in conflicts
    ]


def report_snapshot(
    project_id: str,
    extraction: ExtractionResult,
    conflicts: list[ConflictReport],
    chunk_count: int,
    mode: str,
) -> dict[str, Any]:
    report = build_report(project_id, extraction, conflicts, chunk_count=chunk_count)
    return {
        "mode": mode,
        "entity_counts": entity_counts(extraction),
        "conflict_total": len(conflicts),
        "conflict_counts": conflict_counts(conflicts),
        "conflicts_preview": summarize_conflicts(conflicts[:8]),
    }


def compare_conflict_sets(
    heuristic: list[ConflictReport],
    ollama: list[ConflictReport],
) -> dict[str, Any]:
    heur_keys = {conflict_key(c) for c in heuristic}
    ollama_keys = {conflict_key(c) for c in ollama}
    shared = heur_keys & ollama_keys
    only_heuristic = heur_keys - ollama_keys
    only_ollama = ollama_keys - heur_keys
    return {
        "shared_count": len(shared),
        "only_heuristic_count": len(only_heuristic),
        "only_ollama_count": len(only_ollama),
        "only_heuristic_titles": [k[1] for k in sorted(only_heuristic)],
        "only_ollama_titles": [k[1] for k in sorted(only_ollama)],
    }


def entity_deltas(heur: dict[str, int], ollama: dict[str, int]) -> dict[str, int]:
    keys = set(heur) | set(ollama)
    return {k: ollama.get(k, 0) - heur.get(k, 0) for k in sorted(keys)}


def compare_extraction_modes(
    chunks: list[Chunk],
    *,
    project_id: str = "mode_compare",
    model: str = OLLAMA_DEFAULT_MODEL,
) -> dict[str, Any]:
    if not chunks:
        raise ValueError("需要至少一個文本區塊才能比較。")

    heur_extraction = run_extraction(chunks, use_llm=False)
    heur_conflicts = run_conflict_detection(heur_extraction)
    heur_snapshot = report_snapshot(
        project_id, heur_extraction, heur_conflicts, len(chunks), "heuristic"
    )

    llm = get_llm(model=model)
    ollama_available = llm.is_available()
    ollama_used = False
    ollama_snapshot: dict[str, Any] | None = None
    overlap: dict[str, Any] | None = None
    deltas: dict[str, int] | None = None

    if ollama_available:
        ollama_extraction = run_extraction(chunks, use_llm=True, llm=llm)
        ollama_conflicts = run_conflict_detection(ollama_extraction)
        ollama_used = True
        ollama_snapshot = report_snapshot(
            project_id, ollama_extraction, ollama_conflicts, len(chunks), "ollama"
        )
        overlap = compare_conflict_sets(heur_conflicts, ollama_conflicts)
        deltas = entity_deltas(heur_snapshot["entity_counts"], ollama_snapshot["entity_counts"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "chunk_count": len(chunks),
        "model": model,
        "ollama_available": ollama_available,
        "ollama_used": ollama_used,
        "architecture": {
            "ai_used_for": [
                "entity_extraction",
                "event_extraction",
                "world_rule_extraction",
            ],
            "rule_based_core": [
                "conflict_detection",
                "evidence_matching",
                "json_report_generation",
            ],
            "optional_report_summary": "not_enabled_in_mvp",
        },
        "heuristic": heur_snapshot,
        "ollama": ollama_snapshot,
        "comparison": {
            "entity_deltas": deltas,
            "conflict_overlap": overlap,
            "interpretation": _interpretation(heur_snapshot, ollama_snapshot, overlap),
        },
        "notes": NOTES,
    }


def _interpretation(
    heur: dict[str, Any],
    ollama: dict[str, Any] | None,
    overlap: dict[str, Any] | None,
) -> str:
    if ollama is None:
        return "Ollama 未連線，僅完成 heuristic 抽取；衝突檢核仍由 deterministic rules 執行。"
    shared = overlap["shared_count"] if overlap else 0
    heur_total = heur["conflict_total"]
    ollama_total = ollama["conflict_total"]
    if heur_total == ollama_total == shared:
        return (
            "兩種抽取模式在規則引擎下產生相同衝突集合；"
            "差異主要體現在實體／事件抽取數量。"
        )
    return (
        f"Heuristic 檢出 {heur_total} 筆、Ollama 檢出 {ollama_total} 筆衝突，"
        f"其中 {shared} 筆一致；差異來自抽取結果不同，但判定引擎相同。"
    )


def compare_to_markdown(result: dict[str, Any]) -> str:
    heur = result["heuristic"]
    lines = [
        "# Heuristic vs Ollama 比較報告",
        "",
        f"- 產生時間：{result['generated_at']}",
        f"- chunk_count：{result['chunk_count']}",
        f"- Ollama 模型：{result['model']}",
        f"- Ollama 連線：{'是' if result['ollama_available'] else '否'}",
        "",
        "## 架構說明",
        "",
        "- **AI 輔助**：實體、事件、世界規則抽取",
        "- **Rule-based Core**：衝突偵測、證據比對、JSON 報告",
        "",
        "## 抽取統計",
        "",
        "| 項目 | Heuristic | Ollama | Δ (Ollama − Heuristic) |",
        "|---|---:|---:|---:|",
    ]
    ollama = result.get("ollama") or {}
    ollama_counts = ollama.get("entity_counts", {})
    deltas = (result.get("comparison") or {}).get("entity_deltas") or {}
    for key, val in heur["entity_counts"].items():
        o_val = ollama_counts.get(key, "—")
        delta = deltas.get(key, "—")
        lines.append(f"| {key} | {val} | {o_val} | {delta} |")

    lines.extend(
        [
            "",
            "## 衝突檢核（deterministic rules）",
            "",
            f"- Heuristic 衝突數：{heur['conflict_total']}",
            f"- Ollama 衝突數：{ollama.get('conflict_total', '—')}",
        ]
    )
    overlap = (result.get("comparison") or {}).get("conflict_overlap")
    if overlap:
        lines.extend(
            [
                f"- 兩者一致：{overlap['shared_count']}",
                f"- 僅 Heuristic：{overlap['only_heuristic_count']}",
                f"- 僅 Ollama：{overlap['only_ollama_count']}",
            ]
        )
    interp = (result.get("comparison") or {}).get("interpretation", "")
    if interp:
        lines.extend(["", "## 解讀", "", interp])
    return "\n".join(lines)


def load_chunks_from_project(project_id: str) -> list[Chunk]:
    from src.storage import init_db, load_chunks

    init_db()
    return load_chunks(project_id)


def load_chunks_from_text(text: str, project_id: str, strategy: str = "auto") -> list[Chunk]:
    return chunk_document(text, "compare-doc", project_id, strategy=strategy)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare heuristic vs Ollama extraction modes.")
    parser.add_argument("--project-id", help="Load chunks from SQLite project")
    parser.add_argument("--text-file", type=Path, help="Load text file and chunk on the fly")
    parser.add_argument("--model", default=OLLAMA_DEFAULT_MODEL)
    parser.add_argument("--strategy", default="auto")
    parser.add_argument("--output", type=Path, help="Write JSON result to path")
    parser.add_argument("--markdown", type=Path, help="Write markdown summary to path")
    args = parser.parse_args()

    if not args.project_id and not args.text_file:
        parser.error("請指定 --project-id 或 --text-file")

    if args.project_id:
        chunks = load_chunks_from_project(args.project_id)
        project_id = args.project_id
    else:
        text = args.text_file.read_text(encoding="utf-8")
        project_id = args.text_file.stem
        chunks = load_chunks_from_text(text, project_id, strategy=args.strategy)

    result = compare_extraction_modes(chunks, project_id=project_id, model=args.model)

    out_dir = ROOT / "evaluation" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output or out_dir / f"{project_id}_mode_compare.json"
    md_path = args.markdown or out_dir / f"{project_id}_mode_compare.md"

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(compare_to_markdown(result), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(result["comparison"].get("interpretation", ""))


if __name__ == "__main__":
    main()
