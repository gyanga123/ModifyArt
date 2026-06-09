#!/usr/bin/env python3
"""
提取 OpenSquilla 修改结果中的正文并追加到输出文件。

用法:
    python extract_chapter.py <raw_edit_json_path> [output_txt_path]

示例:
    python extract_chapter.py "story-analyzer/workspaces/贞观贱王：我抢了弟弟的龙脉骨/output/raw_edit_7.json"

默认输出路径为 story-analyzer/workspaces/贞观贱王：我抢了弟弟的龙脉骨/output/改文_贞观贱王.txt
"""

import json
import re
import sys
import os

# 尝试修复 mojibake（乱码）—— 将错误解码的 UTF-8 重新编码回原始字节，再用正确编码解码
def fix_mojibake(text):
    """Attempt to fix mojibake by re-encoding to latin-1 and decoding as gbk, etc."""
    # The text was likely GBK bytes decoded as UTF-8, producing mojibake.
    # Strategy: encode back to latin-1 (which preserves bytes), then decode as gbk.
    try:
        # Encode the mojibake string back to bytes via latin-1 (lossless for any byte)
        raw_bytes = text.encode('latin-1')
        # Try GBK first
        try:
            fixed = raw_bytes.decode('gbk')
            # Check if it looks like valid Chinese
            if any('一' <= c <= '鿿' for c in fixed[:50]):
                return fixed
        except:
            pass
        # Try GB18030
        try:
            fixed = raw_bytes.decode('gb18030')
            if any('一' <= c <= '鿿' for c in fixed[:50]):
                return fixed
        except:
            pass
    except:
        pass
    return text  # Return as-is if we can't fix


def extract_clean_chapter(text_field):
    """从 OpenSquilla 的 text 字段中提取干净的章节正文。"""
    # First, try to fix mojibake
    fixed = fix_mojibake(text_field)
    text_field = fixed

    # Try to find the chapter content between markers
    # Pattern 1: "**修改后的第N章**" ... up to modification details
    patterns = [
        (r'\*\*修改后(?:的)?(第\d+章[：:].*?)\*\*', 'mod_detail'),  # **修改后的第X章：...**
        (r'(第\d+章[：:].*?)\s*\n', 'mod_simple'),  # 第X章：...
    ]

    # Find modification detail section end
    detail_markers = [
        '**修改细节对照**',
        '修改细节对照',
        '**修改明细**',
        '修改明细',
        '**验证清单**',
        '**修改总结**',
        '修改总结',
        '**验证',
        '| # | 原文',
        '| # | 位置',
        '---\n\n**修改',
        '**修改详情**',
        '修改详情',
        '**修改记录**',
        '修改记录',
        '修改前后对照',
        '| # | 类型',
    ]

    # Find where the modification detail/analysis section starts
    detail_start = len(text_field)
    for marker in detail_markers:
        idx = text_field.find(marker)
        if idx >= 0 and idx < detail_start:
            detail_start = idx

    # Try to extract just the chapter content
    # Look for the chapter title, then extract until detail_start

    # Pattern: "修改后的第N章" followed by the chapter content
    chapter_patterns = [
        r'\*\*修改后(?:的)?(第\d+章.*?)\*\*',
        r'##?\s*修改后(?:的)?(第\d+章)',
        r'修改后(?:的)?(第\d+章[：:])',
        r'(第\d+章[：:].*?)(?:\n|$)',
    ]

    for pattern in chapter_patterns:
        match = re.search(pattern, text_field)
        if match:
            start = match.start()
            chapter_text = text_field[start:detail_start]
            return chapter_text.strip()

    # If no pattern matched but we can find the chapter title directly
    chapter_match = re.search(r'第\d+章[：:]', text_field)
    if chapter_match:
        start = chapter_match.start()
        chapter_text = text_field[start:detail_start]
        return chapter_text.strip()

    # Last resort: return everything and let caller deal with it
    return text_field.strip()


def extract_usage_info(data):
    """从 JSON 数据中提取使用量信息。"""
    usage = data.get('usage', {})
    if not usage:
        return ''

    model = usage.get('model', 'unknown')
    tokens_in = usage.get('input_tokens', 0)
    tokens_out = usage.get('output_tokens', 0)
    tokens_total = usage.get('total_tokens', 0)
    cost = usage.get('cost_usd', 0)

    return f"\n\n【Token 消耗】输入: {tokens_in} | 输出: {tokens_out} | 总计: {tokens_total} | 模型: {model} | 费用: ${cost:.6f}"


def process_raw_edit(raw_edit_path, output_path=None):
    """处理 raw_edit JSON 文件，提取正文并追加到输出文件。"""
    # Read the raw file
    with open(raw_edit_path, 'rb') as f:
        raw_data = f.read()

    # Find the last valid JSON line (skip log lines at the beginning)
    content_str = raw_data.decode('utf-8', errors='replace')
    lines = content_str.strip().split('\n')

    # Find the last line that looks like a valid JSON object
    data = None
    for line in reversed(lines):
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                data = json.loads(line)
                break
            except json.JSONDecodeError:
                # Try to find JSON in the line (some logs wrap JSON)
                # Look for the outermost {...} structure
                brace_start = line.find('{')
                if brace_start >= 0:
                    try:
                        data = json.loads(line[brace_start:])
                        break
                    except:
                        pass
                continue

    if not data:
        print(f"错误: 无法从 {raw_edit_path} 解析 JSON", file=sys.stderr)
        return False

    # Extract the text field
    text_field = data.get('text', '')
    if not text_field:
        print(f"错误: JSON 中无 'text' 字段", file=sys.stderr)
        return False

    # Extract clean chapter
    clean_chapter = extract_clean_chapter(text_field)

    # Detect chapter number
    chapter_match = re.search(r'第(\d+)章', clean_chapter)
    chapter_num = chapter_match.group(1) if chapter_match else '??'

    # Determine output path
    if not output_path:
        # Default: same workspace as input
        input_dir = os.path.dirname(os.path.abspath(raw_edit_path))
        output_path = os.path.join(input_dir, '改文_贞观贱王.txt')

    # Check if chapter already exists in output
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            existing = f.read()
        if f'第{chapter_num}章' in existing:
            print(f"⚠ 第 {chapter_num} 章已在输出文件中存在，跳过追加")
            return True

    # Append to output
    with open(output_path, 'a', encoding='utf-8') as f:
        # Add a blank line separator if file isn't empty
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            f.write('\n\n\n')
        f.write(clean_chapter)

    print(f"✅ 第 {chapter_num} 章已追加到 {output_path}")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    raw_edit_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(raw_edit_path):
        print(f"错误: 文件不存在 {raw_edit_path}", file=sys.stderr)
        sys.exit(1)

    success = process_raw_edit(raw_edit_path, output_path)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
