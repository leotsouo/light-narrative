"""Tests for evaluation/evaluate_report.py"""
from __future__ import annotations

import json
from pathlib import Path

from evaluation.evaluate_report import evaluate, is_reasonable_evidence, match_pair

ROOT = Path(__file__).resolve().parent.parent


def test_match_pair_requires_conflict_type() -> None:
    gt = {
        "conflict_type": "unique_item_conflict",
        "related_entities": ["銀鑰匙"],
        "must_include_keywords": ["銀鑰匙", "唯一"],
    }
    pred = {
        "conflict_type": "character_state_conflict",
        "title": "角色死亡後仍活動",
        "related_entities": ["羅恩"],
        "evidence_a": "羅恩停止呼吸。",
        "evidence_b": "羅恩從她身後說話。",
    }
    ok, reason, _score = match_pair(gt, pred)
    assert not ok
    assert "mismatch" in reason


def test_evaluate_fog_bell_report() -> None:
    report = json.loads((ROOT / "data/exports/report_fog_bell_story.json").read_text(encoding="utf-8"))
    gt = json.loads((ROOT / "evaluation/ground_truth/fog_bell_gt.json").read_text(encoding="utf-8"))
    result = evaluate(report, gt)
    assert result["total_expected"] == 6
    assert result["tp"] >= 5
    assert result["recall"] >= 0.8


def test_evaluate_clean_story_no_false_positives() -> None:
    report = json.loads((ROOT / "data/exports/report_sample_clean_story.json").read_text(encoding="utf-8"))
    gt = json.loads((ROOT / "evaluation/ground_truth/clean_story_gt.json").read_text(encoding="utf-8"))
    result = evaluate(report, gt)
    assert result["total_expected"] == 0
    assert result["total_predicted"] == 0
    assert result["tp"] == 0
    assert result["fp"] == 0


def test_evidence_rejects_fake_phrase() -> None:
    gt = {"must_include_keywords": ["羅恩"]}
    pred = {
        "evidence_a": "死亡相關描述",
        "evidence_b": "活動相關描述",
    }
    assert not is_reasonable_evidence(gt, pred)
