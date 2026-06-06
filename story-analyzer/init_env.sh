#!/bin/bash
# init_env.sh — 一键环境检查
# 用法: bash init_env.sh             # 检查+输出报告
#        bash init_env.sh --fix-path # 自动修复 PATH（加到 .bashrc）
#        bash init_env.sh --check-only # 只检查不输出建议
# 返回码: 0=全部通过, 1=有警告, 2=有阻断项

# ─── 颜色 ───
RED='\e[31m'; GREEN='\e[32m'; YELLOW='\e[33m'; CYAN='\e[36m'; RESET='\e[0m'
PASS="${GREEN}✓${RESET}"; WARN="${YELLOW}⚠${RESET}"; FAIL="${RED}✗${RESET}"

HAS_BLOCKER=0; HAS_WARN=0

check() {
    local label="$1" status="$2" msg="$3"
    case "$status" in
        pass) echo -e "  $PASS $label";;
        warn) echo -e "  $WARN $label  → $msg"; HAS_WARN=1;;
        fail) echo -e "  $FAIL $label  → $msg"; HAS_BLOCKER=1;;
    esac
}

heading() { echo -e "\n${CYAN}═══ $1 ═══${RESET}"; }

# ─── 1. Gateway ───
heading "Gateway 守护进程"
GW_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18791/health 2>/dev/null)
if [ "$GW_STATUS" = "200" ]; then
    GW_OK=$(curl -s http://127.0.0.1:18791/health 2>/dev/null)
    check "Gateway (127.0.0.1:18791)" "pass" "$GW_OK"
else
    check "Gateway (127.0.0.1:18791)" "fail" "未运行！执行: opensquilla gateway run &"
fi

# ─── 2. PATH ───
heading "PATH & 可执行文件"

# Python — 直接检查文件，不依赖 which（Windows bash PATH 解析有问题）
if [ -x "/d/tools/python/python" ]; then
    PYTHON_VER=$(/d/tools/python/python --version 2>&1)
    check "python (/d/tools/python/python) — $PYTHON_VER" "pass"
elif echo "$(which python 2>/dev/null)" | grep -q "WindowsApps"; then
    check "python" "fail" "WindowsApps stub 挡路。执行: export PATH=/d/tools/python:\$PATH"
else
    check "python" "fail" "找不到 /d/tools/python/python。请确认 Python 已安装"
fi

# opensquilla
OS_PATH=$(which opensquilla 2>/dev/null)
if echo "$OS_PATH" | grep -q ".local/bin/opensquilla"; then
    check "opensquilla ($OS_PATH)" "pass"
else
    check "opensquilla" "fail" "找不到 opensquilla。预期: ~/.local/bin/opensquilla"
fi

# ─── 3. API Key ───
heading "API Key"
ENV_PATH="d:/project file/ModifyArt/backend/.env"
if [ -f "$ENV_PATH" ]; then
    KEY_COUNT=$(grep -c "DEEPSEEK_API_KEY=sk-" "$ENV_PATH" 2>/dev/null)
    if [ "$KEY_COUNT" -gt 0 ]; then
        check "DeepSeek API Key ($ENV_PATH)" "pass"
    else
        check "DeepSeek API Key" "fail" ".env 存在但未找到 DEEPSEEK_API_KEY=sk-..."
    fi
else
    check "DeepSeek API Key" "fail" ".env 文件不存在: $ENV_PATH"
fi

# ─── 4. 目录结构 ───
heading "项目目录"
ANALYZER="d:/project file/ModifyArt/story-analyzer"
[ -d "$ANALYZER" ] && check "$ANALYZER" "pass" || check "$ANALYZER" "fail" "目录不存在"
[ -d "$ANALYZER/output" ] && check "  output/" "pass" || check "  output/" "warn" "不存在"
[ -d "$ANALYZER/输出" ] && check "  输出/" "pass" || check "  输出/" "warn" "不存在"
[ -d "$ANALYZER/prompts" ] && check "  prompts/" "pass" || check "  prompts/" "warn" "不存在"

# 原文
NOVEL="d:/project file/ModifyArt/【改】逆世天途_utf8.txt"
[ -f "$NOVEL" ] && check "原文 ($NOVEL)" "pass" || check "原文" "fail" "不存在"

# Phase 1 产出
[ -f "$ANALYZER/output/story_summary.md" ] && check "  story_summary.md" "pass" || check "  story_summary.md" "warn" "Phase 1 未完成？"
[ -f "$ANALYZER/output/character_profiles.md" ] && check "  character_profiles.md" "pass" || check "  character_profiles.md" "warn" "Phase 1 未完成？"

# ─── 5. MCP 可用性 ───
heading "MCP Bridge"
MCP_CONFIG="C:/Users/Administrator/.claude/.mcp.json"
if [ -f "$MCP_CONFIG" ]; then
    check "MCP 配置 ($MCP_CONFIG)" "pass"
    # 检查 opensquilla-mcp-launcher.sh 是否存在
    LAUNCHER="C:/Users/Administrator/.claude/scripts/opensquilla-mcp-launcher.sh"
    [ -f "$LAUNCHER" ] && check "  启动脚本" "pass" || check "  启动脚本" "warn" "找不到启动脚本"
else
    check "MCP 配置" "warn" "不存在"
fi

# ─── 6. OpenSquilla 供应商状态 ───
heading "OpenSquilla 供应商"
if command -v opensquilla &>/dev/null; then
    PROVIDER_OUTPUT=$(opensquilla providers status 2>&1)
    if echo "$PROVIDER_OUTPUT" | grep -qi "deepseek" 2>/dev/null; then
        check "DeepSeek 供应商" "pass"
    else
        check "DeepSeek 供应商" "warn" "状态异常。运行 opensquilla onboard status 查看详情"
    fi
fi

# ─── 汇总 ───
heading "检查结果"
if [ "$HAS_BLOCKER" -gt 0 ]; then
    echo -e "${RED}有 $HAS_BLOCKER 项阻断问题，请修复后再继续${RESET}"
    echo ""
    echo "快速修复:"
    echo "  PATH:   export PATH=/d/tools/python:~/.local/bin:\$PATH"
    echo "  Python: 如果 python 指向 WindowsApps，用 D:/tools/python/python"
    echo "  Gateway: opensquilla gateway run &"
    exit 2
elif [ "$HAS_WARN" -gt 0 ]; then
    echo -e "${YELLOW}有 $HAS_WARN 项警告，建议查看但不阻断执行${RESET}"
    exit 1
else
    echo -e "${GREEN}全部通过！可以开始工作了。${RESET}"
    exit 0
fi
