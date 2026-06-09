"""輕量智敘 MVP — Streamlit 介面。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src.agents.report_agent import generate_full_report
from src.chunker import chunk_document
from src.config import OLLAMA_DEFAULT_MODEL
from src.graph_builder import build_knowledge_graph, graph_stats, graph_to_pyvis_html
from src.ingest import build_document, read_upload
from src.llm_client import get_llm
from src.report_writer import conflicts_to_dataframe
from src.storage import (
    clear_project_text,
    create_project,
    delete_chunk,
    delete_project,
    export_report_json,
    get_latest_document,
    get_project,
    init_db,
    list_projects,
    load_chunks,
    load_extraction,
    load_report,
    save_chunks,
    save_document,
)

st.set_page_config(
    page_title="輕量智敘",
    page_icon="📖",
    layout="wide",
)

init_db()

st.title("輕量智敘")
st.caption("本地優先的長篇敘事一致性檢查 — 偵測人設漂移、時間線、物品與世界觀衝突")

# --- 側欄：專案 ---
with st.sidebar:
    st.header("專案")
    projects = list_projects()
    project_options = {f"{p.name} ({p.id[:8]})": p.id for p in projects}

    with st.form("new_project", clear_on_submit=True):
        new_name = st.text_input("新專案名稱")
        new_desc = st.text_area("說明（選填）", height=68)
        if st.form_submit_button("建立專案") and new_name.strip():
            p = create_project(new_name.strip(), new_desc.strip())
            st.success(f"已建立：{p.name}")
            st.rerun()

    if project_options:
        selected_label = st.selectbox("選擇專案", list(project_options.keys()))
        project_id = project_options[selected_label]

        with st.expander("刪除專案"):
            st.caption("永久移除專案及其所有文本與分析資料，無法復原。")
            confirm_delete = st.checkbox(
                f"我確定要刪除「{selected_label.split(' (')[0]}」",
                key="confirm_delete_project",
            )
            if st.button("刪除此專案", disabled=not confirm_delete):
                delete_project(project_id)
                st.success("專案已刪除")
                st.rerun()
    else:
        st.info("請先建立專案")
        project_id = None

    st.divider()
    use_llm = st.checkbox("使用 Ollama LLM 抽取", value=False)
    ollama_model = st.text_input("Ollama 模型", value=OLLAMA_DEFAULT_MODEL)
    if use_llm:
        llm = get_llm(model=ollama_model)
        if llm.is_available():
            st.success("Ollama 已連線")
        else:
            st.warning("Ollama 未連線，將改用規則/heuristic 抽取")

if not project_id:
    st.stop()

project = get_project(project_id)
st.subheader(project.name if project else "專案")
if project and project.description:
    st.write(project.description)

tab_upload, tab_analyze, tab_graph, tab_report = st.tabs(
    ["上傳文本", "分析", "知識圖", "衝突報告"]
)

# --- 上傳 ---
with tab_upload:
    uploaded = st.file_uploader("上傳故事／劇本（.txt / .md / .docx）", type=["txt", "md", "docx"])
    chunk_strategy = st.selectbox(
        "分塊策略",
        ["auto", "chapter", "scene", "fixed"],
        format_func=lambda x: {
            "auto": "自動（章節→場景）",
            "chapter": "依章節",
            "scene": "依場景分隔",
            "fixed": "固定長度",
        }[x],
    )

    if uploaded and st.button("匯入並分塊", type="primary"):
        text = read_upload(uploaded.name, uploaded.getvalue())
        doc = build_document(project_id, uploaded.name, text)
        save_document(doc)
        chunks = chunk_document(text, doc.id, project_id, strategy=chunk_strategy)
        save_chunks(chunks)
        st.success(f"已匯入 {uploaded.name}，共 {len(chunks)} 個區塊")
        with st.expander("預覽分塊"):
            for c in chunks[:10]:
                st.markdown(f"**{c.index + 1}. {c.chapter_title}** ({c.kind})")
                st.text(c.text[:300] + ("…" if len(c.text) > 300 else ""))

    chunks = load_chunks(project_id)
    doc = get_latest_document(project_id)

    if chunks or doc:
        st.divider()
        st.subheader("已上傳的文本")
        if doc:
            st.caption(f"檔案：{doc.filename} · 上傳於 {doc.uploaded_at.strftime('%Y-%m-%d %H:%M')}")
        st.info(f"目前共有 {len(chunks)} 個文本區塊")

        with st.expander("管理文本區塊", expanded=len(chunks) <= 8):
            for c in chunks:
                col_main, col_del = st.columns([5, 1])
                with col_main:
                    st.markdown(f"**{c.index + 1}. {c.chapter_title}** · `{c.kind}`")
                    st.text(c.text[:200] + ("…" if len(c.text) > 200 else ""))
                with col_del:
                    if st.button("刪除", key=f"del_chunk_{c.id}", type="secondary"):
                        delete_chunk(project_id, c.id)
                        st.toast(f"已刪除區塊：{c.chapter_title}")
                        st.rerun()

        st.markdown("##### 清除全部")
        confirm_clear = st.checkbox(
            "我確定要清除此專案的所有上傳文本與分析結果",
            key="confirm_clear_text",
        )
        also_analysis = st.checkbox(
            "一併清除分析報告與知識圖資料",
            value=True,
            key="clear_analysis_too",
            disabled=not confirm_clear,
        )
        if st.button(
            "清除全部上傳文本",
            type="primary",
            disabled=not confirm_clear,
        ):
            clear_project_text(project_id, clear_analysis=also_analysis)
            st.success("已清除上傳文本" + ("與分析結果" if also_analysis else ""))
            st.rerun()

# --- 分析 ---
with tab_analyze:
    chunks = load_chunks(project_id)
    if not chunks:
        st.warning("請先在上傳頁匯入文本")
    elif st.button("執行敘事分析", type="primary"):
        with st.spinner("抽取實體與事件、偵測衝突…"):
            llm = get_llm(model=ollama_model) if use_llm else None
            report, extraction = generate_full_report(
                project_id, chunks, use_llm=use_llm, llm=llm
            )
        st.success("分析完成")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("角色", report.entity_counts.get("characters", 0))
        c2.metric("地點", report.entity_counts.get("locations", 0))
        c3.metric("物品", report.entity_counts.get("objects", 0))
        c4.metric("事件", report.entity_counts.get("events", 0))
        c5.metric("衝突", len(report.conflicts))
        st.caption(f"chunk_count = {report.chunk_count}")

# --- 知識圖 ---
with tab_graph:
    extraction = load_extraction(project_id)
    if not extraction:
        st.warning("請先執行分析")
    else:
        g = build_knowledge_graph(extraction)
        stats = graph_stats(g)
        st.json(stats)
        html = graph_to_pyvis_html(g)
        st.components.v1.html(html, height=520, scrolling=True)

# --- 報告 ---
with tab_report:
    report = load_report(project_id)
    if not report:
        st.warning("尚無報告，請先執行分析")
    else:
        st.json(report.conflict_counts)
        st.dataframe(conflicts_to_dataframe(report.conflicts), use_container_width=True)

        for c in report.conflicts:
            with st.expander(f"[{c.severity}] {c.title}"):
                st.write(f"**類型**：{c.conflict_type}")
                if c.related_entities:
                    st.caption("相關實體：" + ", ".join(c.related_entities))
                st.markdown("**主張 A**")
                st.write(c.claim_a)
                st.markdown("**主張 B**")
                st.write(c.claim_b)
                st.markdown("**證據 A**")
                st.markdown("> " + (c.evidence_a or "").strip().replace("\n", "\n> "))
                st.markdown("**證據 B**")
                st.markdown("> " + (c.evidence_b or "").strip().replace("\n", "\n> "))
                st.markdown("**說明**")
                st.write(c.explanation)
                if c.suggested_fix:
                    st.info(f"建議：{c.suggested_fix}")

        if st.button("匯出 JSON 報告"):
            path = export_report_json(report)
            st.success(f"已匯出至 {path}")
