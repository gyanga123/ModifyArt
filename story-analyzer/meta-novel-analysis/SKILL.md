---
name: meta-novel-analysis
description: "分析长篇小说《逆世天途》的逻辑一致性和重复模式。输入为 story_summary.md（章节概要）和 character_profiles.md（角色档案），输出结构化的分析报告。适用于：逻辑一致性审查、重复套路检测、角色行为矛盾发现、时间线梳理。在 Claude Code 中通过 opensquilla agent CLI 调用。"
metadata:
  emoji: "📖"
---

# meta-novel-analysis

分析长篇小说《逆世天途》的专业流程。分两轮：**逻辑一致性分析**和**重复模式分析**，均基于 Phase 1 产出的 .md 概要，不读原文。

## 前置条件

- Phase 1 已完成（`output/story_summary.md` 和 `output/character_profiles.md` 已生成）
- OpenSquilla Gateway 运行中
- 显式指定 `--model deepseek-v4-pro`（避免 router 降级）

## 分析一：逻辑一致性

从 6 个维度检测：角色行为矛盾、实力体系不一致、设定冲突、时间线矛盾、角色关系/记忆不一致、动机不连贯。

### 调用方式

```bash
opensquilla agent \
  --model deepseek-v4-pro \
  --file output/story_summary.md \
  --file output/character_profiles.md \
  --message "你是一位资深的文学编辑，擅长长篇小说中的逻辑一致性分析。

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

请基于材料进行分析，不要编造章节号。" \
  --json --timeout 300 --unattended > output/raw_logic.json 2>/dev/null
```

### 提取结果

```bash
python -c "
import json
with open('output/raw_logic.json', 'rb') as f:
    raw = f.read()
idx = raw.find(b'{\"status\"')
data = json.loads(raw[idx:].decode('gbk'))
with open('输出/逻辑一致性分析.md', 'w', encoding='utf-8') as f:
    f.write(data['text'])
"
```

## 分析二：重复模式

从 6 个维度检测：情节套路重复、战斗模式重复、叙事手法重复、对话同质化、情感节奏重复、其他重复模式。

### 调用方式

同上，使用 `phase2_repetition.txt` 作为 prompt，输出到 `输出/重复模式分析.md`。

## 输出文件规范

| 分析类型 | 输出路径 | 备注 |
|---------|---------|------|
| 逻辑一致性 | `输出/逻辑一致性分析.md` | 中文命名，UTF-8 |
| 重复模式 | `输出/重复模式分析.md` | 中文命名，UTF-8 |
| 修复建议 | `输出/逻辑修复建议.md` | 基于分析结果人工编写 |

## 注意事项

1. **不读原文做分析** — 只读 .md 概要，重读原文浪费 token
2. **显式指定模型** — 必须 `--model deepseek-v4-pro`
3. **先缓存再提取** — 原始 JSON 先存 `output/raw_*.json`，写入 .md 失败只重试提取
4. **会话模式** — 多轮分析用 `--session-id novel-phase2` 共享上下文
5. **GBK 解码** — Windows bash pipe 输出为 GBK，需 `.decode('gbk')` 再 `json.loads()`
6. **不重跑** — 检查缓存，已有结果直接跳过
