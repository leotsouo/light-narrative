from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts
from src.narrative_patterns import filter_person_names
from src.state_tracker import derive_character_states


def test_observer_not_marked_dead() -> None:
    text = """## 第一章：死亡
羅恩停止呼吸。艾琳確認他已經死亡。

## 第二章：又出現
羅恩從她身後說：「不要害怕，孩子。」
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    names = filter_person_names(["羅恩", "艾琳", "立刻"])
    states = derive_character_states(chunks, names)
    dead_chars = {s.character for s in states if s.state in ("dead", "buried")}
    assert "羅恩" in dead_chars
    assert "艾琳" not in dead_chars
    assert "立刻" not in dead_chars


def test_character_state_conflict_dead_then_active() -> None:
    text = """## 第一章：死亡
羅恩停止呼吸。艾琳確認他已經死亡。

## 第二章：又出現
羅恩從她身後說：「不要害怕，孩子。」
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    assert any(c.conflict_type == "character_state_conflict" for c in conflicts)
    assert any(c.related_entities == ["羅恩"] for c in conflicts if c.conflict_type == "character_state_conflict")
