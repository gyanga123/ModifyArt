#!/usr/bin/env python3
"""story-analyzer 主管线 — Phase 1: 分批处理 + Phase 2: 深度分析"""

import json
import sys
import time
import re
from pathlib import Path

from openai import OpenAI

import config
from chapter_parser import parse_chapters, Chapter


# ─── 辅助函数 ───────────────────────────────────────────────


def read_file(path: Path) -> str:
    """读取文件，不存在则返回空字符串"""
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


def append_file(path: Path, text: str):
    """追加内容到文件"""
    with open(path, "a", encoding="utf-8") as f:
        f.write(text.strip() + "\n\n")
    print(f"  → 已追加到 {path.name}")


def write_file(path: Path, text: str):
    """覆写文件"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")
    print(f"  → 已写入 {path.name}")


def load_progress() -> int:
    """读取进度：已处理到第几章"""
    if config.PROGRESS_PATH.exists():
        with open(config.PROGRESS_PATH) as f:
            data = json.load(f)
            return data.get("last_chapter", 0)
    return 0


def save_progress(chapter: int):
    """保存进度"""
    data = {
        "last_chapter": chapter,
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(config.PROGRESS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── DeepSeek API ───────────────────────────────────────────


def call_deepseek(prompt: str, model: str = None, temperature: float = 0.3) -> str:
    """调用 DeepSeek API，返回响应文本"""
    api_key = config.load_api_key()
    client = OpenAI(api_key=api_key, base_url=config.DEEPSEEK_BASE_URL)

    model = model or config.DEEPSEEK_MODEL

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=4096,
    )

    return response.choices[0].message.content


# ─── 提示词构建 ─────────────────────────────────────────────


def build_phase1_prompt(
    batch: list[Chapter],
    existing_summary: str,
    existing_profiles: str,
    existing_technique: str = "",
) -> str:
    """构建 Phase 1 批处理的提示词"""
    prompt_template = read_file(config.PROMPTS_DIR / "phase1_batch.txt")

    # 组装章节文本
    chapters_text = ""
    for ch in batch:
        chapters_text += f"\n### {ch.header}\n\n{ch.content}\n"
        chapters_text += "---\n"

    return prompt_template.replace("{existing_story_summary}", existing_summary or "（暂无）")\
                          .replace("{existing_character_profiles}", existing_profiles or "（暂无）")\
                          .replace("{existing_writing_technique}", existing_technique or "（暂无）")\
                          .replace("{chapters}", chapters_text.strip())


def build_phase2_prompt(template_name: str, summary: str, profiles: str, technique: str = "") -> str:
    """构建 Phase 2 分析提示词"""
    template = read_file(config.PROMPTS_DIR / template_name)
    return template.replace("{story_summary}", summary)\
                   .replace("{character_profiles}", profiles)\
                   .replace("{writing_technique}", technique or "（暂无）")


# ─── 响应解析 ───────────────────────────────────────────────


def split_phase1_response(response: str) -> tuple[str, str, str]:
    """
    将 API 返回拆分为「故事概要」「人物小传更新」「写作手法记录」三部分。
    返回 (summary_section, profile_section, technique_section)
    """
    summary_part = ""
    profile_part = ""
    technique_part = ""

    # 按 ## 标题切分
    sections = re.split(r"\n(?=## )", response)

    # 对于每个切块，检查是否嵌入了下级标题（### 第二部分/第三部分）
    # 这是因为模型有时会用 ### 而非 ## 写 section 标题
    refined = []
    for sec in sections:
        if "### 第二部分：人物小传更新" in sec:
            sub = re.split(r"\n(?=### 第二部分：人物小传更新)", sec)
            refined.extend(sub)
        elif "### 第三部分：写作手法记录" in sec:
            sub = re.split(r"\n(?=### 第三部分：写作手法记录)", sec)
            refined.extend(sub)
        else:
            refined.append(sec)

    # 第二轮：如果某个块内还嵌着另一部分（如第二部分块内嵌第三部分）
    refined2 = []
    for sec in refined:
        if "### 第三部分：写作手法记录" in sec:
            sub = re.split(r"\n(?=### 第三部分：写作手法记录)", sec)
            refined2.extend(sub)
        else:
            refined2.append(sec)

    for sec in refined2:
        if "故事概要" in sec[:40]:
            summary_part = sec.strip()
        elif "人物小传更新" in sec[:40]:
            profile_part = sec.strip()
        elif "写作手法记录" in sec[:40]:
            technique_part = sec.strip()

    if not summary_part:
        print("  [警告] 未能从响应中解析出「故事概要」部分")
        summary_part = response

    if not technique_part:
        print("  [提示] 本次未输出写作手法记录（可能章节过短或无典型特征）")

    return summary_part, profile_part, technique_part


# ─── Phase 1 ────────────────────────────────────────────────


def run_phase1(start_from: int = 0):
    """Phase 1: 分批处理全部章节"""
    print("=" * 60)
    print("Phase 1: 分批提取故事概要 + 人物小传")
    print(f"批次大小: {config.BATCH_SIZE} 章")
    print("=" * 60)

    # 解析章节
    chapters = parse_chapters(str(config.NOVEL_PATH))
    if start_from > 0:
        print(f"从第 {start_from} 章之后继续")

    # 过滤出待处理的章节
    remaining = [c for c in chapters if c.number > start_from]
    print(f"待处理章节: {len(remaining)} 章 ({remaining[0].number}-{remaining[-1].number})")

    # 分批处理
    total_batches = (len(remaining) + config.BATCH_SIZE - 1) // config.BATCH_SIZE
    batch_count = 0

    for i in range(0, len(remaining), config.BATCH_SIZE):
        batch = remaining[i:i + config.BATCH_SIZE]
        batch_count += 1
        ch_start = batch[0].number
        ch_end = batch[-1].number

        print(f"\n[{batch_count}/{total_batches}] 处理 第{ch_start}章-第{ch_end}章 ...")

        # 读已有的 md 文件作为上下文
        existing_summary = read_file(config.STORY_SUMMARY_PATH)
        existing_profiles = read_file(config.CHARACTER_PROFILES_PATH)
        existing_technique = read_file(config.WRITING_TECHNIQUE_PATH)

        # 构建 prompt 并调用 API
        prompt = build_phase1_prompt(batch, existing_summary, existing_profiles, existing_technique)
        response = call_deepseek(prompt)

        if not response:
            print("  [错误] API 返回空响应，跳过此批")
            continue

        # 解析响应（三部分）
        summary_section, profile_section, technique_section = split_phase1_response(response)

        # 追加到文件
        if summary_section:
            append_file(config.STORY_SUMMARY_PATH, summary_section)

        if profile_section:
            append_file(config.CHARACTER_PROFILES_PATH, profile_section)

        if technique_section:
            append_file(config.WRITING_TECHNIQUE_PATH, technique_section)

        # 保存进度
        save_progress(ch_end)

        # 批次间隔（避免限流）
        if batch_count < total_batches:
            time.sleep(1)

    print(f"\n✓ Phase 1 完成！共处理 {batch_count} 批，{len(remaining)} 章")
    print(f"  → 故事概要: {config.STORY_SUMMARY_PATH}")
    print(f"  → 人物小传: {config.CHARACTER_PROFILES_PATH}")
    print(f"  → 写作手法记录: {config.WRITING_TECHNIQUE_PATH}")


# ─── Phase 2 ────────────────────────────────────────────────


def run_phase2():
    """Phase 2: 基于已生成的材料做深度分析"""
    print("\n" + "=" * 60)
    print("Phase 2: 深度分析（重复模式 + 逻辑一致性）")
    print("=" * 60)

    # 读取 Phase 1 产出
    summary = read_file(config.STORY_SUMMARY_PATH)
    profiles = read_file(config.CHARACTER_PROFILES_PATH)
    technique = read_file(config.WRITING_TECHNIQUE_PATH)

    if not summary or len(summary) < 100:
        print("[错误] 故事概要为空或太短，请先运行 Phase 1")
        return
    if not profiles or len(profiles) < 100:
        print("[错误] 人物小传为空或太短，请先运行 Phase 1")
        return

    print(f"故事概要: {len(summary)} 字符")
    print(f"人物小传: {len(profiles)} 字符")
    print(f"写作手法记录: {len(technique)} 字符")
    print()

    # ── 重复模式分析 ──
    print("[分析 1/2] 重复模式分析 ...")
    repetition_prompt = build_phase2_prompt(
        "phase2_repetition.txt", summary, profiles, technique
    )
    repetition_result = call_deepseek(repetition_prompt)

    if repetition_result:
        write_file(config.REPETITION_ANALYSIS_PATH, repetition_result)
    else:
        print("  [错误] 重复分析 API 返回空")

    time.sleep(1)

    # ── 逻辑一致性分析 ──
    print("[分析 2/2] 逻辑一致性分析 ...")
    logic_prompt = build_phase2_prompt("phase2_logic.txt", summary, profiles)
    logic_result = call_deepseek(logic_prompt)

    if logic_result:
        write_file(config.LOGIC_ANALYSIS_PATH, logic_result)
    else:
        print("  [错误] 逻辑分析 API 返回空")

    print(f"\n✓ Phase 2 完成！")
    print(f"  → 重复模式分析: {config.REPETITION_ANALYSIS_PATH}")
    print(f"  → 逻辑一致性分析: {config.LOGIC_ANALYSIS_PATH}")


# ─── 主入口 ─────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="story-analyzer — 小说分析管线")
    parser.add_argument("--phase", choices=["1", "2", "all"], default="1",
                        help="运行阶段: 1=分批提取, 2=深度分析, all=全部")
    parser.add_argument("--resume", action="store_true",
                        help="从上次进度处继续 Phase 1")
    parser.add_argument("--from-chapter", type=int, default=0,
                        help="从指定章节后开始处理")

    args = parser.parse_args()
    config.ensure_dirs()

    if args.phase in ("1", "all"):
        start_from = 0
        if args.resume:
            start_from = load_progress()
            print(f"检测到上次进度: 第 {start_from} 章")
        if args.from_chapter:
            start_from = args.from_chapter

        run_phase1(start_from=start_from)

    if args.phase in ("2", "all"):
        run_phase2()


if __name__ == "__main__":
    main()
