# -*- coding: utf-8 -*-
"""补译新版 RizomUV 顶部工具栏 7 个分组标题（旧最终版已验证安全的翻译）。

从当前安装目录（新版汉化）复制，只补这 7 个 UI 槽：
  UV Set->UV集, Select->选择, Seams->缝合, Unwrap->展开,
  Projections->投影, Similar->相似, Packing->排布

安全约束：
  - 只处理 UI 区 0x6d00000-0x6e20000
  - 每个英文串必须恰好一个 \x00English\x00 独立槽
  - 指针密度 < 6、后面不接 Vars.、零填充预算足够
  - 文件大小不变，UI 区之外零改动
"""
import hashlib
from pathlib import Path

SRC = Path(r'C:\Program Files\Rizom Lab\RizomUV 2027.0\rizomuv.exe')
OUT = Path(r'E:\A_1\ai\wd\rizom_cn\rizomuv_new_cn_toolbar.exe')
UI_LO, UI_HI = 0x6d00000, 0x6e20000
PAIRS = [('UV Set', 'UV集'), ('Select', '选择'), ('Seams', '缝合'),
         ('Unwrap', '展开'), ('Projections', '投影'), ('Similar', '相似'),
         ('Packing', '排布')]


def md5(d):
    return hashlib.md5(d).hexdigest()


def main():
    data = bytearray(SRC.read_bytes())
    size = len(data)
    expected = 'cf53e1496873dffba10983d180a0cdcf'
    if md5(data) != expected:
        raise SystemExit('源不是已验证的新版汉化 exe，已停止')

    def gap_end(off):
        i = off
        while i < size and data[i] != 0:
            i += 1
        while i < size and data[i] == 0:
            i += 1
        return i

    def find_all(nd):
        r, s = [], UI_LO
        while True:
            i = data.find(nd, s, UI_HI)
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
        if len(occ) != 1:
            raise SystemExit('%s: 独立槽数量异常 %d，已停止' % (en, len(occ)))
        off = occ[0] + 1
        if ptr_density(off) >= 6:
            raise SystemExit('%s: 指针密度过高，已停止' % en)
        ge = gap_end(off)
        if data[ge:ge + 12].startswith(b'Vars.'):
            raise SystemExit('%s: 后接 Vars. 键，已停止' % en)
        nb = zh.encode('utf-8')
        if len(nb) + 1 > ge - off:
            raise SystemExit('%s: 零填充预算不足，已停止' % en)
        data[off:ge] = nb + b'\x00' * ((ge - off) - len(nb))
        patched.append((en, zh, off))

    OUT.write_bytes(data)
    print('生成:', OUT)
    print('MD5 :', md5(data))
    print('大小:', len(data))
    for en, zh, off in patched:
        print('  %-12s -> %-6s @ 0x%x' % (en, zh, off))


if __name__ == '__main__':
    main()
