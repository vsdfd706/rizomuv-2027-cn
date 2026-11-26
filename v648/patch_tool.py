# -*- coding: utf-8 -*-
"""
新版本 RizomUV 2027.0.648 Win 简体中文汉化工具
================================================================
一个文件，三种用法：
  1) 直接运行（双击 exe / python patch_tool.py）→ 图形界面，两个大按钮
  2) python patch_tool.py --install → 命令行一键汉化（供“一键汉化.bat”调用）
  3) python patch_tool.py --restore → 命令行一键还原

本工具不含、也不分发 RizomUV 程序本体；只对使用者自己持有的正版原版打补丁。
汉化逻辑完整复用同目录 build.py（4 批补丁合一，已验证可重建最终版），
本文件只负责：版本校验 → 备份 → 调用构建 → 安装 → 建快捷方式 → 日志反馈。
"""
import contextlib
import hashlib
import io
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import runpy
from pathlib import Path

# build.py 通过 importlib 动态加载，PyInstaller 静态分析看不到它内部的 import。
# 这里显式声明，强制把 json/re 打进 exe，否则运行到 build.py 会报 No module named 'json'。
import json as _json_for_packer
import re as _re_for_packer
_DYNAMIC_DEPS = (_json_for_packer, _re_for_packer)

# ---------------------------------------------------------------- 常量
EXPECTED_MD5 = 'abbc69339a373f08cbc3507111d97fbf'      # 新版本英文原版 RizomUV 2027.0.648 Win
EXPECTED_OUTPUT_MD5 = 'dbcc0c422c914a261b83201003f74b39'  # 最终汉化版自检值（含网格面板 4 + 视口显示标签 4 + 全量悬停说明 841 条）
APP_TITLE = 'RizomUV 2027.0.648 简体中文汉化工具'

PF = os.environ.get('ProgramFiles') or r'C:\Program Files'
PF86 = os.environ.get('ProgramFiles(x86)') or r'C:\Program Files (x86)'
INSTALL_DIRS = [
    Path(PF) / 'Rizom Lab' / 'RizomUV 2027.0',
    Path(PF86) / 'Rizom Lab' / 'RizomUV 2027.0',
    Path(PF) / 'Rizom Lab' / 'RizomUV 2027',
]
EXE_NAME = 'rizomuv.exe'
BAK_NAME = 'rizomuv_en_backup.exe'

# 新版本只需 build.py（4 批补丁合一）及其词典/黑名单资源
RES_FILES = ['verified_dict.json']
RES_DIRS = ['dicts']


# ---------------------------------------------------------------- 工具函数
def resource_dir() -> Path:
    """返回内嵌资源根目录（含 build.py / verified_dict.json / dicts/）。兼容 PyInstaller。"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def log(msg=''):
    print(msg, flush=True)


# 运行时可被用户/GUI 覆盖的安装目录
INSTALL_DIR_OVERRIDE: Path | None = None


def set_install_dir(path: Path | None):
    global INSTALL_DIR_OVERRIDE
    INSTALL_DIR_OVERRIDE = Path(path) if path else None


def _dirs_with_rizomuv() -> list:
    """多途径探测可能装着 RizomUV 的目录（按可信度排序，去重）。"""
    found = []

    def add(p):
        if p and p.exists() and (p / EXE_NAME).exists():
            k = str(p).lower()
            if k not in seen:
                seen.add(k)
                found.append(p)

    seen = set()

    # 1) 用户手动指定（最高优先级）
    if INSTALL_DIR_OVERRIDE:
        add(INSTALL_DIR_OVERRIDE)

    # 2) Windows 卸载注册表（最可靠，能找到自定义安装路径）
    try:
        import winreg
        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
        ]
        for hive, base in roots:
            try:
                key = winreg.OpenKey(hive, base)
            except OSError:
                continue
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(key, i)
                except OSError:
                    break
                i += 1
                try:
                    sk = winreg.OpenKey(key, sub)
                    display, _ = winreg.QueryValueEx(sk, 'DisplayName')
                    if display and 'rizomuv' in str(display).lower():
                        for val in ('InstallLocation', 'DisplayIcon'):
                            try:
                                raw, _ = winreg.QueryValueEx(sk, val)
                                if raw:
                                    p = Path(str(raw).strip('"'))
                                    add(p if p.is_dir() else p.parent)
                            except OSError:
                                pass
                    winreg.CloseKey(sk)
                except OSError:
                    pass
            winreg.CloseKey(key)
    except Exception:
        pass

    # 3) 常见固定路径 + 各盘符下的常见位置
    candidates = list(INSTALL_DIRS)
    drives = []
    try:
        import string
        for letter in string.ascii_uppercase:
            d = Path(f'{letter}:\\')
            if d.exists():
                drives.append(d)
    except Exception:
        pass
    for dr in drives:
        candidates += [
            dr / 'Rizom Lab' / 'RizomUV 2027.0',
            dr / 'Program Files' / 'Rizom Lab' / 'RizomUV 2027.0',
            dr / 'Program Files (x86)' / 'Rizom Lab' / 'RizomUV 2027.0',
        ]
    for p in candidates:
        add(p)

    # 4) 用户目录、桌面、下载里的 rizomuv.exe（便携版 / 绿色版）
    for env in ('USERPROFILE', 'PUBLIC', 'OneDrive'):
        base = os.environ.get(env)
        if base:
            for sub in ('Desktop', 'Downloads', 'Documents', 'Rizom Lab', 'RizomUV 2027.0'):
                add(Path(base) / sub)

    # 本补丁仅适用新版本 2027.0.648 Win：把名字含 2027 的目录排到最前
    found.sort(key=lambda p: 0 if '2027' in str(p) else 1)
    return found


def install_dir() -> Path:
    dirs = _dirs_with_rizomuv()
    if dirs:
        return dirs[0]
    # 没探测到，返回默认路径（install() 会给出明确错误）
    return INSTALL_DIR_OVERRIDE or INSTALL_DIRS[0]


def original_candidates() -> list:
    """收集可能的英文原版 exe 路径（按优先级）。"""
    out = []
    # 覆盖所有探测到的安装目录，而不只是第一个
    for d in _dirs_with_rizomuv():
        out += [d / BAK_NAME, d / EXE_NAME]
    here = resource_dir()
    out += [here / 'rizomuv.exe.bak', here / EXE_NAME]
    for line in ['C:\\Users\\Public\\Downloads\\rizomuv.exe']:
        out.append(Path(line))
    # 去重、只保留存在的文件
    seen, uniq = set(), []
    for p in out:
        k = str(p).lower()
        if k not in seen and p.exists():
            seen.add(k)
            uniq.append(p)
    return uniq


def find_original() -> Path | None:
    """自动寻找 MD5 精确匹配的英文原版。"""
    for p in original_candidates():
        try:
            if md5(p) == EXPECTED_MD5:
                return p
        except OSError:
            pass
    return None


def check_version(exe: Path):
    """返回 (是否匹配, 说明文字)。绝不抛异常给上层。"""
    if not exe or not exe.exists():
        return False, '找不到文件：%s' % exe
    actual = md5(exe)
    if actual == EXPECTED_MD5:
        return True, '版本正确：新版本 RizomUV 2027.0.648 Win'
    # 判断是否已经是汉化版
    tag = ''
    if actual == EXPECTED_OUTPUT_MD5:
        tag = '（这个文件看起来已经是汉化版了，不能用它再次构建）'
    return False, ('版本不匹配：需要新版本 RizomUV 2027.0.648 Win 的英文原版\n'
                   '  期望 MD5：%s\n'
                   '  你的文件：%s%s\n'
                   '  请改用正确的英文原版 rizomuv.exe；若你装的是 2027.0.598，请用老版本工具。' % (EXPECTED_MD5, actual, tag))


# ---------------------------------------------------------------- 构建引擎
def build(original: Path, workdir: Path | None = None, emit=log) -> Path:
    """调用同目录 build.py 从英文原版构建最终汉化版，返回产物路径。"""
    res = resource_dir()
    build_py = res / 'build.py'
    if not build_py.exists():
        raise RuntimeError('缺少构建脚本：%s（exe 打包不完整？）' % build_py)
    workdir = Path(workdir or tempfile.mkdtemp(prefix='rizom648_'))
    dest = workdir / 'rizomuv_cn_648.exe'

    # 进程内导入 build.py 并调用其构建函数（避免 exe 递归启动子进程）
    import importlib.util
    spec = importlib.util.spec_from_file_location('_rizom648_build', build_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # build.py 的资源路径基于 __file__，打包环境下需指向解包目录
    mod.HERE = res
    mod.DICT = res / 'verified_dict.json'
    mod.BLOCK = res / 'dicts' / 'blocklist_ui_only.txt'
    if not mod.DICT.exists() or not mod.BLOCK.exists():
        raise RuntimeError('缺少词表或黑名单（exe 打包不完整？）')

    mod.build(Path(original), dest, emit=emit)
    actual = md5(dest)
    if actual != EXPECTED_OUTPUT_MD5:
        raise RuntimeError('产出 MD5 与已知值不符（%s），已停止安装。' % actual)
    return dest


def is_admin() -> bool:
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def rizomuv_running() -> bool:
    """检测 RizomUV 是否在运行。只认真正的进程表行，避免错误文本误判。"""
    try:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq rizomuv.exe', '/NH'],
                           capture_output=True, text=True)
        for line in (r.stdout or '').splitlines():
            # 真正的进程行以 "rizomuv.exe" 开头；INFO/ERROR 行不会这样
            if line.strip().lower().startswith('rizomuv.exe'):
                return True
    except Exception:
        pass
    return False


def need_admin(target: Path) -> bool:
    """目标不可写时需要管理员权限。"""
    try:
        with open(target / '__wtest__.tmp', 'wb'):
            pass
        (target / '__wtest__.tmp').unlink()
        return False
    except OSError:
        return True


def install(cn_exe: Path, target_dir: Path, emit=log) -> Path:
    """备份原版 + 安装汉化版。返回目标 exe 路径。"""
    dst = target_dir / EXE_NAME
    bak = target_dir / BAK_NAME
    if not dst.exists():
        raise RuntimeError('找不到 RizomUV 安装目录：%s' % dst)

    # 关闭正在运行的 RizomUV
    if rizomuv_running():
        raise RuntimeError('RizomUV 仍在运行，请先关闭它再安装。')

    if not bak.exists():
        shutil.copyfile(dst, bak)
        emit('已备份英文原版 → %s' % bak)
    else:
        emit('英文原版备份已存在，跳过备份。')
    shutil.copyfile(cn_exe, dst)
    emit('已安装汉化版 → %s' % dst)
    return dst


def create_shortcut(target: Path, emit=log):
    """在桌面创建“RizomUV 2027 (中文)”快捷方式。"""
    try:
        desktop = Path(os.environ['USERPROFILE']) / 'Desktop'
        if not desktop.exists():
            desktop = Path(os.environ.get('PUBLIC', r'C:\Users\Public')) / 'Desktop'
        lnk = desktop / 'RizomUV 2027 (中文).lnk'
        ps = ('$w=New-Object -ComObject WScript.Shell; '
              '$s=$w.CreateShortcut("%s"); '
              '$s.TargetPath="%s"; '
              '$s.WorkingDirectory="%s"; '
              '$s.Save()' % (lnk, target, target.parent))
        subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, text=True, timeout=30)
        emit('已创建桌面快捷方式：%s' % lnk)
    except Exception as e:
        emit('快捷方式创建失败（不影响汉化）：%s' % e)


def restore(target_dir: Path, emit=log):
    """用备份还原英文原版。"""
    dst, bak = target_dir / EXE_NAME, target_dir / BAK_NAME
    if not bak.exists():
        raise RuntimeError('找不到英文原版备份：%s\n无法还原。' % bak)
    if rizomuv_running():
        raise RuntimeError('RizomUV 仍在运行，请先关闭它再还原。')
    shutil.copyfile(bak, dst)
    emit('已还原为英文原版 → %s' % dst)


# ---------------------------------------------------------------- 流程封装
def do_install(manual_original: Path | None = None, emit=log):
    emit('=== 一键汉化开始 ===')
    original = manual_original or find_original()
    ok, msg = check_version(original)
    emit(msg)
    if not ok:
        raise RuntimeError('版本校验未通过，已停止。' + ('\n' + msg if '\n' not in msg else ''))
    dirs = _dirs_with_rizomuv()
    if len(dirs) > 1:
        emit('检测到多个 RizomUV 安装目录，使用：%s' % dirs[0])
        for d in dirs[1:]:
            emit('       （另有：%s）' % d)
    target = install_dir()
    emit('安装目录：%s' % target)
    if need_admin(target) and not is_admin():
        raise RuntimeError('安装目录需要管理员权限，请以管理员身份运行本工具。')
    cn = build(original, emit=emit)
    dst = install(cn, target, emit=emit)
    create_shortcut(dst, emit=emit)
    emit('=== 全部完成：现在可以启动 RizomUV，界面已是简体中文 ===')


def do_restore(emit=log):
    emit('=== 一键还原开始 ===')
    target = install_dir()
    emit('安装目录：%s' % target)
    if need_admin(target) and not is_admin():
        raise RuntimeError('安装目录需要管理员权限，请以管理员身份运行本工具。')
    restore(target, emit=emit)
    emit('=== 完成：已恢复英文原版 ===')


# ---------------------------------------------------------------- 命令行入口
def cli():
    mode = '--install' if '--install' in sys.argv else ('--restore' if '--restore' in sys.argv else None)
    manual = None
    if '--exe' in sys.argv:
        p = sys.argv[sys.argv.index('--exe') + 1]
        manual = Path(p)
    if '--dir' in sys.argv:
        p = sys.argv[sys.argv.index('--dir') + 1]
        set_install_dir(Path(p))
    if '--selftest' in sys.argv:
        try:
            orig = manual or find_original()
            log('资源目录：%s' % resource_dir())
            ok, msg = check_version(orig)
            log(msg)
            if not ok:
                return 2
            out = build(orig, emit=log)
            good = md5(out) == EXPECTED_OUTPUT_MD5
            log('自检结果：%s' % ('通过 ✓' if good else '失败 ✗'))
            return 0 if good else 3
        except Exception as e:
            log('[错误] %s' % e)
            return 2
    if not mode:
        log(__doc__)
        return 0
    try:
        if mode == '--install':
            do_install(manual)
        else:
            do_restore()
    except Exception as e:
        log('\n[错误] %s' % e)
        log('处理失败，未做任何更改。')
        return 2
    return 0


# ---------------------------------------------------------------- 图形界面
def gui():
    """现代简洁的图形界面 —— Premium Minimal / 浅色中性。

    底层流程（探测 / 校验 / 构建 / 安装 / 还原 / 询问）保持不变，
    本函数只负责视觉呈现、布局与交互反馈。
    """
    import tkinter as tk
    from tkinter import filedialog, messagebox
    import ui_theme as T

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry('%dx%d' % (T.WIN_W, T.WIN_H))
    root.minsize(T.MIN_W, T.MIN_H)
    root.configure(bg=T.SURFACE)

    # 高 DPI awareness（Windows）：让字体在缩放屏上更清晰
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    F = T.FONT_UI
    MONO = T.FONT_MONO

    q = queue.Queue()
    running = {'v': False}
    manual = {'p': None}

    # ------------------------------------------------------------------
    # 根布局：品牌区 / 主体 / 底部操作区，主体用 grid 权重实现响应式
    # ------------------------------------------------------------------
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=1)  # 主体（row 2）随窗口高度伸缩

    # ---- 品牌区（纯文字，无底板/无角标）----
    header = tk.Frame(root, bg=T.SURFACE)
    header.grid(row=0, column=0, sticky='ew')
    header.columnconfigure(1, weight=1)
    head_inner = tk.Frame(header, bg=T.SURFACE)
    head_inner.grid(row=0, column=0, sticky='w', padx=T.PAD_X, pady=(T.SP['lg'], T.SP['md']))
    head_inner.columnconfigure(1, weight=1)

    tk.Label(head_inner, text='RizomUV 汉化', font=(F, T.FS['brand'], 'bold'),
             bg=T.SURFACE, fg=T.TEXT).grid(row=0, column=0, sticky='w')
    # 版本标签：纯文字，无彩色底板
    tk.Label(head_inner, text='2027.0.648 · 新版本', font=(F, T.FS['subtitle']),
             bg=T.SURFACE, fg=T.TEXT_DIM).grid(row=0, column=1, sticky='w', padx=(T.SP['sm'], 0))
    tk.Label(head_inner, text='只汉化界面文字，不改动任何功能',
             font=(F, T.FS['body']), bg=T.SURFACE, fg=T.TEXT_2).grid(
                 row=1, column=0, columnspan=2, sticky='w', pady=(T.SP['xs'], 0))

    # 一条极淡分隔（唯一的结构线，用于区分品牌与内容）
    sep = tk.Frame(root, bg=T.BORDER, height=1)
    sep.grid(row=1, column=0, sticky='ew')

    # ---- 主体 ----
    body = tk.Frame(root, bg=T.SURFACE)
    body.grid(row=2, column=0, sticky='nsew')
    body.columnconfigure(0, weight=1)
    body.rowconfigure(5, weight=1)  # 日志区（row 5）占据剩余空间
    bpad = {'padx': T.PAD_X}

    def section_label(parent, text, row):
        return tk.Label(parent, text=text, font=(F, T.FS['section'], 'bold'),
                        bg=T.SURFACE, fg=T.TEXT_DIM).grid(
                            row=row, column=0, sticky='w', padx=T.PAD_X, pady=(T.SP['md'], T.SP['sm']))

    # 分区标题：环境检测
    section_label(body, '环境检测', 0)

    # 状态行组件（无卡片底板：圆点 + 文字，靠留白分组）
    def status_row(parent, row):
        f = tk.Frame(parent, bg=T.SURFACE)
        f.grid(row=row, column=0, sticky='ew', padx=T.PAD_X, pady=(0, T.SP['sm']))
        f.columnconfigure(1, weight=1)
        dot = tk.Label(f, text='●', font=(F, 12), bg=T.SURFACE, fg=T.TEXT_DIM,
                       width=2, anchor='center')
        dot.grid(row=0, column=0, sticky='w')
        lbl = tk.Label(f, text='检测中…', font=(F, T.FS['status']), bg=T.SURFACE,
                       fg=T.TEXT_2, justify='left', anchor='w', wraplength=620)
        lbl.grid(row=0, column=1, sticky='ew')
        return dot, lbl

    dot_p, lbl_p = status_row(body, 1)
    dot_d, lbl_d = status_row(body, 2)

    # 工具按钮行：轻量幽灵按钮（默认透明底 + 细描边，hover 淡底）
    tools = tk.Frame(body, bg=T.SURFACE)
    tools.grid(row=3, column=0, sticky='w', padx=T.PAD_X, pady=(T.SP['xs'], T.SP['sm']))

    def ghost(parent, text, cmd):
        b = tk.Button(parent, text=text, font=(F, T.FS['body']), command=cmd,
                      bg=T.BTN_BG, fg=T.ACCENT, bd=1,
                      highlightbackground=T.BORDER, highlightthickness=1,
                      relief='flat', padx=T.TOOL_BTN_PADX, pady=T.TOOL_BTN_PADY,
                      cursor='hand2', activebackground=T.BTN_BG_HOVER,
                      activeforeground=T.ACCENT_HOVER)
        b.bind('<Enter>', lambda e, w=b: w.configure(bg=T.BTN_BG_HOVER))
        b.bind('<Leave>', lambda e, w=b: w.configure(bg=T.BTN_BG))
        return b

    def pick():
        f = filedialog.askopenfilename(title='选择英文原版 rizomuv.exe',
                                       filetypes=[('RizomUV 程序', '*.exe'), ('所有文件', '*.*')])
        if not f:
            return
        p = Path(f)
        ok, msg = check_version(p)
        if not ok:
            messagebox.showerror('版本不匹配', msg)
            return
        manual['p'] = p
        refresh_info()

    def pick_dir():
        d = filedialog.askdirectory(title='选择 RizomUV 安装目录（含 rizomuv.exe 的文件夹）')
        if not d:
            return
        dp = Path(d)
        if not (dp / EXE_NAME).exists():
            messagebox.showerror('不是安装目录',
                                 '这个文件夹里没有 rizomuv.exe。\n请选择包含 rizomuv.exe 的目录。')
            return
        set_install_dir(dp)
        refresh_info()

    # 让 body 的行号留给日志：工具行放在第 3 行，日志放第 4 行
    btn_pick = ghost(tools, '选择原版文件', pick)
    btn_pick.pack(side='left', padx=(0, T.SP['sm']))
    btn_dir = ghost(tools, '更换安装目录', pick_dir)
    btn_dir.pack(side='left')

    def set_cards(p, dirs, target, busy=False):
        if busy:
            dot_p.configure(fg=T.TEXT_DIM)
            lbl_p.configure(text='正在工作，请稍候…', fg=T.TEXT_2)
            dot_d.configure(fg=T.TEXT_DIM)
            lbl_d.configure(text='安装目录：%s' % target, fg=T.TEXT_2)
            return
        if p:
            lbl_p.configure(text='英文原版：%s' % p, fg=T.TEXT)
            dot_p.configure(fg=T.OK)
        else:
            cands = original_candidates()
            tip = '英文原版：未找到（需新版本 2027.0.648 Win）'
            if cands:
                tip += ' · 检测到但版本不符：' + '、'.join(c.name for c in cands[:3])
            lbl_p.configure(text=tip, fg=T.ERROR)
            dot_p.configure(fg=T.ERROR)
        if dirs:
            extra = '（发现 %d 处，可切换）' % len(dirs) if len(dirs) > 1 else ''
            lbl_d.configure(text='安装目录：%s %s' % (target, extra), fg=T.TEXT)
            dot_d.configure(fg=T.OK)
        else:
            lbl_d.configure(text='安装目录：未找到：%s（请“更换安装目录”）' % target, fg=T.ERROR)
            dot_d.configure(fg=T.ERROR)

    def refresh_info(emit=None):
        p = manual['p'] or find_original()
        dirs = _dirs_with_rizomuv()
        target = install_dir()
        if emit:
            emit(('__INFO__', p, dirs, target))
        else:
            set_cards(p, dirs, target)

    # ---- 日志区（抬升面 + 极淡描边，随窗口伸缩）----
    tk.Label(body, text='操作日志', font=(F, T.FS['section'], 'bold'),
             bg=T.SURFACE, fg=T.TEXT_DIM).grid(
                 row=4, column=0, sticky='w', padx=T.PAD_X, pady=(T.SP['md'], T.SP['sm']))
    logwrap = tk.Frame(body, bg=T.SURFACE_ALT, highlightbackground=T.BORDER,
                       highlightthickness=1)
    logwrap.grid(row=5, column=0, sticky='nsew', padx=T.PAD_X, pady=(0, T.SP['md']))
    logwrap.columnconfigure(0, weight=1)
    logwrap.rowconfigure(0, weight=1)
    logbox = tk.Text(logwrap, height=1, font=(MONO, T.FS['log']), wrap='none',
                     bg=T.SURFACE_ALT, fg=T.TEXT_2, relief='flat', bd=0,
                     padx=12, pady=10, insertbackground=T.ACCENT)
    logbox.grid(row=0, column=0, sticky='nsew')
    scroll = tk.Scrollbar(logwrap, command=logbox.yview)
    scroll.grid(row=0, column=1, sticky='ns')
    logbox.configure(yscrollcommand=scroll.set)

    # ---- 底部操作区（主按钮 + 状态提示）----
    actions = tk.Frame(body, bg=T.SURFACE)
    actions.grid(row=6, column=0, sticky='ew', padx=T.PAD_X, pady=(T.SP['sm'], T.PAD_X))
    actions.columnconfigure(2, weight=1)

    hint = tk.Label(actions, text='', font=(F, T.FS['caption'] if 'caption' in T.FS else T.FS['subtitle']),
                    bg=T.SURFACE, fg=T.TEXT_DIM, anchor='w')

    def set_hint(text, color=None):
        hint.configure(text=text, fg=color or T.TEXT_DIM)

    def primary_button(parent, text, cmd):
        b = tk.Button(parent, text=text, font=(F, T.FS['button'], 'bold'), command=cmd,
                      bg=T.ACCENT, fg='#FFFFFF', bd=0, width=14,
                      activebackground=T.ACCENT_HOVER, activeforeground='#FFFFFF',
                      cursor='hand2', relief='flat', pady=10,
                      highlightbackground=T.ACCENT, highlightthickness=1)
        b.bind('<Enter>', lambda e, w=b: w.configure(bg=T.ACCENT_HOVER) if str(w['state']) == 'normal' else None)
        b.bind('<Leave>', lambda e, w=b: w.configure(bg=T.ACCENT) if str(w['state']) == 'normal' else None)
        return b

    def ghost_button(parent, text, cmd):
        b = tk.Button(parent, text=text, font=(F, T.FS['button']), command=cmd,
                      bg=T.BTN_BG, fg=T.TEXT_2, bd=1, width=14,
                      highlightbackground=T.BORDER, highlightthickness=1,
                      relief='flat', cursor='hand2', pady=10,
                      activebackground=T.BTN_BG_HOVER, activeforeground=T.TEXT)
        b.bind('<Enter>', lambda e, w=b: w.configure(bg=T.BTN_BG_HOVER) if str(w['state']) == 'normal' else None)
        b.bind('<Leave>', lambda e, w=b: w.configure(bg=T.BTN_BG) if str(w['state']) == 'normal' else None)
        return b

    def finish_work():
        running['v'] = False
        for b in (btn_han, btn_res, btn_pick, btn_dir):
            b.configure(state='normal')
        refresh_info()

    def pump():
        try:
            while True:
                item = q.get_nowait()
                if isinstance(item, tuple) and item and item[0] == '__ASK__':
                    _, question, resp_q = item
                    root.attributes('-topmost', True)
                    ans = messagebox.askyesno('确认', question)
                    root.attributes('-topmost', False)
                    resp_q.put(ans)
                elif isinstance(item, tuple) and item and item[0] == '__INFO__':
                    _, p, dirs, target = item
                    set_cards(p, dirs, target)
                elif isinstance(item, tuple) and item and item[0] == '__HINT__':
                    _, text, color = item
                    set_hint(text, color)
                elif item == '__DONE__':
                    finish_work()
                else:
                    logbox.insert('end', str(item) + '\n')
                    logbox.see('end')
        except queue.Empty:
            pass
        root.after(100, pump)

    def runner(task, label):
        running['v'] = True
        for b in (btn_han, btn_res, btn_pick, btn_dir):
            b.configure(state='disabled')
        logbox.delete('1.0', 'end')
        set_hint(label + ' 进行中…', T.INFO if hasattr(T, 'INFO') else T.TEXT_2)
        set_cards(None, [], install_dir(), busy=True)

        def emit(msg):
            q.put(msg)

        def ask(question):
            resp_q = queue.Queue()
            q.put(('__ASK__', question, resp_q))
            return resp_q.get()

        def work():
            try:
                task(emit, ask)
            except Exception as e:
                emit('')
                emit('失败：%s' % e)
            finally:
                q.put('__DONE__')

        threading.Thread(target=work, daemon=True).start()

    def task_han(emit, _ask):
        emit('正在检测英文原版（读取校验，约几秒）…')
        p = manual['p'] or find_original()
        ok, msg = check_version(p)
        emit(msg)
        if not ok:
            emit('已停止。请检查版本，或点“选择原版文件”。')
            q.put(('__HINT__', '版本校验未通过', T.ERROR))
            return
        target = install_dir()
        if not (target / EXE_NAME).exists():
            emit('找不到安装目录：%s' % target)
            emit('请点“更换安装目录”选择正确文件夹。')
            q.put(('__HINT__', '未找到安装目录', T.ERROR))
            return
        if not _ask('即将把简体中文版安装到：\n%s\n\n请确认 RizomUV 已完全关闭。' % target):
            emit('已取消。')
            return
        emit('开始安装（自动备份原版）…')
        do_install(p, emit=emit)
        q.put(('__HINT__', '完成 · 现在可以启动 RizomUV', T.OK))

    def task_res(emit, _ask):
        target = install_dir()
        if not (target / EXE_NAME).exists():
            emit('找不到安装目录：%s' % target)
            emit('请点“更换安装目录”。')
            q.put(('__HINT__', '未找到安装目录', T.ERROR))
            return
        if not _ask('即将把 RizomUV 恢复为英文原版：\n%s\n\n继续？' % target):
            emit('已取消。')
            return
        do_restore(emit=emit)
        q.put(('__HINT__', '完成 · 已恢复英文原版', T.OK))

    btn_han = primary_button(actions, '一键汉化', lambda: runner(task_han, '汉化'))
    btn_han.grid(row=0, column=0, sticky='w')
    btn_res = ghost_button(actions, '一键还原', lambda: runner(task_res, '还原'))
    btn_res.grid(row=0, column=1, sticky='w', padx=(T.SP['sm'], 0))
    hint.grid(row=0, column=2, sticky='e')
    actions.columnconfigure(2, weight=1)

    # ---- 快捷键（可访问性）----
    root.bind('<Control-h>', lambda e: runner(task_han, '汉化') if not running['v'] else None)
    root.bind('<Control-r>', lambda e: runner(task_res, '还原') if not running['v'] else None)
    # Tab 顺序：选择原版 -> 更换目录 -> 一键汉化 -> 一键还原
    btn_pick.lift()
    set_hint('提示：Ctrl+H 汉化 · Ctrl+R 还原')

    threading.Thread(target=lambda: refresh_info(q.put), daemon=True).start()
    root.after(100, pump)
    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) > 1 and (sys.argv[1] in ('--install', '--restore') or '--selftest' in sys.argv):
        sys.exit(cli())
    gui()
