# -*- coding: utf-8 -*-
"""首选项 Viewports 页 UI 标签汉化，基于 menu2 完整版。"""
from pathlib import Path

BASE = Path('build')/'rizomuv_menu2_final.exe'
OUT  = Path('build')/'rizomuv_prefs_final.exe'

# (offset, 原英文, 中文)
ITEMS = [
    # 左侧分类
    (0x6d55bc8, 'Viewports',       '视口'),
    (0x6ddd248, 'Global UI',       '全局界面'),
    (0x6ddd258, 'Auto Save',       '自动保存'),
    (0x6ddd268, 'Miscellaneous',   '杂项'),
    (0x6ddd278, 'Import Export',   '导入导出'),
    # 分组标题 / 复选框
    (0x6d72598, 'Anti-aliasing',   '抗锯齿'),
    (0x6daf418, 'Lighting',        '光照'),
    (0x6dddcd0, 'Lit wireframe',   '光照线框'),
    # Mesh 颜色项标签
    (0x6de1560, 'Ambient',         '环境'),
    (0x6de1568, 'Pinned vertexes', '固定顶点'),
    (0x6de1578, '3D space borders','3D空间边界'),
    (0x6de1590, 'Constrained edges','约束边'),
    (0x6de15a8, 'Highlight',       '高亮'),
]

# 跳过：Off/On(枚举值,槽过小)、Mesh(指针表相邻,疑似内部)、Color(Stamper枚举值)、
#       Debug(窗口菜单组,复用槽背景不明)、Background(UV快照区共用槽)。

def main():
    buf = bytearray(BASE.read_bytes())
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
        print('%-10s %-20s -> %-12s slot=%2d need=%2d' % (hex(off), en, zh, slot, need))
    OUT.write_bytes(bytes(buf))
    print('OUTPUT', OUT)

if __name__ == '__main__':
    main()
