from src.chunker import chunk_document
from src.agents.report_agent import run_extraction
from src.conflict_rules import detect_all_conflicts


def test_world_rule_violation_night_bell() -> None:
    text = """## 第零章：規則
夜晚敲鐘會讓黑霧靠近城牆。

## 第一章：事件
她拉下鐘繩，讓晨鐘在夜半響起。鐘聲傳遍全城，黑霧卻沒有靠近，反而迅速退回城外。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    assert any(c.conflict_type == "world_rule_violation" for c in conflicts)

