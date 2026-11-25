# -*- coding: utf-8 -*-
"""补译 Transform 选择面板中的纯 UI 标签（第一安全批次）。

基于当前已装的工具栏补译版 (8018ad29)，只补下列界面显示标签。
严格排除：功能名/命令名 (Transform/Shape/Shortest Path/Preview)、
危险词 (Protect map)、枚举值 (Off/Planar/Curved, By drag direction,
Max edge count, Optimized for triangles)。

安全约束：
  - 只改 UI 区 0x6d00000-0x6e20000
  - 每个英文串恰好一个独立 \x00English\x00 槽，且全程序唯一
  - 指针密度 < 6、零填充预算足够、文件大小不变、UI 区外零改动
"""
import hashlib
from pathlib import Path

SRC = Path(r'C:\Program Files\Rizom Lab\RizomUV 2027.0\rizomuv.exe')
OUT = Path(r'E:\A_1\ai\wd\rizom_cn\rizomuv_new_cn_panel.exe')
UI_LO, UI_HI = 0x6d00000, 0x6e20000
EXPECTED_SRC_MD5 = '8018ad29b03772d8b51f8c676220e334'

# 纯界面显示标签（词表已有译法优先用之）
PAIRS = [
    ('Select through polygons', '穿透多边形选择'),
    ('Across seams', '跨接缝'),
    ('Angle limit', '角度限制'),
    ('Geometry-based', '基于几何'),
    ('Across selection', '跨选区'),
    ('Symmetry plane', '对称面'),
    ('Straightness', '直线度'),   # 词表已验证译法
    ('Sharpness', '锐度'),
]


def md5(d):
    return hashlib.md5(d).hexdigest()


def main():
    data = bytearray(SRC.read_bytes())
    size = len(data)
    if md5(data) != EXPECTED_SRC_MD5:
        raise SystemExit('源不是已验证的工具栏补译版，已停止')

    def gap_end(off):
        i = off
        while i < size and data[i] != 0:
            i += 1
        while i < size and data[i] == 0:
            i += 1
        return i

    def find_all(nd):
        r, s = [], 0
        while True:
            i = data.find(nd, s)
            if i < 0:
                break
            r.append(i)
            s = i + 1
        return r

    def ptr_density(off, radius=96):
        seg = data[max(0, off - radius):min(size, off + radius)]
        return sum(1 for i in range(0, len(seg) - 8, 4)
                   if seg[i + 4] == 1 and seg[i + 5] == 0
                   and seg[i + 6] == 0 and seg[i + 7] == 0)

    patched = []
    for en, zh in PAIRS:
        nd = b'\x00' + en.encode('ascii') + b'\x00'
        occ = find_all(nd)
        inui = [o for o in occ if UI_LO <= o < UI_HI]
        if len(occ) != 1 or len(inui) != 1:
            raise SystemExit('%s: 槽位不唯一 (total=%d ui=%d)，已停止'
                             % (en, len(occ), len(inui)))
        off = inui[0] + 1
        if ptr_density(off) >= 6:
            raise SystemExit('%s: 指针密度过高，已停止' % en)
        ge = gap_end(off)
        nb = zh.encode('utf-8')
        if len(nb) + 1 > ge - off:
            raise SystemExit('%s: 零填充预算不足 (%d/%d)，已停止'
                             % (en, len(nb), ge - off))
        data[off:ge] = nb + b'\x00' * ((ge - off) - len(nb))
        patched.append((en, zh, off))

    OUT.write_bytes(data)
    print('生成:', OUT)
    print('MD5 :', md5(data))
    print('大小:', len(data))
    for en, zh, off in patched:
        print('  %-26s -> %-8s @ 0x%x' % (en, zh, off))


if __name__ == '__main__':
    main()
