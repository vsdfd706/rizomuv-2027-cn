# 只翻译用户红框内的 Similar 面板与提示。
from pathlib import Path

BASE = Path(Path('build')/'rizomuv_box_final.exe')
OUT = Path(Path('build')/'rizomuv_similar_final.exe')
EN = Path(Path('rizomuv.exe.bak'))

TIP_EN = (
    'Many models repeat the same shape - bolts, planks, fingers, wheels. '
    'When those parts share the same topology (the same polygon connectivity), '
    "there's no reason to cut and unwrap each one by hand.\n\n"
    'Similar finds islands that match topologically - even when they differ in 3D size or proportion - '
    'and transfers a cut, an unwrap or a stacking from one to all the others. '
    'Stacking the matches on top of each other also lets them share the same texture space, saving resolution.\n\n'
    'The Similarity slider sets how close a match has to be before the transfer applies: '
    'loosen it to catch near-duplicates, tighten it to keep only exact ones.'
)

TIP_ZH = (
    '很多模型会重复使用相同形状——螺栓、木板、手指、轮子。若这些部件拓扑相同（多边形连接关系一致），就没必要逐个手动切开并展开。\n\n'
    '“相似”会查找拓扑匹配的岛，即使它们在 3D 中大小或比例不同，也会把一个岛的切口、展开或堆叠传递给其余岛。'
    '把匹配项叠放还能共享同一纹理空间，节省分辨率。\n\n'
    '“相似度”滑块决定匹配接近到什么程度才执行传递。调低可捕获近似重复项，调高则只保留完全相同的项。'
)

# (原版上下文, 目标子串前缀, 英文, 中文)
SLOTS = [
    (b'Many models repeat the same shape', b'', TIP_EN, TIP_ZH),
    (b'\x00Similar\x00',                  b'\x00', 'Similar',          '相似'),
    (b'\x00Similarity kind\x00',          b'\x00', 'Similarity kind',  '相似度类型'),
    (b'\x00Symmetry mode\x00',            b'\x00', 'Symmetry mode',    '对称模式'),
    (b'\x00Similarity\x00',               b'\x00', 'Similarity',       '相似度'),
    (b'\x00Source\x00',                   b'\x00', 'Source',           '来源'),
    (b'Uncut|Across elements\x00',        b'Uncut|', 'Across elements', '跨元素'),
    (b'Cut|Across islands\x00',           b'Cut|',   'Across islands',  '跨岛'),
    (b'\x00Straight\x00',                 b'\x00', 'Straight',         '同向'),
    (b'\x00Symmetric\x00',                b'\x00', 'Symmetric',        '对称'),
    (b'Selection|All\x00',                b'Selection|', 'All',        '全'),
    (b'First Selected|Selection\x00',     b'First Selected|', 'Selection', '选择'),
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
        raise SystemExit(f'英文槽位不唯一: {english[:30]!r}, hits={len(hits)}')

    off = hits[0] + len(prefix)
    if data[off:off + len(english)] != english.encode('utf-8'):
        raise SystemExit(f'当前版本槽位内容不符: {english[:30]!r}')

    budget = gap_end(data, off) - off
    nb = chinese.encode('utf-8')
    if len(nb) + 1 > budget:
        raise SystemExit(f'空间不足: {english[:30]!r} budget={budget}, need={len(nb) + 1}')

    data[off:off + budget] = nb + b'\x00' * (budget - len(nb))
    print(f'PATCH {english[:30]!r:<34} -> {chinese[:20]!r:<24} @ {hex(off)}')

OUT.write_bytes(data)
print(f'written {OUT}')
