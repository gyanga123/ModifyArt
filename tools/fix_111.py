#!/usr/bin/env python3
"""Fix escaped quotes in 111.txt"""
p = r'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨\output\111.txt'

with open(p, 'rb') as f:
    raw = f.read()

# Count escaped quotes - backslash + double-quote (0x5c 0x22)
count = 0
for i in range(len(raw) - 1):
    if raw[i] == 0x5c and raw[i+1] == 0x22:
        count += 1
print(f"Escaped quotes found: {count}")

# Replace each 0x5c 0x22 with just 0x22
result = bytearray()
i = 0
while i < len(raw):
    if i < len(raw) - 1 and raw[i] == 0x5c and raw[i+1] == 0x22:
        result.append(0x22)  # just the quote
        i += 2
    else:
        result.append(raw[i])
        i += 1

with open(p, 'wb') as f:
    f.write(bytes(result))

# Verify
with open(p, 'rb') as f:
    raw2 = f.read()

count2 = 0
for i in range(len(raw2) - 1):
    if raw2[i] == 0x5c and raw2[i+1] == 0x22:
        count2 += 1

print(f"After fix: {count2} remaining")

# Show the user's selected line
with open(p, 'r', encoding='utf-8') as f:
    for line in f:
        if '李恪嘴角轻扬' in line:
            print(f"Fixed line: {line.rstrip()}")
            break
