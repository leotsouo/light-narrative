"""Compare system JSON reports against ground truth for final project evaluation."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

FAKE_EVIDENCE_PHRASES = (
    "死亡相關描述",
    "安葬相關描述",
    "活動相關描述",
    "無證據",
    "相關描述",
)

NOTES = [
    "This is a simplified evaluation for final project reporting, not a formal benchmark."
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip())


def safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 3)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def conflict_blob(conflict: dict[str, Any]) -> str:
    parts = [
        conflict.get("title", ""),
        conflict.get("claim_a", ""),
        conflict.get("claim_b", ""),
        conflict.get("evidence_a", ""),
        conflict.get("evidence_b", ""),
        " ".join(conflict.get("related_entities", [])),
    ]
    return "".join(parts)


def canonical_conflict_key(conflict: dict[str, Any]) -> tuple[str, tuple[str, ...], str]:
    entities = tuple(sorted(normalize_text(x) for x in conflict.get("related_entities", []) if x))
    return (
        conflict.get("conflict_type", ""),
        entities,
        normalize_text(conflict.get("title", "")),
    )


def keyword_hits(keywords: list[str], text: str) -> list[str]:
    return [kw for kw in keywords if kw and kw in text]


def entity_overlap(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    exp = {normalize_text(x) for x in expected.get("related_entities", []) if x}
    pred = {normalize_text(x) for x in predicted.get("related_entities", []) if x}
    if not exp or not pred:
        return False
    for a in exp:
        for b in pred:
            if a == b or a in b or b in a:
                return True
    return False


def evidence_text(predicted: dict[str, Any]) -> str:
    return f"{predicted.get('evidence_a', '')}{predicted.get('evidence_b', '')}"


def looks_like_source_sentence(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    cjk = sum(1 for ch in stripped if "\u4e00" <= ch <= "\u9fff")
    latin = sum(1 for ch in stripped if ch.isalpha() and ord(ch) < 128)
    return cjk >= 5 or latin >= 10


def is_reasonable_evidence(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    ea = (predicted.get("evidence_a") or "").strip()
    eb = (predicted.get("evidence_b") or "").strip()
    if not ea or not eb:
        return False
    for fake in FAKE_EVIDENCE_PHRASES:
        if fake in ea or fake in eb:
            return False
    if not looks_like_source_sentence(ea) and not looks_like_source_sentence(eb):
        return False
    keywords = expected.get("must_include_keywords", [])
    ev = evidence_text(predicted)
    if keywords and keyword_hits(keywords, ev):
        return True
    return looks_like_source_sentence(ea) and looks_like_source_sentence(eb)


def match_pair(expected: dict[str, Any], predicted: dict[str, Any]) -> tuple[bool, str, int]:
    if expected.get("conflict_type") != predicted.get("conflict_type"):
        return False, "conflict_type mismatch", 0

    blob = conflict_blob(predicted)
    keywords = expected.get("must_include_keywords", [])
    hits = keyword_hits(keywords, blob)
    overlap = entity_overlap(expected, predicted)
    ev_hits = keyword_hits(keywords, evidence_text(predicted))

    if not overlap and not hits:
        return False, "no entity overlap or keyword hit", 0
    if keywords and not ev_hits:
        return False, "keywords not found in evidence", 0

    score = len(hits) + (2 if overlap else 0) + len(ev_hits)
    reason_parts = ["conflict_type matched"]
    if overlap:
        reason_parts.append("entity overlap")
    if hits:
        reason_parts.append(f"{len(hits)} keyword(s) matched")
    return True, " and ".join(reason_parts), score


def count_duplicates(predicted: list[dict[str, Any]]) -> int:
    if not predicted:
        return 0

    by_key: dict[tuple[str, tuple[str, ...], str], int] = {}
    for conflict in predicted:
        key = canonical_conflict_key(conflict)
        by_key[key] = by_key.get(key, 0) + 1

    duplicate_by_key = sum(count - 1 for count in by_key.values() if count > 1)
    return duplicate_by_key


def evaluate(report: dict[str, Any], ground_truth: dict[str, Any]) -> dict[str, Any]:
    expected = ground_truth.get("expected_conflicts", [])
    predicted = report.get("conflicts", [])

    candidate_pairs: list[tuple[int, int, int, str]] = []
    for gi, gt in enumerate(expected):
        for pi, pred in enumerate(predicted):
            ok, reason, score = match_pair(gt, pred)
            if ok:
                candidate_pairs.append((score, gi, pi, reason))

    candidate_pairs.sort(key=lambda item: (-item[0], item[1], item[2]))

    matched_gt: set[int] = set()
    matched_pred: set[int] = set()
    matched_conflicts: list[dict[str, Any]] = []
    evidence_correct = 0

    for _score, gi, pi, reason in candidate_pairs:
        if gi in matched_gt or pi in matched_pred:
            continue
        gt = expected[gi]
        pred = predicted[pi]
        matched_gt.add(gi)
        matched_pred.add(pi)
        if is_reasonable_evidence(gt, pred):
            evidence_correct += 1
        matched_conflicts.append(
            {
                "ground_truth_id": gt.get("id"),
                "system_conflict_id": pred.get("id"),
                "conflict_type": pred.get("conflict_type"),
                "match_reason": reason,
                "evidence_ok": is_reasonable_evidence(gt, pred),
            }
        )

    tp = len(matched_conflicts)
    fp = len(predicted) - tp
    fn = len(expected) - tp

    duplicate_count = count_duplicates(predicted)
    total_predicted = len(predicted)

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    if precision is None or recall is None or (precision + recall) == 0:
        f1: float | None = None
    else:
        f1 = round(2 * precision * recall / (precision + recall), 3)

    duplicate_rate = 0.0 if total_predicted == 0 else round(duplicate_count / total_predicted, 3)
    evidence_accuracy = 0.0 if tp == 0 else round(evidence_correct / tp, 3)

    missed_conflicts = [
        {
            "ground_truth_id": expected[gi].get("id"),
            "title": expected[gi].get("title"),
            "conflict_type": expected[gi].get("conflict_type"),
        }
        for gi in range(len(expected))
        if gi not in matched_gt
    ]

    false_positives = [
        {
            "system_conflict_id": predicted[pi].get("id"),
            "title": predicted[pi].get("title"),
            "conflict_type": predicted[pi].get("conflict_type"),
        }
        for pi in range(len(predicted))
        if pi not in matched_pred
    ]

    return {
        "sample_name": ground_truth.get("sample_name", ""),
        "report_path": "",
        "ground_truth_path": "",
        "total_expected": len(expected),
        "total_predicted": total_predicted,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision if precision is not None else 0.0,
        "recall": recall if recall is not None else 0.0,
        "f1": f1 if f1 is not None else 0.0,
        "duplicate_count": duplicate_count,
        "duplicate_rate": duplicate_rate,
        "evidence_accuracy": evidence_accuracy,
        "matched_conflicts": matched_conflicts,
        "missed_conflicts": missed_conflicts,
        "false_positives": false_positives,
        "notes": NOTES,
    }


def render_summary(result: dict[str, Any]) -> str:
    sample = result.get("sample_name", "unknown")
    lines = [
        f"# Evaluation Summary: {sample}",
        "",
        "## Overview",
        "",
        "本次評估使用人工標準答案與系統輸出的 JSON 報告進行比對。",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total Expected | {result.get('total_expected', 0)} |",
        f"| Total Predicted | {result.get('total_predicted', 0)} |",
        f"| TP | {result.get('tp', 0)} |",
        f"| FP | {result.get('fp', 0)} |",
        f"| FN | {result.get('fn', 0)} |",
        f"| Precision | {result.get('precision', 0)} |",
        f"| Recall | {result.get('recall', 0)} |",
        f"| F1 | {result.get('f1', 0)} |",
        f"| Duplicate Count | {result.get('duplicate_count', 0)} |",
        f"| Duplicate Rate | {result.get('duplicate_rate', 0)} |",
        f"| Evidence Accuracy | {result.get('evidence_accuracy', 0)} |",
        "",
        "## Interpretation",
        "",
        "系統已能抓到多數核心衝突，但仍可能存在部分誤判與漏抓。"
        "後續可針對 false positive、evidence selection 與 character consistency drift 進行改善。",
        "",
    ]

    missed = result.get("missed_conflicts", [])
    lines.extend(["## Missed Conflicts", ""])
    if missed:
        for item in missed:
            lines.append(f"- {item.get('conflict_type')}：{item.get('title')}")
    else:
        lines.append("- （無）")
    lines.append("")

    fps = result.get("false_positives", [])
    lines.extend(["## False Positives", ""])
    if fps:
        for item in fps:
            lines.append(f"- {item.get('conflict_type')}：{item.get('title')}")
    else:
        lines.append("- （無）")
    lines.append("")

    lines.extend(
        [
            "## Limitations",
            "",
            "此評估為期末專題展示用的簡化比對方式，並非正式學術級 benchmark。",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Light Narrative report against ground truth.")
    parser.add_argument("--report", required=True, help="Path to exported system report JSON")
    parser.add_argument("--ground-truth", required=True, help="Path to ground truth JSON")
    parser.add_argument("--out", required=True, help="Path to write evaluation result JSON")
    parser.add_argument("--summary", help="Optional path to write Markdown summary")
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    gt_path = Path(args.ground_truth)
    out_path = Path(args.out)

    report = load_json(report_path)
    ground_truth = load_json(gt_path)
    result = evaluate(report, ground_truth)
    result["report_path"] = str(report_path)
    result["ground_truth_path"] = str(gt_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.summary:
        summary_path = Path(args.summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(render_summary(result), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
