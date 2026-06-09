#!/usr/bin/env python3
"""改文前检查：扫描章节原文中的设定冲突，输出修改重点。"""
import re, sys

ch_num = sys.argv[1] if len(sys.argv) > 1 else '18'
workspace = r'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨'

with open(f'{workspace}/原文_贞观贱王：我抢了弟弟的龙脉骨.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find chapter
start = None
for i, line in enumerate(lines):
    if f'第{ch_num}章' in line:
        start = i
        break
if start is None:
    print(f'第{ch_num}章 未找到')
    sys.exit(1)

ch_text = ''.join(lines[start:]).strip()
# Take until next chapter
m = re.search(rf'(第{ch_num}章.*?)(?=\n\s*第\d+章)', ch_text, re.DOTALL)
if m:
    ch_text = m.group(1).strip()

issues = []

# 检查1：龙脉骨在谁手里（第13章后被袁道玄窃走，李恪只剩玉牌）
if int(ch_num) > 13:
    # 李恪持有龙脉骨的描写
    for match in re.finditer(r'[^。]*?(李恪|怀里|袖中|掌心|摸出|取出|拿出)[^。]*?龙脉骨[^。]*?。', ch_text):
        issues.append(f'【龙脉骨设定】李恪不应持有龙脉骨（已被袁道玄窃走）。原文: "{match.group().strip()}" → 改为"玉牌/龙气"')

    # 系统提示中"龙脉骨"
    for match in re.finditer(r'【[^】]*?龙脉骨[^】]*?】', ch_text):
        issues.append(f'【系统提示】涉及"龙脉骨"需改为"龙脉气运"。原文: {match.group()}')

    # 普通人提及龙脉骨
    for match in re.finditer(r'(?:百姓|阿福|房遗爱|贵妃|魏征|朝臣|小太监|侍卫)[^。]*?龙脉骨[^。]*?。', ch_text):
        issues.append(f'【普通人知情】非修道之人不应提及"龙脉骨"。原文: "{match.group().strip()}"')

    # 李愔提及龙脉骨
    for match in re.finditer(r'(?:李愔|小王爷|四殿下|弟弟|阿愔)[^。]*?龙脉骨[^。]*?。', ch_text):
        issues.append(f'【李愔知情】李愔只能感知异常，不能直接说"龙脉骨"。原文: "{match.group().strip()}"')

# 检查2：称呼问题 - 阿福称皇子
for match in re.finditer(r'阿福说小王爷', ch_text):
    issues.append(f'【称呼】阿福称皇子用"殿下"不用"小王爷"。原文: "{match.group()}" → "四殿下"')

# 检查3：普通人不知龙脉骨
if int(ch_num) > 1:
    for match in re.finditer(r'(?:道士|百姓|路人)[^。]*?骨头|龙骨[^。]*?。', ch_text):
        issues.append(f'【普通人知情】百姓传谣不应提"骨头/龙骨"。原文: "{match.group().strip()}"')

if issues:
    print(f'第{ch_num}章 发现 {len(issues)} 处设定冲突：')
    for i, issue in enumerate(issues, 1):
        print(f'  {i}. {issue}')
else:
    print(f'第{ch_num}章 未发现设定冲突')
