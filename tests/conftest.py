import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """測試使用獨立 SQLite，避免污染正式資料庫。"""
    db_path = tmp_path / "test_light_narrative.db"
    monkeypatch.setattr("src.config.DB_PATH", db_path)
    monkeypatch.setattr("src.storage.DB_PATH", db_path)
    from src.storage import init_db

    init_db()
