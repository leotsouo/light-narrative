"""應用程式設定。"""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "light_narrative.db"

# LLM
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.2"
LLM_PROVIDER = "ollama"  # ollama | huggingface
LLM_TIMEOUT_SECONDS = 120

# 分塊
DEFAULT_CHUNK_MAX_CHARS = 2500
CHAPTER_PATTERNS = [
    # 新版 chunker 主要使用內建 regex；此處保留作為其他模組可用的章節提示
    r"^(?:##\s*)?第[零一二三四五六七八九十百\d]+章[：:].*$",
    r"^第[零一二三四五六七八九十百\d]+章[：:].*$",
    r"^Chapter\s+\d+",
]
SCENE_SEPARATORS = ("---", "***", "＊＊＊", "———")

# 衝突嚴重度閾值
SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
