from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts


def test_rule2_resurrection_violation() -> None:
    text = """## 第零章：規則
亡者不能被任何法術復活。

## 第三章：事件
顧沉從火焰中走出，再次復活。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    hits = [c for c in conflicts if c.conflict_type == "world_rule_violation"]
    assert any("復活" in c.title or "復活" in c.claim_b for c in hits)
