# 輕量智敘 — 期末版狀態盤點

本文件依**實際程式碼與測試**整理期末 MVP 狀態（2026-06 交付版）。

## 已完成

| 項目 | 說明 |
|------|------|
| Streamlit 單頁 UI | 專題簡介、專案管理、上傳、分析、知識圖、報告、JSON 匯出、限制提示 |
| SQLite 持久化 | 專案、文本、分塊、抽取結果、報告 |
| 文本 ingest | `.txt` / `.md` / `.docx` 上傳解析 |
| 分塊 | auto / chapter / scene / fixed |
| Heuristic 抽取 | 角色、地點、物品、世界規則、事件 |
| Ollama 可選抽取 | 未連線自動 fallback |
| 7 條 conflict rules | 見 `src/conflict_rules.py` |
| 狀態追蹤 | 角色死亡／活動、物品持有人 |
| 知識圖 | NetworkX + PyVis（含 fallback） |
| JSON 匯出 | `data/exports/` |
| 展示樣本 | `samples/` 三份文本 |
| 測試 | 26 個 pytest（含 rule2、rule4、clean story、renamed story、smoke tests） |
| 期末文件 | README、DEMO_SCRIPT、LIMITATIONS、FINAL_STATUS |

## 部分完成

| 項目 | 現況 |
|------|------|
| 物品名抽取 | 已加 `extract_object_names_from_text` 與過濾，複雜長句仍可能誤抽 |
| 代詞解析 | rule4 已拒絕「自己 vs 自己」；複雜指涉仍有限 |
| 時間相關衝突 | 有死亡後活動、夜間敲鐘等規則，**無**獨立時間線引擎 |
| HuggingFace | 介面 stub 存在，**未實作** |
| LLM 抽取 | Ollama 可用；品質依模型與文本而異，非本次評分核心 |

## 未完成（刻意不在期末範圍）

- FastAPI 後端
- HuggingFace / Transformers 本地推理
- 獨立時間線引擎與視圖
- 自動修稿
- 登入、雲端部署、多人協作
- 多頁路由、大型架構重構

## 期末展示建議講法

1. **開場**：本地優先、規則驅動、可選 Ollama 的中文敘事一致性檢查工具  
2. **核心價值**：7 條 deterministic rules + 可讀報告 + 知識圖  
3. **誠實邊界**：不是 LLM 判衝突、不是自動改稿、不是完整時間線引擎  
4. **加分演示**：`sample_clean_story.txt` 零衝突 + `sample_renamed_conflict_story.txt` 泛化

## 可展示流程

```text
建立專案 → 上傳 sample_conflict_story.txt → 分塊預覽
→ 執行分析（展示統計）→ 衝突報告（2～3 條重點）
→ 知識圖 → JSON 匯出 → clean story 零衝突
```

詳細步驟見 [DEMO_SCRIPT.md](DEMO_SCRIPT.md)。

## 風險與備案

| 風險 | 備案 |
|------|------|
| 現場 Streamlit 啟動失敗 | 先跑 `python -m pytest tests/ -q`；展示已匯出 JSON |
| Ollama 未安裝 | 維持 heuristic 預設，側欄不勾選 LLM |
| PyVis 渲染失敗 | 展示 JSON stats + fallback 提示 |
| 某文本誤報 | 說明 heuristic 限制；改用 `sample_clean_story.txt` 對照 |
| 老師問「為何不用 LLM 判斷衝突」 | 強調 deterministic 可重現、可測試、適合 MVP |

## 驗收指令

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
streamlit run app.py
```

預期：測試全綠；Streamlit 可啟動；三份 sample 可分別得到「多條衝突 / 零衝突 / 換名仍衝突」。
