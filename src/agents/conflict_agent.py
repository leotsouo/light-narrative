"""衝突偵測 agent。"""
from __future__ import annotations

from src.conflict_rules import detect_all_conflicts
from src.schemas import ConflictReport, ExtractionResult


def run_conflict_detection(extraction: ExtractionResult) -> list[ConflictReport]:
    return detect_all_conflicts(extraction)
