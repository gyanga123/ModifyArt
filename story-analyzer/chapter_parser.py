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


# 中文数字 → 阿拉伯数字
_CN_NUMS = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,
            "百":100,"千":1000}


def _cn_to_int(s: str) -> int:
    """中文数字转阿拉伯数字，如 '十二' → 12, '二十一' → 21, '一百零三' → 103"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    total = 0
    curr = 0
    for ch in s:
        val = _CN_NUMS.get(ch)
        if val is None:
            continue
        if val >= 10:
            if curr == 0:
                curr = 1
            total += curr * val
            curr = 0
        else:
            curr = val
    return total + curr


def parse_chapters(filepath: str) -> list[Chapter]:
    """
    解析小说文件，返回章节列表。

    支持的章节格式：
        第N章：标题        — 阿拉伯数字 + 全角冒号
        第N章: 标题        — 阿拉伯数字 + 半角冒号
        第N章 标题         — 阿拉伯数字 + 空格
        第一/二/三章：标题  — 中文数字
        第118章续：        — 带「续」后缀（合并到上一章）
    """
    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    # 匹配章节标题：第N章（支持中文数字和阿拉伯数字，允许前导空格）
    # 忽略 【第N章】 括号格式（歧义太多）
    chapter_pattern = re.compile(
        r"^\s*第([一二三四五六七八九十百\d]+)章(续)?[\s：:]*([^【\n].*)?$",
        re.MULTILINE
    )
    matches = list(chapter_pattern.finditer(text))

    if not matches:
        raise ValueError("未找到任何章节，请检查文件格式")

    chapters = []
    prev_continued = False
    for i, match in enumerate(matches):
        num_str = match.group(1).strip()
        is_continued = bool(match.group(2))  # 带「续」标记
        title = (match.group(3) or "").strip()

        num = _cn_to_int(num_str)

        start = match.end()

        # 内容到下一个章节标题前或文件末尾
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        content = text[start:end].strip()

        # 如果上一章带「续」，合并到上一章
        if prev_continued and chapters:
            chapters[-1].content += "\n" + content
            chapters[-1].title += "（续）"
            prev_continued = False
            continue

        if is_continued:
            # 这一章带续，先创建，下一轮合并
            chapters.append(Chapter(number=num, title=title, content=content))
            prev_continued = True
            continue

        chapters.append(Chapter(number=num, title=title, content=content))

    # 过滤：内容太短（<50字）的判断为解析碎片，剔除
    # 同时处理重复：同章号保留内容较长的那个
    seen = {}
    for ch in chapters:
        if len(ch.content) < 50:
            continue
        if ch.number in seen:
            existing = seen[ch.number]
            if len(ch.content) > len(existing.content):
                seen[ch.number] = ch  # 保留更长的
        else:
            seen[ch.number] = ch

    filtered = list(seen.values())
    filtered.sort(key=lambda c: c.number)

    dupes = len(chapters) - len(filtered)
    if dupes:
        print(f"  [过滤] 移除了 {dupes} 个重复/碎片章节")
    print(f"共 {len(filtered)} 个章节")
    return filtered


def get_chapter_by_number(chapters: list[Chapter], number: int) -> Chapter | None:
    """按章节号查找"""
    for ch in chapters:
        if ch.number == number:
            return ch
    return None
