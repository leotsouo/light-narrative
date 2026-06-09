from src.chunker import chunk_document
from src.agents.report_agent import run_extraction
from src.conflict_rules import detect_all_conflicts


def test_unique_item_conflict() -> None:
    text = """## 第零章：設定
銀鑰匙是唯一能打開地下鐘室的物品。

## 第一章：備用
城防隊有備用鑰匙。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    assert any(c.conflict_type == "unique_item_conflict" for c in conflicts)

