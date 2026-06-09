#!/usr/bin/env python3
"""
一键流水线：第N章 改文→追加→审阅
用法: python run_chapter.py <N>
"""
import sys, os, json, re, subprocess

def log(msg): print(f"[{msg}]")

def run_opensquilla(ch_num):
    log(f"OpenSquilla 改文第{ch_num}章")
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    # Get API key
    env_path = r'd:\project file\ModifyArt\backend\.env'
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith('DEEPSEEK_API_KEY='):
                    env['DEEPSEEK_API_KEY'] = line.split('=',1)[1].strip()
    env['PATH'] = os.path.expanduser('~/.local/bin') + os.pathsep + env.get('PATH','')

    input_md = rf'd:\project file\ModifyArt\tools\input_ch{ch_num}.md'
    rules_md = rf'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨\修改规则.md'
    out_json = rf'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨\output\raw_edit_{ch_num}.json'

    session_id = '贞观贱王-改文'  # 同一本书保持同一会话，上下文不断
    cmd = ['opensquilla', 'agent',
        '--session-id', session_id,
        '--file', rules_md,
        '--file', input_md,
        '--message', f'逐条审查第{ch_num}章输出完整正文+修改细节对照表',
        '--json', '--timeout', '600', '--unattended']

    result = subprocess.run(cmd, capture_output=True, env=env, timeout=600)
    stdout = result.stdout.decode('utf-8', errors='replace')
    with open(out_json, 'w', encoding='utf-8') as f:
        f.write(stdout)

    # Check if valid JSON in output
    for line in reversed(stdout.strip().split('\n')):
        if line.startswith('{'):
            try:
                data = json.loads(line)
                log(f"OpenSquilla OK: {len(data.get('text',''))} chars")
                return data
            except: continue
    log("OpenSquilla JSON not found, using fallback")
    return None

def append_chapter(ch_num, data):
    log(f"追加第{ch_num}章")
    append_py = r'd:\project file\ModifyArt\tools\append_chapter.py'
    raw_json = rf'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨\output\raw_edit_{ch_num}.json'
    result = subprocess.run(['python3', append_py, raw_json], capture_output=True, text=True)
    log(result.stdout.strip() or result.stderr.strip())

def run_reviewer(ch_num):
    log(f"审阅第{ch_num}章")
    main_txt = r'd:\project file\ModifyArt\story-analyzer\workspaces\贞观贱王：我抢了弟弟的龙脉骨\output\改文_贞观贱王.txt'
    skill = r'd:\project file\ModifyArt\.claude\skills\adversarial-reviewer-perspective\SKILL.md'

    # Count lines to find chapter range
    with open(main_txt, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    ch_start = None
    for i, line in enumerate(lines):
        if f'第{ch_num}章' in line:
            ch_start = i
            break

    if ch_start:
        log(f"第{ch_num}章在正文第{ch_start+1}行起")
        # Open in editor for user
        subprocess.run(['code', '--goto', f'{main_txt}:{ch_start+1}'])
    else:
        log("未找到章节位置")

def main():
    ch = sys.argv[1] if len(sys.argv) > 1 else '12'
    log(f"=== 第{ch}章 流水线开始 ===")

    # Check input file exists
    input_file = rf'd:\project file\ModifyArt\tools\input_ch{ch}.md'
    if not os.path.exists(input_file):
        log(f"输入文件不存在: {input_file}")
        sys.exit(1)

    data = run_opensquilla(ch)
    append_chapter(ch, data)
    run_reviewer(ch)

    log(f"=== 第{ch}章 完成 ===")

if __name__ == '__main__':
    main()
