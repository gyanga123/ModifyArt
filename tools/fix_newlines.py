#!/usr/bin/env python3
"""Fix literal \n in the output file."""
import sys

path = sys.argv[1]

with open(path, 'rb') as f:
    raw = f.read()

# Count literal backslash (0x5c) followed by 'n' (0x6e)
count_bs_n = 0
for i in range(len(raw) - 1):
    if raw[i] == 0x5c and raw[i+1] == 0x6e:
        count_bs_n += 1

count_nl = raw.count(b'\n')

print(f"Literal backslash-n: {count_bs_n}")
print(f"Actual newlines: {count_nl}")

if count_bs_n == 0:
    print("No literal backslash-n found, file is OK")
    sys.exit(0)

# Replace all literal \n (0x5c 0x6e) with actual newline (0x0a)
new_raw = bytearray()
i = 0
while i < len(raw):
    if i < len(raw) - 1 and raw[i] == 0x5c and raw[i+1] == 0x6e:
        new_raw.append(0x0a)  # actual newline
        i += 2
    else:
        new_raw.append(raw[i])
        i += 1

with open(path, 'wb') as f:
    f.write(bytes(new_raw))

print(f"Fixed! Replaced {count_bs_n} literal \\n with newlines")
