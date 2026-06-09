#!/usr/bin/env python3
"""
清洗 OpenSquilla raw_edit JSON → 提取纯正文 → 追加到改文主文件。

用法:
    python append_chapter.py <raw_edit_N.json>

自动识别 output/ 所在目录，追加到同目录的 改文_贞观贱王.txt。
支持两种 OpenSquilla 输出模式：
  1. text 字段直接包含正文（raw_edit_7.json 模式）
  2. text 字段为 "The generated file is ready: xxx"（raw_edit_8.json 模式，实际内容在 workspace 文件中）
"""

import json, re, sys, os

# ── 工具函数 ────────────────────────────────────────────────

def extract_json_text(raw: bytes) -> str | None:
    """
    从 log+JSON 混合文件中提取最后一个 JSON 的 text 字段。
    通过 json.loads 完整解析，自动处理 \\n、\\" 等转义。
    兼容 GBK/GB18030 编码。
    """
    lines = raw.split(b'\n')
    for line in reversed(lines):
        line = line.strip()
        if not line or not line.startswith(b'{'):
            continue
        # Try decode as UTF-8 first
        for enc in ('utf-8', 'gbk', 'gb18030', 'gb2312'):
            try:
                decoded = line.decode(enc)
                data = json.loads(decoded)
                text = data.get('text', '')
                if text and len(text) > 50:
                    # Verify it has content (Chinese chars or printable ASCII)
                    if sum(1 for c in text if '一' <= c <= '鿿') > 5 or sum(1 for c in text if c.isprintable()) > 20:
                        return text
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
    return None


def remove_gaibiao(text: str) -> str:
    """删除 【改N】 标记。"""
    return re.sub(r'【改\d+】', '', text)


def remove_trailing_garbage(text: str) -> str:
    """删除结尾的修改对照表、Token 统计、--- 分隔线等。"""
    for marker in ('修改细节对照', '修改明细', '验证清单', '修改总结',
                   'Token 消耗', 'Token消耗', '| # ', '| 序号', '| 类型',
                   '修改详情', '修改记录', '修改前后对照', '修改统计', '验证清单'):
        i = text.find(marker)
        if i >= 0:
            text = text[:i]
    text = re.sub(r'\n---+\s*\*{0,2}\s*$', '', text)
    text = re.sub(r'[（(]完[，,]\s*待续[）)]', '', text)
    return text.strip()


def clean_chapter(text: str) -> str:
    """从 OpenSquilla 回复文本中提取干净章节正文。"""
    # 删掉 markdown 加粗标记
    text = re.sub(r'\*\*', '', text)
    # 删掉表头 #
    text = re.sub(r'^# ', '', text)
    # 查找章节标题
    m = re.search(r'(?:修改后(?:的)?)?(第\d+章[：:].*)', text)
    if m:
        text = text[m.start():]
    text = remove_gaibiao(text)
    text = remove_trailing_garbage(text)
    return text


def find_workspace_chapter(raw_edit_path: str) -> str | None:
    """OpenSquilla 可能把文件写到了 workspace 里，尝试定位。"""
    # 从 raw_edit JSON 中提取 workspace 路径 / 文件名
    with open(raw_edit_path, 'rb') as f:
        raw = f.read()
    txt = raw.decode('utf-8', errors='replace')
    lines = txt.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                data = json.loads(line)
                # artifacts 包含文件信息
                artifacts = data.get('artifacts', [])
                for art in artifacts:
                    name = art.get('name', '')
                    if name and name.endswith('.txt'):
                        # 在 workspace 中搜索
                        wsp = os.path.expanduser('~/.opensquilla/workspace')
                        for root, dirs, files in os.walk(wsp):
                            for f in files:
                                if f == name:
                                    return os.path.join(root, f)
            except:
                pass
    return None


# ── 主流程 ────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法: python append_chapter.py <raw_edit_N.json>")
        sys.exit(1)

    src = sys.argv[1]
    if not os.path.exists(src):
        print(f"文件不存在: {src}")
        sys.exit(1)

    src_abs = os.path.abspath(src)
    out_dir = os.path.dirname(src_abs)
    output_txt = os.path.join(out_dir, '改文_贞观贱王.txt')

    chapter = None
    source_desc = ''

    # 方案 A：从 JSON text 字段提取（通过 json.loads 解析，自动处理转义）
    with open(src_abs, 'rb') as f:
        raw = f.read()
    full_text = extract_json_text(raw)
    if full_text:
        clean = clean_chapter(full_text)
        if re.search(r'第\d+章[：:]\S', clean):
            chapter = clean
            source_desc = 'JSON text field'

    # 方案 B：如果 text 字段是 "generated file is ready"，去 workspace 找
    if not chapter:
        ws_path = find_workspace_chapter(src_abs)
        if ws_path and os.path.exists(ws_path):
            with open(ws_path, 'r', encoding='utf-8', errors='replace') as f:
                ws_text = f.read()
            clean = clean_chapter(ws_text)
            if re.search(r'第\d+章[：:]\S', clean):
                chapter = clean
                source_desc = f'workspace file: {ws_path}'

    # 方案 C：从 chapters/ 目录拿原文
    if not chapter:
        chnum_m = re.search(r'raw_edit_(\d+)\.json$', src_abs)
        if chnum_m:
            chnum = chnum_m.group(1)
            ch_path = os.path.join(out_dir, 'chapters', f'{chnum}.txt')
            if os.path.exists(ch_path):
                with open(ch_path, 'r', encoding='utf-8') as f:
                    chapter = f.read().strip()
                source_desc = f'original chapters/{chnum}.txt (fallback)'

    if not chapter:
        print("错误: 无法从任何来源提取章节正文")
        sys.exit(1)

    # 提取章节号
    num_m = re.search(r'第(\d+)章', chapter)
    ch_num = num_m.group(1) if num_m else '??'

    # 检查是否已存在
    if os.path.exists(output_txt):
        with open(output_txt, 'r', encoding='utf-8') as f:
            existing = f.read()
        if f'第{ch_num}章' in existing[:500]:
            print(f"! 第 {ch_num} 章已在 {output_txt} 中，跳过")
            sys.exit(0)

    # 追加
    with open(output_txt, 'a', encoding='utf-8') as f:
        if os.path.getsize(output_txt) > 0:
            f.write('\n\n\n')
        f.write(chapter)

    print(f"[OK] 第 {ch_num} 章 -> {output_txt}  ({len(chapter)} chars, source={source_desc})")


if __name__ == '__main__':
    main()
