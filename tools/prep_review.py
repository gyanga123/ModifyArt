#!/usr/bin/env python3
"""Prepare comprehensive review input for a given chapter."""
import re, sys

ch_num = sys.argv[1] if len(sys.argv) > 1 else '16'
workspace = r'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨'

# Read story summary for plot context
with open(f'{workspace}/output/story_summary.md', 'r', encoding='utf-8') as f:
    story_summary = f.read()

# Read rewritten chapter from main output
with open(f'{workspace}/output/改文_贞观贱王.txt', 'r', encoding='utf-8') as f:
    written = f.read()

# Extract current chapter from rewritten text
m = re.search(f'第{ch_num}章[：:].*?(?=\n\n\n第|\Z)', written, re.DOTALL)
rewritten_ch = m.group(0).strip() if m else ''

# Read modification table from OpenSquilla output
try:
    with open(f'{workspace}/output/ch{ch_num}_review_input.md', 'r', encoding='utf-8') as f:
        mod_table = f.read()
except:
    mod_table = '(无独立对照表，需从raw_edit提取)'

combined = f"""# 第{ch_num}章 审阅材料

## 一、故事概要（已有剧情上下文）
{story_summary[:10000]}

## 二、改文（改文后完整正文）
{rewritten_ch}

## 三、OpenSquilla 修改对照表
{mod_table}
"""

output = f'{workspace}/output/ch{ch_num}_review_full.md'
with open(output, 'w', encoding='utf-8') as f:
    f.write(combined)

print(f'Story summary: excerpt ({len(story_summary)} chars total)')
print(f'Rewritten: {len(rewritten_ch)} chars')
print(f'Saved: {len(combined)} chars to {output}')
