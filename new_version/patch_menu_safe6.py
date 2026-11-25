# -*- coding: utf-8 -*-
"""补译菜单里 6 个旧版已验证安全的词（迁移倒退修复，第三批）。

基于当前已装的面板补译版 (651a25b1)。
这 6 词在旧最终版 rizomuv_cn_final.exe 里已翻中文并长期使用无问题，
译法来自 verified_dict.json（从旧版差分提取），新版因黑名单被误跳过。

排除：Help（新版槽指针密度 20、邻接指针数据，结构与旧版不同）、
以及旧版从未翻译的菜单命令名 (Move/Rotate/Pin/Unfold/Snap/...)
和对话框按钮、枚举值等。

安全约束：UI 区内唯一独立槽、指针密度 < 6、零填充预算足够、
文件大小不变、UI 区外零改动。
"""
import hashlib
from pathlib import Path

SRC = Path(r'C:\Program Files\Rizom Lab\RizomUV 2027.0\rizomuv.exe')
OUT = Path(r'E:\A_1\ai\wd\rizom_cn\rizomuv_new_cn_menu6.exe')
UI_LO, UI_HI = 0x6d00000, 0x6e20000
EXPECTED_SRC_MD5 = '651a25b166ab27091f6dcc0695756529'

PAIRS = [
    ('Groups', '组'),
    ('Trimsheet', '修剪'),
    ('Optimize', '优化'),
    ('Straighten', '拉直'),
    ('Align', '对齐'),
    ('Flip', '翻转'),
]


def md5(d):
    return hashlib.md5(d).hexdigest()


def main():
    data = bytearray(SRC.read_bytes())
    size = len(data)
    if md5(data) != EXPECTED_SRC_MD5:
        raise SystemExit('源不是已验证的面板补译版，已停止')

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
        occ = find_all(b'\x00' + en.encode('ascii') + b'\x00')
        inui = [o for o in occ if UI_LO <= o < UI_HI]
        if len(occ) != 1 or len(inui) != 1:
            raise SystemExit('%s: 槽位不唯一 (total=%d ui=%d)，已停止'
                             % (en, len(occ), len(inui)))
        off = inui[0] + 1
        pd = ptr_density(off)
        if pd >= 6:
            raise SystemExit('%s: 指针密度 %d 过高，已停止' % (en, pd))
        ge = gap_end(off)
        nb = zh.encode('utf-8')
        if len(nb) + 1 > ge - off:
            raise SystemExit('%s: 零填充预算不足，已停止' % en)
        data[off:ge] = nb + b'\x00' * ((ge - off) - len(nb))
        patched.append((en, zh, off, pd))

    OUT.write_bytes(data)
    print('生成:', OUT)
    print('MD5 :', md5(data))
    print('大小:', len(data))
    for en, zh, off, pd in patched:
        print('  %-12s -> %-6s @ 0x%x (ptr=%d)' % (en, zh, off, pd))


if __name__ == '__main__':
    main()
