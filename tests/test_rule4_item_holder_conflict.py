from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts


def test_rule4_item_holder_conflict() -> None:
    text = """## 第一章：持有
陳安把銀鑰匙掛在腰間。

## 第二章：轉移
周嵐手中握著銀鑰匙，向城門走去。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = [
        c for c in detect_all_conflicts(extraction) if c.conflict_type == "item_location_conflict"
    ]
    assert len(conflicts) == 1
    assert "陳安" in conflicts[0].claim_a
    assert "周嵐" in conflicts[0].claim_b
    assert "自己" not in conflicts[0].claim_a
    assert "自己" not in conflicts[0].claim_b


def test_rule4_skips_unresolved_self_holder() -> None:
    text = """## 第一章
銀鑰匙掛在自己腰間。

## 第二章
銀鑰匙仍掛在自己身上。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = [
        c for c in detect_all_conflicts(extraction) if c.conflict_type == "item_location_conflict"
    ]
    assert conflicts == []
