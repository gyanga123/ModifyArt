"""配置模块 — 从 backend/.env 读取 API key，统一管理路径"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path("d:/project file/ModifyArt")
BACKEND_DIR = PROJECT_ROOT / "backend"
NOVEL_PATH = PROJECT_ROOT / "【改】逆世天途_utf8.txt"
ANALYZER_DIR = PROJECT_ROOT / "story-analyzer"
OUTPUT_DIR = ANALYZER_DIR / "output"
PROMPTS_DIR = ANALYZER_DIR / "prompts"

# 输出文件
STORY_SUMMARY_PATH = OUTPUT_DIR / "story_summary.md"
CHARACTER_PROFILES_PATH = OUTPUT_DIR / "character_profiles.md"
WRITING_TECHNIQUE_PATH = OUTPUT_DIR / "writing_technique.md"
REPETITION_ANALYSIS_PATH = OUTPUT_DIR / "repetition_analysis.md"
LOGIC_ANALYSIS_PATH = OUTPUT_DIR / "logic_analysis.md"

# 进度文件（记录已处理到哪一章）
PROGRESS_PATH = ANALYZER_DIR / ".progress.json"

# DeepSeek API
DEEPSEEK_API_KEY = None
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"    # Phase 1 用
DEEPSEEK_REASONER = "deepseek-reasoner" # Phase 2 用

# Batch 大小
BATCH_SIZE = 3


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
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
