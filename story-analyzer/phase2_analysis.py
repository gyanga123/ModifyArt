#!/usr/bin/env python3
"""Phase 2 analysis via OpenSquilla Gateway HTTP API.
Avoids bash encoding issues by using Python's subprocess directly."""

import subprocess
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
PROMPTS_DIR = os.path.join(SCRIPT_DIR, "prompts")

def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def run_opensquilla_agent(message, files=None, model=None):
    """Run opensquilla agent and return the parsed JSON result."""
    cmd = ["opensquilla", "agent", "--message", message, "--json", "--timeout", "300", "--unattended"]

    if files:
        for f in files:
            cmd += ["--file", f]
    if model:
        cmd += ["--model", model]

    env = os.environ.copy()
    env["PATH"] = f"D:/tools/python;D:/tools/python/Scripts;{env.get('PATH', '')}"

    result = subprocess.run(
        cmd,
        capture_output=True,
        timeout=360,
        env=env
    )

    # stdout should contain the JSON result
    stdout = result.stdout
    stderr = result.stderr

    # Find JSON in stdout
    text = stdout.decode("utf-8", errors="replace")

    # Try to find JSON starting with {"status"
    start = text.find('{"status"')
    if start < 0:
        # Try to find any JSON object
        start = text.find('{')

    if start >= 0:
        try:
            data = json.loads(text[start:])
            return data, text[:start]  # (parsed data, any leading text)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}", file=sys.stderr)
            print(f"stdout preview: {text[:500]}", file=sys.stderr)
            return None, text
    else:
        print(f"No JSON found in output", file=sys.stderr)
        print(f"stdout: {text[:500]}", file=sys.stderr)
        return None, text

def do_logic_analysis():
    """逻辑一致性分析"""
    print("=== Phase 2: 逻辑一致性分析 ===")

    story_summary_path = os.path.join(OUTPUT_DIR, "story_summary.md")
    character_profiles_path = os.path.join(OUTPUT_DIR, "character_profiles.md")
    prompt_path = os.path.join(PROMPTS_DIR, "phase2_logic.txt")

    # Read prompt template
    prompt_template = read_file(prompt_path)

    # Build message - ask agent to read the attached files
    message = """你是一位资深的文学编辑，擅长长篇小说中的逻辑一致性分析。

请读取附件中的两份材料：
- story_summary.md = 全文故事概要
- character_profiles.md = 全文角色档案

基于以上材料，对《逆世天途》全文进行逻辑一致性分析。

## 分析要求

请从以下维度检测逻辑不一致。每个维度请给出具体章节引用和严重程度评估（轻度/中度/重度）：

1. **角色行为矛盾** — 同一角色在不同章节的行为、决策是否前后矛盾
2. **实力体系不一致** — 角色实力是否忽高忽低，缺乏合理解释
3. **设定冲突** — 前文建立的规则（如灵力体系、世界规则）是否在后文被打破
4. **时间线矛盾** — 事件发生的顺序、时间跨度是否合理
5. **角色关系/记忆不一致** — 角色间的相识关系、过往记忆是否前后矛盾
6. **动机不连贯** — 角色的目标和动机是否在半途无故改变或消失

## 输出格式

每个维度按以下 markdown 格式输出：

## 1. 角色行为矛盾

**发现数**: N 处

### 发现 1：矛盾描述
- **涉及角色**: 角色名
- **前文（第X章）**: ...
- **后文（第Y章）**: ...
- **矛盾点**: ...
- **严重程度**: 轻度/中度/重度

请基于材料进行分析，不要编造章节号。"""

    result, log = run_opensquilla_agent(
        message=message,
        files=[story_summary_path, character_profiles_path],
        model="deepseek-v4-pro"
    )

    if result and "text" in result:
        text = result["text"]
        usage = result.get("usage", {})
        routing = result.get("routing", {})

        # Write to file
        output_path = os.path.join(OUTPUT_DIR, "logic_analysis.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# 《逆世天途》逻辑一致性分析报告\n\n")
            f.write("> 由 OpenSquilla 生成\n")
            f.write(f"> 模型: {routing.get('routed_model', '-')} | 路由层级: {routing.get('routed_tier', '-')}\n")
            f.write("> 分析范围：第 1 章 - 第 128 章\n")
            f.write("> 分析日期：2026-06-06\n\n")
            f.write("---\n\n")
            f.write(text)

        print(f"✅ logic_analysis.md 已写入 ({len(text)} 字)")
        print(f"   输入 tokens: {usage.get('input_tokens')}")
        print(f"   输出 tokens: {usage.get('output_tokens')}")
        print(f"   费用: ${usage.get('cost_usd', 0):.4f}")
        print(f"   路由: {routing.get('routed_tier')}/{routing.get('routed_model')}")
        return True
    else:
        print(f"❌ 分析失败")
        return False

def do_repetition_analysis():
    """重复模式分析"""
    print("\n=== Phase 2: 重复模式分析 ===")

    story_summary_path = os.path.join(OUTPUT_DIR, "story_summary.md")
    character_profiles_path = os.path.join(OUTPUT_DIR, "character_profiles.md")

    message = """你是一位资深的文学编辑，擅长长篇小说中的重复模式分析。

请读取附件中的两份材料：
- story_summary.md = 全文故事概要
- character_profiles.md = 全文角色档案

基于以上材料，对《逆世天途》全文进行重复模式分析。

## 分析要求

请从以下维度检测重复模式，每个维度请给出具体章节引用和严重程度评估（轻度/中度/重度）：

1. **情节套路重复** — 相同的困境/解决方案反复出现（如每次遇险都靠"灵机一动"或"突然想起"）
2. **战斗模式重复** — 战斗是否遵循固定套路（先落下风→突然爆发→获胜）
3. **叙事手法重复** — 心理描写、场景过渡、环境描写等是否存在固定句式套路
4. **对话同质化** — 不同角色的说话方式是否雷同，缺乏个性区分
5. **情感节奏重复** — 章节结尾是否总用同样的悬念或情绪收尾
6. **其他重复模式** — 你发现的任何其他重复

## 输出格式

每个维度的输出格式如下（markdown）：

## 1. 情节套路重复

- **严重程度**: 中度/重度
- **首次出现**: 第X章
- **末次出现**: 第Y章
- **频率**: 每Z章出现一次 或 贯穿全文

**表现描述**: [...]

**典型案例**:
- 第X章：[具体表现]
- 第Y章：[具体表现]

**修改建议**: [...]

请基于材料进行分析，不要编造章节号。"""

    result, log = run_opensquilla_agent(
        message=message,
        files=[story_summary_path, character_profiles_path],
        model="deepseek-v4-pro"
    )

    if result and "text" in result:
        text = result["text"]
        usage = result.get("usage", {})
        routing = result.get("routing", {})

        output_path = os.path.join(OUTPUT_DIR, "repetition_analysis.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# 《逆世天途》重复模式分析报告\n\n")
            f.write("> 由 OpenSquilla 生成\n")
            f.write(f"> 模型: {routing.get('routed_model', '-')} | 路由层级: {routing.get('routed_tier', '-')}\n")
            f.write("> 分析范围：第 1 章 - 第 128 章\n")
            f.write("> 分析日期：2026-06-06\n\n")
            f.write("---\n\n")
            f.write(text)

        print(f"✅ repetition_analysis.md 已写入 ({len(text)} 字)")
        print(f"   输入 tokens: {usage.get('input_tokens')}")
        print(f"   输出 tokens: {usage.get('output_tokens')}")
        print(f"   费用: ${usage.get('cost_usd', 0):.4f}")
        print(f"   路由: {routing.get('routed_tier')}/{routing.get('routed_model')}")
        return True
    else:
        print(f"❌ 重复模式分析失败")
        return False

if __name__ == "__main__":
    # Ensure PATH includes opensquilla
    env_path = os.environ.get("PATH", "")
    local_bin = os.path.expanduser("~/.local/bin")
    if local_bin not in env_path:
        os.environ["PATH"] = f"{local_bin};{env_path}"

    # Read API key
    env_path = os.path.join(SCRIPT_DIR, "..", "backend", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY"):
                    key = line.strip().split("=", 1)[1]
                    os.environ["DEEPSEEK_API_KEY"] = key
                    break

    ok = do_logic_analysis()
    if ok:
        do_repetition_analysis()
