"""章节解析器 — 将小说原文按章节切分"""

import re
from dataclasses import dataclass, field


@dataclass
class Chapter:
    number: int
    title: str
    content: str

    @property
    def header(self) -> str:
        return f"第{self.number}章：{self.title}"

    @property
    def full_text(self) -> str:
        return f"{self.header}\n{self.content}"


def parse_chapters(filepath: str) -> list[Chapter]:
    """
    解析小说文件，返回章节列表。

    章节格式：
        第N章：标题
        ...内容...
        逆世天途  （分隔符）
        第N+1章：标题
    """
    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    # 按 "逆世天途" 分隔章节（排除开头标题行的那个）
    # 先找到所有章节标题行
    chapter_pattern = re.compile(r"^第(\d+)章[：:](.+)$", re.MULTILINE)
    matches = list(chapter_pattern.finditer(text))

    if not matches:
        raise ValueError("未找到任何章节，请检查文件格式")

    chapters = []
    for i, match in enumerate(matches):
        num = int(match.group(1))
        title = match.group(2).strip()
        start = match.end()

        # 内容到下一个章节标题前或文件末尾
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        content = text[start:end].strip()
        chapters.append(Chapter(number=num, title=title, content=content))

    # 检查是否有重复章节号
    seen = set()
    for ch in chapters:
        if ch.number in seen:
            print(f"  [警告] 重复章节号: 第{ch.number}章「{ch.title}」")
        seen.add(ch.number)

    print(f"共解析到 {len(chapters)} 个章节（去重后: {len(seen)} 个唯一章节号）")
    return chapters


def get_chapter_by_number(chapters: list[Chapter], number: int) -> Chapter | None:
    """按章节号查找"""
    for ch in chapters:
        if ch.number == number:
            return ch
    return None
