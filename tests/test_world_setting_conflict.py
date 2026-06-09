from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts


def test_world_setting_reversal() -> None:
    text = """## 第零章：設定
城市中央的「聖塔」維持著王國與外界的界線。

## 第六章：反轉
真正的聖塔早在十年前就被移到城外的修道院，城內的聖塔只是複製品。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    assert any(c.conflict_type == "world_setting_conflict" for c in conflicts)
