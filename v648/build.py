# -*- coding: utf-8 -*-
"""新版本 RizomUV 2027.0.648 Win —— 一键汉化构建引擎。

从使用者自己持有的英文原版 rizomuv.exe 出发，在内存中依次应用
已验证安全的界面补丁（主迁移 621 词 + 工具栏 7 + 面板 8 + 菜单 6），
产出纯界面汉化版。只改 UI 字符串区，不动任何程序逻辑。

本文件是 history/ 下 4 个分批脚本的合一重写版，MD5 逐级校验完全一致：
    abbc6933(英文) -> cf53e149 -> 8018ad29 -> 651a25b1 -> ef85533b(最终)

用法：
    python build.py <英文原版.exe> <输出.exe>
不传参数时在命令行交互提示输入路径。
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DICT = HERE / 'verified_dict.json'
BLOCK = HERE / 'dicts' / 'blocklist_ui_only.txt'

# 逐级期望 MD5（英文原版 -> 4 批之后）
MD5_EN = 'abbc69339a373f08cbc3507111d97fbf'
MD5_STAGE = [
    'cf53e1496873dffba10983d180a0cdcf',  # 主迁移 621 词
    '8018ad29b03772d8b51f8c676220e334',  # 工具栏 7 标题
    '651a25b166ab27091f6dcc0695756529',  # 面板 8 标签
    'ef85533b797c7fc841e9c26bd676efae',  # 菜单 6 标签（最终）
]
UI_LO, UI_HI = 0x6d00000, 0x6e20000
DANGER = {'Protect', 'Strategy', 'Tags', 'Threshold', 'Mutations', 'Keep', 'Follow'}

# 后三批的独立补丁对（每对都是已验证安全的界面显示标签）
PAIRS_TOOLBAR = [
    ('UV Set', 'UV集'), ('Select', '选择'), ('Seams', '缝合'),
    ('Unwrap', '展开'), ('Projections', '投影'), ('Similar', '相似'),
    ('Packing', '排布'),
]
PAIRS_PANEL = [
    ('Select through polygons', '穿透多边形选择'), ('Across seams', '跨接缝'),
    ('Angle limit', '角度限制'), ('Geometry-based', '基于几何'),
    ('Across selection', '跨选区'), ('Symmetry plane', '对称面'),
    ('Straightness', '直线度'), ('Sharpness', '锐度'),
]
PAIRS_MENU = [
    ('Groups', '组'), ('Trimsheet', '修剪'), ('Optimize', '优化'),
    ('Straighten', '拉直'), ('Align', '对齐'), ('Flip', '翻转'),
]


def md5(data) -> str:
    if isinstance(data, Path):
        h = hashlib.md5()
        with open(data, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        return h.hexdigest()
    return hashlib.md5(data).hexdigest()


def _helpers(data):
    """返回 (gap_end, find_all, ptr_density)，闭包捕获 data 与 size。"""
    size = len(data)

    def gap_end(off):
        i = off
        while i < size and data[i] != 0:
            i += 1
        while i < size and data[i] == 0:
            i += 1
        return i

    def find_all(nd, lo=UI_LO, hi=UI_HI):
        r, s = [], lo
        while True:
            i = data.find(nd, s, hi)
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

    return gap_end, find_all, ptr_density


def _stage_main(data, emit):
    """第一批：从词表写入 621 条已验证安全词。"""
    gap_end, find_all, ptr_density = _helpers(data)
    tr = json.load(open(DICT, encoding='utf-8'))
    block = set()
    for line in open(BLOCK, encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#'):
            block.add(line)
    applied = 0
    for en, zh in tr.items():
        if en in DANGER or zh == '保护':
            continue
        if en in block:
            continue
        occ = find_all(b'\x00' + en.encode('ascii') + b'\x00')
        if not occ:
            continue
        nb = zh.encode('utf-8')
        for m in occ:
            off = m + 1
            if ptr_density(off) >= 6:
                continue
            ge = gap_end(off)
            if data[ge:ge + 12].startswith(b'Vars.'):
                continue
            if len(nb) + 1 <= ge - off:
                data[off: off + (ge - off)] = nb + b'\x00' * ((ge - off) - len(nb))
                applied += 1
                break
    emit('  写入词条：%d / %d' % (applied, len(tr)))
    return applied


def _stage_pairs(data, pairs, emit, expect_global_unique=True):
    """后续批次：逐对替换独立 UI 槽，逐级校验安全。"""
    gap_end, find_all, ptr_density = _helpers(data)
    size = len(data)
    for en, zh in pairs:
        occ = find_all(b'\x00' + en.encode('ascii') + b'\x00', 0, size)
        inui = [o for o in occ if UI_LO <= o < UI_HI]
        if expect_global_unique:
            if len(occ) != 1 or len(inui) != 1:
                raise RuntimeError('%s: 独立槽数量异常 (total=%d ui=%d)' % (en, len(occ), len(inui)))
        elif len(inui) != 1:
            raise RuntimeError('%s: UI 区内槽不唯一 (total=%d ui=%d)' % (en, len(occ), len(inui)))
        off = inui[0] + 1
        if ptr_density(off) >= 6:
            raise RuntimeError('%s: 指针密度过高，已停止' % en)
        ge = gap_end(off)
        nb = zh.encode('utf-8')
        if len(nb) + 1 > ge - off:
            raise RuntimeError('%s: 零填充预算不足，已停止' % en)
        data[off:ge] = nb + b'\x00' * ((ge - off) - len(nb))


def build(src: Path, dst: Path, emit=print) -> Path:
    """从英文原版构建最终汉化版，逐级校验 MD5。返回输出路径。"""
    src, dst = Path(src), Path(dst)
    data = bytearray(src.read_bytes())
    if md5(data) != MD5_EN:
        raise RuntimeError('源文件不是已验证的新版本英文原版（MD5=%s）。'
                           '请使用 2027.0.648 Win 的正版英文 rizomuv.exe。' % md5(data))
    size = len(data)
    emit('源版本校验通过：%s' % MD5_EN)

    stages = [
        ('主迁移（621 词）', lambda d: _stage_main(d, emit), True),
        ('工具栏 7 标题', lambda d: _stage_pairs(d, PAIRS_TOOLBAR, emit, True), False),
        ('面板 8 标签', lambda d: _stage_pairs(d, PAIRS_PANEL, emit, False), False),
        ('菜单 6 标签', lambda d: _stage_pairs(d, PAIRS_MENU, emit, False), False),
    ]
    for i, (name, fn, _) in enumerate(stages):
        emit('[%d/4] %s ...' % (i + 1, name))
        fn(data)
        actual = md5(data)
        if actual != MD5_STAGE[i]:
            raise RuntimeError('%s 后 MD5 不符（实际 %s，期望 %s），已停止。'
                               % (name, actual, MD5_STAGE[i]))
        if len(data) != size:
            raise RuntimeError('文件大小发生变化，已停止。')

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    emit('产出：%s' % dst)
    emit('MD5 ：%s' % md5(dst))
    emit('自检通过：与已验证的最终汉化版完全一致。')
    return dst


def main():
    if len(sys.argv) >= 3:
        src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    else:
        print('新版本 RizomUV 2027.0.648 Win 一键汉化构建')
        s = input('请输入英文原版 rizomuv.exe 的完整路径：').strip().strip('"')
        src = Path(s)
        dst = src.with_name('rizomuv_cn_648.exe')
    if not src.exists():
        print('[错误] 找不到源文件：%s' % src)
        return 2
    try:
        build(src, dst)
    except Exception as e:
        print('[错误] %s' % e)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
