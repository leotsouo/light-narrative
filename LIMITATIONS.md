# 輕量智敘 — 目前限制

本文件誠實列出期末 MVP 的限制，避免展示時過度承諾。

## 抽取層

- **Heuristic 抽取仍可能誤判**  
  角色名、物品名、地點與事件依 regex／關鍵字抽取，對複雜中文敘事、代詞與長句仍可能漏抽或誤抽。

- **LLM 目前只作可選抽取輔助**  
  側欄勾選 Ollama 後，僅用於實體／事件抽取；若 Ollama 未連線，會自動 fallback 至 heuristic，不會中斷流程。

- **HuggingFace 尚未接線**  
  `HuggingFaceProvider` 為 stub，`complete()` 會拋出 `NotImplementedError`。README 與 UI 不宣稱其可用。

## 衝突偵測層

- **沒有完整時間線引擎**  
  UI 不宣稱「完整時間線分析」。目前最接近的是 rule1（死亡／安葬 vs 後續活動）等狀態先後規則，並非獨立時間軸推理。

- **規則覆蓋有限**  
  僅 7 條 deterministic rules。許多敘事矛盾（例如複雜因果、多線敘事、隱含時間跳躍）目前無法偵測。

- **Negation／例外處理仍不完整**  
  已處理部分否定句（如「從未在夜間敲鐘」），但其他語用例外仍需更多測試與規則。

## 輸出與修稿

- **沒有自動修稿**  
  系統只輸出 `ConflictReport` 與 `suggested_fix` 文字建議，不會修改上傳原文。

- **建議需作者確認**  
  偵測到的衝突可能是伏筆、敘述性反轉或 heuristic 誤報，需人工判斷。

## 中文 NLP

- **代詞解析與實體合併仍有改進空間**  
  「她／他／自己」等指涉在物品持有人、角色行為上仍可能解析失敗；無法解析時會盡量不輸出低可讀性衝突。

- **設定實體 canonicalization 為通用 heuristic**  
  例如「鐘」與「晨鐘」合併依子字串規則，非語意理解，可能在其他文本失效。

## 測試與泛化

- **需要更多不同文本測試泛化能力**  
  雖有 `sample_renamed_conflict_story.txt` 與多個 pytest，但距離「任意長篇小說穩定可用」仍有差距。

- **部分模組測試仍為 smoke level**  
  `graph_builder`、`report_writer`、`ingest` 目前以最小 smoke test 為主，非完整行為覆蓋。

## 部署與架構

- **僅 Streamlit 單頁本地應用**  
  無 FastAPI、無登入、無雲端部署、無多人協作。

- **SQLite 本地儲存**  
  資料存在本機 `data/light_narrative.db`；換機器需自行備份。

## 知識圖

- **PyVis 為可選視覺化**  
  未安裝或渲染失敗時顯示 fallback HTML 與統計，不會讓整個 app 崩潰，但互動圖可能不可用。

## 期末展示建議

對老師說明時，建議強調：

1. 這是 **規則驅動的檢查 MVP**，不是生成式寫作工具  
2. **Ollama 可選**，現場無 LLM 也能 demo  
3. 結果是 **輔助作者發現問題**，不是自動定稿  
4. 未實作功能已列於 README「未來工作」，不在本次交付範圍
