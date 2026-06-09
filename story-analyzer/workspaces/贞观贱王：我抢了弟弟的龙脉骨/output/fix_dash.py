#!/usr/bin/env python3
"""Replace AI-typical —— overuse in narrative text."""
import re

with open('改文_贞观贱王.txt', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')
total_before = text.count('——')
print(f'原始 —— 数量: {total_before}')

changes = 0
new_lines = []

for i, line in enumerate(lines):
    stripped = line.strip()

    # Skip lines that are clearly dialogue or special formatting
    # Dialogue starts with 「 or " and has a closing quote
    # System messages with 【】
    # Sound effects
    skip_line = False

    # Check if this line is dialogue (contains 「」 or is a quote-heavy line)
    quote_chars = stripped.count('"')
    has_opening_quote = stripped.startswith('"')

    # Sound effect lines (only a sound)
    sound_patterns = ['吱呀', '吱——', '啪', '咔']

    # Special cases: lines that are mostly dialogue or sound effects
    for sp in sound_patterns:
        if sp in stripped and len(stripped) < 20:
            skip_line = True
            break

    if skip_line:
        new_lines.append(line)
        continue

    orig = line

    # In narrative lines, replace —— that functions as explanatory comma/colon
    # The key pattern: 「statement —— explanation」
    # Replace —— with ，when followed by explanatory words in non-dialogue context

    # Pattern 1: ——是/正是 → ，是/正是
    if not has_opening_quote:
        line = re.sub(r'——(正是|就是|那是|这是|却是|则是|便是|可是)', r'，\1', line)

    # Pattern 2: ——那/这 → ，那/这 (only when it's explanatory, not dramatic)
    if not has_opening_quote:
        line = re.sub(r'——(那|这)(一|个|些|种|片|枚|块|根|张|条|座|间|处|本|件|副|把|面)', r'，\1\2', line)

    # Pattern 3: ——[人名/身份] at end of sentence
    if not has_opening_quote:
        line = re.sub(r'——，', '，', line)  # cleanup double punctuation
        line = re.sub(r'，——', '，', line)   # cleanup comma-dash

    if line != orig:
        changes += 1

    new_lines.append(line)

text = '\n'.join(new_lines)
total_after = text.count('——')
print(f'替换后 —— 数量: {total_after}')
print(f'修改行数: {changes}')

with open('改文_贞观贱王.txt', 'w', encoding='utf-8') as f:
    f.write(text)

print('完成')
