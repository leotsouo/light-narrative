"""儲存層測試。"""
from src.chunker import chunk_document
from src.ingest import build_document
from src.schemas import ExtractionResult
from src.storage import (
    clear_project_text,
    create_project,
    delete_chunk,
    delete_project,
    init_db,
    list_projects,
    load_chunks,
    load_extraction,
    save_chunks,
    save_document,
    save_extraction,
)


def test_clear_and_delete_chunks() -> None:
    init_db()
    project = create_project("清除測試")
    text = "第一章\n\n內容A\n\n---\n\n內容B"
    doc = build_document(project.id, "test.txt", text)
    save_document(doc)
    chunks = chunk_document(text, doc.id, project.id, strategy="scene")
    save_chunks(chunks)
    assert len(load_chunks(project.id)) == 2

    delete_chunk(project.id, chunks[0].id)
    remaining = load_chunks(project.id)
    assert len(remaining) == 1
    assert remaining[0].index == 0

    save_extraction(project.id, ExtractionResult(characters=[]))
    clear_project_text(project.id, clear_analysis=True)
    assert load_chunks(project.id) == []
    assert load_extraction(project.id) is None


def test_delete_project() -> None:
    init_db()
    project = create_project("待刪除")
    assert len(list_projects()) == 1
    assert delete_project(project.id) is True
    assert list_projects() == []
    assert delete_project(project.id) is False
