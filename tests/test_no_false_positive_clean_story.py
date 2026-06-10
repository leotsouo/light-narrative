from pathlib import Path

from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sample_clean_story.txt"


def test_no_false_positive_clean_story() -> None:
    text = SAMPLE.read_text(encoding="utf-8")
    chunks = chunk_document(text, "d1", "p1", strategy="auto")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    assert conflicts == []
