from pathlib import Path

from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sample_renamed_conflict_story.txt"


def test_renamed_story_generalization() -> None:
    text = SAMPLE.read_text(encoding="utf-8")
    chunks = chunk_document(text, "d1", "p1", strategy="auto")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    types = {c.conflict_type for c in conflicts}
    assert "character_state_conflict" in types
    assert "unique_item_conflict" in types
    assert "world_rule_violation" in types
    assert "character_consistency_drift" in types
    assert not any("陳安" in c.related_entities for c in conflicts)
    assert not any("銀鑰匙" in c.related_entities for c in conflicts)
