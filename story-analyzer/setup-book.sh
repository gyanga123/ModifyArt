#!/bin/bash
# setup-book.sh — 创建新书工作区
# 用法: bash setup-book.sh 书名 [原文路径]

set -e

BOOK_NAME=$1
NOVEL_SRC=$2

if [ -z "$BOOK_NAME" ]; then
    echo "用法: bash setup-book.sh 书名 [原文路径]"
    echo "示例: bash setup-book.sh 逆世天途 "d:/path/to/原文.txt""
    exit 1
fi

SCRIPT_DIR="d:/project file/ModifyArt/story-analyzer"
WORKSPACE="$SCRIPT_DIR/workspaces/$BOOK_NAME"

if [ -d "$WORKSPACE" ]; then
    echo "[!] 工作区已存在: $WORKSPACE"
    echo "  要重新创建请先删除该目录"
    exit 1
fi

# 创建目录结构
mkdir -p "$WORKSPACE/output" "$WORKSPACE/输出"
echo "[OK] 工作区已创建: $WORKSPACE"

# 复制原文
if [ -n "$NOVEL_SRC" ]; then
    if [ -f "$NOVEL_SRC" ]; then
        cp "$NOVEL_SRC" "$WORKSPACE/原文_${BOOK_NAME}.txt"
        echo "[OK] 原文已复制: $WORKSPACE/原文_${BOOK_NAME}.txt"
    else
        echo "[!] 原文文件不存在: $NOVEL_SRC"
        exit 1
    fi
else
    echo "[提示] 未指定原文路径，请手动放置到: $WORKSPACE/原文_${BOOK_NAME}.txt"
fi

echo ""
echo "=== 工作区就绪 ==="
echo "  原文: $WORKSPACE/原文_${BOOK_NAME}.txt"
echo "  Phase 1 产出: $WORKSPACE/output/"
echo "  分析报告: $WORKSPACE/输出/"
echo ""
echo "  开始分析:"
echo "    python pipeline.py --book \"$BOOK_NAME\" --phase 1"
echo "    python run_phase2.py --book \"$BOOK_NAME\" all"
