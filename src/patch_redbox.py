# 只翻译用户红框内的 Texture Scaling / UDIMs 面板文字。
from pathlib import Path

BASE = Path(Path('build')/'rizomuv_udim_final.exe')
OUT = Path(Path('build')/'rizomuv_box_final.exe')
EN = Path(Path('rizomuv.exe.bak'))

# (原版中的唯一上下文, 目标子串前缀, 英文, 中文)
# 内部枚举值 LowLeft/UpRight 等保留，只替换竖线后的显示文案。
SLOTS = [
    (b'\x00Size\x00',                         b'\x00', 'Size',               '尺寸'),
    (b'\x00Offset\x00',                       b'\x00', 'Offset',             '偏移'),
    (b'\x00Transform UVs too\x00',             b'\x00', 'Transform UVs too',  '同时变换 UV'),
    (b'\x00Geometry\x00',                      b'\x00', 'Geometry',           '几何'),
    (b'\x00Fit Origin\x00',                    b'\x00', 'Fit Origin',         '适配原点'),
    (b'\x00Reset\x00',                         b'\x00', 'Reset',              '重置'),
    (b'\x00Non square workflow\x00',           b'\x00', 'Non square workflow','非方形工作流'),
    (b'\x00Normalize\x00',                     b'\x00', 'Normalize',          '归一化'),
    (b'\x00Display\x00',                       b'\x00', 'Display',            '显示'),
    (b'LowLeft|Bottom left\x00',  b'LowLeft|',  'Bottom left',  '左下'),
    (b'LowRight|Bottom right\x00', b'LowRight|', 'Bottom right', '右下'),
    (b'UpLeft|Top left\x00',      b'UpLeft|',   'Top left',     '左上'),
    (b'UpRight|Top right\x00',    b'UpRight|',  'Top right',    '右上'),
    (b'\x00Grid size\x00',                     b'\x00', 'Grid size',          '网格大小'),
    (b'\x00Labeling\x00',                      b'\x00', 'Labeling',           '标签格式'),
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
    nb = chinese.encode('gbk')
    if len(nb) + 1 > budget:
        raise SystemExit(f'空间不足: {english!r} budget={budget}, need={len(nb) + 1}')

    data[off:off + budget] = nb + b'\x00' * (budget - len(nb))
    print(f'PATCH {english!r:<20} -> {chinese!r:<12} @ {hex(off)}')

OUT.write_bytes(data)
print(f'written {OUT}')
