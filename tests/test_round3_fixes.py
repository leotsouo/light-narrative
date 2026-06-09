"""第三輪修正：unique item、active evidence、drift、setting 合併。"""

from src.agents.report_agent import run_extraction
from src.chunker import chunk_document
from src.conflict_rules import detect_all_conflicts
from src.narrative_patterns import (
    canonicalize_setting_entity,
    is_valid_post_death_active_evidence,
    normalize_unique_item_name,
)


def test_normalize_unique_item_rejects_demonstrative() -> None:
    assert normalize_unique_item_name("這") == ""
    assert normalize_unique_item_name("此") == ""
    name = normalize_unique_item_name("這是唯一能打開地下鐘室的銀鑰匙")
    assert name == "銀鑰匙" or name.endswith("鑰匙")
    assert normalize_unique_item_name("銀鑰匙被說成唯一鑰匙") == "銀鑰匙"


def test_unique_item_not_demonstrative_conflict() -> None:
    text = """## 第零章：設定
這是唯一能打開地下鐘室的銀鑰匙。

## 第一章：備用
拍賣會上又出現一把銀色鑰匙。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    unique = [c for c in conflicts if c.conflict_type == "unique_item_conflict"]
    assert len(unique) == 1
    assert unique[0].related_entities[0] not in ("這", "此", "該")
    assert "被說成" not in unique[0].related_entities[0]


def test_post_death_active_evidence_excludes_fallen() -> None:
    assert not is_valid_post_death_active_evidence(
        "羅恩", "她衝下樓梯，看見羅恩倒在鐘室門口，胸口被黑色碎片刺穿。"
    )
    assert is_valid_post_death_active_evidence(
        "羅恩", "羅恩從她身後說：「不要害怕，孩子。」"
    )


def test_character_state_evidence_b_must_be_active() -> None:
    text = """## 第一章：死亡
羅恩停止呼吸。艾琳確認他已經死亡。

## 第二章：倒地
她衝下樓梯，看見羅恩倒在鐘室門口。

## 第三章：又出現
羅恩從她身後說：「不要害怕，孩子。」
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = [
        c for c in detect_all_conflicts(extraction) if c.conflict_type == "character_state_conflict"
    ]
    assert len(conflicts) == 1
    assert "倒在" not in conflicts[0].evidence_b
    assert "身後說" in conflicts[0].evidence_b or "說" in conflicts[0].evidence_b


def test_character_drift_pronoun_combat() -> None:
    text = """## 第一章：設定
艾琳聰明、謹慎，害怕黑暗，也不擅長戰鬥。

## 第三章：行動
她原本膽小，不擅長戰鬥，卻在入口處徒手擊倒兩名守衛，動作熟練得像訓練多年的士兵。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = detect_all_conflicts(extraction)
    assert any(c.conflict_type == "character_consistency_drift" for c in conflicts)


def test_world_setting_merges_generic_entity() -> None:
    entities = ["鐘", "晨鐘", "霧城"]
    assert canonicalize_setting_entity("鐘", entities) == "晨鐘"
    text = """## 第零章：設定
城市中央的「晨鐘」維持著霧城與外界的界線。

## 第六章：反轉
真正的晨鐘早在十年前就被移到城外的修道院，城內的晨鐘只是複製品。
"""
    chunks = chunk_document(text, "d1", "p1", strategy="chapter")
    extraction = run_extraction(chunks, use_llm=False)
    conflicts = [c for c in detect_all_conflicts(extraction) if c.conflict_type == "world_setting_conflict"]
    assert len(conflicts) == 1
    assert conflicts[0].related_entities[0] == "晨鐘"
