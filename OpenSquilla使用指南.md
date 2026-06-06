# OpenSquilla 使用指南

> 版本 0.3.1 | 安装日期 2026-06-04 | 基于官方文档 + 实测

---

## 一、它是什么（不是只切模型）

OpenSquilla 是一个**完整的 AI Agent 运行时**，不是一个简单的模型代理。核心四层能力：

### 1. SquillaRouter 智能路由 — 按难度选模型

```
简单任务（聊天/写作/摘要） → c0/c1 便宜模型
复杂推理（代码审查/数学）   → c2/c3 强模型
```

当前配置 `deepseek` 分级：
| 层级 | 模型 | 月费参考 |
|------|------|---------|
| c0/c1 | deepseek-v4-flash | $0.14/0.28 per 1M |
| c2/c3 | deepseek-v4-pro | $1.74/3.48 per 1M |

**不是"永远用最便宜的"，而是"该省省该花花"。**

### 2. Tool Compression — 这才是省 token 的核心

当 AI 调用工具（读文件、搜索、跑命令）时，返回结果可能几万行。OpenSquilla 自动压缩：

| 模式 | 效果 |
|------|------|
| `truncate` | 智能截断，保留首尾关键信息 |
| `summarize` | 用模型总结长内容，只给下一轮看摘要 |
| `structured projection` | 对 JSON/日志/表格做结构化提取 |

调用期间压缩所产生的次数，也就是用便宜模型来处理中间环节。

### 3. Compaction — 长对话不爆炸

写小说时对话会很长。普通 AI 聊到后面开始"忘事"，token 消耗飙升。OpenSquilla：
- 自动把旧对话压缩成结构化摘要
- 保留：目标/进度/已改文件/已知问题/下一步
- 保持 prompt cache 热度，不让缓存失效

### 4. Meta-Skills — 可复用的智能工作流

内置 9 个稳定工作流（见附表）。调用方式：

```text
Use meta-skill `meta-web-research-to-report`.
帮我调研唐代服饰资料，输出一份带来源引用的报告。
```

---

## 二、启动与管理

### 启动 Gateway（必须先启动）

```powershell
# 设置环境变量（如果重启了终端）
$env:Path = "$env:USERPROFILE\.local\bin;" + $env:Path
$env:DEEPSEEK_API_KEY = "sk-你的key"

# 启动
opensquilla gateway run
```

启动后：
- Web 控制台: http://127.0.0.1:18791/control/
- API 端点: http://127.0.0.1:18791
- 调试日志: `C:\Users\Administrator\.opensquilla\logs\debug.log`

### 常用命令

```bash
opensquilla gateway status          # 查看 gateway 状态
opensquilla onboard status          # 查看配置完整性
opensquilla providers status        # 查看模型供应商状态
opensquilla diagnostics on          # 开启诊断，看 token 消耗明细
opensquilla sessions list           # 列出所有会话
opensquilla cost                    # 查看费用
```

### 检测到的一处值得优化的地方：配置(已实现)

```bash
# 配置新供应商
opensquilla onboard configure provider --provider <供应商名> --model <模型> --api-key-env <环境变量名>

# 支持的中文供应商
# 豆包: volcengine  |  文心: qianfan  |  通义: dashscope
# 智谱: zhipu       |  Kimi: moonshot  |  DeepSeek: deepseek
```

---

## 三、在 Claude Code 中使用（MCP Bridge）

### 架构

```
Claude Code（你当前的对话）
    │
    │ 调用 MCP 工具
    ▼
opensquilla MCP Bridge（本地 stdio 进程）
    │
    │ WebSocket
    ▼
OpenSquilla Gateway（127.0.0.1:18791）
    │
    ├── SquillaRouter → 选模型
    ├── Tool Compression → 压缩结果
    └── Memory → 持久记忆
```

### 可用 MCP 工具

| 工具名 | 用途 | 关键参数 |
|--------|------|---------|
| `messages_send` | **发送消息给 OpenSquilla 处理** | key, message |
| `messages_read` | 读取会话历史 | key, limit |
| `conversations_list` | 列出所有会话 | limit |
| `session_resolve` | 解析会话标识 | key |
| `events_wait` | 等待实时事件 | key, timeout_ms |
| `transcript_export` | 导出会话为 JSONL | key, limit |

### 使用模式

#### 模式 A：单次委托

把子任务丢给 OpenSquilla，用便宜模型处理，结果返回 Claude Code：

```
Claude: 调用 messages_send，key="research"，message="搜索唐代官服等级制度，整理成表格"
        → OpenSquilla 用 Flash 模型 + 搜索 → 返回压缩后的结果
        → Claude 继续基于结果工作
```

#### 模式 B：长会话（写小说适用）

为每个写作任务建独立 session：

```
1. 先用 messages_send 创建一个写作会话
2. 在 OpenSquilla 侧进行长篇幅创作（享受 Compaction + Tool Compression）
3. 需要时用 messages_read 取回成果
4. Claude Code 保持轻量，只做高层决策
```

### 启动文件

- MCP 配置: `C:\Users\Administrator\.claude\.mcp.json`
- MCP 启动脚本: `C:\Users\Administrator\.claude\scripts\opensquilla-mcp-launcher.sh`

---

## 四、项目级模型配置

当前项目 `ModifyArt` 已配好：

```
项目 .claude/settings.json:
  ANTHROPIC_MODEL = deepseek-v4-flash     ← 默认用便宜模型
  ANTHROPIC_DEFAULT_OPUS_MODEL = deepseek-v4-pro[1m]  ← 复杂任务自动升档
  
全局 ~/.claude/settings.json:
  保持 deepseek-v4-pro[1m]  ← 其他项目用 Pro
```

离开这个项目，自动恢复用 Pro。

---

## 五、扩展供应商（以后配）

### 方案 A：OpenRouter 一键通吃

去 [openrouter.ai](https://openrouter.ai) 注册 → 拿到 Key → 一条命令：

```bash
opensquilla onboard configure provider --provider openrouter --api-key-env OPENROUTER_API_KEY
```

一个 Key 访问 200+ 模型（DeepSeek/豆包/文心/智谱/Claude……）。

### 方案 B：逐个配

```bash
# 豆包
opensquilla onboard configure provider --provider volcengine --model doubao-seed-2-0-lite-260215 --api-key-env VOLCENGINE_API_KEY
# 文心
opensquilla onboard configure provider --provider qianfan --model <model> --api-key-env QIANFAN_API_KEY
```

---

## 附录 A：内置 Meta-Skills 列表

| MetaSkill | 用途 |
|-----------|------|
| `meta-document-to-decision` | 合同/报价/续约 → 签/拒/谈判建议 |
| `meta-web-research-to-report` | 多源调研 → 带引用来源的报告 |
| `meta-competitive-intel` | 客户/竞品信号 → 销售/竞品简报 |
| `meta-daily-operator-brief` | 今日任务+上下文 → 操作简报 |
| `meta-job-search-pipeline` | JD+简历 → 申请材料+面试准备 |
| `meta-kid-project-planner` | 安全适龄的项目计划 |
| `meta-paper-write` | 学术论文结构+引用+LaTeX |
| `meta-short-drama` | 短剧脚本+分镜+字幕 |
| `meta-skill-creator` | 把重复工作变成新的 MetaSkill |

## 附录 B：关键文件路径

| 文件 | 路径 |
|------|------|
| Gateway 配置 | `C:\Users\Administrator\.opensquilla\config.toml` |
| 工作区 | `C:\Users\Administrator\.opensquilla\workspace` |
| 记忆数据库 | `C:\Users\Administrator\.opensquilla\state\agents\main\memory.db` |
| Claude Code MCP 配置 | `C:\Users\Administrator\.claude\.mcp.json` |
| MCP 启动脚本 | `C:\Users\Administrator\.claude\scripts\opensquilla-mcp-launcher.sh` |
| 本项目模型配置 | `d:\project file\ModifyArt\.claude\settings.json` |
