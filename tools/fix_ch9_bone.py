"""Fix Chapter 9: change fake bone to real bone with shock realization."""
p = r'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨\output\改文_贞观贱王.txt'

with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 1334 (0-indexed): the bone description
# Line 1336: the reaction
# Line 1338: "找到了。"
old_line_1334 = lines[1333].rstrip('\n')
old_line_1336 = lines[1335].rstrip('\n')
old_line_1338 = lines[1337].rstrip('\n')

print("Before:")
print(f"  1334: [{old_line_1334[:50]}]")
print(f"  1336: [{old_line_1336[:50]}]")
print(f"  1338: [{old_line_1338[:50]}]")

# Find the indentation
import re
indent = old_line_1334[:len(old_line_1334) - len(old_line_1334.lstrip())]

# Replace
lines[1333] = indent + '祭坛中央，静静躺着一根泛着幽蓝光芒的骨头——那气息再熟悉不过，正是他亲手埋藏在宫外的那根真骨！\n'
lines[1335] = indent + '李恪瞳孔骤缩。袁道玄竟找到了他的藏骨之处——是术法追踪？还是从一开始就被盯上了？这老狐狸比他预想的更深。\n'
lines[1337] = indent + '"竟然在这儿……"\n'

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\nAfter fix:")
print("  1334: 祭坛中央...正是他亲手埋藏在宫外的那根真骨！")
print("  1336: 李恪瞳孔骤缩。袁道玄竟找到了他的藏骨之处...")
print("  1338: \"竟然在这儿…\"")
