#!/usr/bin/env python3
"""Extract raw text field bytes from raw_edit JSON files (fixes encoding issues)."""
import json, sys, re, os

def extract_text_bytes(raw_data):
    """Find the 'text' field in the last JSON line and return its raw bytes."""
    lines = raw_data.split(b'\n')
    last_line = None
    for line in reversed(lines):
        line = line.strip()
        if line.startswith(b'{') and line.endswith(b'}'):
            last_line = line
            break
    if not last_line:
        return None

    # Find the text field value
    marker = b'"text": "'
    idx = last_line.find(marker)
    if idx < 0:
        return None

    raw_start = idx + len(marker)
    result = bytearray()
    i = raw_start
    while i < len(last_line):
        b = last_line[i]
        if b == 0x5c:  # backslash
            next_b = last_line[i+1] if i+1 < len(last_line) else 0
            result.append(b)
            result.append(next_b)
            i += 2
            continue
        if b == 0x22:  # double quote
            # Check if this is the end of the field
            rest = last_line[i+1:].lstrip()
            if rest and rest[0:1] in (b',', b'}'):
                break
        result.append(b)
        i += 1

    return bytes(result)

def decode_with_fallback(raw_bytes):
    """Try multiple Chinese encodings, return the best result."""
    for enc in ['gbk', 'gb18030', 'gb2312', 'big5']:
        try:
            decoded = raw_bytes.decode(enc)
            # Validate it has some Chinese character patterns
            # Count CJK characters
            cjk_count = sum(1 for c in decoded if '一' <= c <= '鿿')
            if cjk_count > 10:
                return decoded, enc
        except:
            continue
    return raw_bytes.decode('utf-8', errors='replace'), 'utf8-replaced'

def clean_chapter_text(text):
    """Extract just the chapter content, removing analysis/modification details."""
    # Find modification detail markers
    detail_markers = [
        '修改细节对照', '修改明细', '验证清单', '修改总结',
        '修改详情', '修改记录', '修改前后对照',
        '修改统计', 'Token 消耗', 'Token消耗',
        '| # ', '| 序号', '| 类型',
    ]

    detail_start = len(text)
    for marker in detail_markers:
        idx = text.find(marker)
        if idx >= 0 and idx < detail_start:
            detail_start = idx

    # Also strip the opening conversation before the chapter
    chapter_start = 0

    # Look for chapter title patterns
    patterns = [
        r'修改后(?:的)?(第\d+章)',
        r'(第\d+章[：:].*)',
    ]

    for pat in patterns:
        m = re.search(pat, text)
        if m:
            # Walk backwards to include any preceding "**" markers
            start = m.start()
            # Include up to 2 chars before (like **)
            while start > 0 and text[start-1] == '*':
                start -= 1
            chapter_start = start
            break

    result = text[chapter_start:detail_start].strip()

    # Remove trailing separator lines
    result = re.sub(r'\n---+\s*$', '', result)
    result = re.sub(r'^---+\s*\n', '', result)

    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_raw_text.py <raw_edit.json> [output.txt]")
        sys.exit(1)

    with open(sys.argv[1], 'rb') as f:
        raw = f.read()

    raw_bytes = extract_text_bytes(raw)
    if not raw_bytes:
        print("ERROR: Could not find text field in JSON")
        sys.exit(1)

    decoded, enc = decode_with_fallback(raw_bytes)

    chapter = clean_chapter_text(decoded)

    if len(sys.argv) >= 3:
        outpath = sys.argv[2]
    else:
        outpath = os.path.splitext(sys.argv[1])[0] + '_chapter.txt'

    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(chapter)

    print(f"Decoded as: {enc}")
    print(f"Saved: {outpath} (len={len(chapter)} chars)")
    print(f"Preview: {chapter[:80]}...")

if __name__ == '__main__':
    main()
