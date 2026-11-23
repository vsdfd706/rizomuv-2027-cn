"""通用补丁构建：build.py <词典json,...> <输出exe> [--block blocklist.txt]"""
import json, re, shutil, sys, os

SRC = 'rizomuv.exe.bak'
args = [a for a in sys.argv[1:] if not a.startswith('--')]
dicts = args[0].split(',')
OUT = args[1]

block = set()
if '--block' in sys.argv:
    for bf in sys.argv[sys.argv.index('--block') + 1].split(','):
        for line in open(bf, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#'):
                block.add(line)

raw = {}
for f in dicts:
    raw.update(json.load(open(f, encoding='utf-8')))

# 全小写词条多为 Python/Lua 属性名与格式关键词，一律不动
tr = {k: v for k, v in raw.items() if not (k.islower() and ' ' not in k) and len(k) >= 2}
dropped_case = len(raw) - len(tr)

data = bytearray(open(SRC, 'rb').read())
size = len(data)
LO, HI = 114_400_000, 116_600_000  # UI 字符串区，只在这里做替换

# 0x6e00000 以上是第三方 SDK 字符串表（FBX/Alembic/MKL/Illustrator 等），
# 里面的 Name/Type/Value/Scaling 等是运行时标识符，翻译会导致
# FBX 属性操作报错（空 ERROR 洪水）、桥接失败。只允许 UI 主区。
REGIONS = [(114_400_000, 0x6e00_000)]


def gap_end(off):
    i = off
    while i < size and data[i] != 0:
        i += 1
    while i < size and data[i] == 0:
        i += 1
    return i


def find_all(needle):
    res = []
    for rlo, rhi in REGIONS:
        start = rlo
        while True:
            i = data.find(needle, start, rhi)
            if i < 0:
                break
            res.append(i)
            start = i + 1
    return res


def ptr_density(off, radius=96):
    """统计 off 附近 8 字节指针（0x00000001_xxxxxxxx，模块内地址）的数量。
    指针密集 = 该字符串是命令字段/属性注册表条目，而非普通 UI 标签。"""
    a = max(0, off - radius)
    b = min(size, off + radius)
    seg = data[a:b]
    n = 0
    for i in range(0, len(seg) - 8, 4):
        w = seg[i:i + 8]
        if w[4] == 1 and w[5] == 0 and w[6] == 0 and w[7] == 0:
            n += 1
    return n


# 会被程序当作配置键的标签（prefs/controls 的键由标签去掉空格得到），
# 这些字符串变长会被截断成非法 UTF-8，必须确保不超原文长度。
RISKY = set()
try:
    import re as _re
    _txt = open('prefs_backup.txt', encoding='utf-8', errors='replace').read()
    _keys = set(_re.findall(r'([A-Za-z][A-Za-z0-9_]*)\s+(?:bool|int|double|string|vector3d|table)\b', _txt))
    _nos = {k.replace(' ', ''): k for k in tr}
    for _k in _keys:
        if _k in tr:
            RISKY.add(_k)
        elif _k in _nos:
            RISKY.add(_nos[_k])
except FileNotFoundError:
    pass

# 实测验证过会被写进小固定缓冲区的标签（见 shortbuf.txt）
SHORTBUF = set()
try:
    for _l in open('shortbuf.txt', encoding='utf-8'):
        _l = _l.strip()
        if _l and not _l.startswith('#'):
            SHORTBUF.add(_l)
except FileNotFoundError:
    pass

# 少数确实是界面标签、却落在指针表里的字符串（菜单栏「帮助」这类）：
# 用 force_patch.txt 显式放行，同样受「不超原文长度」约束
FORCE = set()
try:
    for _l in open('force_patch.txt', encoding='utf-8'):
        _l = _l.strip()
        if _l and not _l.startswith('#'):
            FORCE.add(_l)
except FileNotFoundError:
    pass
struct_offsets = {}

patched = 0
skipped_block = []
skipped_tight = []
skipped_struct = []
skipped_grow = []
notfound = []
KEYPFX = (b'Vars.',)
if '--strict' in sys.argv:
    KEYPFX = (b'ZOMID_', b'Vars.', b'Prefs.')
skip_key = 0
for en, zh in tr.items():
    if en in block:
        skipped_block.append(en)
        continue
    occ = find_all(b'\x00' + en.encode('ascii') + b'\x00')
    if not occ:
        notfound.append(en)
        continue
    nb = zh.encode('gbk')
    done = False
    for m in occ:
        off = m + 1
        # 指针密集区域 = 命令字段/属性/工具栏/面板注册表（由本地指针表引用），
        # 其字符串是查找键或运行时标识符（Path/Value/Type/Feature Palette 等），
        # 翻译会产生坏命令、坏配置键或查找失败（空 ERROR），一律跳过。
        if ptr_density(off) >= 6 and en not in FORCE:
            skipped_struct.append((en, hex(off)))
            struct_offsets.setdefault(en, []).append(off)
            continue
        # 长度不得超过原文：程序会把某些标签拷进固定长度缓冲区当配置键
        # （prefs/controls），变长会被截断成非法 UTF-8（如「像素」只剩 像\xe7\xb4），
        # 导致配置文件损坏、面板/设置丢失。
        if en in SHORTBUF and len(nb) > len(en):
            skipped_grow.append((en, len(en), len(nb)))
            continue
        ge = gap_end(off)
        budget = ge - off
        # 该串后面紧跟 ZOMID_*/Vars.*/Prefs.* 时，它是变量名/键名，不能改
        nxt = data[ge:ge + 12]
        if nxt.startswith(KEYPFX):
            skip_key += 1
            continue
        if len(nb) + 1 <= budget:
            data[off:off + budget] = nb + b'\x00' * (budget - len(nb))
            patched += 1
            done = True
        else:
            skipped_tight.append((en, budget, len(nb) + 1))
    if not done and not any(s[0] == en for s in skipped_tight):
        skipped_tight.append((en, 0, len(nb) + 1))

# 强制补丁：只对显式放行的 UI 标签，且不得超出原文长度
forced = 0
for en in FORCE & set(tr):
    nb = tr[en].encode('gbk')
    if len(nb) > len(en):
        continue
    for off in find_all(b'\x00' + en.encode('ascii') + b'\x00'):
        off += 1
        if ptr_density(off) < 6:
            continue
        ge = gap_end(off)
        budget = ge - off
        if len(nb) + 1 <= budget:
            data[off:off + budget] = nb + b'\x00' * (budget - len(nb))
            forced += 1

open(OUT, 'wb').write(data)
print('entries', len(tr), 'patched', patched, 'blocked', len(skipped_block),
      'key-skip', skip_key, 'tight', len(skipped_tight), 'notfound', len(notfound),
      'struct-skip', len(skipped_struct), 'grow-skip', len(skipped_grow), 'forced', forced)
for s in skipped_tight[:10]:
    print('  TIGHT', s)
for s in skipped_grow[:20]:
    print('  GROW-SKIP', s)
