# 期末簡報 — 評估摘要

## 1. 為什麼要做比較報告？

我們不是只展示「系統有輸出衝突」，而是進一步用**人工標準答案**比對系統輸出的 JSON 報告，檢查系統是否真的抓到正確衝突。

透過 TP、FP、FN、Precision、Recall 與 Evidence Accuracy，可以觀察：

- 抓取能力（Recall）
- 誤判情況（Precision / FP）
- 漏抓情況（FN）
- 證據品質（Evidence Accuracy）
- 重複輸出（Duplicate Rate）

---

## 2. 我們比較了什麼？

| 比較面向 | 內容 |
|----------|------|
| **版本改善** | 早期單塊文本 vs 目前章節分塊、去重、證據過濾 |
| **有矛盾文本** | `fog_bell_story.txt`（霧城之鐘，6 類核心衝突） |
| **無矛盾文本** | `sample_clean_story.txt`（測 false positive） |
| **換名文本** | `sample_renamed_conflict_story.txt`（測泛化） |

---

## 3. 使用哪些指標？

- **TP / FP / FN**
- **Precision / Recall / F1**
- **Duplicate Rate**
- **Evidence Accuracy**

評估腳本：`evaluation/evaluate_report.py`

---

## 4. 目前初步結果

### fog_bell（霧城之鐘）

| 指標 | 數值 |
|------|-----:|
| 預期衝突 | 6 |
| 系統輸出 | 6 |
| TP | 6 |
| FP | 0 |
| FN | 0 |
| Precision | 1.0 |
| Recall | 1.0 |
| F1 | 1.0 |
| Evidence Accuracy | 1.0 |

→ 在主要展示文本上，六類核心衝突皆能對上標準答案。

### clean_story（無矛盾）

| 指標 | 數值 |
|------|-----:|
| 預期衝突 | 0 |
| 系統輸出 | 0 |
| FP | 0 |

→ 文本雖含「死亡」「唯一」「不能」等詞，但未亂報衝突。

### renamed_story（換名）

| 指標 | 數值 |
|------|-----:|
| 預期衝突 | 5 |
| 系統輸出 | 7 |
| TP | 5 |
| FP | 2 |
| FN | 0 |
| Precision | 0.714 |
| Recall | 1.0 |
| F1 | 0.833 |

→ 換名後仍能抓到主要衝突（Recall 1.0），但多抓到 2 條（item_location、character_drift），Precision 約 0.71。

---

## 5. 目前限制

1. **matching 是簡化版**：靠 `conflict_type` + 關鍵詞 + 實體交集，不是論文級 benchmark
2. **ground truth 需人工維護**：只覆蓋 sample 文本，不代表任意長篇小說
3. **FP 可能來自合理但不在標準答案內的偵測**（如 renamed 的 item_location）
4. **evaluation 不修改主系統**，只做離線驗收

---

## 6. 後續如何改善

- 擴充 ground truth 到更多文本類型
- 降低 renamed 文本的 FP（例如 item_location 是否應納入標準答案）
- 改善 character drift 的角色名解析（目前偶有代詞誤抽）
- 若未來有版本迭代，可固定同一套 ground truth 重跑 evaluation 追蹤 F1 變化

---

## 7. 期末現場可執行指令

```bash
# 1. 產生 demo 報告（若尚未匯出）
python evaluation/generate_demo_reports.py

# 2. 評估霧城之鐘
python evaluation/evaluate_report.py \
  --report data/exports/report_fog_bell_story.json \
  --ground-truth evaluation/ground_truth/fog_bell_gt.json \
  --out evaluation/results/fog_bell_eval.json \
  --summary evaluation/results/fog_bell_summary.md
```

結果 JSON：`evaluation/results/fog_bell_eval.json`  
Markdown 摘要：`evaluation/results/fog_bell_summary.md`
