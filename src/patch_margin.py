# 翻译 Margin 悬浮提示及标题（像素单位与普通单位两个变体一起处理）。
from pathlib import Path

BASE = Path(Path('build')/'rizomuv_similar_final.exe')
OUT = Path(Path('build')/'rizomuv_margin_final.exe')
EN = Path(Path('rizomuv.exe.bak'))

SLOTS = [
    (
        "The empty space left on the UV tile's edge. "
        'As with a piece of printable paper, a UV map can have margins at the edges of the map.',
        'UV 平铺边缘留出的空白空间。就像一张可打印的纸一样，UV 贴图也可以在边缘留有边距。',
    ),
    (
        "The empty space left on the UV tile's edge in pixel unit. "
        'As with a piece of printable paper, a UV map can have margins at the edges of the map.',
        '以像素为单位的 UV 平铺边缘留出的空白空间。就像一张可打印的纸一样，UV 贴图也可以在边缘留有边距。',
    ),
    ('Margin', '边距'),
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
    context = english.encode('gbk')
    hits = []
    start = 0
    while True:
        pos = en.find(context, start)
        if pos < 0:
            break
        if 0x6d00000 <= pos < 0x6e10000:
            hits.append(pos)
        start = pos + 1

    # Margin 单词在多个内部键中出现，只取精确字符串格。
    if english == 'Margin':
        hits = [p for p in hits if en[p - 1] == 0 and en[p + len(context)] == 0]

    if len(hits) != 1:
        raise SystemExit(f'英文槽位不唯一: {english[:30]!r}, hits={len(hits)}')

    off = hits[0]
    if data[off:off + len(context)] != context:
        raise SystemExit(f'当前版本槽位内容不符: {english[:30]!r}')

    budget = gap_end(data, off) - off
    nb = chinese.encode('gbk')
    if len(nb) + 1 > budget:
        raise SystemExit(f'空间不足: {english[:30]!r} budget={budget}, need={len(nb) + 1}')

    data[off:off + budget] = nb + b'\x00' * (budget - len(nb))
    print(f'PATCH {english[:40]!r:<44} -> {chinese!r:<44} @ {hex(off)}')

OUT.write_bytes(data)
print(f'written {OUT}')
