"""完整分析流程。"""
from __future__ import annotations

from src.agents.character_agent import merge_characters
from src.agents.conflict_agent import run_conflict_detection
from src.agents.entity_agent import (
    extract_entities_heuristic,
    extract_entities_llm,
    merge_extractions,
)
from src.agents.event_agent import extract_events_heuristic, extract_events_llm
from src.llm_client import BaseLLMProvider, get_llm
from src.report_writer import build_report
from src.schemas import AnalysisReport, Chunk, ExtractionResult
from src.state_tracker import derive_character_states, derive_item_states
from src.storage import save_extraction, save_report


def run_extraction(
    chunks: list[Chunk],
    use_llm: bool = False,
    llm: BaseLLMProvider | None = None,
) -> ExtractionResult:
    if use_llm:
        llm = llm or get_llm()
        if not llm.is_available():
            use_llm = False

    parts: list[ExtractionResult] = []
    for chunk in chunks:
        if use_llm and llm:
            ent = extract_entities_llm(chunk, llm)
            events = extract_events_llm(chunk, llm)
        else:
            ent = extract_entities_heuristic(chunk)
            events = extract_events_heuristic(chunk)
        ent.events = events
        parts.append(ent)

    merged = merge_extractions(parts)
    merged.characters = merge_characters(merged.characters)

    from src.narrative_patterns import filter_person_names

    character_names = filter_person_names([c.name for c in merged.characters])
    merged.characters = [c for c in merged.characters if c.name in character_names]
    merged.character_states = derive_character_states(chunks, character_names)
    merged.item_states = derive_item_states(
        chunks,
        items=[o.name for o in merged.objects],
        rules=merged.world_rules,
        events=merged.events,
    )
    return merged


def generate_full_report(
    project_id: str,
    chunks: list[Chunk],
    use_llm: bool = False,
    llm: BaseLLMProvider | None = None,
    persist: bool = True,
) -> tuple[AnalysisReport, ExtractionResult]:
    extraction = run_extraction(chunks, use_llm=use_llm, llm=llm)
    conflicts = run_conflict_detection(extraction)
    report = build_report(
        project_id=project_id,
        extraction=extraction,
        conflicts=conflicts,
        chunk_count=len(chunks),
    )
    if persist:
        save_extraction(project_id, extraction)
        save_report(report)
    return report, extraction
