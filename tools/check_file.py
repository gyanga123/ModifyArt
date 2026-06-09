#!/usr/bin/env python3
"""检查改文文件各章节状态"""
import re, os, sys

path = r"d:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨\output\改文_贞观贱王.txt"

with open(path, 'rb') as f:
    raw = f.read()

# Find all chapter markers
markers = [b'\xe7\xac\xac\xe2\x85\xa6\xe7\xab\xa0',  # 第7章
           b'\xe7\xac\xac\xe2\x85\xa5\xe7\xab\xa0',  # 第8章  (incorrect)
           b'\xe7\xac\xac\xe2\x85\xa7\xe7\xab\xa0',  # 第9章  (incorrect)
           ]

# Just search for "第" + digit + "章" pattern
pattern = re.compile(b'\xe7\xac\xac[\x00-\xff]\xe7\xab\xa0')

for m in pattern.finditer(raw):
    ch = m.group().decode('utf-8', errors='replace')
    pos = m.start()
    nl_before = raw[:pos].count(b'\n') + 1
    # Show the chapter title line
    end = raw.find(b'\n', pos) if raw.find(b'\n', pos) >= 0 else pos+60
    title = raw[pos:end].decode('utf-8', errors='replace')[:60]
    print(f"Line {nl_before:>4}: {ch} - {title}")

with open(path, 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

ch7_count = text.count('第7章')
ch8_count = text.count('第8章')
print(f"\n第7章 occurrences: {ch7_count}")
print(f"第8章 occurrences: {ch8_count}")
print(f"File size: {len(raw)} bytes")
print(f"Total lines: {raw.count(b'\n') + 1}")
