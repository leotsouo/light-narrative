"""Generate export JSON reports for evaluation demos."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.report_agent import generate_full_report
from src.chunker import chunk_document
from src.storage import export_report_json, init_db

FOG_BELL = """## 第零章：世界規則

亡者不能被任何法術復活。

這是唯一能打開地下鐘室的銀鑰匙。

夜晚敲鐘會讓黑霧靠近城牆。

城市中央的「晨鐘」維持著霧城與外界的界線。

---

## 第一章：設定

艾琳聰明、謹慎，害怕黑暗，也不擅長戰鬥。

---

## 第二章：死亡

羅恩停止呼吸。艾琳確認他已經死亡。

---

## 第三章：矛盾

羅恩從她身後說：「不要害怕，孩子。」

拍賣會上又出現一把銀色鑰匙。

艾琳拉下鐘繩，讓晨鐘在夜半響起。鐘聲傳遍全城，黑霧卻沒有靠近，反而迅速退回城外。

真正的晨鐘早在十年前就被移到城外的修道院，城內的晨鐘只是複製品。

羅恩從火焰中走出，再次復活。

---

## 第四章：漂移

她原本膽小，不擅長戰鬥，卻在入口處徒手擊倒兩名守衛，動作熟練得像訓練多年的士兵。
"""


def main() -> None:
    init_db()
    samples_dir = ROOT / "samples"
    exports_dir = ROOT / "data" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    fog_path = samples_dir / "fog_bell_story.txt"
    fog_path.write_text(FOG_BELL, encoding="utf-8")

    for name in (
        "fog_bell_story.txt",
        "sample_conflict_story.txt",
        "sample_clean_story.txt",
        "sample_renamed_conflict_story.txt",
    ):
        text = (samples_dir / name).read_text(encoding="utf-8")
        project_id = name.replace(".txt", "")
        chunks = chunk_document(text, "d1", project_id, strategy="auto")
        report, _ = generate_full_report(project_id, chunks, use_llm=False, persist=False)
        out = exports_dir / f"report_{project_id}.json"
        export_report_json(report, out)
        print(f"Wrote {out} ({len(report.conflicts)} conflicts)")


if __name__ == "__main__":
    main()
