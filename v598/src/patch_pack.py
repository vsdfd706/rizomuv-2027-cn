# 翻译红框内排布面板的纯 UI 文案；保留配置内部值（如 Efficient）。
from pathlib import Path

BASE = Path(Path('build')/'rizomuv_margin_final.exe')
OUT = Path(Path('build')/'rizomuv_pack_final.exe')
EN = Path(Path('rizomuv.exe.bak'))

# (原版上下文, 目标子串前缀, 英文, 中文)
SLOTS = [
    (b'\x00Padding\x00',             b'\x00', 'Padding',           '填充'),
    (b'\x00Scale\x00',               b'\x00', 'Scale',             '缩放'),
    (b'2|Equalize\x00',              b'2|',   'Equalize',          '均衡'),
    (b'\x00DMap\x00',                b'\x00', 'DMap',              '密度'),
    (b'Fill|Auto Fit\x00',           b'Fill|', 'Auto Fit',         '自适应'),
    (b'\x00Mix Scales\x00',          b'\x00', 'Mix Scales',        '混合缩放'),
    (b'\x00Orientation\x00',         b'\x00', 'Orientation',       '朝向'),
    (b'\x00Automatic\x00',           b'\x00', 'Automatic',         '自动'),
    (b'\x00Orientation search\x00',  b'\x00', 'Orientation search','朝向搜索'),
    (b'None|Off\x00',                b'None|', 'Off',              '关闭'),
    (b'\x00Advanced\x00',            b'\x00', 'Advanced',          '高级'),
    (b'0|Auto\x00',                  b'0|',   'Auto',              '自'),
    (b'\x00Box\x00',                 b'\x00', 'Box',               '盒'),
    (b'\x00Use GPU\x00',             b'\x00', 'Use GPU',           '用 GPU'),
    (b'\x00Pack group content\x00',  b'\x00', 'Pack group content','打包组内容'),
    (b'\x00Distribute in tiles\x00', b'\x00', 'Distribute in tiles','分配到平铺'),
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

for context, prefix, english, chinese in SLOTS:
    hits = []
    start = 0
    while True:
        pos = en.find(context, start)
        if pos < 0:
            break
        if 0x6d00000 <= pos < 0x6e10000:
            hits.append(pos)
        start = pos + 1
    if len(hits) != 1:
        raise SystemExit(f'英文槽位不唯一: {english!r}, hits={len(hits)}')

    off = hits[0] + len(prefix)
    if data[off:off + len(english)] != english.encode('ascii'):
        raise SystemExit(f'当前版本槽位内容不符: {english!r}')

    budget = gap_end(data, off) - off
    nb = chinese.encode('utf-8')
    if len(nb) + 1 > budget:
        raise SystemExit(f'空间不足: {english!r} budget={budget}, need={len(nb) + 1}')

    data[off:off + budget] = nb + b'\x00' * (budget - len(nb))
    print(f'PATCH {english!r:<20} -> {chinese!r:<12} @ {hex(off)}')

OUT.write_bytes(data)
print(f'written {OUT}')
