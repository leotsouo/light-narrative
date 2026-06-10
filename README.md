# 輕量智敘（Light Narrative）

本地優先的中文敘事一致性檢查 MVP。協助作者偵測小說、劇本與原創 IP 文本中的敘事不一致，例如角色死亡後仍活動、唯一物品矛盾、世界規則違反、人設漂移與設定反轉。

**本系統不是自動寫故事工具**，專注於檢查、報告與修正建議（`suggested_fix`），不會改寫原文。

## 系統定位

- **本地端**中文敘事一致性檢查 MVP
- **規則驅動為主**：7 條 deterministic conflict rules
- **Ollama LLM 可選**：僅作實體／事件抽取輔助；未連線時自動 fallback 至 heuristic
- **衝突判斷不由 LLM 決定**

## 已實作功能

- Streamlit 單頁 UI（專案管理、上傳、分析、知識圖、衝突報告、JSON 匯出）
- SQLite 本地持久化
- 上傳 `.txt` / `.md` / `.docx` 並分塊（auto / chapter / scene / fixed）
- Heuristic 抽取 + 可選 Ollama 抽取
- 7 條確定性衝突規則：
  1. 角色死亡／安葬後仍活動
  2. 亡者不能復活 vs 復活事件
  3. 唯一物品 vs 備用品
  4. 物品持有人不一致
  5. 夜晚敲鐘規則 vs 夜間敲鐘事件
  6. 人設限制 vs 高能力行為（character drift）
  7. 世界設定早期描述 vs 後期反轉
- NetworkX + PyVis 知識圖（缺 PyVis 時有友善 fallback）
- JSON 報告匯出至 `data/exports/`
- `samples/` 展示用範例文本
- 30 個 pytest 測試

## 未實作功能與限制

| 項目 | 狀態 |
|------|------|
| FastAPI 後端 | 未實作 |
| HuggingFace 本地推理 | **Stub**（`NotImplementedError`） |
| 獨立時間線引擎 | 未實作（僅有部分狀態先後規則） |
| 自動修稿 | 未實作（僅 `suggested_fix` 文字建議） |
| 登入／雲端協作 | 未實作 |

詳見 [LIMITATIONS.md](LIMITATIONS.md) 與 [FINAL_STATUS.md](FINAL_STATUS.md)。

## 安裝

```bash
cd light-narrative
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
```

## 啟動

```bash
streamlit run app.py
```

瀏覽器開啟後即可操作。**不需要 Ollama** 也能完整展示（預設 heuristic 抽取）。

### Ollama（選用）

```bash
ollama pull llama3.2
ollama serve
```

在側欄勾選「使用 Ollama LLM 抽取（可選）」以提升抽取品質。

## 使用流程

1. 側欄建立或選擇專案
2. **上傳文本** — 匯入 `.txt` / `.md` / `.docx` 並選擇分塊策略
3. **分析** — 執行敘事分析，檢視抽取統計與衝突數
4. **知識圖** — 檢視 NetworkX 圖形統計與 PyVis 互動圖
5. **衝突報告** — 檢視衝突類型、證據、說明與建議
6. **匯出 JSON** — 報告寫入 `data/exports/report_{project_id前8字}.json`

展示建議使用 `samples/sample_conflict_story.txt`（有矛盾）與 `samples/sample_clean_story.txt`（無矛盾）。操作腳本見 [DEMO_SCRIPT.md](DEMO_SCRIPT.md)。

## 文本處理上限與建議用量

本 MVP **不是**為整本長篇小說設計，實際測試與期末展示主要使用 `samples/` 內的**短篇文本**（約 300～400 字、3～5 個 chunk）。以下依目前 repo 實作說明上限與建議。

### 上傳限制

- `app.py` 的 `st.file_uploader` **未設定** `max_upload_size` 參數。
- 因此沿用 **Streamlit 預設**：`server.maxUploadSize = 200 MB`（本 repo 未提供 `.streamlit/config.toml` 覆寫）。
- 上傳後整份檔案會以 bytes 讀入記憶體（`uploaded.getvalue()`），並完整寫入 SQLite `documents.raw_text`。

### 分塊設定

- **fixed 預設字數**：`DEFAULT_CHUNK_MAX_CHARS = 2500`（見 `src/config.py`）。
- 分塊策略（見 `src/chunker.py`）：
  - **auto**：先依「第 X 章」切章；章內若有 `---` / `***` 等場景分隔符再切；單段超過約 `2500 × 1.5` 字時改依場景切。
  - **chapter**：只依章節標題切；若無章節標題則整篇成一塊。
  - **scene**：依場景分隔符切；若無分隔符則 fallback 為 fixed 切塊。
  - **fixed**：依段落累積，每塊上限 2500 字。
- 程式**未設定** chunk 數量上限；文本越長 → chunk 越多 → 分析時間大致線性增加。

### SQLite 儲存

- `chunks.text`、`documents.raw_text`、`extractions.payload`、`reports.payload` 皆為 SQLite `TEXT`，**程式層未設定**筆數或字數上限。
- 實務瓶頸在記憶體、分析耗時與 UI 渲染，而非資料庫欄位型別本身。

### 分析模式瓶頸

| 模式 | 主要限制 |
|------|----------|
| **heuristic（預設）** | 每 chunk 依序跑 regex／關鍵字抽取；事件每 chunk 最多 **40** 筆；chunk 越多越慢；抽取品質在長文本、複雜指代下可能下降。 |
| **Ollama（可選）** | 每 chunk 送 **前 3000 字**給 LLM（entity + event 各 1 次請求）；單次請求 timeout **120 秒**；未在程式中設定 context window，受模型與 Ollama 預設限制；chunk 數 × 2 次 API ≈ 分析時間與失敗風險。 |

### 建議文本量

| 用途 | 建議 |
|------|------|
| **目前實際測試／開發** | 短篇片段、單章或數章 excerpt，約 **500 字～2 萬字** |
| **期末展示** | 直接使用 `samples/`（約 **300～400 字**），或自備結構類似的中短篇（含章節標題），**5～15 個 chunk** 以內 |
| **不建議** | 整本小說（十萬字以上）、無章節／無場景標記的超長單段文本、一次上傳數十萬字期待穩定分析 |

> 若需處理更長文本，應先在外部切章、分段上傳，或僅抽取關鍵章節——這屬於後續擴充，非目前 MVP 保證能力。

## 測試

```bash
python -m pytest tests/ -q
```

## 專案結構

```text
light-narrative/
  app.py                 # Streamlit 入口
  requirements.txt
  README.md
  DEMO_SCRIPT.md
  LIMITATIONS.md
  FINAL_STATUS.md
  samples/               # 期末展示用範例文本
  data/                  # SQLite 與 JSON 匯出（執行時建立）
  src/
    config.py
    schemas.py
    ingest.py
    chunker.py
    llm_client.py
    graph_builder.py
    conflict_rules.py
    report_writer.py
    storage.py
    state_tracker.py
    narrative_patterns.py
    agents/
  tests/
```

## 目前限制

- Heuristic 抽取仍可能誤判實體／物品名
- LLM 只作可選抽取輔助，不作衝突判斷核心
- 中文代詞解析與實體合併仍有改進空間
- 需更多不同文本驗證泛化能力

## 未來工作

- FastAPI 後端
- HuggingFace / llama.cpp 本地推理
- 獨立時間線視圖與引擎
- 更完整的 LLM 抽取與評估管線
- 自動修稿（需另立安全與作者確認機制）

## 授權

MIT（可依需求調整）
