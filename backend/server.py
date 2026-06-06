"""
ModifyArt Backend - 单文件 FastAPI 服务
调用 DeepSeek API 进行文本深度改写
"""

import os
import sys
import time
import difflib
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv
from context_manager import load_context, save_context, format_context, detect_chapter

load_dotenv()

# ── Config ──────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
MAX_TOKENS = 4096
TEMPERATURE = 0.3
TIMEOUT = 120

PROMPTS_DIR = Path(__file__).parent / "prompts"

# ── App ─────────────────────────────────────────────────
app = FastAPI(title="ModifyArt", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──────────────────────────────────────────────
class ModifyRequest(BaseModel):
    text: str
    operation: str
    extra_instruction: str = ""
    context_file: str = ""
    preserve_level: str = "standard"  # light | standard | aggressive（仅 pipeline 有效）
    previous_result: str = ""  # refine 模式下的上次改写结果


class ContextUpdateRequest(BaseModel):
    context_file: str
    change: str = ""           # 修改摘要
    problems: str = ""         # 章节问题（换行分隔）
    chapter: str = ""          # 章节号
    character_updates: dict[str, str] = {}  # 人物更新: {"苏曼尼": "建议...", "苏晚": "建议..."}


class ContextExtractRequest(BaseModel):
    analysis_text: str
    context_file: str = ""


class DiffHunk(BaseModel):
    type: str  # equal | insert | delete
    content: str


class ModifyResponse(BaseModel):
    original_text: str
    modified_text: str
    diff_hunks: list[DiffHunk]
    operation: str
    model: str
    tokens_used: int
    processing_time_ms: float
    extracted_problems: list[str] = []  # 章节+全局问题（合并列表，前端展示用）
    character_updates: dict[str, str] = {}  # 人物更新: {"苏曼尼": "建议...", "苏晚": "建议..."}
    detected_chapter: str = ""  # 检测到的章节号
    context_summary: str = ""  # 注入的上下文摘要


# ── Helpers ─────────────────────────────────────────────
def load_prompt(operation: str) -> str:
    """加载操作对应的 prompt 模板"""
    prompt_file = PROMPTS_DIR / f"{operation}.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return "请对以下文本进行处理。只输出处理后的文本，不要加任何解释。"


def build_diff(original: str, modified: str) -> list[DiffHunk]:
    """生成逐字符 diff，用于前端对比展示"""
    matcher = difflib.SequenceMatcher(None, original, modified)
    hunks: list[DiffHunk] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            hunks.append(DiffHunk(type="equal", content=original[i1:i2]))
        elif tag == "delete":
            hunks.append(DiffHunk(type="delete", content=original[i1:i2]))
        elif tag == "replace":
            hunks.append(DiffHunk(type="delete", content=original[i1:i2]))
            hunks.append(DiffHunk(type="insert", content=modified[j1:j2]))
        elif tag == "insert":
            hunks.append(DiffHunk(type="insert", content=modified[j1:j2]))
    return hunks


def merge_diff_hunks(hunks: list[DiffHunk]) -> str:
    """将 diff hunks 合并为纯文本（去除 delete 类型）"""
    return "".join(h.content for h in hunks if h.type != "delete")


# ── API Routes ──────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "model": DEEPSEEK_MODEL,
        "has_api_key": bool(DEEPSEEK_API_KEY),
    }


@app.post("/api/modify", response_model=ModifyResponse)
async def modify(req: ModifyRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="未设置 DEEPSEEK_API_KEY 环境变量。请在 .env 文件中设置。",
        )

    valid_ops = {"polish", "remove_filler", "format", "dedup_plot", "logic_check", "pipeline", "refine"}
    if req.operation not in valid_ops:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的操作: {req.operation}。可用: {valid_ops}",
        )

    client = AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=float(TIMEOUT),
    )

    # 构建基础上下文（按章节过滤问题）
    extra = ""
    context_summary = ""
    has_logic_issues = False
    current_chapter = detect_chapter(req.text)
    if req.context_file:
        ctx = load_context(req.context_file)
        extra = format_context(ctx, current_chapter)
        # 检测当前章节是否有逻辑类问题
        ch_problems = ctx.get("章节问题", {})
        curr_problems = ch_problems.get(current_chapter, []) if current_chapter else []
        if curr_problems:
            has_logic_issues = any(
                kw in p for p in curr_problems
                for kw in ["逻辑", "矛盾", "时间线", "因果", "位置", "认知"]
            )
        parts = []
        if ctx.get("人物"):
            parts.append(f"{len(ctx['人物'])}人物")
        if ctx.get("事件"):
            parts.append(f"{len(ctx['事件'])}事件")
        total = sum(len(v) for v in ch_problems.values())
        if total:
            ch_label = f"第{current_chapter}章" if current_chapter else "全局"
            this_ch = len(ch_problems.get(current_chapter, [])) if current_chapter else 0
            parts.append(f"问题{this_ch}个/共{total}个")
        if parts:
            context_summary = "已注入: " + " · ".join(parts)
        else:
            context_summary = "上下文为空"
    # 有逻辑问题时，覆盖润笔 prompt 中"保持情节不变"的限制
    if has_logic_issues and req.operation in ("polish", "pipeline", "remove_filler", "refine"):
        extra += "\n\n【重要指令】上文列出了一些逻辑矛盾。请在改写时修复这些矛盾，即使需要改变原文的事件顺序、人物位置或情节推进。不要因为'保持原文'的规则而跳过逻辑修复。"
    if req.extra_instruction:
        extra += f"\n\n额外要求: {req.extra_instruction}"

    t0 = time.time()
    total_tokens = 0
    extracted_problems: list[str] = []
    character_updates: dict[str, str] = {}

    if req.operation == "pipeline":
        # 流水线：去水句 → 润色 → 分段
        # 根据 preserve_level 调整去水句的力度
        preserve_hint = _preserve_hint(req.preserve_level)
        steps = [
            ("remove_filler", "去水句", preserve_hint),
            ("polish", "润色改写", ""),
            ("format", "智能分段", ""),
        ]
        current = req.text
        for op_key, op_name, hint in steps:
            prompt = load_prompt(op_key)
            if hint:
                prompt += hint
            # 上下文放在用户消息开头，AI 更重视
            user_content = extra + "\n\n【待处理文本】\n" + current if extra else current
            try:
                response = await client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_content},
                    ],
                )
                current = response.choices[0].message.content or ""
                total_tokens += response.usage.total_tokens if response.usage else 0
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"{op_name} 失败: {e}")
        modified = current

    elif req.operation == "refine":
        # 修正模式：上下文放在用户消息开头
        system_prompt = load_prompt("refine")
        user_prompt = extra + "\n\n" if extra else ""
        user_prompt += (
            f"【原文】\n{req.text}\n\n"
            f"【上次改写结果】\n{req.previous_result}\n\n"
            f"【用户修改意见】\n{req.extra_instruction or '请改进改写质量，减少过度简化，保持原文的逻辑连贯性'}"
        )
        try:
            response = await client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"修正失败: {e}")
        modified = response.choices[0].message.content or ""
        total_tokens = response.usage.total_tokens if response.usage else 0

    elif req.operation in ("dedup_plot", "logic_check"):
        # 分析类操作（去重/逻辑校验）：上下文放用户消息，自动提取问题，不显示应用按钮
        system_prompt = load_prompt(req.operation)
        user_content = extra + "\n\n【待分析文本】\n" + req.text if extra else req.text
        try:
            response = await client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DeepSeek API 调用失败: {e}")
        modified = response.choices[0].message.content or ""
        total_tokens = response.usage.total_tokens if response.usage else 0

        # 自动提取并分类
        findings = await _extract_findings(client, modified)
        character_updates = findings["character_updates"]
        # 合并章节问题 + 全局问题，供前端展示
        extracted_problems = findings["chapter_problems"] + findings["global_problems"]

    else:
        # 单步操作：polish / remove_filler / format — 上下文放用户消息
        system_prompt = load_prompt(req.operation)
        if req.operation == "remove_filler":
            system_prompt += _preserve_hint(req.preserve_level)
        user_content = extra + "\n\n【待处理文本】\n" + req.text if extra else req.text
        try:
            response = await client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DeepSeek API 调用失败: {e}")
        modified = response.choices[0].message.content or ""
        total_tokens = response.usage.total_tokens if response.usage else 0

    elapsed = (time.time() - t0) * 1000
    diff = build_diff(req.text, modified)

    return ModifyResponse(
        original_text=req.text,
        modified_text=modified,
        diff_hunks=diff,
        operation=req.operation,
        model=DEEPSEEK_MODEL,
        tokens_used=total_tokens,
        processing_time_ms=round(elapsed, 2),
        extracted_problems=extracted_problems,
        character_updates=character_updates,
        detected_chapter=current_chapter or "",
        context_summary=context_summary,
    )


@app.post("/api/context/extract")
async def extract_context(req: ContextExtractRequest):
    """从情节去重分析报告中提取结构化问题列表（不自动保存，由用户确认后通过 /api/context 保存）"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="未设置 DEEPSEEK_API_KEY")

    client = AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=float(TIMEOUT),
    )

    problems = await _extract_problems(client, req.analysis_text)
    return {"problems": problems}


@app.get("/api/context")
async def get_context(context_file: str):
    """获取书籍的上下文"""
    return load_context(context_file)


@app.post("/api/context")
async def update_context(req: ContextUpdateRequest):
    """更新书籍上下文（增量更新）"""
    ctx = load_context(req.context_file)

    # ── 人物更新：模糊匹配已有角色名，避免"苏曼妮"和"苏曼尼"创建两个 ──
    if req.character_updates:
        existing_names = list(ctx["人物"].keys())
        for name, suggestion in req.character_updates.items():
            matched = _fuzzy_match(name, existing_names)
            if matched:
                ctx["人物"][matched]["近期变动"] = suggestion
            else:
                ctx["人物"][name] = {"状态": "存活", "近期变动": suggestion}

    # ── 章节问题：按章节存储 ──
    if req.problems:
        new_problems = [p.strip() for p in req.problems.split("\n") if p.strip()]
        chapter_key = req.chapter or "全局"
        chapter_problems = ctx.setdefault("章节问题", {}).setdefault(chapter_key, [])
        existing = set(chapter_problems)
        for p in new_problems:
            if p not in existing:
                chapter_problems.append(p)
                existing.add(p)

    # ── 改动记录：以日期为 key ──
    if req.change:
        today = time.strftime("%Y-%m-%d")
        ctx["改动记录"][today] = req.change

    save_path = save_context(req.context_file, ctx)
    return {"status": "ok", "path": str(save_path), "context": ctx}


# ── Internal helpers ────────────────────────────────────
def _preserve_hint(level: str) -> str:
    """根据保留力度返回去水句的追加指令"""
    hints = {
        "light": (
            "\n\n注意：本次请使用【轻度删减】力度。"
            "只删除明显的套话、废话、'众所周知'类空泛表达。"
            "保留过渡段落、情感描写和环境渲染，不要删减叙事节奏所需的内容。"
        ),
        "standard": (
            "\n\n注意：本次请使用【标准删减】力度。"
            "删除套话、重复解释、注水修饰，但保留必要的过渡和情感描写。"
        ),
        "aggressive": (
            "\n\n注意：本次请使用【激进删减】力度。"
            "大刀阔斧地删除一切非核心内容，只保留推动情节的关键句子。"
        ),
    }
    return hints.get(level, hints["standard"])


async def _extract_findings(client: AsyncOpenAI, analysis_text: str):
    """从分析报告中提取分类结果（AI 输出 JSON，json.loads 解析）"""
    prompt = (
        "从以下情节分析报告中提取发现，必须严格输出 JSON 格式：\n\n"
        '{\n'
        '  "character_updates": {\n'
        '    "人物名": "针对该人物的具体改进建议"\n'
        '  },\n'
        '  "chapter_problems": [\n'
        '    "[类型] 当前章节特有的具体问题"\n'
        '  ],\n'
        '  "global_problems": [\n'
        '    "[类型] 全书写作习惯问题"\n'
        '  ]\n'
        '}\n\n'
        "规则：\n"
        "- character_updates: 只填入分析中明确提到名字的人物，没有人物相关建议则 {} \n"
        "- chapter_problems: 只填入针对本章特定场景的逻辑、节奏、情节矛盾问题，没有则 []\n"
        "- global_problems: 填入跨章节的写作习惯、套路、表达方式问题，没有则 []\n"
        "- 每个值用双引号，不要用单引号\n"
        "- 只输出 JSON，不要加任何解释或 markdown 标记\n\n"
        f"分析报告:\n{analysis_text}"
    )
    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            max_tokens=1024,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "你是一个 JSON 数据提取助手。只输出 JSON，不要加```json```标记，不要加任何其他文字。"},
                {"role": "user", "content": prompt},
            ],
        )
        text = response.choices[0].message.content or ""
        return _parse_findings_json(text)
    except Exception:
        return {"character_updates": {}, "chapter_problems": [], "global_problems": []}


def _parse_findings_json(text: str) -> dict:
    """解析 AI 输出的 JSON（自动处理 ```json``` 包裹和尾部逗号）"""
    import json as _json
    # 去除可能的 markdown 代码块包裹
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        data = _json.loads(text)
        return {
            "character_updates": data.get("character_updates", {}),
            "chapter_problems": data.get("chapter_problems", []),
            "global_problems": data.get("global_problems", []),
        }
    except _json.JSONDecodeError:
        # 回退到旧解析
        return _parse_findings_fallback(text)


def _fuzzy_match(name: str, candidates: list[str], threshold: float = 0.5) -> str | None:
    """模糊匹配中文名。完全匹配 > 包含关系 > 字符重叠率"""
    if name in candidates:
        return name
    for c in candidates:
        if c in name or name in c:
            return c
    name_set = set(name)
    for c in candidates:
        c_set = set(c)
        if not name_set or not c_set:
            continue
        # 用较宽松的比率：共同字符数 / 较短名字长度
        common = len(name_set & c_set)
        shorter_len = min(len(name), len(c))
        ratio = common / max(shorter_len, 1)
        if ratio >= threshold and len(name) == len(c):
            return c
    return None


def _parse_findings_fallback(text: str) -> dict:
    """回退解析：按行解析，按内容特征分类"""
    result = {"character_updates": {}, "chapter_problems": [], "global_problems": []}
    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) < 6:
            continue
        # 去除前导编号如 "1. " "1、" "- "
        cleaned = line
        for prefix in ["- ", "• ", "* "]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        # 匹配 "1. " "1、" "1)"
        import re
        cleaned = re.sub(r'^\d+[\.\、\)\s]+', '', cleaned).strip()

        if not cleaned or len(cleaned) < 6:
            continue
        # 人物相关：有中文名+冒号
        if re.match(r'^[一-鿿]{2,4}[：:]', cleaned):
            m = re.match(r'^(.+?)[：:]\s*(.+)$', cleaned)
            if m:
                result["character_updates"][m.group(1).strip()] = m.group(2).strip()
        # 章节问题：以 [类型] 开头
        elif cleaned.startswith("[") and "]" in cleaned[:20]:
            result["chapter_problems"].append(cleaned)
        # 全局问题：其他所有
        elif len(cleaned) > 6:
            result["global_problems"].append(cleaned)
    return result


# ── Entry ───────────────────────────────────────────────
def main():
    import uvicorn

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
