"""將長文本分割為章節／場景／區塊。"""
from __future__ import annotations

import re

from src.config import DEFAULT_CHUNK_MAX_CHARS, SCENE_SEPARATORS
from src.schemas import Chunk


CHAPTER_HEADING_RE = re.compile(
    r"^(?:##\s*)?(第[零一二三四五六七八九十百\d]+章(?:[：:\s].+)?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_chapter_index(title: str) -> int | None:
    """
    從「第零章」「第八章」等解析章節序號（0-based）。
    支援：零一二三四五六七八九十百、以及阿拉伯數字。
    """
    m = re.search(r"第([零一二三四五六七八九十百\d]+)章", title)
    if not m:
        return None
    token = m.group(1)
    if token.isdigit():
        return int(token)

    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if token in digits:
        return digits[token]

    # 簡單處理十/百（MVP 足夠）
    total = 0
    current = 0
    for ch in token:
        if ch in digits:
            current = digits[ch]
        elif ch == "十":
            total += (current or 1) * 10
            current = 0
        elif ch == "百":
            total += (current or 1) * 100
            current = 0
        else:
            return None
    total += current
    return total if total >= 0 else None


def split_by_chapters(text: str) -> list[dict]:
    """
    依章節標題切分並保留 char span。
    回傳：
      {
        "chapter_index": int,
        "chapter_title": str,
        "text": str,
        "start_char": int,
        "end_char": int
      }[]
    """
    matches = list(CHAPTER_HEADING_RE.finditer(text))
    if not matches:
        cleaned = text.strip()
        return [
            {
                "chapter_index": 0,
                "chapter_title": "全文",
                "text": cleaned,
                "start_char": 0,
                "end_char": len(cleaned),
            }
        ]

    sections: list[dict] = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip("\n")
        start_char = body_start
        end_char = body_end
        chapter_index = _parse_chapter_index(title)
        if chapter_index is None:
            chapter_index = i
        sections.append(
            {
                "chapter_index": chapter_index,
                "chapter_title": title,
                "text": body.strip(),
                "start_char": start_char,
                "end_char": end_char,
            }
        )
    return [s for s in sections if s["text"] or s["chapter_title"]]


def split_by_scenes(text: str) -> list[tuple[str, str]]:
    parts: list[str] = [text]
    for sep in SCENE_SEPARATORS:
        new_parts: list[str] = []
        for part in parts:
            new_parts.extend(re.split(rf"\n\s*{re.escape(sep)}\s*\n", part))
        parts = new_parts
    return [(f"場景 {i + 1}", p.strip()) for i, p in enumerate(parts) if p.strip()]


def split_fixed(text: str, max_chars: int = DEFAULT_CHUNK_MAX_CHARS) -> list[tuple[str, str]]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para) + 2

    if current:
        chunks.append("\n\n".join(current))

    return [(f"區塊 {i + 1}", c) for i, c in enumerate(chunks)]


def chunk_document(
    text: str,
    document_id: str,
    project_id: str,
    strategy: str = "auto",
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
) -> list[Chunk]:
    """
    strategy: auto | chapter | scene | fixed
    auto: 先章節，章內再場景；單段過長則 fixed
    """
    raw_sections: list[dict] = []  # chapter_title, text, kind, chapter_index, start_char, end_char

    if strategy in ("auto", "chapter"):
        chapters = split_by_chapters(text)
        if len(chapters) > 1 or strategy == "chapter":
            for chap in chapters:
                title = chap["chapter_title"]
                body = chap["text"]
                if len(body) > max_chars * 1.5:
                    for st, sub in split_by_scenes(body):
                        raw_sections.append(
                            {
                                "chapter_title": f"{title} - {st}",
                                "text": sub,
                                "kind": "scene",
                                "chapter_index": chap["chapter_index"],
                                "start_char": chap["start_char"],
                                "end_char": chap["end_char"],
                            }
                        )
                else:
                    scenes = split_by_scenes(body)
                    if len(scenes) > 1:
                        for st, sub in scenes:
                            raw_sections.append(
                                {
                                    "chapter_title": f"{title} - {st}",
                                    "text": sub,
                                    "kind": "scene",
                                    "chapter_index": chap["chapter_index"],
                                    "start_char": chap["start_char"],
                                    "end_char": chap["end_char"],
                                }
                            )
                    else:
                        raw_sections.append(
                            {
                                "chapter_title": title,
                                "text": body,
                                "kind": "chapter",
                                "chapter_index": chap["chapter_index"],
                                "start_char": chap["start_char"],
                                "end_char": chap["end_char"],
                            }
                        )
        elif strategy == "chapter":
            cleaned = text.strip()
            raw_sections.append(
                {
                    "chapter_title": "全文",
                    "text": cleaned,
                    "kind": "chapter",
                    "chapter_index": 0,
                    "start_char": 0,
                    "end_char": len(cleaned),
                }
            )

    if not raw_sections:
        if strategy in ("auto", "scene"):
            scenes = split_by_scenes(text)
            if len(scenes) > 1:
                raw_sections = [
                    {
                        "chapter_title": t,
                        "text": b,
                        "kind": "scene",
                        "chapter_index": i,
                        "start_char": 0,
                        "end_char": 0,
                    }
                    for i, (t, b) in enumerate(scenes)
                ]
        if not raw_sections:
            raw_sections = [
                {
                    "chapter_title": t,
                    "text": b,
                    "kind": "chunk",
                    "chapter_index": i,
                    "start_char": 0,
                    "end_char": 0,
                }
                for i, (t, b) in enumerate(split_fixed(text, max_chars))
            ]

    chunks: list[Chunk] = []
    for idx, section in enumerate(raw_sections):
        body = (section.get("text") or "").strip()
        if not body:
            continue
        chunks.append(
            Chunk(
                document_id=document_id,
                project_id=project_id,
                index=idx,
                chapter_index=int(section.get("chapter_index") or idx),
                chapter_title=str(section.get("chapter_title") or ""),
                text=body,
                kind=str(section.get("kind") or "chunk"),
                start_char=int(section.get("start_char") or 0),
                end_char=int(section.get("end_char") or 0),
            )
        )
    if not chunks and text.strip():
        cleaned = text.strip()
        chunks.append(
            Chunk(
                document_id=document_id,
                project_id=project_id,
                index=0,
                chapter_index=0,
                chapter_title="全文",
                text=cleaned,
                kind="chunk",
                start_char=0,
                end_char=len(cleaned),
            )
        )
    return chunks
