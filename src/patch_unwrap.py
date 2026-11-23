# 翻译红框内展开面板英文项；遇到内部变量冲突时按日志逐项回退。
from pathlib import Path

BASE = Path(Path('build')/'rizomuv_pack_final.exe')
OUT = Path(Path('build')/'rizomuv_unwrap_final.exe')
EN = Path(Path('rizomuv.exe.bak'))

SLOTS = [
    ('Live update',          '实时更新'),
    ('Optimize',             '优化'),
    ('Unfold iterations',    '展开迭代次数'),
    ('Optimize iterations',  '优化迭代次数'),
    ('Strength',             '强度'),
    ('Angles / Lengths',     '角度 / 长度'),
    ('Use density map',      '使用密度图'),
    ('Sanity checks',        '完整性检查'),
    ('Prevent flips',        '防止翻转'),
    ('Prevent overlaps',     '防止重叠'),
    ('Overlap gap',          '重叠间距'),
    ('Borders',              '边界'),
    ('Align borders',        '对齐边界'),
    ('Auto-orient',          '自动定向'),
    ('Fill holes',           '填充孔洞'),
    ('Free selection border','自由选择边界'),
]


def gap_end(buf: bytearray, off: int) -> int:
    i = off
    while i < len(buf) and buf[i] != 0:
        i += 1
    while i < len(buf) and buf[i] == 0:
        i += 1
    return i


en = EN.read_bytes()
data = bytearray(BASE.read_bytes())

for english, chinese in SLOTS:
    pattern = ('\x00' + english + '\x00').encode('gbk')
    hits = []
    start = 0
    while True:
        pos = en.find(pattern, start)
        if pos < 0:
            break
        if 0x6d00000 <= pos < 0x6e10000:
            hits.append(pos + 1)
        start = pos + 1
    if len(hits) != 1:
        raise SystemExit(f'英文槽位不唯一: {english!r}, hits={len(hits)}')

    off = hits[0]
    if data[off:off + len(english)] != english.encode('gbk'):
        raise SystemExit(f'当前版本槽位内容不符: {english!r}')

    budget = gap_end(data, off) - off
    nb = chinese.encode('gbk')
    if len(nb) + 1 > budget:
        raise SystemExit(f'空间不足: {english!r} budget={budget}, need={len(nb) + 1}')

    data[off:off + budget] = nb + b'\x00' * (budget - len(nb))
    print(f'PATCH {english!r:<22} -> {chinese!r:<14} @ {hex(off)}')

OUT.write_bytes(data)
print(f'written {OUT}')
