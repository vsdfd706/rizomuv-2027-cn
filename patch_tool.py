# -*- coding: utf-8 -*-
"""
RizomUV 2027 简体中文汉化工具
================================================================
一个文件，三种用法：
  1) 直接运行（双击 exe / python patch_tool.py）→ 图形界面，两个大按钮
  2) python patch_tool.py --install → 命令行一键汉化（供“一键汉化.bat”调用）
  3) python patch_tool.py --restore → 命令行一键还原

本工具不含、也不分发 RizomUV 程序本体；只对使用者自己持有的正版原版打补丁。
汉化逻辑完整复用 src/ 下经过实测的 13 个脚本，本文件只负责：
版本校验 → 备份 → 调用脚本 → 安装 → 建快捷方式 → 日志反馈。
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

# 补丁脚本通过 runpy 动态加载，PyInstaller 静态分析看不到它们内部的 import。
# 这里显式声明，强制把 json/re 打进 exe，否则运行到 build.py 会报 No module named 'json'。
import json as _json_for_packer
import re as _re_for_packer
_DYNAMIC_DEPS = (_json_for_packer, _re_for_packer)

# ---------------------------------------------------------------- 常量
EXPECTED_MD5 = '2ddf8d6da2000ae3eac66d7eea59a311'      # 原版 2027.0.598.g864535413
EXPECTED_OUTPUT_MD5 = '1a2c16e67fb3a1b595c0fa0622f1940a'  # 汉化版自检值
APP_TITLE = 'RizomUV 2027 简体中文汉化工具'

PF = os.environ.get('ProgramFiles') or r'C:\Program Files'
PF86 = os.environ.get('ProgramFiles(x86)') or r'C:\Program Files (x86)'
INSTALL_DIRS = [
    Path(PF) / 'Rizom Lab' / 'RizomUV 2027.0',
    Path(PF86) / 'Rizom Lab' / 'RizomUV 2027.0',
    Path(PF) / 'Rizom Lab' / 'RizomUV 2027',
]
EXE_NAME = 'rizomuv.exe'
BAK_NAME = 'rizomuv_en_backup.exe'

# 构建步骤：(脚本名, 传给 sys.argv 的参数列表) —— 与 build_all.py 完全同序
STEPS = [
    ('build.py',        ['dicts/tr_core.json,dicts/tr_phrase.json', 'build/rizomuv_ui_only.exe',
                         '--block', 'dicts/blocklist_ui_only.txt']),
    ('patch_menu.py',   ['build/rizomuv_menu_final.exe', 'dicts/menu_all.json']),
    ('patch_tooltip.py', []),
    ('patch_all.py',    ['build/rizomuv_panel_final.exe', 'dicts/batch_all.json']),
    ('patch_udim.py',   []),
    ('patch_redbox.py', []),
    ('patch_similar.py', []),
    ('patch_margin.py', []),
    ('patch_pack.py',   []),
    ('patch_unwrap.py', []),
    ('patch_tabs2.py',  []),
    ('patch_menu2.py',  []),
    ('patch_prefs.py',  []),
]
RES_FILES = ['force_patch.txt', 'prefs_backup.txt', 'shortbuf.txt']


# ---------------------------------------------------------------- 工具函数
def resource_dir() -> Path:
    """返回内嵌资源根目录（含 src/ dicts/ *.txt）。兼容 PyInstaller。"""
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

    # 本补丁仅适用 2027.0.598：把名字含 2027 的目录排到最前
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
        return True, '版本正确：RizomUV 2027.0.598（g864535413）'
    # 判断是否已经是汉化版
    tag = ''
    if actual == EXPECTED_OUTPUT_MD5:
        tag = '（这个文件看起来已经是汉化版了，不能用它再次构建）'
    return False, ('版本不匹配：需要 RizomUV 2027.0.598（g864535413）\n'
                   '  期望 MD5：%s\n'
                   '  你的文件：%s%s\n'
                   '  请改用正确的英文原版 rizomuv.exe。' % (EXPECTED_MD5, actual, tag))


# ---------------------------------------------------------------- 构建引擎
def build(original: Path, workdir: Path | None = None, emit=log) -> Path:
    """复用 src/ 脚本构建汉化版，返回 out/rizomuv_cn.exe 路径。"""
    res = resource_dir()
    workdir = Path(workdir or tempfile.mkdtemp(prefix='rizomcn_'))
    emit('工作目录：%s' % workdir)

    # 1) 搭建与 build_all.py 一致的目录结构
    (workdir / 'build').mkdir(parents=True, exist_ok=True)
    (workdir / 'out').mkdir(parents=True, exist_ok=True)
    for name in ['src', 'dicts']:
        src = res / name
        if not src.exists():
            raise RuntimeError('缺少资源目录：%s（exe 打包不完整？）' % src)
        shutil.copytree(src, workdir / name, dirs_exist_ok=True)
    for txt in RES_FILES:
        shutil.copyfile(res / txt, workdir / txt)
    shutil.copyfile(original, workdir / 'rizomuv.exe.bak')

    # 2) 按顺序执行 13 个原始脚本（进程内 runpy，避免 exe 递归启动）
    old_cwd, old_argv = os.getcwd(), sys.argv
    os.chdir(workdir)
    try:
        for i, (script, args) in enumerate(STEPS, 1):
            emit('[%02d/%02d] %s ...' % (i, len(STEPS), script))
            sys.argv = [script] + args
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                runpy.run_path(str(workdir / 'src' / script), run_name='__main__')
            detail = buf.getvalue().strip()
            if detail:
                emit('        ' + detail.splitlines()[0])
    except Exception as e:
        raise RuntimeError('构建失败于第 %d 步：%s\n%s' % (i, script, e)) from e
    finally:
        os.chdir(old_cwd)
        sys.argv = old_argv

    # 3) 收尾产出
    final = workdir / 'build' / 'rizomuv_prefs_final.exe'
    dest = workdir / 'out' / 'rizomuv_cn.exe'
    shutil.copyfile(final, dest)
    actual = md5(dest)
    emit('产出：%s' % dest)
    emit('MD5 ：%s' % actual)
    if actual == EXPECTED_OUTPUT_MD5:
        emit('自检通过 ✓ 与已验证的汉化版完全一致')
    else:
        emit('注意：MD5 与已知值不同，请留意功能验证。')
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
    import tkinter as tk
    from tkinter import filedialog, messagebox

    # ---- 配色 ----
    PRIMARY = '#2563EB'
    PRIMARY_DK = '#1D4ED8'
    OK = '#059669'
    BAD = '#DC2626'
    TEXT = '#1F2937'
    MUTED = '#6B7280'
    CARD = '#F8FAFC'
    BORDER = '#E2E8F0'
    FONT = 'Microsoft YaHei UI'

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry('700x560')
    root.resizable(False, False)
    root.configure(bg='#FFFFFF')

    q = queue.Queue()
    running = {'v': False}
    manual = {'p': None}
    state = {'dot': None}

    # ---- 顶部标题条 ----
    header = tk.Frame(root, bg=PRIMARY, height=78)
    header.pack(fill='x')
    header.pack_propagate(False)
    tk.Label(header, text='  RizomUV 2027  简体中文汉化', font=(FONT, 16, 'bold'),
             bg=PRIMARY, fg='white').pack(anchor='w', pady=(12, 0))
    tk.Label(header, text='  只汉化界面文字，不改动任何功能', font=(FONT, 10),
             bg=PRIMARY, fg='#DBEAFE').pack(anchor='w', pady=(2, 0))

    body = tk.Frame(root, bg='#FFFFFF', padx=20, pady=14)
    body.pack(fill='both', expand=True)

    # ---- 状态卡片 ----
    def card(parent):
        f = tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                     highlightthickness=1, padx=12, pady=9)
        f.pack(fill='x', pady=(0, 8))
        dot = tk.Label(f, text='●', font=(FONT, 13), bg=CARD, fg=MUTED)
        dot.pack(side='left', padx=(0, 8))
        lbl = tk.Label(f, text='检测中…', font=(FONT, 10), bg=CARD, fg=TEXT,
                       justify='left', anchor='w', wraplength=610)
        lbl.pack(side='left', fill='x')
        return dot, lbl

    dot_p, lbl_p = card(body)
    dot_d, lbl_d = card(body)

    def set_cards(p, dirs, target):
        if p:
            lbl_p.configure(text='英文原版：%s' % p, fg=TEXT)
            dot_p.configure(fg=OK)
        else:
            cands = original_candidates()
            tip = '英文原版：未找到（需 2027.0.598）'
            if cands:
                tip += ' · 检测到但版本不符：' + '、'.join(c.name for c in cands[:3])
            lbl_p.configure(text=tip, fg=BAD)
            dot_p.configure(fg=BAD)
        if dirs:
            extra = '（发现 %d 处，可切换）' % len(dirs) if len(dirs) > 1 else ''
            lbl_d.configure(text='安装目录：%s %s' % (target, extra), fg=TEXT)
            dot_d.configure(fg=OK)
        else:
            lbl_d.configure(text='安装目录：未找到：%s（请“更换安装目录”）' % target, fg=BAD)
            dot_d.configure(fg=BAD)

    def refresh_info(emit=None):
        p = manual['p'] or find_original()
        dirs = _dirs_with_rizomuv()
        target = install_dir()
        if emit:
            emit(('__INFO__', p, dirs, target))
        else:
            set_cards(p, dirs, target)

    # ---- 工具按钮行 ----
    tools = tk.Frame(body, bg='#FFFFFF')
    tools.pack(fill='x', pady=(2, 10))

    def ghost(parent, text, cmd):
        return tk.Button(parent, text=text, font=(FONT, 10), command=cmd,
                         bg='#FFFFFF', fg=PRIMARY, bd=1,
                         highlightbackground=BORDER, highlightthickness=1,
                         relief='flat', padx=10, pady=4, cursor='hand2')

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
            messagebox.showerror('不是安装目录', '这个文件夹里没有 rizomuv.exe。\n请选择包含 rizomuv.exe 的目录。')
            return
        set_install_dir(dp)
        refresh_info()

    btn_pick = ghost(tools, '选择原版文件', pick)
    btn_pick.pack(side='left', padx=(0, 8))
    btn_dir = ghost(tools, '更换安装目录', pick_dir)
    btn_dir.pack(side='left')

    # ---- 日志区 ----
    tk.Label(body, text='操作日志', font=(FONT, 10, 'bold'), bg='#FFFFFF',
             fg=MUTED).pack(anchor='w', pady=(0, 4))
    logwrap = tk.Frame(body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    logwrap.pack(fill='both', expand=True)
    logbox = tk.Text(logwrap, height=11, font=('Consolas', 9), wrap='none',
                     bg=CARD, fg=TEXT, relief='flat', bd=0, padx=8, pady=6)
    logbox.pack(side='left', fill='both', expand=True)
    scroll = tk.Scrollbar(logwrap, command=logbox.yview)
    scroll.pack(side='right', fill='y')
    logbox.configure(yscrollcommand=scroll.set)

    # ---- 主操作按钮 ----
    actions = tk.Frame(body, bg='#FFFFFF')
    actions.pack(fill='x', pady=(12, 0))

    def finish_work():
        running['v'] = False
        for b in (btn_han, btn_res, btn_pick, btn_dir):
            b.configure(state='normal')

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
                elif item == '__DONE__':
                    finish_work()
                else:
                    logbox.insert('end', str(item) + '\n')
                    logbox.see('end')
        except queue.Empty:
            pass
        root.after(100, pump)

    def runner(task):
        running['v'] = True
        for b in (btn_han, btn_res, btn_pick, btn_dir):
            b.configure(state='disabled')
        logbox.delete('1.0', 'end')

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
                emit('❌ 失败：%s' % e)
            finally:
                q.put('__DONE__')

        threading.Thread(target=work, daemon=True).start()

    def task_han(emit, ask):
        emit('正在检测英文原版（读取校验，约几秒）…')
        p = manual['p'] or find_original()
        ok, msg = check_version(p)
        emit(msg)
        if not ok:
            emit('已停止。请检查版本，或点“选择原版文件”。')
            return
        target = install_dir()
        if not (target / EXE_NAME).exists():
            emit('找不到安装目录：%s' % target)
            emit('请点“更换安装目录”选择正确文件夹。')
            return
        if not ask('即将把简体中文版安装到：\n%s\n\n确认 RizomUV 已关闭？' % target):
            emit('已取消。')
            return
        do_install(p, emit=emit)

    def task_res(emit, ask):
        target = install_dir()
        if not (target / EXE_NAME).exists():
            emit('找不到安装目录：%s' % target)
            emit('请点“更换安装目录”。')
            return
        if not ask('即将把 RizomUV 恢复为英文原版：\n%s\n\n继续？' % target):
            emit('已取消。')
            return
        do_restore(emit=emit)

    btn_han = tk.Button(actions, text='一键汉化', font=(FONT, 11, 'bold'),
                        bg=PRIMARY, fg='white', bd=0, width=15, pady=7,
                        activebackground=PRIMARY_DK, activeforeground='white',
                        cursor='hand2', command=lambda: runner(task_han))
    btn_han.pack(side='left', padx=(0, 12))
    btn_res = tk.Button(actions, text='一键还原', font=(FONT, 11),
                        bg='#FFFFFF', fg=TEXT, bd=1, width=15, pady=7,
                        highlightbackground=BORDER, highlightthickness=1,
                        relief='flat', cursor='hand2', command=lambda: runner(task_res))
    btn_res.pack(side='left')

    threading.Thread(target=lambda: refresh_info(q.put), daemon=True).start()
    root.after(100, pump)
    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) > 1 and (sys.argv[1] in ('--install', '--restore') or '--selftest' in sys.argv):
        sys.exit(cli())
    gui()
