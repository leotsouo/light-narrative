"""分塊模組測試。"""

from src.chunker import chunk_document


def test_chunk_document_markdown_chapters() -> None:
    text = """## 第零章：世界觀設定
內容 A

## 第一章：鐘塔失竊
內容 B

## 第二章：隊長的命令
內容 C
"""
    chunks = chunk_document(text, document_id="doc1", project_id="proj1", strategy="chapter")
    assert len(chunks) == 3
    assert chunks[0].chapter_title == "第零章：世界觀設定"
    assert chunks[1].chapter_title == "第一章：鐘塔失竊"
    assert chunks[2].chapter_title == "第二章：隊長的命令"
    assert chunks[0].chapter_index == 0
    assert chunks[2].chapter_index == 2
    assert chunks[0].start_char <= chunks[0].end_char
