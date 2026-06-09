"""保留：以 sample_story.txt 跑完整流程。"""

from pathlib import Path

from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts

SAMPLE = Path(__file__).parent / "sample_story.txt"


def test_sample_story_pipeline() -> None:
    text = SAMPLE.read_text(encoding="utf-8")
    chunks = chunk_document(text, "d1", "p1", strategy="auto")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    assert len(chunks) >= 1
    assert len(conflicts) >= 1
