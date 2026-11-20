# 继续汉化：标签页按钮区剩余英文（基于当前安装版 rizomuv.exe = unwrap_final）
# 只改 UI 字符串槽，用 gap_end budget 防溢出；复用已验证的补丁逻辑。
from pathlib import Path

BASE = Path(Path('build')/'rizomuv_unwrap_final.exe')
OUT = Path(Path('build')/'rizomuv_tabs2_final.exe')

# (偏移, 原英文, 中文)  —— 均为标签页按钮，同组已汉化过，纯 UI
SLOTS = [
    (0x6d3ea34, 'Brush',       '笔刷'),
    (0x6d3ea58, 'Projections', '投影'),
    (0x6d3ea68, 'Script Hub',  '脚本中心'),
    (0x6d3ea88, 'Trimsheet',   '修剪'),
    (0x6d3eaac, 'Axis',        '轴'),
]


def gap_end(buf, off):
    i = off
    while i < len(buf) and buf[i] != 0:
        i += 1
    while i < len(buf) and buf[i] == 0:
        i += 1
    return i


data = bytearray(BASE.read_bytes())
for off, english, chinese in SLOTS:
    if data[off:off + len(english)] != english.encode('ascii'):
        raise SystemExit(f'槽位内容不符: {english!r} @ {hex(off)}')
    budget = gap_end(data, off) - off
    nb = chinese.encode('utf-8')
    if len(nb) + 1 > budget:
        raise SystemExit(f'空间不足: {english!r} budget={budget}, need={len(nb)+1}')
    data[off:off + budget] = nb + b'\x00' * (budget - len(nb))
    print(f'PATCH {english!r:<14} -> {chinese!r:<10} @ {hex(off)} budget={budget}')

OUT.write_bytes(data)
print(f'written {OUT}')
