# -*- coding: utf-8 -*-
"""
RizomUV 2027.0.598 简体中文补丁 —— 一键构建

从你自己购买的英文原版 rizomuv.exe 出发，依次应用词典与 UI 补丁，
产出纯界面汉化版（不改动任何内部运行逻辑）。

用法：
    1. 把英文原版 rizomuv.exe 复制到本目录，命名为 rizomuv.exe.bak
    2. python build_all.py
    3. 产物在 out/rizomuv_cn.exe

注意：本脚本不含也不分发 RizomUV 程序本体，请自行持有正版授权。
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'rizomuv.exe.bak'
BUILD = ROOT / 'build'
OUT = ROOT / 'out'
DICT = ROOT / 'dicts'
SCRIPTS = ROOT / 'src'

# 英文原版预期 MD5（RizomUV 2027.0.598.g864535413）
EXPECTED_MD5 = '2ddf8d6da2000ae3eac66d7eea59a311'


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def run(script: str, *args: str):
    cmd = [sys.executable, str(SCRIPTS / script), *map(str, args)]
    print('\n>>>', ' '.join(cmd))
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        sys.exit(f'构建失败：{script} 返回 {r.returncode}')


def main():
    if not SRC.exists():
        sys.exit('缺少英文原版：请把正版 rizomuv.exe 复制到本目录并改名为 rizomuv.exe.bak')

    actual = md5(SRC)
    if actual != EXPECTED_MD5:
        print(f'[警告] 英文原版 MD5={actual}，与预期 {EXPECTED_MD5} 不符。')
        print('       补丁按固定偏移匹配字符串，软件版本不一致可能导致失败。')
        print('       如需继续请输入 yes：', end='')
        if sys.stdin.readline().strip().lower() != 'yes':
            sys.exit('已取消。')

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir()
    OUT.mkdir(exist_ok=True)

    # 1) 词典 + 黑名单 -> 基础纯 UI 汉化版
    run('build.py',
        f'{DICT / "tr_core.json"},{DICT / "tr_phrase.json"}',
        BUILD / 'rizomuv_ui_only.exe',
        '--block', DICT / 'blocklist_ui_only.txt')

    # 2) 菜单 / 说明 / 面板词
    run('patch_menu.py', BUILD / 'rizomuv_menu_final.exe', DICT / 'menu_all.json')
    run('patch_tooltip.py')
    run('patch_all.py', BUILD / 'rizomuv_panel_final.exe', DICT / 'batch_all.json')

    # 3) 各面板增量补丁
    for script in [
        'patch_udim.py', 'patch_redbox.py', 'patch_similar.py',
        'patch_margin.py', 'patch_pack.py', 'patch_unwrap.py',
        'patch_tabs2.py', 'patch_menu2.py', 'patch_prefs.py',
    ]:
        run(script)

    final = BUILD / 'rizomuv_prefs_final.exe'
    dest = OUT / 'rizomuv_cn.exe'
    shutil.copyfile(final, dest)
    print(f'\n[完成] 汉化版已生成：{dest}')
    print(f'       MD5 = {md5(dest)}')
    print(f'       大小 = {dest.stat().st_size:,} 字节')


if __name__ == '__main__':
    main()
