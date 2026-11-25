# 在纯界面汉化版基础上，翻译 UDIM 面板标题及通用展开面板提示。
from pathlib import Path

BASE = Path(Path('build')/'rizomuv_panel_final.exe')
OUT = Path(Path('build')/'rizomuv_udim_final.exe')
EN = Path(Path('rizomuv.exe.bak'))

# 精确匹配原版英文槽位，避免误改内部键。
SLOTS = [
    (b'ToolbarOpen\x00 panel\x00', b'ToolbarOpen\x00', ' panel', ' 面板'),
    (b'\x00Expand \x00Display', b'\x00', 'Expand ', '展开 '),
    (b'\x00UDIMs\x00\x00\x00ZOMID_EXPANDABLE_CUSTOM_UDIMS_UI',
     b'\x00', 'UDIMs', 'UDIM块'),
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
    print(f'PATCH {english!r} -> {chinese!r} @ {hex(off)}, budget={budget}')

OUT.write_bytes(data)
print(f'written {OUT}')
