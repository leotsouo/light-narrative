# 輕量智敘（Light Narrative）

本地優先的長篇敘事一致性檢查 MVP。用於偵測小說、劇本、遊戲劇情與原創 IP 文件中的敘事不一致、人設漂移、時間線衝突、物品／地點矛盾與世界觀規則違反。

**本系統不是自動寫故事工具**，專注於檢查與報告。

## 技術棧

- Python 3.11+
- Streamlit（UI）
- SQLite（本地儲存）
- Pydantic（結構化 schema）
- NetworkX + PyVis（知識圖）
- python-docx（`.docx` 讀取）
- Ollama 本地 API（可選 LLM 抽取；未連線時使用 heuristic）

## 快速開始

```bash
cd light-narrative
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
streamlit run app.py
```

瀏覽器開啟後：

1. 側欄建立專案
2. **上傳文本** — 匯入 `.txt` / `.md` / `.docx` 並分塊
3. **分析** — 抽取實體／事件並偵測衝突
4. **知識圖** — 檢視 NetworkX 圖
5. **衝突報告** — 檢視嚴重度、證據與修訂建議

### Ollama（選用）

```bash
ollama pull llama3.2
ollama serve
```

在側欄勾選「使用 Ollama LLM 抽取」以提升抽取品質。

## 專案結構

```text
light-narrative/
  app.py                 # Streamlit 入口
  requirements.txt
  data/                  # SQLite 與匯出
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
    agents/              # 抽取與分析 agents
  tests/
```

## 測試

```bash
pytest tests/ -v
```

## 後續擴充（規劃）

- FastAPI 後端
- llama.cpp / 量化模型
- Hugging Face Transformers 完整實作

## 授權

MIT（可依需求調整）
