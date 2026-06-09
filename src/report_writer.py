"""產生分析報告。"""
from __future__ import annotations

from src.schemas import AnalysisReport, ConflictReport, ExtractionResult


def build_report(
    project_id: str,
    extraction: ExtractionResult,
    conflicts: list[ConflictReport],
    chunk_count: int = 0,
) -> AnalysisReport:
    entity_counts = {
        "characters": len(extraction.characters),
        "locations": len(extraction.locations),
        "objects": len(extraction.objects),
        "events": len(extraction.events),
        "world_rules": len(extraction.world_rules),
    }

    conflict_counts: dict[str, int] = {
        "world_rule_violation": 0,
        "character_state_conflict": 0,
        "unique_item_conflict": 0,
        "item_location_conflict": 0,
        "character_consistency_drift": 0,
        "world_setting_conflict": 0,
    }
    for c in conflicts:
        conflict_counts[c.conflict_type] = conflict_counts.get(c.conflict_type, 0) + 1

    return AnalysisReport(
        project_id=project_id,
        chunk_count=chunk_count,
        entity_counts=entity_counts,
        conflict_counts=conflict_counts,
        conflicts=conflicts,
    )


def conflicts_to_dataframe(conflicts: list[ConflictReport]):
    import pandas as pd

    rows = [
        {
            "類型": c.conflict_type,
            "嚴重度": c.severity,
            "標題": c.title,
            "說明": c.explanation,
            "建議": c.suggested_fix,
            "相關實體": ", ".join(c.related_entities),
        }
        for c in conflicts
    ]
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["類型", "嚴重度", "標題", "說明", "建議", "相關實體"]
    )
