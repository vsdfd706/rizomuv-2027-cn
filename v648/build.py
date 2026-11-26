# -*- coding: utf-8 -*-
"""新版本 RizomUV 2027.0.648 Win —— 一键汉化构建引擎。

从使用者自己持有的英文原版 rizomuv.exe 出发，在内存中依次应用
已验证安全的界面补丁（主迁移 621 词 + 工具栏 7 + 面板 8 + 菜单 6
+ 网格面板 4 + 视口显示标签 4 + 控件悬停说明 841 条），产出纯界面汉化版。
长篇中文说明在标点后插入 ASCII 空格作为断行点：说明框靠空格换行，中文整串
无空格会单行溢出遮挡文字；163 条长段落已加断点，678 条短句保持原样。
只改 UI 字符串区，不动任何程序逻辑。

本文件是 history/ 下 4 个分批脚本的合一重写版，MD5 逐级校验完全一致：
    abbc6933(英文) -> cf53e149 -> 8018ad29 -> 651a25b1 -> ef85533b
    -> e03fd1a2(网格面板 4) -> f0bcc86d(视口显示标签 4)
    -> dbcc0c42(全量悬停说明 841 条，最终）

注意：网格面板的分组标题 "Grid" 属于内部注册名（与 Factory/Selection/
Pixel/Tile/Group/BBox 同组，且已在黑名单中），刻意保留英文，避免触发
`variable is not found` 一类的内部寻址错误。

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
TIPS = HERE / 'dicts' / 'tooltips_zh.json'

# 逐级期望 MD5（英文原版 -> 4 批之后）
MD5_EN = 'abbc69339a373f08cbc3507111d97fbf'
MD5_STAGE = [
    'cf53e1496873dffba10983d180a0cdcf',  # 主迁移 621 词
    '8018ad29b03772d8b51f8c676220e334',  # 工具栏 7 标题
    '651a25b166ab27091f6dcc0695756529',  # 面板 8 标签
    'ef85533b797c7fc841e9c26bd676efae',  # 菜单 6 标签
    'e03fd1a234b6788e54d325d7f2063485',  # 网格面板 4 标签
    'f0bcc86da50a9b3e1e54bd135722cc48',  # 视口显示标签 4
    'dbcc0c422c914a261b83201003f74b39',  # 全量悬停说明 841 条（最终）
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
# 视口显示设置 → Grid 面板：4 个纯显示标签。
# 每个槽后面都跟着独立的 Prefs./Vars. 配置键与 ZOMID_*_UI 控件 ID，
# 程序不靠标签文本寻址，因此只改标签是安全的。
# "Show pixel grid" 槽仅 16 字节，装不下"显示像素网格"(19B)，
# 沿用词表既有译法 'pixel grid' -> '像素网格'。
PAIRS_GRID = [
    ('Show grid', '显示网格'),
    ('Divisions', '划分数'),
    ('Snap subdivisions', '吸附细分'),
    ('Show pixel grid', '像素网格'),
]
# 视口显示设置里的 4 个独立显示标签：全文件唯一、低指针密度、
# 后跟 Prefs./Vars. 键或 ZOMID_*_UI 控件 ID（程序不靠标签文本寻址）。
# 译文沿用 verified_dict.json 既有译法，保证术语统一。
PAIRS_VIEWPORT = [
    ('Lighting', '光照'),
    ('Pixels', '像素'),
    ('Subdiv.', '细分'),
    ('Browse...', '浏览...'),
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


def _stage_tooltips(data, emit):
    """第 7 批：写入控件悬停说明（鼠标停在按钮/设置项上弹出的解释）。

    这些槽在二进制里是标准的四元组：
        [悬停说明句] -> [快捷键] -> [显示标签] -> [ZOMID_*_UI 控件 ID]
    显示标签在前几批已汉化且一直正常工作，程序靠末尾的控件 ID 寻址，
    因此只改第一项说明文字不会影响任何功能。

    按「偏移」而不是按字符串查找来定位，避免误改同一英文句子的其他副本。
    沿用与前几批相同的安全规则：UI 区内、独立 NUL 边界槽、仍为纯 ASCII、
    零填充预算充足、指针密度 < 6。不满足的一律跳过，不报错中断。
    词表按「文件偏移」定位，共 841 条（含补上第 7 批漏提取的 0x6dca920）。
    显示宽度 > 80 的长段落在中文标点后插入 ASCII 空格作断行点，每段 <= 80，
    避免固定不滚动的说明框里中文单行溢出；短句不加空格。
    """
    gap_end, _, ptr_density = _helpers(data)
    tr = json.load(open(TIPS, encoding='utf-8'))
    applied = 0
    skipped = 0
    size = len(data)
    for key in sorted(tr, key=lambda k: int(k, 16)):
        off = int(key, 16)
        if not (UI_LO <= off < UI_HI):
            skipped += 1
            continue
        if data[off - 1] != 0:
            skipped += 1
            continue
        e = off
        while e < size and data[e] != 0:
            e += 1
        raw = bytes(data[off:e])
        # 允许 LF/CR/TAB：部分说明原文是多段文本（例如 0x6dca920 的
        # "选择相似"说明含 \n 分段），这些空白属于正文排版而非二进制数据，
        # 不能因此被当成非文本槽跳过。词表按偏移定位，只放行词表内的条目。
        if not all(32 <= c < 127 or c in (9, 10, 13) for c in raw):
            skipped += 1
            continue
        ge = gap_end(off)
        nb = tr[key].encode('utf-8')
        if len(nb) + 1 > ge - off:
            skipped += 1
            continue
        if ptr_density(off) >= 6:
            skipped += 1
            continue
        data[off:ge] = nb + b'\x00' * ((ge - off) - len(nb))
        applied += 1
    emit('  写入悬停说明：%d 条（按安全规则跳过 %d 条）' % (applied, skipped))
    return applied


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
        ('网格面板 4 标签', lambda d: _stage_pairs(d, PAIRS_GRID, emit, True), False),
        ('视口显示标签 4', lambda d: _stage_pairs(d, PAIRS_VIEWPORT, emit, True), False),
        ('控件悬停说明', lambda d: _stage_tooltips(d, emit), False),
    ]
    for i, (name, fn, _) in enumerate(stages):
        emit('[%d/%d] %s ...' % (i + 1, len(stages), name))
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
