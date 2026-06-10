# 輕量智敘 — 系統評估模組

本資料夾提供期末專題用的**簡化版 evaluation module**，用來比對：

- 系統輸出的 JSON 報告（`data/exports/report_*.json`）
- 人工標準答案（`evaluation/ground_truth/*.json`）

**此模組不影響主系統 Streamlit app**，也不會修改 production conflict rules。

---

## 為什麼需要 evaluation？

期末展示不能只有「系統有輸出」，還需要回答：

- 抓對了多少？（TP）
- 誤判了多少？（FP）
- 漏抓了多少？（FN）
- 證據是否合理？

透過 ground truth 比對，可以呈現**版本改善**、**文本泛化**與**證據品質**。

---

## 名詞解釋

### TP / FP / FN

| 指標 | 意思 |
|------|------|
| **TP（True Positive）** | 系統抓對的衝突 |
| **FP（False Positive）** | 系統誤判、但 ground truth 沒有的衝突 |
| **FN（False Negative）** | ground truth 有，但系統漏抓的衝突 |

### Precision / Recall / F1

| 指標 | 公式 | 白話 |
|------|------|------|
| **Precision** | TP / (TP + FP) | 系統抓出來的衝突中，有多少是真的？ |
| **Recall** | TP / (TP + FN) | 真正存在的衝突中，系統抓到了多少？ |
| **F1** | 2PR / (P + R) | Precision 與 Recall 的綜合指標 |

### Duplicate Rate

若多筆 system conflicts 有相同 `(conflict_type, related_entities, title)`，多出的筆數視為 duplicate。

```text
Duplicate Rate = duplicate_count / total_predicted
```

### Evidence Accuracy

在 TP 中，檢查 `evidence_a` / `evidence_b` 是否：

- 非空
- 不是「死亡相關描述」等假句
- 長度合理
- 包含 ground truth 關鍵詞，或像原文句子

```text
Evidence Accuracy = evidence_correct_count / total_matched_tp
```

---

## Ground Truth 格式

見 `evaluation/ground_truth/fog_bell_gt.json` 範例：

```json
{
  "sample_name": "fog_bell",
  "description": "測試用途說明",
  "expected_conflicts": [
    {
      "id": "gt_001",
      "conflict_type": "character_state_conflict",
      "title": "角色死亡後仍活動",
      "related_entities": ["羅恩"],
      "must_include_keywords": ["羅恩", "死亡", "說"]
    }
  ]
}
```

**注意：**

- ground truth **可以**包含 sample 角色名（如羅恩、銀鑰匙）
- `src/` production code **不可以**硬寫這些名稱

---

## 如何建立 ground truth

1. 準備測試文本（見 `samples/`）
2. 人工閱讀文本，列出應被抓到的衝突
3. 為每筆衝突填 `conflict_type`（需與系統輸出一致）
4. 填 `related_entities` 與 `must_include_keywords` 供簡化比對

目前已提供三份：

| 檔案 | 對應文本 |
|------|----------|
| `fog_bell_gt.json` | `samples/fog_bell_story.txt`（霧城之鐘） |
| `clean_story_gt.json` | `samples/sample_clean_story.txt` |
| `renamed_story_gt.json` | `samples/sample_renamed_conflict_story.txt` |

---

## 如何取得 system report JSON

### 方法 A：Streamlit 匯出

1. `streamlit run app.py`
2. 上傳文本 → 執行分析 → 衝突報告 → **匯出 JSON 報告**
3. 檔案會寫入 `data/exports/report_*.json`

### 方法 B：離線產生 demo 報告

```bash
python evaluation/generate_demo_reports.py
```

會產生：

- `data/exports/report_fog_bell_story.json`
- `data/exports/report_sample_conflict_story.json`
- `data/exports/report_sample_clean_story.json`
- `data/exports/report_sample_renamed_conflict_story.json`

---

## 如何執行 evaluate_report.py

```bash
python evaluation/evaluate_report.py \
  --report data/exports/report_fog_bell_story.json \
  --ground-truth evaluation/ground_truth/fog_bell_gt.json \
  --out evaluation/results/fog_bell_eval.json \
  --summary evaluation/results/fog_bell_summary.md
```

參數：

| 參數 | 說明 |
|------|------|
| `--report` | 系統輸出的 JSON 報告 |
| `--ground-truth` | 人工標準答案 |
| `--out` | 評估結果 JSON |
| `--summary` | （選用）Markdown 摘要 |

---

## 如何解讀結果

- **Precision 高**：誤判少，但可能漏抓
- **Recall 高**：漏抓少，但可能誤判多
- **F1**：兩者平衡
- **Duplicate Rate 高**：同一衝突重複輸出，需改善去重
- **Evidence Accuracy 低**：雖抓到類型，但證據品質不佳

### 目前初步結果（demo 報告）

| 文本 | TP | FP | FN | Precision | Recall | F1 |
|------|---:|---:|---:|---:|---:|---:|
| fog_bell | 6 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| clean_story | 0 | 0 | 0 | — | — | — |
| renamed_story | 5 | 2 | 0 | 0.714 | 1.0 | 0.833 |

---

## 限制

- matching 是**簡化版**（關鍵詞 + 實體交集），不是正式學術 benchmark
- 同一 `world_rule_violation` 內不同子類型，靠 keywords 區分
- 不評估抽取層 entity 正確率
- 不影響主系統，只用於期末報告與開發驗收

---

## 相關檔案

| 檔案 | 用途 |
|------|------|
| `evaluate_report.py` | CLI 評估主程式 |
| `generate_demo_reports.py` | 離線產生 demo JSON 報告 |
| `ground_truth/` | 人工標準答案 |
| `results/` | 評估輸出 |
| `results/comparison_template.md` | 簡報比較表模板 |
| `results/final_presentation_evaluation_summary.md` | 期末簡報摘要 |
