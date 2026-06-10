# 輕量智敘 — 期末展示操作腳本

本文件提供可照著進行的 Demo 流程，約 8～12 分鐘。

## 事前準備

1. 確認已安裝依賴：`pip install -r requirements.txt`
2. 確認測試通過：`python -m pytest tests/ -q`
3. 準備展示文本：`samples/sample_conflict_story.txt`
4. （選用）若需展示 Ollama：先啟動 `ollama serve`；否則維持預設 heuristic 即可

---

## 步驟 1：啟動系統

在專案根目錄執行：

```bash
streamlit run app.py
```

瀏覽器開啟 Streamlit 頁面後，向老師說明：

> 這是「輕量智敘」，本地優先的中文敘事一致性檢查 MVP。衝突偵測以 7 條 deterministic rules 為主，Ollama 只是可選的抽取輔助。

---

## 步驟 2：建立或選擇專案

1. 在左側側欄輸入專案名稱，例如「期末展示」
2. 按「建立專案」
3. 確認側欄顯示「預設使用規則／heuristic 抽取，無需 Ollama」

---

## 步驟 3：上傳展示文本

1. 切換到 **上傳文本** 分頁
2. 上傳 `samples/sample_conflict_story.txt`
3. 分塊策略選 **auto（自動）**
4. 按 **匯入並分塊**
5. 展開 **分塊預覽**，說明系統依章節／場景切分文本

---

## 步驟 4：說明 chunk_count

1. 切換到 **分析** 分頁
2. 指出側欄或上傳頁顯示的區塊數（約 5 個 chunk）
3. 說明：後續抽取與衝突偵測都以這些 chunk 為單位

---

## 步驟 5：執行分析並展示統計

1. 按 **執行敘事分析**
2. 等待完成後，展示統計列：
   - 角色數
   - 地點數
   - 物品數
   - 事件數
   - 世界規則數
   - **衝突數**（預期約 6～7 條）
3. 說明：`chunk_count` 與各 entity 計數

---

## 步驟 6：展示衝突報告概覽

1. 切換到 **衝突報告** 分頁
2. 展示 `conflict_counts` JSON（各類型衝突數量）
3. 展示衝突表格（類型、嚴重度、標題）

---

## 步驟 7：深入展示 2～3 個重點衝突

建議依序展開以下 expander：

### A. 角色死亡後仍活動（`character_state_conflict`）

- 指出 **證據 A**：死亡／安葬原文
- 指出 **證據 B**：死後說話或活動句
- 說明：這是 rule1，不是 LLM 判斷

### B. 唯一物品衝突（`unique_item_conflict`）

- 說明前文宣稱「唯一」，後文出現備用／第二把
- 展示 evidence_a / evidence_b

### C. 世界規則違反或設定反轉

擇一展示：

- **夜晚敲鐘**（`world_rule_violation`）：規則 vs 夜間敲鐘事件
- **設定反轉**（`world_setting_conflict`）：早期「晨鐘」設定 vs 後文揭示複製品

可補充：系統也偵測人設漂移（`character_consistency_drift`）與物品持有人不一致（`item_location_conflict`）。

---

## 步驟 8：展示知識圖

1. 切換到 **知識圖** 分頁
2. 展示 JSON 統計（節點／邊／類型計數）
3. 展示 PyVis 互動圖（角色、事件、規則等節點）
4. 若 PyVis 不可用，說明 fallback 仍會顯示統計，不會讓整個 app 崩潰

---

## 步驟 9：匯出 JSON 報告

1. 回到 **衝突報告** 分頁底部
2. 按 **匯出 JSON 報告**
3. 指出成功訊息中的路徑：`data/exports/report_xxxxxxxx.json`
4. 說明：可供存檔、比對或後續工具讀取

---

## 步驟 10：展示「不亂報錯」能力（加分）

1. 清除或新建專案
2. 上傳 `samples/sample_clean_story.txt`
3. 執行分析
4. 說明：文本中有「死亡」「唯一」「不能」等詞，但**沒有明顯矛盾**，系統應輸出 **0 條衝突**

（選用）再上傳 `samples/sample_renamed_conflict_story.txt`，說明換了角色名／物品名仍能抓到類似衝突，代表不是硬寫單一文本。

---

## 步驟 11：說明限制與未來工作

向老師說明（可搭配頁面底部「系統限制提示」）：

- Heuristic 抽取仍可能誤判
- LLM 只是可選抽取輔助
- **沒有**完整時間線引擎、自動修稿、HuggingFace 本地推理
- 衝突判斷以規則為主，結果需作者最終確認

未來可擴充：FastAPI、更完整時間線、更多文本泛化測試。

---

## 常見問題備答

**Q：沒有 Ollama 能 demo 嗎？**  
A：可以。預設 heuristic 即可完整展示 7 條規則。

**Q：會自動幫我改稿嗎？**  
A：不會。只提供 `suggested_fix` 建議。

**Q：這是時間線引擎嗎？**  
A：不是。目前只有部分狀態先後規則（如死亡後活動），沒有獨立時間軸引擎。

**Q：如果現場分析失敗？**  
A：可改用已匯出的 `data/exports/` JSON，或現場跑 `python -m pytest tests/ -q` 證明核心邏輯通過。
