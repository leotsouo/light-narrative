# 版本與文本比較模板（期末簡報用）

以下表格可在期末報告或簡報中填入實際數字。部分「早期版本」為開發歷程描述，請依你的實際迭代調整。

---

## 1. 版本改善比較

| 評估項目 | 早期版本 | 目前版本 | 改善狀況 |
|---|---:|---:|---|
| chunk_count | 1 | 5～9 | 已能按章節／場景切分 |
| world_rule_violation | 過多重複 | 2（fog_bell） | 去重與否定句過濾改善 |
| character_state_conflict | 有誤判 | 1 | 死亡／活動證據更精準 |
| unique_item_conflict | 可抓但重複 | 1 | 指示代詞誤抓降低 |
| character_consistency_drift | 0 | 1 | 已能抓限制 vs 高能力行為 |
| world_setting_conflict | 0 | 1 | 已能抓重大設定反轉 |
| item_location_conflict | 持有人解析差 | 可選輸出 | 代名詞未解析時不輸出 |

---

## 2. 測試文本泛化比較

| 測試文本 | 目的 | 預期衝突數 | 系統抓到（TP） | 誤判（FP） | 漏抓（FN） |
|---|---|---:|---:|---:|---:|
| fog_bell（有矛盾） | 測是否能抓到真正問題 | 6 | 6 | 0 | 0 |
| clean_story（無矛盾） | 測 false positive | 0 | 0 | 0 | 0 |
| renamed_story（換名） | 測泛化能力 | 5 | 5 | 2 | 0 |

> 數字來源：`evaluation/results/*_eval.json`（以 `generate_demo_reports.py` 產生之報告評估）

---

## 3. 指標說明（簡報口條）

| 指標 | 簡單中文說明 |
|------|--------------|
| **TP** | 抓對的衝突 |
| **FP** | 誤判的衝突（系統多報） |
| **FN** | 漏抓的衝突（標準答案有、系統沒抓到） |
| **Precision** | 系統抓出來的衝突中，有多少是真的 |
| **Recall** | 真正存在的衝突中，系統抓到了多少 |
| **F1** | Precision 與 Recall 的綜合分數 |
| **Duplicate Rate** | 同一衝突被重複輸出的比例 |
| **Evidence Accuracy** | 系統附上的原文證據是否合理 |

---

## 4. fog_bell 指標摘要（可直接貼簡報）

| Metric | Value |
|---|---:|
| Precision | 1.0 |
| Recall | 1.0 |
| F1 | 1.0 |
| Duplicate Rate | 0.0 |
| Evidence Accuracy | 1.0 |

---

## 5. renamed_story 指標摘要

| Metric | Value |
|---|---:|
| Precision | 0.714 |
| Recall | 1.0 |
| F1 | 0.833 |
| Duplicate Rate | 0.0 |
| Evidence Accuracy | 1.0 |

**False Positives（示例）：**

- `item_location_conflict`：物品持有人不一致（額外抓到，未列入 ground truth）
- `character_consistency_drift`：角色能力漂移（額外抓到）

---

## 6. 使用方式

1. 從 Streamlit 匯出 JSON，或執行 `python evaluation/generate_demo_reports.py`
2. 執行 `python evaluation/evaluate_report.py ...`
3. 將 `evaluation/results/*_eval.json` 的數字填入上表
