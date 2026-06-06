#!/usr/bin/env python3
"""run_phase2.py — Phase 2 幂等分析脚本

用法:
  python run_phase2.py logic                      # 逻辑一致性分析
  python run_phase2.py repetition                  # 重复模式分析
  python run_phase2.py all                         # 全部（先 logic 后 repetition）
  python run_phase2.py logic --force               # 强制重跑（忽略缓存）

特性:
  - 幂等：检查缓存，不重复调 API
  - GBK 解码：修复 Windows pipe 编码问题
  - 费用追踪：每次运行报告 token 消耗和费用
  - 显式 --model deepseek-v4-pro，避免 router 降级
"""
import sys
import os
import json
import subprocess
from pathlib import Path

# 全局控制：强制重跑
FORCE = False

# ─── 路径 ───
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
CN_OUTPUT_DIR = SCRIPT_DIR / "输出"
PROMPTS_DIR = SCRIPT_DIR / "prompts"
NOVEL_PATH = Path("d:/project file/ModifyArt/【改】逆世天途_utf8.txt")

# 输出文件名（中文，统一后缀 _逆世天途）
ANALYSES = {
    "logic": {
        "output_file": CN_OUTPUT_DIR / "逻辑一致性分析_逆世天途.md",
        "raw_cache": OUTPUT_DIR / "raw_logic.json",
        "prompt_file": PROMPTS_DIR / "phase2_logic.txt",
        "title": "《逆世天途》逻辑一致性分析报告",
    },
    "repetition": {
        "output_file": CN_OUTPUT_DIR / "重复模式分析_逆世天途.md",
        "raw_cache": OUTPUT_DIR / "raw_repetition.json",
        "prompt_file": PROMPTS_DIR / "phase2_repetition.txt",
        "title": "《逆世天途》重复模式分析报告",
    },
}

OPENSSQUILLA = "opensquilla"
MODEL = "deepseek-v4-pro"
TIMEOUT_SEC = 360


# ══════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════

def log(msg: str):
    print(f"  {msg}")


def warn(msg: str):
    print(f"  !! {msg}")


def err(msg: str):
    print(f"  [错误] {msg}", file=sys.stderr)


def read_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def check_prerequisites() -> bool:
    """检查分析所需的依赖文件是否存在"""
    ok = True
    checks = [
        (OUTPUT_DIR / "story_summary.md", "Phase 1 输出 story_summary.md 不存在"),
        (OUTPUT_DIR / "character_profiles.md", "Phase 1 输出 character_profiles.md 不存在"),
    ]
    for path, msg in checks:
        if not path.exists():
            err(msg)
            ok = False
    if not ok:
        err("请先完成 Phase 1")
    return ok


def has_cache(analysis: str) -> bool:
    """检查是否有可用缓存"""
    cfg = ANALYSES[analysis]
    raw_exists = cfg["raw_cache"].exists()
    final_exists = cfg["output_file"].exists()
    if raw_exists and final_exists and final_exists.stat().st_size > 100:
        log(f"[缓存] {cfg['raw_cache'].name} + {cfg['output_file'].name} 已存在，跳过")
        return True
    if raw_exists and not final_exists:
        warn("原始 JSON 缓存存在但最终 .md 不存在，尝试重新提取...")
        return extract_from_cache(analysis)
    return False


def extract_from_cache(analysis: str) -> bool:
    """从缓存的原始 JSON 重新提取 .md 输出"""
    cfg = ANALYSES[analysis]
    raw_path = cfg["raw_cache"]
    if not raw_path.exists():
        return False

    log(f"[提取] 从 {raw_path.name} 重新提取...")
    try:
        with open(raw_path, "rb") as f:
            raw = f.read()

        # 找到 JSON 起始位置
        idx = raw.find(b'{"status"')
        if idx < 0:
            warn("缓存文件未找到 JSON 结构")
            return False

        # GBK 解码（Windows pipe 编码）
        data = json.loads(raw[idx:].decode("gbk"))
        text = data.get("text", "")

        if not text or len(text) < 50:
            warn("提取的文本为空或太短")
            return False

        # 写入 .md
        write_md(analysis, text, data)
        log(f"[完成] → {cfg['output_file'].name} ({len(text)} 字)")
        return True

    except Exception as e:
        warn(f"提取失败: {e}")
        return False


def write_md(analysis: str, text: str, result: dict):
    """将分析结果写入最终 .md 文件（中文路径）"""
    cfg = ANALYSES[analysis]
    usage = result.get("usage", {})
    routing = result.get("routing", {})

    header = f"""# {cfg['title']}

> 由 OpenSquilla 生成
> 模型: {routing.get('routed_model', '-')} | 路由层级: {routing.get('routed_tier', '-')}
> 分析范围：第 1 章 - 第 128 章（Phase 1 已完成部分）
> 分析日期：2026-06-06

---

"""
    # 确保目录存在
    CN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(cfg["output_file"], "w", encoding="utf-8") as f:
        f.write(header)
        f.write(text)

    # 同时写一份到 output/ 备份（英文路径，便于程序引用）
    backup = OUTPUT_DIR / cfg["raw_cache"].name.replace("raw_", "").replace(".json", ".md")
    with open(backup, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(text)


def report_cost(result: dict):
    """输出费用报告"""
    usage = result.get("usage", {})
    routing = result.get("routing", {})
    cost = usage.get("cost_usd", 0)
    tier = routing.get("routed_tier", "?")
    model = routing.get("routed_model", "?")
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    log(f"  模型: {tier}/{model} | 输入: {inp} tokens | 输出: {out} tokens | 费用: ${cost:.4f}")


def run_analysis(analysis: str, force: bool = False) -> bool:
    """执行一次 Phase 2 分析"""
    cfg = ANALYSES[analysis]

    # 缓存检查
    if not force and has_cache(analysis):
        return True

    log(f"[运行] 调用 OpenSquilla ({MODEL}) 进行 {analysis} 分析...")

    # 读 prompt 模板
    prompt_text = read_file(cfg["prompt_file"])

    # 组装 message（告诉模型读取附件）
    has_technique = (OUTPUT_DIR / "writing_technique.md").exists()
    materials = ["- story_summary.md = 全文故事概要", "- character_profiles.md = 全文角色档案"]
    if has_technique:
        materials.append("- writing_technique.md = 写作手法记录（基于原文提取的章末结尾、战斗结构、过渡方式等事实）")

    attach_list = "\n".join(materials)
    message = f"""你是一位资深的文学编辑，擅长长篇小说分析。

请读取附件中的材料：
{attach_list}

基于以上材料，对《逆世天途》全文进行分析。

{prompt_text}"""

    # 构建命令
    cmd = [
        OPENSSQUILLA, "agent",
        "--model", MODEL,
        "--file", str(OUTPUT_DIR / "story_summary.md"),
        "--file", str(OUTPUT_DIR / "character_profiles.md"),
    ]
    if has_technique:
        cmd += ["--file", str(OUTPUT_DIR / "writing_technique.md")]
    cmd += ["--message", message, "--json", "--timeout", "300", "--unattended"]

    # 执行
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        warn(f"OpenSquilla 超时（{TIMEOUT_SEC}s），请重试或拆小分析范围")
        return False
    except FileNotFoundError:
        err("找不到 opensquilla 命令。请确认 PATH 正确或先运行 init_env.sh")
        return False

    # 保存原始输出（先存再解析，避免编码问题丢失数据）
    raw_bytes = proc.stdout
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(cfg["raw_cache"], "wb") as f:
        f.write(raw_bytes)

    # 提取 JSON
    try:
        idx = raw_bytes.find(b'{"status"')
        if idx < 0:
            # 尝试找任何 JSON 对象
            idx = raw_bytes.find(b"{")
        if idx < 0:
            stderr_text = proc.stderr.decode("gbk", errors="replace")[:500]
            err(f"输出中未找到 JSON。stderr: {stderr_text}")
            return False

        data = json.loads(raw_bytes[idx:].decode("gbk"))
        text = data.get("text", "")

        if not text or len(text) < 50:
            warn("返回文本为空或太短，查看 stderr 了解详情")
            stderr_text = proc.stderr.decode("gbk", errors="replace")[:500]
            if stderr_text:
                warn(f"stderr: {stderr_text}")
            return False

        # 写入 .md
        write_md(analysis, text, data)
        log(f"[完成] → {cfg['output_file'].name} ({len(text)} 字)")
        report_cost(data)
        return True

    except json.JSONDecodeError as e:
        err(f"JSON 解析失败: {e}")
        # 保存原始输出供调试
        debug_path = cfg["raw_cache"].with_suffix(".debug.txt")
        with open(debug_path, "wb") as f:
            f.write(raw_bytes[:2000])
        warn(f"原始输出前 2000 字节已保存到 {debug_path.name}")
        return False
    except Exception as e:
        err(f"处理结果时出错: {e}")
        return False


# ══════════════════════════════════════════
#  会话模式（多轮共享上下文）
# ══════════════════════════════════════════

SESSION_ID = "novel-phase2"


def session_start(force_run: bool = False) -> bool:
    """启动新会话，第一轮分析（逻辑一致性）"""
    log(f"[会话] 启动新会话: {SESSION_ID}")
    cfg = ANALYSES["logic"]

    if cfg["output_file"].exists() and not force_run:
        log("[缓存] 逻辑分析结果已存在，跳过会话启动")
        return True

    prompt_text = read_file(cfg["prompt_file"])
    message = f"""你是一位资深的文学编辑，擅长长篇小说中的逻辑一致性分析。

请读取附件中的两份材料：
- story_summary.md = 全文故事概要
- character_profiles.md = 全文角色档案

基于以上材料，对《逆世天途》全文进行逻辑一致性分析。

{prompt_text}"""

    cmd = [
        OPENSSQUILLA, "agent",
        "--session-id", SESSION_ID,
        "--model", MODEL,
        "--file", str(OUTPUT_DIR / "story_summary.md"),
        "--file", str(OUTPUT_DIR / "character_profiles.md"),
        "--message", message,
        "--json",
        "--timeout", "300",
    ]

    log("[会话] 第一轮：逻辑一致性分析...")
    return _session_round(cmd, "logic")


def session_continue(analysis_type: str) -> bool:
    """在同一会话中继续第二轮分析（重复模式）"""
    cfg = ANALYSES[analysis_type]

    prompt_text = read_file(cfg["prompt_file"])
    message = f"""接下来，请在同一份材料的基础上进行另一项分析。

{prompt_text}"""

    cmd = [
        OPENSSQUILLA, "agent",
        "--session-id", SESSION_ID,
        "--model", MODEL,
        "--message", message,
        "--json",
        "--timeout", "300",
    ]

    log(f"[会话] 第二轮：重复模式分析...")
    return _session_round(cmd, analysis_type)


def _session_round(cmd: list, analysis: str) -> bool:
    """执行一轮会话分析"""
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        warn(f"超时（{TIMEOUT_SEC}s）")
        return False
    except FileNotFoundError:
        err("找不到 opensquilla 命令")
        return False

    raw_bytes = proc.stdout
    cfg = ANALYSES[analysis]

    # 缓存原始 JSON
    with open(cfg["raw_cache"], "wb") as f:
        f.write(raw_bytes)

    # 解析并写入
    try:
        idx = raw_bytes.find(b'{"status"')
        if idx < 0:
            idx = raw_bytes.find(b"{")
        if idx < 0:
            err("输出中未找到 JSON")
            return False

        data = json.loads(raw_bytes[idx:].decode("gbk"))
        text = data.get("text", "")

        if not text or len(text) < 50:
            warn("返回文本为空")
            return False

        write_md(analysis, text, data)
        log(f"[完成] → {cfg['output_file'].name} ({len(text)} 字)")
        report_cost(data)
        return True

    except Exception as e:
        err(f"处理失败: {e}")
        return False


# ══════════════════════════════════════════
#  入口
# ══════════════════════════════════════════

def print_usage():
    print("""用法:
  python run_phase2.py <command> [--force]

命令:
  logic         逻辑一致性分析
  repetition    重复模式分析
  all           先 logic 后 repetition
  session       会话模式（多轮共享上下文）
  extract       从已有缓存重新提取 .md

选项:
  --force       忽略缓存，强制重跑
  --help        显示本帮助
""")


def main():
    global FORCE
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print_usage()
        return

    command = args[0]
    FORCE = "--force" in args

    if command == "extract":
        for analysis in ["logic", "repetition"]:
            if ANALYSES[analysis]["raw_cache"].exists():
                extract_from_cache(analysis)
            else:
                log(f"[跳过] {analysis} 无缓存")
        return

    if command == "session":
        if not check_prerequisites():
            sys.exit(1)
        ok = session_start(force_run=FORCE)
        if ok:
            session_continue("repetition")
        return

    if command == "all":
        if not check_prerequisites():
            sys.exit(1)
        ok = run_analysis("logic", FORCE)
        if ok:
            run_analysis("repetition", FORCE)
        return

    if command in ANALYSES:
        if not check_prerequisites():
            sys.exit(1)
        success = run_analysis(command, FORCE)
        sys.exit(0 if success else 1)

    print_usage()
    sys.exit(1)


if __name__ == "__main__":
    main()
