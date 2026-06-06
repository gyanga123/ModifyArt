#!/usr/bin/env python3
"""Extract text field from raw OpenSquilla JSON result and write to logic_analysis.md"""
import json

with open('output/raw_logic_result.json', 'rb') as f:
    raw = f.read()

lines = raw.split(b'\n')
json_lines = []
in_json = False
for line in lines:
    if line.startswith(b'{"status"'):
        in_json = True
    if in_json:
        json_lines.append(line)

if not json_lines:
    print("ERROR: no JSON found")
    exit(1)

json_str = b'\n'.join(json_lines)
data = json.loads(json_str)
text = data['text']

with open('output/logic_analysis.md', 'w', encoding='utf-8') as f:
    f.write('# 《逆世天途》逻辑一致性分析报告\n\n')
    f.write('> 由 OpenSquilla 生成\n')
    f.write('> 分析范围：第 1 章 - 第 128 章\n')
    f.write('> 分析日期：2026-06-06\n\n')
    f.write('---\n\n')
    f.write(text)

print(f'OK - 写入 logic_analysis.md, 正文 {len(text)} 字')
usage = data.get('usage', {})
print(f'输入 tokens: {usage.get("input_tokens")}')
print(f'输出 tokens: {usage.get("output_tokens")}')
print(f'费用: ${usage.get("cost_usd", 0):.4f}')
routing = data.get('routing', {})
print(f'路由层级: {routing.get("routed_tier")}')
print(f'路由模型: {routing.get("routed_model")}')
