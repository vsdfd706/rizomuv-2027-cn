# -*- coding: utf-8 -*-
"""窗口菜单续翻：基于最新 tabs2 完整版，按固定偏移补丁 UI 字符串槽。"""
from pathlib import Path

BASE = Path('build')/'rizomuv_tabs2_final.exe'
OUT  = Path('build')/'rizomuv_menu2_final.exe'

# (offset, 原版英文, 中文)
ITEMS = [
    (0x6d3ea00, 'Misc Transforms',   '杂项变换'),
    (0x6d3ea10, 'Seams',             '缝合'),
    (0x6d3ea18, 'Auto Seams',        '自动缝'),        # 槽位仅12字节，缩写
    (0x6d3ea48, 'Similar',           '相似'),
    (0x6d3eb68, 'Symmetry',          '对称'),
    (0x6d3ebd4, 'Script',            '脚本'),
    (0x6d3ec98, 'Polygon Groups',    '多边形组'),
    (0x6d3ecc8, 'Preferences',       '首选项'),
    (0x6d3ecd8, 'Orientation Selector', '方向选择器'),
    (0x6d3ed10, 'Color ID Map',      '颜色ID图'),
    (0x6d3ed30, 'Color Map',         '颜色图'),
]

# 明确跳过的危险/不可行项：
# Scene(0x6d3eaa4) 历史误译致模型空白；Viewport 3D/UV 历史误译致加载失败；
# Log 槽位仅4字节放不下中文；Exporter 标签在 UI 区外且像内部命令名。

def main():
    buf = bytearray(BASE.read_bytes())
    changed = []
    for off, en, zh in ITEMS:
        j = off
        while buf[j] != 0:
            j += 1
        k = j
        while buf[k] == 0:
            k += 1
        actual = bytes(buf[off:j]).decode('gbk', 'replace')
        if actual == zh:
            print('SKIP @%s already %s' % (hex(off), zh))
            continue
        if actual != en:
            raise SystemExit('MISMATCH @%s expected %r got %r' % (hex(off), en, actual))
        slot = k - off
        need = len(zh.encode('gbk')) + 1
        if need > slot:
            raise SystemExit('NO SPACE @%s %s need=%d slot=%d' % (hex(off), en, need, slot))
        buf[off:k] = zh.encode('gbk') + b'\x00' * (slot - len(zh.encode('gbk')))
        changed.append((hex(off), en, zh, slot, need))
    OUT.write_bytes(bytes(buf))
    for row in changed:
        print('%-10s %-24s -> %-12s slot=%2d need=%2d' % row)
    print('OUTPUT', OUT)

if __name__ == '__main__':
    main()
