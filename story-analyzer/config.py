"""配置模块 — 从 backend/.env 读取 API key，统一管理路径"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path("d:/project file/ModifyArt")
BACKEND_DIR = PROJECT_ROOT / "backend"
ANALYZER_DIR = PROJECT_ROOT / "story-analyzer"
PROMPTS_DIR = ANALYZER_DIR / "prompts"

# ─── 当前书状态（默认：逆世天途，向后兼容）───
BOOK_NAME = "逆世天途"
NOVEL_PATH = PROJECT_ROOT / "【改】逆世天途_utf8.txt"
OUTPUT_DIR = ANALYZER_DIR / "output"
CN_OUTPUT_DIR = ANALYZER_DIR / "输出"
PROGRESS_PATH = ANALYZER_DIR / ".progress.json"

# 输出文件
STORY_SUMMARY_PATH = OUTPUT_DIR / "story_summary.md"
CHARACTER_PROFILES_PATH = OUTPUT_DIR / "character_profiles.md"
WRITING_TECHNIQUE_PATH = OUTPUT_DIR / "writing_technique.md"
REPETITION_ANALYSIS_PATH = OUTPUT_DIR / "repetition_analysis.md"
LOGIC_ANALYSIS_PATH = OUTPUT_DIR / "logic_analysis.md"

# DeepSeek API
DEEPSEEK_API_KEY = None
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"    # Phase 1 用
DEEPSEEK_REASONER = "deepseek-reasoner" # Phase 2 用

# Batch 大小
BATCH_SIZE = 3


def set_book(book_name: str, novel_path: str = None):
    """切换到指定书名的工作区

    Args:
        book_name: 书名（用于目录名和输出文件名后缀）
        novel_path: 原文txt路径（不指定则按约定查找）
    """
    global BOOK_NAME, NOVEL_PATH, OUTPUT_DIR, CN_OUTPUT_DIR, PROGRESS_PATH
    global STORY_SUMMARY_PATH, CHARACTER_PROFILES_PATH, WRITING_TECHNIQUE_PATH
    global REPETITION_ANALYSIS_PATH, LOGIC_ANALYSIS_PATH

    BOOK_NAME = book_name
    WORKSPACE_DIR = ANALYZER_DIR / "workspaces" / book_name

    OUTPUT_DIR = WORKSPACE_DIR / "output"
    CN_OUTPUT_DIR = WORKSPACE_DIR / "输出"
    PROGRESS_PATH = WORKSPACE_DIR / ".progress.json"

    STORY_SUMMARY_PATH = OUTPUT_DIR / "story_summary.md"
    CHARACTER_PROFILES_PATH = OUTPUT_DIR / "character_profiles.md"
    WRITING_TECHNIQUE_PATH = OUTPUT_DIR / "writing_technique.md"
    REPETITION_ANALYSIS_PATH = OUTPUT_DIR / "repetition_analysis.md"
    LOGIC_ANALYSIS_PATH = OUTPUT_DIR / "logic_analysis.md"

    # 原文路径：优先使用传入路径，否则按约定查找
    if novel_path:
        NOVEL_PATH = Path(novel_path)
    else:
        NOVEL_PATH = WORKSPACE_DIR / f"原文_{book_name}.txt"


def load_api_key() -> str:
    """从 backend/.env 加载 DeepSeek API key"""
    global DEEPSEEK_API_KEY
    if DEEPSEEK_API_KEY:
        return DEEPSEEK_API_KEY

    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        raise FileNotFoundError(
            f".env 文件不存在: {env_path}\n"
            f"请确保 backend/.env 中有 DEEPSEEK_API_KEY=sk-..."
        )

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                DEEPSEEK_API_KEY = line.split("=", 1)[1].strip()
                break

    if not DEEPSEEK_API_KEY:
        raise ValueError(f".env 文件中未找到 DEEPSEEK_API_KEY")

    return DEEPSEEK_API_KEY


def ensure_dirs():
    """确保输出目录存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
