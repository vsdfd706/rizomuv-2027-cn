# -*- coding: utf-8 -*-
"""把已验证的 723 条汉化词表迁移到新版 RizomUV exe。

数据基础：verified_dict.json 是从"最终完整版 exe"与英文原版差分提取的 723 条
词条，全部在本机实测 0 报错（含 20 UI 标签 + 16 功能名 + 主词典）。

安全逻辑（与旧 build.py 默认规则一致，边界按新版上移）：
  - 只改 UI 字符串区 0x6d00000 - 0x6e20000（新版 UI 键最后出现在 0x6e1dc5e，
    SDK 区 Translation/Scaling 从 0x6e9e000 起，留足安全距离）。
  - 黑名单（blocklist_ui_only.txt）里的历史危险词一律跳过。
  - 指针密度 >= 6 的槽（命令字段/注册表键）跳过。
  - 后面紧跟 Vars. 的串是变量名，跳过。
  - UTF-8 中文必须放得进零填充预算，绝不越界、绝不加长文件。
  - Protect/Strategy/Tags 等危险词不在词表中，二次兜底检查。
"""
import hashlib, json
from pathlib import Path

SRC = Path(r'E:\A_1\ai\wd\rizom_cn\rizomuv_newbase.exe')
OUT = Path(r'E:\A_1\ai\wd\rizom_cn\rizomuv_new_cn.exe')
DICT = Path(r'E:\A_1\ai\wd\rizom_cn\verified_dict.json')
BLOCK = Path(r'E:\A_1\ai\wd\rizomuv-2027-cn\dicts\blocklist_ui_only.txt')
EXPECTED_SRC_MD5 = 'abbc69339a373f08cbc3507111d97fbf'
UI_LO, UI_HI = 0x6d00000, 0x6e20000

# 绝对危险词兜底（即使词表里混入也不翻）
DANGER = {'Protect', 'Strategy', 'Tags', 'Threshold', 'Mutations', 'Keep', 'Follow'}


def md5(d):
    return hashlib.md5(d).hexdigest()


def main():
    data = bytearray(SRC.read_bytes())
    if md5(data) != EXPECTED_SRC_MD5:
        raise SystemExit('源文件不是已验证的新版英文 exe，已停止（MD5=%s）' % md5(data))
    size = len(data)

    tr = json.load(open(DICT, encoding='utf-8'))
    block = set()
    for line in open(BLOCK, encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#'):
            block.add(line)

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
        n = 0
        for i in range(0, len(seg) - 8, 4):
            w = seg[i:i + 8]
            if w[4] == 1 and w[5] == 0 and w[6] == 0 and w[7] == 0:
                n += 1
        return n

    applied, skipped = [], {'block': 0, 'danger': 0, 'notfound': 0,
                            'struct': 0, 'key': 0, 'tight': 0}
    for en, zh in tr.items():
        if en in DANGER or zh == '保护':
            skipped['danger'] += 1
            continue
        if en in block:
            skipped['block'] += 1
            continue
        occ = find_all(b'\x00' + en.encode('ascii') + b'\x00')
        if not occ:
            skipped['notfound'] += 1
            continue
        nb = zh.encode('utf-8')
        done = False
        for m in occ:
            off = m + 1
            if ptr_density(off) >= 6:
                skipped['struct'] += 1
                continue
            ge = gap_end(off)
            if data[ge:ge + 12].startswith(b'Vars.'):
                skipped['key'] += 1
                continue
            if len(nb) + 1 <= ge - off:
                data[off:off + (ge - off)] = nb + b'\x00' * ((ge - off) - len(nb))
                applied.append((en, zh, off))
                done = True
                break
            skipped['tight'] += 1

    OUT.write_bytes(data)
    print('生成:', OUT)
    print('MD5 :', md5(data))
    print('大小 :', len(data))
    print('写入 :', len(applied), '/', len(tr))
    print('跳过 :', skipped)


if __name__ == '__main__':
    main()
