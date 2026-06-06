# story-analyzer 测试计划

> 最后更新：2026-06-06
> 规则：**严格按计划执行，未经确认不得偏离**

---

## 架构

```
story-analyzer/
├── pipeline.py              # Phase 1 主管线（直调 DeepSeek API）
├── run_phase2.py            # Phase 2 幂等分析脚本（调用 OpenSquilla agent CLI）
├── init_env.sh              # 一键环境检查
├── chapter_parser.py        # 章节解析
├── config.py                # 配置
├── prompts/                 # Prompt 模板
│   ├── phase1_batch.txt     #   Phase 1（含概要+人物+手法三段输出）
│   ├── phase2_repetition.txt
│   └── phase2_logic.txt
├── meta-novel-analysis/
│   └── SKILL.md             # OpenSquilla Meta-Skill（已注册到 config.toml）
├── output/                  # 程序引用用（英文路径）
│   ├── story_summary.md
│   ├── character_profiles.md
│   ├── writing_technique.md     # ← 新增：写作手法记录
│   ├── raw_logic.json
│   └── raw_repetition.json
├── 输出/                    # 人类阅读用（中文路径，统一 _逆世天途 后缀）
│   ├── 逻辑一致性分析_逆世天途.md
│   └── 重复模式分析_逆世天途.md
└── PLAN.md
```

---

## 阶段一：Phase 1 — 分批提取

### 输入
- 原文：`d:\project file\ModifyArt\【改】逆世天途_utf8.txt`（358 章，~1.5MB）

### 处理方式
- **脚本直调 DeepSeek API**（复用 `backend/.env` 的 API key）
- 模型：`deepseek-v4-flash`（Phase 1 只需理解转述，不需要复杂推理）
- Batch 大小：**3 章/批**
- 每批调用一次 API：输入 3 章原文 + 已有 story_summary.md + 已有 character_profiles.md + 已有 writing_technique.md
- 输出：**三段输出**追加到对应的 .md 文件
  - 故事概要 → story_summary.md
  - 人物小传 → character_profiles.md
  - 写作手法记录 → writing_technique.md（新增：章末结尾/战斗结构/特殊用词/过渡/对话特征）
- 进度追踪：`.progress.json`（断点续跑用）

### 输出文件
- `output/story_summary.md`：每 3 章一个概要段落，顺序追加
- `output/character_profiles.md`：人物小传，持续累积追加
- `output/writing_technique.md`：写作手法记录，持续累积追加（章末结尾/战斗结构/特殊用词/过渡/对话特征）

---

## 阶段二：Phase 2 — 深度分析

### 前提条件
- Phase 1 已全部完成（或至少完成足够章节）
- **OpenSquilla Gateway 必须已启动**

### 处理方式
- **不再读取原文**（只基于 Phase 1 产出的 .md 文件）
- 调用方式：**OpenSquilla agent CLI**（`opensquilla agent`）
- 模型：**`deepseek-v4-pro`**（显式指定，不依赖自动路由）
- 输入材料：三份 Phase 1 产出
  - `story_summary.md` → L1 情节套路检测
  - `character_profiles.md` → 角色对话同质化检测
  - `writing_technique.md` → L2 叙事手法/L3 执行细节检测
- 如果 Gateway 未启动，**不得绕过**，应先运行 init_env.sh

### 输出文件
- `输出/逻辑一致性分析_逆世天途.md`：逻辑一致性分析
- `输出/重复模式分析_逆世天途.md`：重复模式分析

---

## 核心规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | **严格按计划执行** | 计划变更必须先确认，不得自行"灵活处理" |
| 2 | **隔离性** | 所有代码放在 `story-analyzer/` 下，不碰 `backend/` 和 `extension/` |
| 3 | **API 调用方式** | Phase 1 直调 DeepSeek API；Phase 2 必须走 OpenSquilla MCP |
| 4 | **不读原文做 Phase 2** | Phase 2 只读 .md 概要，重读原文就是浪费 token |
| 5 | **数据落地 .md** | 不用数据库，全部存为 markdown 文件 |
| 6 | **人物小传要累积** | 追加模式，角色已存在时只追加行为记录，不重复完整小传 |
| 7 | **Phase 2 显式指定模型** | 必须 `--model deepseek-v4-pro`，不依赖自动路由（router 可能降级） |
| 8 | **输出文件命名规范** | `输出/分析类型_逆世天途.md` 格式，统一 `_逆世天途` 后缀 |
| 9 | **不重跑不浪费** | 分析结果 JSON 先缓存，写入失败只重试提取不重新调 API |

---

## Operations — 操作手册

### 0. 环境准备

```bash
# 确保 Gateway 运行（守护进程，常驻后台）
curl http://127.0.0.1:18791/health
# 若不运行：
opensquilla gateway run &

# 确保 PATH 正确（避免 WindowsApps stub 挡路）
which opensquilla    # → ~/.local/bin/opensquilla
which python         # → D:/tools/python/python.exe
```

### 1. Phase 2 分析（标准流程）

```bash
# 单次分析（推荐）
opensquilla agent \
  --model deepseek-v4-pro \
  --file output/story_summary.md \
  --file output/character_profiles.md \
  --message "分析要求..." \
  --json --timeout 300 --unattended > output/raw_result.json 2>/dev/null

# 提取结果（解决 GBK 编码问题，用 Python subprocess）
D:/tools/python/python.exe -c "
import json, subprocess
# 直接从原始 JSON 文件提取
with open('output/raw_result.json', 'rb') as f:
    raw = f.read()
idx = raw.find(b'{\"status\"')
data = json.loads(raw[idx:].decode('gbk'))  # 关键：GBK 解码
with open('输出/文件名.md', 'w', encoding='utf-8') as f:
    f.write(data['text'])
"
```

### 2. 会话式分析（多轮共享上下文）

```bash
opensquilla agent \
  --session-id novel-phase2 \
  --model deepseek-v4-pro \
  --file output/story_summary.md \
  --file output/character_profiles.md \
  --message "第一轮：逻辑一致性分析" --json --timeout 300

# 第二轮不用 --file，同一 session 保持上下文
opensquilla agent \
  --session-id novel-phase2 \
  --model deepseek-v4-pro \
  --message "第二轮：现在做重复模式分析" --json --timeout 300
```

### 3. 查看历史分析

- Web UI: http://127.0.0.1:18791/control/
- CLI: `opensquilla sessions list` → `opensquilla sessions read <key>`
