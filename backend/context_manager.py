"""故事上下文管理 — 每本书一个独立的 JSON 文件
结构以人物为单元，AI 可按姓名查找、按章节过滤。
"""

import json
import re
from pathlib import Path
from datetime import datetime

CONTEXT_DIR = Path(__file__).parent.parent / "context"


def get_context_path(book_file: str) -> Path:
    book_name = Path(book_file).stem
    return CONTEXT_DIR / f"{book_name}.json"


def detect_chapter(text: str) -> str | None:
    """从文本中检测章节号。
    搜索前 5000 字符（章节标题可能在选中范围之外）。
    """
    head = text[:5000] if len(text) > 5000 else text
    # 1. 第92章 / 第 92 章 / 第九十二章
    m = re.search(r'第\s*(\d+[\-\d]*)\s*章', head)
    if m:
        return m.group(1)
    # 2. 纯数字章标记: "92." 或 "92、" 或 "92 " 在行首
    m = re.search(r'(?:^|\n)\s*(\d{1,4})[\.、\s]', head, re.MULTILINE)
    if m:
        num = int(m.group(1))
        # 只在合理范围（1-9999）内返回
        if 1 <= num <= 9999:
            return str(num)
    # 3. 备选：文本中出现 "第92" 等部分匹配
    m = re.search(r'第\s*(\d{2,4})', head)
    if m:
        return m.group(1)
    return None


def load_context(book_file: str) -> dict:
    ctx_path = get_context_path(book_file)
    if not ctx_path.exists():
        return _empty_context(book_file)
    try:
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
        for key, default in _empty_context(book_file).items():
            if key not in data:
                data[key] = default
        return data
    except Exception:
        return _empty_context(book_file)


def save_context(book_file: str, data: dict) -> Path:
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    ctx_path = get_context_path(book_file)
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return ctx_path


def format_context(data: dict, current_chapter: str | None = None) -> str:
    """将上下文格式化为 AI 可精准查找的 prompt 文本。
    current_chapter: 当前正在处理的章节号，用于过滤章节问题。
    """
    lines = ["\n--- 故事当前上下文 ---"]

    # ── 人物档案（以人物名为 key） ──
    if data.get("人物"):
        lines.append("\n【人物档案】（按姓名索引）")
        for name, info in data["人物"].items():
            gender = info.get("性别", "")
            age = info.get("年龄", "")
            identity = info.get("身份", "")
            status = info.get("状态", "存活")
            personality = info.get("性格", "")
            recent = info.get("近期变动", "")

            header = f"{name}"
            if gender or age:
                header += f" | {gender} | {age}岁"
            if identity:
                header += f" | {identity}"
            header += f" | {status}"
            lines.append(f"\n  [{header}]")
            if personality:
                lines.append(f"    性格: {personality}")
            if recent:
                lines.append(f"    近期: {recent}")

    # ── 关键事件（按章节索引） ──
    if data.get("事件"):
        lines.append("\n【关键事件】（按章节索引）")
        for ch, desc in data["事件"].items():
            lines.append(f"  {ch}: {desc}")

    # ── 世界观设定 ──
    if data.get("设定"):
        lines.append("\n【世界观/设定】")
        for key, val in data["设定"].items():
            lines.append(f"  {key}: {val}")

    # ── 章节问题：分两层 ——
    # 本章专属问题 → 必须在本章修改中解决
    # 全局问题 → 全书写作习惯，本次改写时注意避开
    fix_now: list[str] = []
    avoid_global: list[str] = []
    if data.get("章节问题"):
        avoid_global = data["章节问题"].get("全局", [])
        if current_chapter and current_chapter in data["章节问题"]:
            fix_now = data["章节问题"][current_chapter]

    if fix_now:
        ch_label = f"第{current_chapter}章" if current_chapter else "当前"
        # 区分逻辑问题和风格问题
        logic_items = [p for p in fix_now if "逻辑" in p or "矛盾" in p or "时间线" in p or "位置" in p or "因果" in p or "认知" in p]
        other_items = [p for p in fix_now if p not in logic_items]
        if logic_items:
            lines.append(f"\n【{ch_label}必须修复的逻辑问题 — 请重构场景来修复，不是润色文字】")
            for i, p in enumerate(logic_items, 1):
                lines.append(f"  {i}. {p}")
        if other_items:
            lines.append(f"\n【{ch_label}必须修复的其他问题】")
            for i, p in enumerate(other_items, 1):
                lines.append(f"  {i}. {p}")

    if avoid_global:
        lines.append("\n【全书写作时请刻意避开的模式】")
        for i, p in enumerate(avoid_global, 1):
            lines.append(f"  {i}. {p}")

    # ── 近期改动 ──
    if data.get("改动记录"):
        lines.append("\n【近期改动】")
        for date, desc in list(data["改动记录"].items())[-5:]:
            lines.append(f"  {date}: {desc}")

    lines.append("\n--- 上下文结束 ---\n")
    return "\n".join(lines)


def _empty_context(book_file: str) -> dict:
    return {
        "book": Path(book_file).stem,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "updated": "",
        "人物": {},        # { "苏曼尼": { 性别, 年龄, 身份, 状态, 性格, 近期变动 } }
        "事件": {},        # { "第5章": "泼咖啡", "第92章": "盗取设计稿" }
        "设定": {},        # { "人物关系": "...", "世界观": "..." }
        "章节问题": {},    # { "92": ["问题1", "问题2"], "全局": [...] }
        "改动记录": {},    # { "2026-05-31": "修改摘要" }
    }
