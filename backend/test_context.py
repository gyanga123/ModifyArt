"""
ModifyArt 上下文系统单元测试
运行: cd backend && python test_context.py
"""
import json
import sys
from pathlib import Path

# 添加 backend 目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from context_manager import (
    detect_chapter, load_context, save_context,
    format_context, _empty_context,
)
from server import _parse_findings_json, _parse_findings_fallback

PASS = 0
FAIL = 0


def check(name: str, actual, expected):
    global PASS, FAIL
    if actual == expected:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")
        print(f"    期望: {expected!r}")
        print(f"    实际: {actual!r}")


def check_contains(name: str, text: str, *keywords, not_in=None):
    global PASS, FAIL
    if not_in is None:
        not_in = []
    missing = [k for k in keywords if k not in text]
    has_forbidden = [k for k in not_in if k in text]
    if not missing and not has_forbidden:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        if missing:
            print(f"  ✗ {name} — 缺少: {missing}")
        if has_forbidden:
            print(f"  ✗ {name} — 不应包含: {has_forbidden}")


# ── 1. detect_chapter ──────────────────────────────
print("\n=== detect_chapter ===")
check("第92章标准格式",     detect_chapter("第92章\n苏曼尼蹲在文件柜旁白"), "92")
check("第86-88章范围",     detect_chapter("第86-88章\n医院病房"), "86-88")
check("带空格第 92 章",    detect_chapter("第 92 章 盗取设计稿"), "92")
check("数字章标记 92.",    detect_chapter("92. 对峙\n苏晚冷冷看着她"), "92")
check("无章标记返回None",  detect_chapter("苏曼尼蹲在文件柜旁白，后门感应灯亮了"), None)
check("空文本",            detect_chapter(""), None)


# ── 2. _parse_findings_json ────────────────────────
print("\n=== _parse_findings_json ===")
# 测试标准 JSON
result = _parse_findings_json('''{
  "character_updates": {
    "苏曼尼": "崩溃缺乏层次",
    "苏晚": "对话过于理性"
  },
  "chapter_problems": [
    "[逻辑问题] 感应灯刚亮不可能已在拷贝文件"
  ],
  "global_problems": [
    "[重复桥段] 遇险-被救模式单一"
  ]
}''')
check("JSON解析-人物",      result["character_updates"].get("苏曼尼"), "崩溃缺乏层次")
check("JSON解析-章节问题",  len(result["chapter_problems"]), 1)
check("JSON解析-全局问题",  len(result["global_problems"]), 1)

# 测试带 markdown 包裹
result2 = _parse_findings_json('''```json
{"character_updates": {}, "chapter_problems": ["[逻辑] 问题"], "global_problems": []}
```''')
check("Markdown包裹解析",   len(result2["chapter_problems"]), 1)

# 测试空输入
result3 = _parse_findings_json("")
check("空输入",             result3, {"character_updates": {}, "chapter_problems": [], "global_problems": []})


# ── 3. fallback 解析 ───────────────────────────────
print("\n=== _parse_findings_fallback ===")
text = """
苏曼尼: 崩溃缺乏层次，建议增加先冷静再崩溃的过渡
苏晚：对话过于理性说教
[逻辑问题] 感应灯刚亮不可能已在拷贝文件
[情绪模式] 苏晚情绪转折过于突兀
[重复桥段] 遇险-被救模式单一
"""
result = _parse_findings_fallback(text)
# 回退解析：[类型] 类问题都按章节问题处理
check("回退解析-人物苏曼尼",  result["character_updates"].get("苏曼尼", ""),
      "崩溃缺乏层次，建议增加先冷静再崩溃的过渡")
check("回退解析-人物苏晚",    "苏晚" in result["character_updates"], True)
check("回退解析-总问题数",    len(result["chapter_problems"]) + len(result["global_problems"]), 3)


# ── 4. format_context — 注入正确性 ────────────────
print("\n=== format_context ===")
ctx = {
    "book": "测试",
    "人物": {
        "苏曼尼": {"性别": "女", "年龄": "26", "状态": "存活",
                 "性格": "因嫉妒而生恨", "近期变动": "崩溃缺乏层次"},
        "王富贵": {"状态": "已死亡", "近期变动": ""},
    },
    "事件": {"第5章": "泼咖啡", "第92章": "盗取设计稿"},
    "设定": {"世界观": "现代都市"},
    "章节问题": {
        "92": ["[逻辑问题] 感应灯刚亮不可能已在拷贝文件"],
        "86": ["[情绪问题] 苏晚转折突兀"],
        "全局": ["[重复桥段] 遇险-被救模式单一"],
    },
    "改动记录": {"2026-05-31": "第92章优化"},
}

# 改写第92章时
fmt92 = format_context(ctx, "92")
check_contains("92章-含人物苏曼尼", fmt92, "苏曼尼", "近期", "崩溃")
check_contains("92章-含92章专属问题", fmt92, "必须修复", "感应灯")
check_contains("92章-含全局问题", fmt92, "刻意避开", "遇险-被救")
check_contains("92章-不含86章问题", fmt92, not_in=["情绪问题", "转折突兀"])
check_contains("92章-含状态存活", fmt92, "存活")
check_contains("92章-含已死亡", fmt92, "已死亡")

# 改写第86章时
fmt86 = format_context(ctx, "86")
check_contains("86章-含86章问题", fmt86, "情绪问题", "转折突兀")
check_contains("86章-不含92章问题", fmt86, not_in=["感应灯"])

# 空上下文
fmt_empty = format_context(_empty_context("测试.txt"), "92")
check("空上下文简短", len(fmt_empty) < 200, True)


# ── 5. 完整保存流程模拟 ────────────────────────────
print("\n=== 完整流程模拟 ===")
# 模拟：分析第92章 → 提取 → 保存 → 改写
ctx = _empty_context("钻石.txt")

# Step 1: AI 提取结果
findings = {
    "character_updates": {"苏曼尼": "崩溃缺乏层次，增加先冷静再崩溃的过渡"},
    "chapter_problems": ["[逻辑问题] 感应灯刚亮不可能已在拷贝文件"],
    "global_problems": ["[重复桥段] 遇险-被救模式单一"],
}

# Step 2: 保存人物更新
for name, suggestion in findings["character_updates"].items():
    if name not in ctx["人物"]:
        ctx["人物"][name] = {"状态": "存活"}
    ctx["人物"][name]["近期变动"] = suggestion

# Step 3: 保存章节问题到 "92"
chapter = "92"
ctx.setdefault("章节问题", {}).setdefault(chapter, [])
for p in findings["chapter_problems"]:
    if p not in ctx["章节问题"][chapter]:
        ctx["章节问题"][chapter].append(p)

# Step 4: 保存全局问题
ctx.setdefault("章节问题", {}).setdefault("全局", [])
for p in findings["global_problems"]:
    if p not in ctx["章节问题"]["全局"]:
        ctx["章节问题"]["全局"].append(p)

# Step 5: 改动记录
ctx["改动记录"]["2026-05-31"] = "第92章分析"

check("人物-苏曼尼近期变动", ctx["人物"]["苏曼尼"]["近期变动"],
      "崩溃缺乏层次，增加先冷静再崩溃的过渡")
check("章节问题-92章", len(ctx["章节问题"].get("92", [])), 1)
check("章节问题-全局", len(ctx["章节问题"].get("全局", [])), 1)
check("章节问题-无86章key", "86" not in ctx["章节问题"], True)
check("改动记录", list(ctx["改动记录"].values())[0], "第92章分析")


# ── 结果 ───────────────────────────────────────────
print(f"\n{'='*40}")
print(f"通过: {PASS}  失败: {FAIL}  总计: {PASS + FAIL}")
if FAIL == 0:
    print("全部通过 ✓")
else:
    print(f"{FAIL} 项失败 ✗")
    sys.exit(1)
