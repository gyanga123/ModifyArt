p = r'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨\output\改文_贞观贱王.txt'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(1333, 1342):
    line = lines[i]
    rline = line.rstrip('\n').rstrip('\r')
    spaces = '·' * 4
    print('Line', i+1, ': len=', len(rline), ': [', rline[:60], ']')
