from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts


def test_character_consistency_drift() -> None:
    text = """## 第一章：設定
小明聰明謹慎，害怕黑暗，也不擅長戰鬥。

## 第三章：行動
小明在入口處徒手擊倒兩名守衛，動作熟練得像訓練多年的士兵。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    assert any(c.conflict_type == "character_consistency_drift" for c in conflicts)
