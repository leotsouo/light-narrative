# Heuristic vs Ollama 比較報告

- 產生時間：2026-06-10T00:17:06.671697+00:00
- chunk_count：5
- Ollama 模型：llama3.2
- Ollama 連線：否

## 架構說明

- **AI 輔助**：實體、事件、世界規則抽取
- **Rule-based Core**：衝突偵測、證據比對、JSON 報告

## 抽取統計

| 項目 | Heuristic | Ollama | Δ (Ollama − Heuristic) |
|---|---:|---:|---:|
| characters | 5 | — | — |
| locations | 1 | — | — |
| objects | 2 | — | — |
| events | 6 | — | — |
| world_rules | 5 | — | — |

## 衝突檢核（deterministic rules）

- Heuristic 衝突數：6
- Ollama 衝突數：—

## 解讀

Ollama 未連線，僅完成 heuristic 抽取；衝突檢核仍由 deterministic rules 執行。