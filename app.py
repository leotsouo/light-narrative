"""輕量智敘 MVP — Streamlit 介面（Luxury Editorial × Forensic Evidence Dashboard）。"""
from __future__ import annotations

import html as html_module
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from evaluation.compare_modes import compare_extraction_modes, compare_to_markdown
from src.agents.report_agent import generate_full_report
from src.chunker import chunk_document
from src.config import OLLAMA_DEFAULT_MODEL
from src.graph_builder import build_knowledge_graph, graph_stats, graph_to_pyvis_html
from src.ingest import build_document, read_upload
from src.llm_client import get_llm
from src.schemas import AnalysisReport, Chunk, ConflictReport
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

# ---------------------------------------------------------------------------
# UI theme & helpers
# ---------------------------------------------------------------------------

CONFLICT_TYPE_LABELS = {
    "world_rule_violation": "世界規則違反",
    "character_state_conflict": "角色狀態衝突",
    "unique_item_conflict": "唯一物品衝突",
    "item_location_conflict": "物品位置衝突",
    "character_consistency_drift": "人設一致性漂移",
    "world_setting_conflict": "世界設定衝突",
}

SEVERITY_LABELS = {"high": "高", "medium": "中", "low": "低"}


def _esc(text: str) -> str:
    return html_module.escape(text or "")


def inject_global_styles() -> None:
    st.markdown(
        """
<style>
:root {
  --bg-main: #F9F8F6;
  --bg-panel: #F2EEE8;
  --bg-card: #FFFFFF;
  --text-main: #1A1A1A;
  --text-muted: #6C6863;
  --border-subtle: rgba(26,26,26,0.12);
  --border-strong: rgba(26,26,26,0.22);
  --accent-gold: #D4AF37;
  --accent-red: #B94A48;
  --accent-blue: #3F5E9A;
  --accent-green: #4F7C5A;
  --accent-purple: #6C5A8E;
  --shadow-soft: 0 1px 3px rgba(26,26,26,0.06);
  --shadow-hover: 0 3px 10px rgba(26,26,26,0.10);
  --transition: 0.35s ease;
}

.stApp {
  background: linear-gradient(180deg, var(--bg-main) 0%, #F5F3EF 100%);
  color: var(--text-main);
  font-family: Inter, "Noto Sans TC", "Microsoft JhengHei", sans-serif;
}

.main .block-container {
  max-width: 1100px;
  padding-top: 2rem;
  padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
  background-color: var(--bg-panel);
  border-right: 1px solid var(--border-subtle);
}

[data-testid="stSidebar"] .block-container {
  padding-top: 1.5rem;
}

h1, h2, h3, .hero-title, .section-title, .conflict-title {
  font-family: "Noto Serif TC", "Songti TC", serif;
  color: var(--text-main);
}

.stButton > button {
  border-radius: 0 !important;
  transition: border-color var(--transition), background var(--transition), color var(--transition);
  font-family: Inter, "Noto Sans TC", sans-serif;
  letter-spacing: 0.02em;
}

.stButton > button[kind="primary"] {
  background: var(--text-main);
  border: 1px solid var(--text-main);
  color: var(--bg-card);
  font-weight: 500;
}

.stButton > button[kind="primary"]:hover {
  background: var(--bg-card);
  color: var(--text-main);
  border-color: var(--accent-gold);
  box-shadow: var(--shadow-hover);
}

.stButton > button[kind="secondary"] {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
}

.stButton > button[kind="secondary"]:hover {
  border-color: var(--accent-gold);
  color: var(--text-main);
}

.stTextInput input, .stTextArea textarea {
  background-color: var(--bg-card) !important;
  color: var(--text-main) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 0 !important;
}

.stSelectbox > div > div {
  background-color: var(--bg-card) !important;
  border-radius: 0 !important;
  border-color: var(--border-subtle) !important;
}

.stFileUploader {
  background: var(--bg-card);
  border: 1px dashed var(--border-strong);
  border-radius: 0;
  padding: 0.75rem;
}

.stFileUploader:hover {
  border-color: var(--accent-gold);
  transition: border-color var(--transition);
}

/* --- Layout shell --- */
.app-shell {
  width: 100%;
}

/* --- Hero --- */
.app-hero {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-top: 2px solid var(--accent-gold);
  padding: 2.5rem 2.75rem 2rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-soft);
}

.hero-eyebrow {
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 0 0.75rem 0;
  font-family: Inter, sans-serif;
  font-weight: 500;
}

.hero-title {
  font-size: 2.4rem;
  font-weight: 700;
  margin: 0 0 0.35rem 0;
  letter-spacing: 0.04em;
  line-height: 1.15;
}

.hero-subtitle {
  font-size: 0.92rem;
  color: var(--accent-blue);
  margin: 0 0 1.25rem 0;
  font-family: Inter, sans-serif;
  font-weight: 500;
  letter-spacing: 0.03em;
}

.hero-desc {
  color: var(--text-muted);
  font-size: 0.95rem;
  line-height: 1.75;
  margin: 0 0 1.5rem 0;
  max-width: 680px;
}

.hero-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.75rem;
}

.hero-disclaimer {
  border-top: 1px solid var(--border-subtle);
  padding-top: 1.25rem;
  font-size: 0.88rem;
  line-height: 1.75;
  color: var(--text-muted);
}

.gold-rule {
  display: inline-block;
  width: 2.5rem;
  height: 2px;
  background: var(--accent-gold);
  margin-bottom: 0.75rem;
}

/* --- Badges --- */
.editorial-badge,
.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 0;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid var(--border-subtle);
  background: var(--bg-main);
  color: var(--text-muted);
  transition: border-color var(--transition);
}

.editorial-badge:hover,
.status-badge:hover {
  border-color: var(--accent-gold);
}

.status-success {
  border-color: rgba(79,124,90,0.35);
  background: rgba(79,124,90,0.06);
  color: var(--accent-green);
}

.status-warning {
  border-color: rgba(212,175,55,0.4);
  background: rgba(212,175,55,0.06);
  color: #9A7B1A;
}

.status-danger {
  border-color: rgba(185,74,72,0.35);
  background: rgba(185,74,72,0.05);
  color: var(--accent-red);
}

.status-info {
  border-color: rgba(63,94,154,0.3);
  background: rgba(63,94,154,0.05);
  color: var(--accent-blue);
}

.status-purple {
  border-color: rgba(108,90,142,0.3);
  background: rgba(108,90,142,0.05);
  color: var(--accent-purple);
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin: 0.35rem 0;
}

/* --- Sections --- */
.section-intro {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-top: 2px solid var(--accent-gold);
  padding: 1.5rem 1.75rem 1.25rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-soft);
}

.section-rule {
  border: none;
  border-top: 1px solid var(--border-subtle);
  margin: 2rem 0 2.5rem;
  height: 0;
}

/* Streamlit 無法用 split HTML 包住 widget，隱藏殘留的空容器 */
.section-wrap:empty,
.export-card:empty,
div.section-wrap:empty,
div.export-card:empty {
  display: none !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
  height: 0 !important;
  min-height: 0 !important;
  overflow: hidden !important;
}

/* 知識圖 iframe 下方多餘留白 */
div[data-testid="stCustomComponentV1"] {
  margin-bottom: 0 !important;
  line-height: 0;
}

div[data-testid="stCustomComponentV1"] iframe {
  display: block;
  border: 1px solid var(--border-subtle);
}

.section-kicker {
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 0 0.5rem 0;
  font-family: Inter, sans-serif;
}

.section-title {
  font-size: 1.4rem;
  margin: 0 0 0.5rem 0;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.section-desc {
  color: var(--text-muted);
  font-size: 0.88rem;
  line-height: 1.7;
  margin: 0 0 1.25rem 0;
}

.muted-text {
  color: var(--text-muted);
  font-size: 0.82rem;
  line-height: 1.6;
}

.project-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-subtle);
}

.project-name {
  font-family: "Noto Serif TC", serif;
  font-size: 1.15rem;
  color: var(--text-main);
}

.sidebar-kicker {
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 1.25rem 0 0.5rem 0;
  font-weight: 600;
  border-top: 1px solid var(--border-subtle);
  padding-top: 1rem;
}

.sidebar-kicker:first-of-type {
  border-top: none;
  padding-top: 0;
  margin-top: 0.5rem;
}

/* --- Metrics --- */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
  gap: 0.85rem;
  margin: 1.25rem 0;
}

.metric-card {
  background: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-top: 2px solid transparent;
  padding: 1.1rem 1.2rem;
  box-shadow: var(--shadow-soft);
  transition: border-color var(--transition), box-shadow var(--transition);
}

.metric-card:hover {
  border-top-color: var(--accent-gold);
  box-shadow: var(--shadow-hover);
}

.metric-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.metric-value {
  font-size: 2.1rem;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1;
  font-family: Inter, sans-serif;
}

.metric-hint {
  font-size: 0.76rem;
  color: var(--text-muted);
  margin-top: 0.45rem;
}

/* --- Chunk / manuscript --- */
.chunk-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-top: 1px solid var(--border-strong);
  border-left: 2px solid var(--accent-gold);
  padding: 1rem 1.25rem;
  margin-bottom: 0.75rem;
  box-shadow: var(--shadow-soft);
  transition: box-shadow var(--transition), border-left-color var(--transition);
}

.chunk-card:hover {
  box-shadow: var(--shadow-hover);
  border-left-color: var(--text-main);
}

.chunk-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.55rem;
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  font-family: Inter, sans-serif;
}

.chunk-title {
  font-family: "Noto Serif TC", serif;
  font-weight: 600;
  color: var(--text-main);
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
}

.manuscript-preview {
  color: var(--text-muted);
  font-size: 0.88rem;
  line-height: 1.7;
  font-family: "Noto Serif TC", "Songti TC", serif;
  font-style: italic;
  padding-left: 0.5rem;
  border-left: 1px solid var(--border-subtle);
}

/* --- Conflict cards --- */
.conflict-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  padding: 1.5rem 1.75rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-soft);
  transition: box-shadow var(--transition);
}

.conflict-card:hover {
  box-shadow: var(--shadow-hover);
}

.conflict-card-high { border-left: 3px solid var(--accent-red); }
.conflict-card-medium { border-left: 3px solid var(--accent-gold); }
.conflict-card-low { border-left: 3px solid var(--accent-blue); }

.conflict-header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.85rem;
}

.conflict-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 0.65rem 0;
  line-height: 1.45;
}

.related-entities {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 0.85rem;
  letter-spacing: 0.01em;
}

.claim-block {
  background: var(--bg-main);
  border: 1px solid var(--border-subtle);
  padding: 0.85rem 1.1rem;
  margin-bottom: 0.65rem;
}

.claim-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent-blue);
  margin-bottom: 0.35rem;
  font-weight: 600;
}

.claim-text {
  color: var(--text-main);
  font-size: 0.88rem;
  line-height: 1.65;
}

.evidence-block {
  border-left: 3px solid var(--accent-gold);
  background: rgba(212,175,55,0.08);
  padding: 1rem 1.25rem;
  margin-bottom: 0.65rem;
}

.evidence-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #9A7B1A;
  margin-bottom: 0.4rem;
  font-weight: 600;
}

.evidence-text {
  color: var(--text-main);
  font-size: 0.9rem;
  line-height: 1.75;
  font-family: "Noto Serif TC", "Songti TC", serif;
  font-style: italic;
}

.explanation-block {
  color: var(--text-muted);
  font-size: 0.88rem;
  line-height: 1.7;
  margin: 0.75rem 0 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-subtle);
}

.suggested-fix-block {
  background: rgba(79,124,90,0.05);
  border: 1px solid rgba(79,124,90,0.2);
  padding: 0.85rem 1.1rem;
  margin-top: 0.65rem;
}

.fix-label {
  font-size: 0.68rem;
  color: var(--accent-green);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.35rem;
  font-weight: 600;
}

/* --- Export & evaluation --- */
.export-card {
  background: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-top: 2px solid var(--accent-gold);
  padding: 1.5rem 1.75rem;
}

.evaluation-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  padding: 2rem 2.25rem;
  margin-bottom: 1.75rem;
  box-shadow: var(--shadow-soft);
}

.eval-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  margin-top: 1rem;
}

.eval-table th, .eval-table td {
  border: 1px solid var(--border-subtle);
  padding: 0.6rem 0.85rem;
  text-align: left;
}

.eval-table th {
  background: var(--bg-main);
  color: var(--text-muted);
  font-weight: 600;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.eval-table td {
  color: var(--text-main);
}

.graph-stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.graph-note {
  color: var(--text-muted);
  font-size: 0.84rem;
  line-height: 1.65;
  margin-top: 1rem;
  padding: 0.85rem 1.1rem;
  background: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-left: 2px solid var(--accent-blue);
  font-style: italic;
}

.footer-note {
  border-top: 1px solid var(--border-subtle);
  padding-top: 1.5rem;
  margin-top: 0.5rem;
}

.ai-status-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 2px solid var(--accent-purple);
  padding: 1rem 1.1rem;
  margin: 0.75rem 0 1rem;
}

.ai-status-card .ai-status-title {
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent-purple);
  font-weight: 600;
  margin-bottom: 0.65rem;
}

.ai-status-row {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.8rem;
  margin-bottom: 0.35rem;
  line-height: 1.5;
}

.ai-status-row .label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.ai-status-row .value {
  color: var(--text-main);
  text-align: right;
}

.ai-role-list {
  margin: 0.5rem 0 0;
  padding-left: 1.1rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  line-height: 1.65;
}

.ai-role-list li.ai-on { color: var(--accent-blue); }
.ai-role-list li.ai-off { color: var(--text-muted); }
.ai-role-list li.rule-on { color: var(--accent-green); }

.ai-hybrid-note {
  margin-top: 0.75rem;
  padding-top: 0.65rem;
  border-top: 1px solid var(--border-subtle);
  font-size: 0.76rem;
  line-height: 1.65;
  color: var(--text-muted);
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
  margin-top: 0.75rem;
}

.compare-table th, .compare-table td {
  border: 1px solid var(--border-subtle);
  padding: 0.55rem 0.75rem;
  text-align: left;
}

.compare-table th {
  background: var(--bg-main);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.compare-table td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.compare-table tr.delta-positive td:last-child { color: var(--accent-blue); }
.compare-table tr.delta-negative td:last-child { color: var(--accent-red); }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
  background: transparent;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def status_badge(label: str, kind: str = "") -> str:
    kind_map = {
        "success": "status-success",
        "warning": "status-warning",
        "danger": "status-danger",
        "info": "status-info",
        "purple": "status-purple",
    }
    extra = kind_map.get(kind, "")
    cls = f"status-badge {extra}".strip()
    return f'<span class="{cls}">{_esc(label)}</span>'


def editorial_badge(label: str) -> str:
    return f'<span class="editorial-badge">{_esc(label)}</span>'


def render_hero() -> None:
    st.markdown(
        f"""
<div class="app-shell">
<div class="app-hero">
  <div class="hero-eyebrow">Narrative Audit · Local-first</div>
  <div class="gold-rule"></div>
  <div class="hero-title">輕量智敘</div>
  <div class="hero-subtitle">Local-first Narrative Logic Auditor</div>
  <p class="hero-desc">
    將長篇故事拆解為角色、物品、事件與世界規則，產生可追溯 evidence 的敘事一致性檢核報告。
  </p>
  <div class="hero-badges">
    {editorial_badge("Local-first")}
    {editorial_badge("Rule-based Core")}
    {editorial_badge("Optional Ollama")}
  </div>
  <div class="hero-disclaimer">
    本系統目前採用 <strong>deterministic rules</strong> 為核心，Ollama LLM 為可選抽取輔助。
    系統不會自動改寫原文，也不會替作者決定劇情對錯，而是提供可追溯 evidence 的檢核報告，
    協助作者找出需要確認、補伏筆或修正的敘事風險。
    <br><br>
    <span class="muted-text">
    中文章節級文本為主要支援對象 · 本地端 MVP · 系統輸出需人工確認
    </span>
  </div>
</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(kicker: str, number: str, title: str, desc: str) -> None:
    st.markdown(
        f"""
<div class="section-intro">
  <div class="gold-rule"></div>
  <div class="section-kicker">{_esc(kicker)}</div>
  <h3 class="section-title">{_esc(number)}｜{_esc(title)}</h3>
  <p class="section-desc">{_esc(desc)}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_section_rule() -> None:
    st.markdown('<hr class="section-rule">', unsafe_allow_html=True)


def graph_iframe_height(node_count: int) -> int:
    if node_count <= 0:
        return 220
    return max(280, min(460, 160 + node_count * 22))


def render_metric_cards(report: AnalysisReport | None) -> None:
    items = [
        ("Characters", report.entity_counts.get("characters", 0) if report else "—", "角色實體"),
        ("Locations", report.entity_counts.get("locations", 0) if report else "—", "地點實體"),
        ("Objects", report.entity_counts.get("objects", 0) if report else "—", "物品實體"),
        ("Events", report.entity_counts.get("events", 0) if report else "—", "敘事事件"),
        ("World Rules", report.entity_counts.get("world_rules", 0) if report else "—", "世界規則"),
        ("Conflicts", len(report.conflicts) if report else "—", "檢出衝突"),
    ]
    cards = "".join(
        f"""
<div class="metric-card">
  <div class="metric-label">{_esc(label)}</div>
  <div class="metric-value">{value}</div>
  <div class="metric-hint">{_esc(hint)}</div>
</div>
        """
        for label, value, hint in items
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)
    if report:
        st.markdown(
            f'<p class="muted-text">chunk_count = {report.chunk_count} · '
            f'分析時間：{report.generated_at.strftime("%Y-%m-%d %H:%M")}</p>',
            unsafe_allow_html=True,
        )


def render_chunk_card(chunk: Chunk, preview_len: int = 120) -> str:
    preview = chunk.text[:preview_len] + ("…" if len(chunk.text) > preview_len else "")
    return f"""
<div class="chunk-card">
  <div class="chunk-meta">
    <span>Chunk #{chunk.index + 1}</span>
    <span>·</span>
    <span>{_esc(chunk.kind)}</span>
    <span>·</span>
    <span>{chunk.start_char} – {chunk.end_char}</span>
  </div>
  <div class="chunk-title">{_esc(chunk.chapter_title or f"區塊 {chunk.index + 1}")}</div>
  <div class="manuscript-preview">「{_esc(preview)}」</div>
</div>
    """


def render_conflict_card(conflict: ConflictReport) -> str:
    sev = conflict.severity if conflict.severity in ("high", "medium", "low") else "medium"
    sev_cls = f"conflict-card-{sev}"
    ctype = CONFLICT_TYPE_LABELS.get(conflict.conflict_type, conflict.conflict_type)
    sev_label = SEVERITY_LABELS.get(conflict.severity, conflict.severity)

    entities = ""
    if conflict.related_entities:
        entities = (
            f'<div class="related-entities">相關實體：{_esc(", ".join(conflict.related_entities))}</div>'
        )

    ev_a = _esc((conflict.evidence_a or "").strip())
    ev_b = _esc((conflict.evidence_b or "").strip())

    suggested = ""
    if conflict.suggested_fix:
        suggested = f"""
<div class="suggested-fix-block">
  <div class="fix-label">Suggested Fix</div>
  <div>{_esc(conflict.suggested_fix)}</div>
</div>
        """

    sev_kind = "danger" if sev == "high" else "warning" if sev == "medium" else "info"

    return f"""
<div class="conflict-card {sev_cls}">
  <div class="conflict-header">
    {status_badge(ctype)}
    {status_badge(f"Severity · {sev_label}", sev_kind)}
  </div>
  <div class="conflict-title">{_esc(conflict.title)}</div>
  {entities}
  <div class="claim-block">
    <div class="claim-label">Claim A</div>
    <div class="claim-text">{_esc(conflict.claim_a)}</div>
  </div>
  <div class="claim-block">
    <div class="claim-label">Claim B</div>
    <div class="claim-text">{_esc(conflict.claim_b)}</div>
  </div>
  <div class="evidence-block">
    <div class="evidence-label">Evidence A</div>
    <div class="evidence-text">「{ev_a}」</div>
  </div>
  <div class="evidence-block">
    <div class="evidence-label">Evidence B</div>
    <div class="evidence-text">「{ev_b}」</div>
  </div>
  <div class="explanation-block"><strong>說明：</strong>{_esc(conflict.explanation)}</div>
  {suggested}
</div>
    """


def check_pyvis_available() -> bool:
    try:
        import pyvis  # noqa: F401
        return True
    except ImportError:
        return False


def resolve_analysis_mode(use_llm: bool, ollama_connected: bool) -> str:
    if use_llm and ollama_connected:
        return "Ollama-assisted extraction"
    if use_llm and not ollama_connected:
        return "Heuristic only (Ollama fallback)"
    return "Heuristic only"


def render_ai_status_card(
    use_llm: bool,
    ollama_model: str,
    ollama_connected: bool,
    last_mode: str | None = None,
) -> None:
    mode = resolve_analysis_mode(use_llm, ollama_connected)
    conn_label = "Connected" if ollama_connected else "Unavailable"
    conn_kind = "success" if ollama_connected else "warning"
    llm_active = use_llm and ollama_connected

    ai_items = [
        ("Entity extraction", llm_active),
        ("Event extraction", llm_active),
        ("World rule extraction", llm_active),
        ("Optional report summary", False),
    ]
    ai_list = "".join(
        f'<li class="{"ai-on" if on else "ai-off"}">'
        f'{_esc(label)}{"" if on else "（未啟用）"}</li>'
        for label, on in ai_items
    )
    rule_list = "".join(
        f'<li class="rule-on">{_esc(item)}</li>'
        for item in (
            "Conflict detection",
            "Evidence matching",
            "JSON report generation",
        )
    )
    last_run = (
        f'<div class="ai-status-row"><span class="label">Last Run</span>'
        f'<span class="value">{_esc(last_mode)}</span></div>'
        if last_mode
        else ""
    )

    st.markdown(
        f"""
<div class="ai-status-card">
  <div class="ai-status-title">Hybrid AI Architecture</div>
  <div class="ai-status-row">
    <span class="label">Analysis Mode</span>
    <span class="value">{_esc(mode)}</span>
  </div>
  <div class="ai-status-row">
    <span class="label">Model Name</span>
    <span class="value">{_esc(ollama_model if use_llm else "—")}</span>
  </div>
  <div class="ai-status-row">
    <span class="label">Ollama Status</span>
    <span class="value">{status_badge(conn_label, conn_kind)}</span>
  </div>
  {last_run}
  <div class="ai-status-row" style="margin-top:0.5rem">
    <span class="label">AI Used For</span><span class="value"></span>
  </div>
  <ul class="ai-role-list">{ai_list}</ul>
  <div class="ai-status-row" style="margin-top:0.35rem">
    <span class="label">Rule-based Core</span><span class="value"></span>
  </div>
  <ul class="ai-role-list">{rule_list}</ul>
  <div class="ai-hybrid-note">
    本系統採用 hybrid AI 架構。LLM 用於輔助語意抽取，確定性規則用於衝突檢核，以提高可解釋性與穩定性。
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_mode_comparison(result: dict) -> None:
    heur = result["heuristic"]
    ollama = result.get("ollama")
    deltas = (result.get("comparison") or {}).get("entity_deltas") or {}
    overlap = (result.get("comparison") or {}).get("conflict_overlap")
    interp = (result.get("comparison") or {}).get("interpretation", "")

    rows = ""
    for key, h_val in heur["entity_counts"].items():
        o_val = ollama["entity_counts"].get(key, 0) if ollama else None
        delta = deltas.get(key)
        if delta is None:
            delta_str = "—"
            row_cls = ""
        else:
            delta_str = f"{delta:+d}" if delta else "0"
            row_cls = "delta-positive" if delta > 0 else "delta-negative" if delta < 0 else ""
        rows += (
            f'<tr class="{row_cls}"><td>{_esc(key)}</td>'
            f'<td class="num">{h_val}</td>'
            f'<td class="num">{o_val if o_val is not None else "—"}</td>'
            f'<td class="num">{delta_str}</td></tr>'
        )

    overlap_html = ""
    if overlap:
        overlap_html = f"""
<p class="muted-text" style="margin-top:0.75rem">
  衝突一致：<strong>{overlap["shared_count"]}</strong> ·
  僅 Heuristic：<strong>{overlap["only_heuristic_count"]}</strong> ·
  僅 Ollama：<strong>{overlap["only_ollama_count"]}</strong>
</p>
        """

    st.markdown(
        f"""
<div class="export-card" style="margin-top:1rem">
  {status_badge("Mode Comparison", "info")}
  <p class="muted-text" style="margin:0.65rem 0 0">
    模型：<code>{_esc(result.get("model", ""))}</code> ·
    Ollama：{"已連線" if result.get("ollama_used") else "未使用"}
  </p>
  <table class="compare-table">
    <thead>
      <tr><th>項目</th><th>Heuristic</th><th>Ollama</th><th>Δ</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p class="muted-text" style="margin-top:0.75rem">
    衝突數 — Heuristic：<strong>{heur["conflict_total"]}</strong>
    {f' · Ollama：<strong>{ollama["conflict_total"]}</strong>' if ollama else ""}
  </p>
  {overlap_html}
  <p class="muted-text" style="margin-top:0.5rem;font-style:italic">{_esc(interp)}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_evaluation_section() -> None:
    st.markdown(
        """
<div class="evaluation-card">
  <div class="gold-rule"></div>
  <div class="section-kicker">Offline Evaluation</div>
  <h3 class="section-title">Evaluation-ready Output</h3>
  <p class="section-desc">
    本系統輸出的 JSON report 可與人工 ground truth 比對，
    計算 TP、FP、FN、Precision、Recall、F1 與 Evidence Accuracy。
  </p>
  <table class="eval-table">
    <thead>
      <tr><th>指標</th><th>意義</th></tr>
    </thead>
    <tbody>
      <tr><td>TP</td><td>抓對的衝突</td></tr>
      <tr><td>FP</td><td>誤判</td></tr>
      <tr><td>FN</td><td>漏抓</td></tr>
      <tr><td>Precision</td><td>系統輸出的衝突中有多少是真的</td></tr>
      <tr><td>Recall</td><td>真正存在的衝突中抓到多少</td></tr>
      <tr><td>Evidence Accuracy</td><td>證據是否合理</td></tr>
    </tbody>
  </table>
  <p class="muted-text" style="margin-top:1rem">
    evaluation module 位於 <code>evaluation/</code> 目錄，可離線執行指標計算。
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="輕量智敘",
    page_icon="📋",
    layout="wide",
)

inject_global_styles()
init_db()

render_hero()

# --- Sidebar ---
with st.sidebar:
    st.markdown(
        """
<div class="hero-eyebrow" style="margin-bottom:0.5rem">Workspace</div>
<div style="font-family:'Noto Serif TC',serif;font-size:1.05rem;margin-bottom:0.25rem">
  輕量智敘
</div>
<p class="muted-text" style="margin:0">專案工作區</p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-kicker">Project Workspace</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="sidebar-kicker">Analysis Mode</div>', unsafe_allow_html=True)
    use_llm = st.checkbox("使用 Ollama LLM 抽取（可選）", value=False)
    ollama_model = st.text_input("Ollama 模型", value=OLLAMA_DEFAULT_MODEL)
    llm_check = get_llm(model=ollama_model) if use_llm else None
    ollama_connected = llm_check.is_available() if llm_check else False
    last_mode = st.session_state.get("last_analysis_mode")
    render_ai_status_card(use_llm, ollama_model, ollama_connected, last_mode)

    st.markdown('<div class="sidebar-kicker">Upload Settings</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="sidebar-kicker">System Status</div>', unsafe_allow_html=True)
    status_html = '<div class="status-row">' + status_badge("SQLite Ready", "success")
    if use_llm:
        if ollama_connected:
            status_html += status_badge("Ollama Connected", "success")
        else:
            status_html += status_badge("Ollama Unavailable", "warning")
    else:
        status_html += status_badge("Heuristic Mode", "info")
    if check_pyvis_available():
        status_html += status_badge("PyVis Available", "success")
    else:
        status_html += status_badge("PyVis Fallback", "warning")
    status_html += "</div>"
    st.markdown(status_html, unsafe_allow_html=True)

    st.markdown(
        '<p class="muted-text" style="border-top:1px solid rgba(26,26,26,0.12);'
        'margin-top:1.25rem;padding-top:0.75rem;margin-bottom:0">'
        "展示用範例文本位於 <code>samples/</code> 資料夾。</p>",
        unsafe_allow_html=True,
    )

if not project_id:
    st.stop()

project = get_project(project_id)
chunks = load_chunks(project_id)
doc = get_latest_document(project_id)
report = load_report(project_id)
extraction = load_extraction(project_id)

st.markdown(
    f"""
<div class="project-header">
  <div class="project-name">{_esc(project.name if project else "專案")}</div>
  {"<p class='muted-text' style='margin:0.35rem 0 0'>" + _esc(project.description) + "</p>" if project and project.description else ""}
</div>
    """,
    unsafe_allow_html=True,
)

# ===========================================================================
# 01｜文本上傳與分塊
# ===========================================================================
render_section_header("Manuscript Intake", "01", "文本上傳與分塊",
    "系統會先將文本切分為可分析的章節或場景區塊，避免直接把全文交給模型造成不穩定。")

uploaded = st.file_uploader("上傳故事／劇本（.txt / .md / .docx）", type=["txt", "md", "docx"])

if uploaded and st.button("匯入並分塊", type="primary", key="import_chunks"):
    try:
        text = read_upload(uploaded.name, uploaded.getvalue())
        new_doc = build_document(project_id, uploaded.name, text)
        save_document(new_doc)
        new_chunks = chunk_document(text, new_doc.id, project_id, strategy=chunk_strategy)
        save_chunks(new_chunks)
        st.success(f"已匯入 {uploaded.name}，共 {len(new_chunks)} 個區塊")
        chunks = new_chunks
        doc = new_doc
    except ValueError as exc:
        st.error(str(exc))

if chunks or doc:
    if doc:
        st.markdown(
            f'<p class="muted-text">檔案：{_esc(doc.filename)} · '
            f'上傳於 {doc.uploaded_at.strftime("%Y-%m-%d %H:%M")}</p>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<p class="muted-text">目前共有 <strong>{len(chunks)}</strong> 個文本區塊</p>',
        unsafe_allow_html=True,
    )

    if chunks:
        st.markdown('<p class="muted-text" style="margin-top:1rem">分塊預覽（前 10 塊）</p>', unsafe_allow_html=True)
        preview_html = "".join(render_chunk_card(c) for c in chunks[:10])
        st.markdown(preview_html, unsafe_allow_html=True)
        if len(chunks) > 10:
            st.caption(f"其餘 {len(chunks) - 10} 個區塊未顯示。")

    with st.expander("管理文本區塊"):
        for c in chunks:
            col_main, col_del = st.columns([5, 1])
            with col_main:
                st.markdown(render_chunk_card(c, preview_len=80), unsafe_allow_html=True)
            with col_del:
                if st.button("刪除", key=f"del_chunk_{c.id}", type="secondary"):
                    delete_chunk(project_id, c.id)
                    st.toast(f"已刪除區塊：{c.chapter_title}")
                    st.rerun()

    with st.expander("清除全部文本"):
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
        if st.button("清除全部上傳文本", type="primary", disabled=not confirm_clear):
            clear_project_text(project_id, clear_analysis=also_analysis)
            st.success("已清除上傳文本" + ("與分析結果" if also_analysis else ""))
            st.rerun()
else:
    st.info("請上傳 .txt / .md / .docx 文本以開始分析。")

render_section_rule()

# ===========================================================================
# 02｜抽取結果總覽
# ===========================================================================
render_section_header("Extraction Summary", "02", "抽取結果總覽",
    "以下統計來自目前文本的 heuristic / optional LLM 抽取結果，可作為後續衝突檢查的基礎。")

if not chunks:
    st.warning("請先在上傳區匯入文本。")
elif st.button("執行敘事分析", type="primary", key="run_analysis"):
    with st.spinner("抽取實體與事件、偵測衝突…"):
        llm = get_llm(model=ollama_model) if use_llm else None
        connected = llm.is_available() if llm else False
        report, extraction = generate_full_report(
            project_id, chunks, use_llm=use_llm, llm=llm
        )
        st.session_state["last_analysis_mode"] = resolve_analysis_mode(use_llm, connected)
        st.session_state["last_ollama_model"] = ollama_model if use_llm else None
    st.success("分析完成")
    st.rerun()
else:
    render_ai_status_card(
        use_llm,
        ollama_model,
        ollama_connected if use_llm else False,
        st.session_state.get("last_analysis_mode"),
    )
    if report:
        render_metric_cards(report)
        st.markdown(
            '<p class="muted-text">衝突結果以 7 條 deterministic rules 判定，非 LLM 判斷。'
            "系統產出需要人工確認。</p>",
            unsafe_allow_html=True,
        )
    else:
        render_metric_cards(None)
        st.info("尚未執行分析，請點擊上方按鈕開始。")

    st.markdown(
        '<p class="muted-text" style="margin-top:1.25rem">'
        "<strong>Heuristic vs Ollama 比較</strong> — "
        "對同一文本分別以規則抽取與 Ollama 抽取，再以相同規則引擎檢核衝突。</p>",
        unsafe_allow_html=True,
    )
    if st.button("執行 Heuristic vs Ollama 比較", key="run_mode_compare"):
        with st.spinner("比較兩種抽取模式…（Ollama 未連線時僅顯示 Heuristic）"):
            try:
                cmp_result = compare_extraction_modes(
                    chunks, project_id=project_id, model=ollama_model
                )
                st.session_state["mode_comparison"] = cmp_result
                out_dir = ROOT / "evaluation" / "results"
                out_dir.mkdir(parents=True, exist_ok=True)
                slug = project_id[:8]
                json_path = out_dir / f"{slug}_mode_compare.json"
                md_path = out_dir / f"{slug}_mode_compare.md"
                json_path.write_text(
                    json.dumps(cmp_result, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                md_path.write_text(compare_to_markdown(cmp_result), encoding="utf-8")
                st.session_state["mode_compare_paths"] = (str(json_path), str(md_path))
            except ValueError as exc:
                st.error(str(exc))
    if st.session_state.get("mode_comparison"):
        render_mode_comparison(st.session_state["mode_comparison"])
        paths = st.session_state.get("mode_compare_paths")
        if paths:
            st.caption(f"已寫入：{paths[0]} · {paths[1]}")

render_section_rule()

# ===========================================================================
# 03｜知識圖譜
# ===========================================================================
render_section_header("Knowledge Graph", "03", "知識圖譜",
    "以圖譜方式輔助觀察角色、物品、事件與規則之間的關係。知識圖用於輔助理解，不直接代表最終判定。")

if not extraction:
    st.warning("請先執行分析以產生知識圖。")
else:
    g = build_knowledge_graph(extraction)
    stats = graph_stats(g)
    st.markdown(
        f"""
<div class="graph-stats-row">
  {status_badge(f"Nodes · {stats.get('nodes', 0)}", "info")}
  {status_badge(f"Edges · {stats.get('edges', 0)}", "info")}
  {status_badge(f"Characters · {stats.get('character', 0)}", "purple")}
  {status_badge(f"Events · {stats.get('event', 0)}", "warning")}
</div>
        """,
        unsafe_allow_html=True,
    )
    iframe_h = graph_iframe_height(stats.get("nodes", 0))
    html = graph_to_pyvis_html(g, height=f"{iframe_h}px")
    st.components.v1.html(html, height=iframe_h, scrolling=False)
    st.markdown(
        '<div class="graph-note">知識圖用於輔助理解，不直接代表最終判定。</div>',
        unsafe_allow_html=True,
    )

render_section_rule()

# ===========================================================================
# 04｜衝突檢核報告
# ===========================================================================
render_section_header("Conflict Audit", "04", "衝突檢核報告",
    "每筆衝突皆應附上原文證據。系統不直接修改故事，而是指出需要人工確認的敘事風險。")

if not report:
    st.warning("尚無報告，請先執行分析。")
elif not report.conflicts:
    st.success("未檢出敘事衝突。")
    render_metric_cards(report)
else:
    st.markdown(
        f'<p class="muted-text">共檢出 <strong>{len(report.conflicts)}</strong> 筆衝突</p>',
        unsafe_allow_html=True,
    )
    if report.conflict_counts:
        count_badges = "".join(
            status_badge(f"{CONFLICT_TYPE_LABELS.get(k, k)} · {v}", "warning")
            for k, v in report.conflict_counts.items()
        )
        st.markdown(f'<div class="status-row" style="margin:0.75rem 0">{count_badges}</div>', unsafe_allow_html=True)

    for conflict in report.conflicts:
        st.markdown(render_conflict_card(conflict), unsafe_allow_html=True)

render_section_rule()

# ===========================================================================
# 05｜報告匯出
# ===========================================================================
render_section_header("Report Export", "05", "報告匯出",
    "匯出的 JSON 可用於後續 evaluation module，與人工 ground truth 比對 TP、FP、FN 與證據品質。")

if not report:
    st.warning("尚無報告可匯出，請先執行分析。")
else:
    col_export, col_info = st.columns([1, 2])
    with col_export:
        if st.button("匯出 JSON 報告", type="primary", key="export_json"):
            path = export_report_json(report)
            st.session_state["last_export_path"] = str(path)
            st.success("已匯出")
    with col_info:
        export_path = st.session_state.get(
            "last_export_path", f"exports/report_{report.project_id[:8]}.json"
        )
        st.markdown(
            f"""
<div class="export-card">
  {status_badge("Evaluation-ready", "success")}
  <p class="muted-text" style="margin:0.75rem 0 0">
    <strong>匯出路徑：</strong><code>{_esc(export_path)}</code><br>
    <strong>最後生成時間：</strong>{report.generated_at.strftime("%Y-%m-%d %H:%M:%S")}<br>
    <strong>提醒：</strong>JSON 可用於 evaluation module 離線比對 ground truth。
  </p>
</div>
            """,
            unsafe_allow_html=True,
        )

render_evaluation_section()

st.markdown(
    """
<div class="evaluation-card footer-note">
  <div class="section-kicker">System Limits</div>
  <p class="muted-text" style="margin:0;line-height:1.8">
    <strong>誠實說明</strong><br>
    · heuristic 抽取仍可能誤判；Ollama 僅為可選抽取輔助<br>
    · 衝突判斷以 7 條規則為主，<strong>不是</strong>完整時間線引擎<br>
    · 只提供 suggested_fix 建議，<strong>不會</strong>自動修稿<br>
    · HuggingFace / FastAPI 尚未接線（future work）<br>
    · 中文章節級文本為目前主要支援範圍；系統輸出需人工確認
  </p>
</div>
    """,
    unsafe_allow_html=True,
)
